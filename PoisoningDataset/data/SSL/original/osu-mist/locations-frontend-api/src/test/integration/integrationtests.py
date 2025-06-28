import json
import ssl
import sys
import unittest
from datetime import datetime
from random import randint

import geojson

from api_request import blank_result, \
                        check_ssl, \
                        get_buildings_with_services, \
                        id_request, \
                        not_found_request, \
                        query_request, \
                        response_time, \
                        results_with_links, \
                        unauth_request, \
                        get_weekly_menu
from configuration_load import get_access_token, \
                               get_single_resource_id, \
                               get_url


class gateway_tests(unittest.TestCase):
    def test_services(self):
        buildings = get_buildings_with_services(services_url, access_token)
        query_params = {'page[size]': 500}

        for building_id in buildings:
            # Test that a building's service links back to the same building
            building_object = id_request(locations_url, access_token,
                                         building_id)
            for service in building_object['data']['relationships'][
                    'services']['data']:
                service_object = id_request(services_url, access_token,
                                            service['id'])
                parent_id = service_object['data']['relationships'][
                    'locations']['data'][0]['id']

                self.assertEqual(building_id, str(parent_id))

            # Test that the relationships object and the services endpoint
            # have the same number of services
            request_url = locations_url + "/" + building_id + "/services"
            building_services = query_request(request_url, access_token, "get",
                                              query_params).json()
            self.assertEqual(
                len(building_object['data']['relationships']['services'][
                    'data']), len(building_services['data']))

    # Tests a single resource ID in different case styles
    def test_id(self):
        response = id_request(locations_url, access_token, single_resourse_id)
        self.assertIsNotNone(response["data"])
        self.assertEqual(response["data"]["id"], single_resourse_id)

        response = id_request(locations_url, access_token,
                              single_resourse_id.upper())
        self.assertIsNotNone(response["data"])

        response = id_request(locations_url, access_token,
                              single_resourse_id.lower())
        self.assertIsNotNone(response["data"])

    # Tests that different verbs return expected responses
    def test_verbs(self):
        query_params = {'q': 'Oxford'}

        self.assertEqual(
            query_request(locations_url, access_token, "get",
                          query_params).status_code, 200)

        # DW not returning allowed methods headers,
        # Apigee returning bad gateway
        if query_request(locations_url, access_token, "post",
                         query_params).status_code == 502:
            self.skipTest("""DW not returning allowed methods headers
                   that Apigee is expecting""")

        self.assertEqual(
            query_request(locations_url, access_token, "post",
                          query_params).status_code, 405)
        self.assertEqual(
            query_request(locations_url, access_token, "put",
                          query_params).status_code, 405)
        self.assertEqual(
            query_request(locations_url, access_token, "delete",
                          query_params).status_code, 405)

    # Tests that certain parameters return expected number of results
    def test_results(self):
        all_dixon = query_request(locations_url, access_token, "get", {
            'q': 'Dixon'
        }).json()
        self.assertEqual(len(all_dixon['data']), 4)

        dining_dixon = query_request(locations_url, access_token, "get", {
            'q': 'Dixon',
            'type': 'dining'
        }).json()
        self.assertEqual(len(dining_dixon['data']), 1)

        building_dixon = query_request(locations_url, access_token, "get", {
            'q': 'Dixon',
            'type': 'building'
        }).json()
        self.assertEqual(len(building_dixon['data']), 2)

        # test search only from name + abbr
        building_library = query_request(locations_url, access_token, "get", {
            'q': 'library',
            'campus': 'corvallis',
            'type': 'building'
        }).json()
        self.assertEqual(len(building_library['data']), 1)

        building_library = query_request(locations_url, access_token, "get", {
            'q': 'vlib'
        }).json()
        self.assertEqual(len(building_library['data']), 1)

        # test filter
        dining_library = query_request(locations_url, access_token, "get", {
            'q': 'library',
            'type': 'dining'
        }).json()
        self.assertEqual(len(dining_library['data']), 0)

        building_engineering = query_request(locations_url, access_token,
                                             "get", {
                                                 'q': 'engineering',
                                                 'type': 'building',
                                                 'campus': 'corvallis'
                                             }).json()
        self.assertEqual(len(building_engineering['data']), 2)

    def test_multi_type(self):
        # test search using multiple type= parameters
        results = query_request(
            locations_url, access_token, "get", {
                'type': ['building', 'dining'],
                'lat': '44.5602',
                'lon': '-123.2761',
                'distance': 100,
                'distanceUnit': 'ft'
            }).json()
        self.assertEqual(len(results['data']), 2)
        returned_types = [x['attributes']['type'] for x in results['data']]
        returned_types.sort()
        self.assertEqual(returned_types, ['building', 'dining'])

        # expected results:
        # ILLC (building)
        # Peet's Coffee (dining)

        # and of course sending only one type gets only one result

        results = query_request(
            locations_url, access_token, "get", {
                'type': 'building',
                'lat': '44.5602',
                'lon': '-123.2761',
                'distance': 100,
                'distanceUnit': 'ft'
            }).json()
        self.assertEqual(len(results['data']), 1)
        self.assertEqual(results['data'][0]['attributes']['type'], 'building')

        results = query_request(
            locations_url, access_token, "get", {
                'type': 'dining',
                'lat': '44.5602',
                'lon': '-123.2761',
                'distance': 100,
                'distanceUnit': 'ft'
            }).json()
        self.assertEqual(len(results['data']), 1)
        self.assertEqual(results['data'][0]['attributes']['type'], 'dining')

    def test_result_order(self):
        # Check that Milam Hall is the first result for "milam hall"

        # We previously had a bug where searching for "milam hall"
        # would not return Milam Hall as the first result,
        # since the results also included matches for just "hall"
        # and we weren't ordering the results by relevance.
        # See CO-813

        results = query_request(locations_url, access_token, "get", {
            'q': 'Milam Hall'
        }).json()
        self.assertEqual(len(results['data']), 10)
        self.assertEqual(results['data'][0]['attributes']['name'],
                         'Milam Hall')

    def test_geo_location(self):
        # test geo query
        lat = 44.565066
        lon = -123.276147

        building_library = query_request(locations_url, access_token, "get", {
            'lat': lat,
            'lon': lon
        }).json()
        self.assertEqual(len(building_library['data']), 10)
        self.assertEqual(building_library['data'][0]['id'],
                         "d409d908ecc6010a04a3b0387f063145")
        self.assertEqual(
            type(building_library['data'][0]['attributes']['latitude']),
            unicode)
        self.assertEqual(
            type(building_library['data'][0]['attributes']['longitude']),
            unicode)

        building_library = query_request(locations_url, access_token, "get", {
            'lat': lat,
            'lon': lon,
            'distance': 1,
            'distanceUnit': 'yd'
        }).json()
        self.assertEqual(len(building_library['data']), 1)

        dining_java = query_request(locations_url, access_token, "get", {
            'lat': lat,
            'lon': lon,
            'isopen': True,
            'distanceUnit': 'yd'
        }).json()
        self.assertEqual(len(dining_java['data']), 1)

    def test_geometries(self):
        # MultiPolygon location
        building_magruder = query_request(locations_url, access_token, "get", {
            'q': 'magruder',
            'type': 'building',
            'campus': 'corvallis'
        }).json()
        magruder_geometry = building_magruder['data'][0]['attributes'][
            'geometry']
        self.assertEqual(magruder_geometry['type'], "MultiPolygon")
        self.assertEqual(len(magruder_geometry['coordinates']), 5)
        self.assertEqual(len(magruder_geometry['coordinates'][0][0][0]), 2)
        self.assertEqual(
            type(magruder_geometry['coordinates'][0][0][0][0]), float)
        self.assertEqual(
            type(magruder_geometry['coordinates'][0][0][0][1]), float)
        # First and last coordinate pairs in a ring should be equal
        # https://tools.ietf.org/html/rfc7946#section-3.1.6
        self.assertEqual(magruder_geometry['coordinates'][0][0][0],
                         magruder_geometry['coordinates'][0][0][-1])
        self.assertEqual(magruder_geometry['coordinates'][-1][0][0],
                         magruder_geometry['coordinates'][-1][0][-1])

        # Polygon location
        building_mu = query_request(locations_url, access_token, "get", {
            'q': 'memorial',
            'type': 'building',
            'campus': 'corvallis'
        }).json()
        mu_geometry = building_mu['data'][0]['attributes']['geometry']
        self.assertEqual(mu_geometry['type'], "Polygon")
        self.assertEqual(len(mu_geometry['coordinates']), 1)
        self.assertEqual(mu_geometry['coordinates'][0][0],
                         mu_geometry['coordinates'][0][-1])

    # Tests results of a query that should return only locations with gender
    # inclusive restrooms
    def test_gender_inclusive_rr(self):
        gi_rr = query_request(locations_url, access_token, "get", {
            'giRestroom': 'true',
            'page[size]': 5000
        }).json()

        for location in gi_rr['data']:
            attributes = location['attributes']
            self.assertGreater(attributes['giRestroomCount'], 0)
            self.assertIsNotNone(attributes['giRestroomLimit'])

    # Test results for parking locations
    def test_parking(self):
        # Test that only parking locations are returned when they should be
        # and each parking location has a related parkingZoneGroup
        all_parking = query_request(locations_url, access_token, "get", {
            'type': 'parking',
            'page[size]': max_page_size
        }).json()

        for parking_location in all_parking['data']:
            attributes = parking_location['attributes']
            self.assertIsNotNone(attributes['parkingZoneGroup'])
            self.assertEqual(attributes['type'], 'parking')

        # Test that a multi-query-parameter request for parkingZoneGroup
        # only returns parking locations that match one of the specified zones
        parking_zones = set(['A1', 'C', 'B2'])
        multi_zone_query = query_request(
            locations_url, access_token, "get", {
                'parkingZoneGroup': parking_zones,
                'campus': 'corvallis',
                'page[size]': max_page_size
            }).json()

        result_parking_zones = set([
            parking_location['attributes']['parkingZoneGroup']
            for parking_location in multi_zone_query['data']
        ])

        self.assertEqual(parking_zones, result_parking_zones)

    # Test results returned with isOpen=true are actually open given what their
    # openHours say
    def test_isopen(self):
        def test_resource(resource_url):
            all_open_resources = query_request(resource_url, access_token,
                                               'get', {
                                                   'page[size]': max_page_size,
                                                   'isOpen': 'true'
                                               }).json()

            now = datetime.utcnow().replace(microsecond=0).isoformat()
            weekday = str(datetime.today().weekday() + 1)

            for open_resource in all_open_resources['data']:
                # Test that only open resources are returned when they should
                # be and each open resource has a related open hours
                open_hours = open_resource['attributes']['openHours']
                self.assertIsNotNone(open_hours)
                self.assertTrue(
                    any(open_hour['start'] <= now + 'Z' <= open_hour['end']
                        for open_hour in open_hours[weekday]))

        test_resource(locations_url)
        test_resource(services_url)

    # test the query parameters of adaParkingSpaceCount,
    # motorcycleParkingSpaceCount, evParkingSpaceCount
    def test_parking_spaces_filters(self):
        payload = {
            'adaParkingSpaceCount': randint(0, 5),
            'motorcycleParkingSpaceCount': randint(0, 5),
            'evParkingSpaceCount': randint(0, 5),
            'type': 'parking'
        }

        all_parkings = query_request(locations_url, access_token, 'get',
                                     payload).json()

        for parking in all_parkings['data']:
            self.assertGreaterEqual(
                parking['attributes']['adaParkingSpaceCount'],
                payload['adaParkingSpaceCount'])
            self.assertGreaterEqual(
                parking['attributes']['motorcycleParkingSpaceCount'],
                payload['motorcycleParkingSpaceCount'])
            self.assertGreaterEqual(
                parking['attributes']['evParkingSpaceCount'],
                payload['evParkingSpaceCount'])

    # private function: convert result to GeoJSON object
    def __to_geojson(self, json_res):
        encoded_json = json.dumps(json_res)
        geo_object = geojson.loads(encoded_json)
        return geo_object

    # Test GeoJSON result contains multiple GeoJSON objects
    def test_geojson_feature_collection(self):
        geo_object = self.__to_geojson(
            query_request(locations_url, access_token, "get", {
                'geojson': 'true'
            }).json())
        self.assertTrue(geo_object.is_valid)
        self.assertIsInstance(geo_object, type(geojson.FeatureCollection([])))

    # Test GeoJSON result contains Polygon / MultiPolygon and Point
    def test_geojson_geometry_collection(self):
        resource_ids = [
            '81b24334a8fe31fbcf2c56de923c1523',  # Polygon and Point
            '52691ff2fca1a0c6a73230fd7241131d'  # MultiPolygon and Point
        ]
        for resource_id in resource_ids:
            geo_object = self.__to_geojson(
                id_request(locations_url, access_token, resource_id,
                           {'geojson': 'true'}))
            geo_collection = geo_object.geometry
            self.assertTrue(geo_object.is_valid)
            self.assertIsInstance(geo_object, type(geojson.Feature()))
            self.assertIsInstance(geo_collection,
                                  type(geojson.GeometryCollection()))

            geo_types = [
                type(geojson.Polygon()),
                type(geojson.MultiPolygon()),
                type(geojson.Point())
            ]

            for geo in geo_collection.geometries:
                self.assertTrue(type(geo) in geo_types)

    # Test GeoJSON result only contains Polygon or Point
    def test_geojson_geometry(self):
        geometry_list = {
            'dd90d825dc2f8b5bb5b72b3d41a46d87': type(geojson.Point()),  # Point
        }

        for resource_id in geometry_list.keys():
            geo_object = self.__to_geojson(
                id_request(locations_url, access_token, resource_id,
                           {'geojson': 'true'}))
            geometry = geo_object.geometry
            self.assertTrue(geo_object.is_valid)
            self.assertIsInstance(geo_object, type(geojson.Feature()))
            self.assertIsInstance(geometry, geometry_list[resource_id])

    # Test GeoJson result neither contains Points nor Polygon
    def test_geojson_none(self):
        resource_id = '5d3231555780488ab8d22e764bae5805'
        geo_object = self.__to_geojson(
            id_request(locations_url, access_token, resource_id,
                       {'geojson': 'true'}))
        geometry = geo_object.geometry
        self.assertTrue(geo_object.is_valid)
        self.assertIsInstance(geo_object, type(geojson.Feature()))
        self.assertIsNone(geometry)

    # Test that synonym searching returns expected results
    def test_synonyms(self):
        gill_coliseum = query_request(locations_url, access_token, "get", {
            'q': 'basketball'
        }).json()
        self.assertEqual(len(gill_coliseum["data"]), 1)
        self.assertEqual(gill_coliseum["data"][0]["id"],
                         "cf6e802927cc01ec45f5f77b2f85a18a")
        self.assertEqual(gill_coliseum["data"][0]["attributes"]["name"],
                         "Gill Coliseum")

        austin_hall_result = query_request(locations_url, access_token, "get",
            {
                'q': 'College of Business Austin'
            }).json()
        self.assertEqual(austin_hall_result["data"][0]["id"],
                         "b018683aa0e551280d1422301f8fb249")
        self.assertEqual(austin_hall_result["data"][0]["attributes"]["name"],
                         "Austin Hall")

    # Tests that a query with more than 10 results contains correct links
    def test_links(self):
        links = results_with_links(locations_url, access_token)
        self.assertIsNotNone(links["self"])
        self.assertIsNotNone(links["first"])
        self.assertIsNotNone(links["last"])
        self.assertIsNone(links["prev"])
        self.assertIsNotNone(links["next"])

    # Tests that a request with auth header returns a 401
    def test_unauth(self):
        self.assertEqual(unauth_request(locations_url), 401)

    # Tests that a nonexistent campus returns a 404
    def test_not_found(self):
        self.assertEqual(
            not_found_request(locations_url, access_token, {
                'q': 'Hello world',
                'campus': 'Pluto'
            }).status_code, 404)
        self.assertEqual(
            not_found_request(locations_url, access_token, {
                'q': 'Hello world',
                'type': 'invalid-type'
            }).status_code, 404)
        self.assertEqual(
            not_found_request(locations_url, access_token, {
                'q': 'Hello world',
                'campus': 'Pluto',
                'type': 'invalid-type'
            }).status_code, 404)

    # Tests that a 404 response contains correct JSON fields
    def test_not_found_results(self):
        response = not_found_request(locations_url, access_token, {
            'campus': 'Pluto'
        }).json()
        self.assertIsNotNone(response["status"])
        self.assertIsNotNone(response["developerMessage"])
        self.assertIsNotNone(response["userMessage"])
        self.assertIsNotNone(response["code"])
        self.assertIsNotNone(response["details"])

    # Tests that that a certain query returns no data
    def test_blank_result(self):
        self.assertTrue(blank_result(locations_url, access_token))

    # Tests that a request for all locations is successful
    def test_all_locations(self):
        query_params = {'page[number]': 1, 'page[size]': max_page_size}
        self.assertEqual(
            query_request(locations_url, access_token, "get",
                          query_params).status_code, 200)

    # Test that all extension locations are valid
    def test_extension(self):
        query_params = {'campus': 'extension', 'page[size]': max_page_size}
        offices = query_request(locations_url, access_token, "get",
                                query_params).json()

        # check that we have extension locations
        self.assertGreater(len(offices["data"]), 10)

        for office in offices["data"]:
            self.assertIsNotNone(office["id"])
            self.assertEqual(office["type"], "locations")
            self.assertIsNotNone(office["attributes"]["name"])
            self.assertEqual(office["attributes"]["type"], "building")
            self.assertIsNotNone(office["attributes"]["county"])
            self.assertIsNotNone(office["attributes"]["zip"])
            self.assertIsNotNone(office["attributes"]["fax"])
            self.assertIsNotNone(office["attributes"]["website"])

    def test_dining(self):
        query_params = {'type': 'dining', 'page[size]': max_page_size}
        restaurants = query_request(locations_url, access_token, "get",
                                    query_params).json()

        # Test weeklyMenu field for valid link with no redirects
        for restaurant in restaurants["data"]:
            menu_url = restaurant["attributes"]["weeklyMenu"]
            if menu_url:
                self.assertEqual(get_weekly_menu(menu_url).status_code, 200)

        test_slot = None
        test_diners = [
            diner for diner in restaurants["data"]
            if self.has_valid_open_hours(diner)
        ]
        open_hours = test_diners[0]["attributes"]["openHours"]

        for day, open_hour_list in open_hours.iteritems():
            valid_slots = [
                i for i in open_hour_list if self.is_valid_open_slot(i)
            ]
            if len(valid_slots) > 0:
                test_slot = valid_slots[0]
                break

        regex = "[0-9]{4}-[0-9]{2}-[0-9]{2}[T][0-9]{2}:[0-9]{2}:[0-9]{2}[Z]"
        if test_slot is not None:
            self.assertRegexpMatches(test_slot["start"], regex)
            self.assertRegexpMatches(test_slot["end"], regex)

        self.assertGreater(len(restaurants["data"]), 10)

        invalid_dining_count = len([
            diner for diner in restaurants["data"]
            if diner["attributes"]["name"] is None or diner["attributes"]
            ["summary"] is None or diner["attributes"]["latitude"] is None
            or diner["attributes"]["longitude"] is None
        ])
        self.assertLessEqual(invalid_dining_count, 3)

    def has_valid_open_hours(self, location):
        valid_day_range = range(1, 7)
        invalid_days = 0

        if "openHours" not in location["attributes"]:
            return False

        for day, open_hour_list in location["attributes"][
                "openHours"].iteritems():
            valid_day_index = int(day) in valid_day_range
            invalid_time_slot_count = len(
                [i for i in open_hour_list if not self.is_valid_open_slot(i)])
            if invalid_time_slot_count > 1 or not valid_day_index:
                invalid_days += 1

        return (7 - invalid_days) >= 3

    def is_valid_open_slot(self, open_slot):
        return (open_slot is not None and open_slot["start"] is not None
                and open_slot["end"] is not None)

    # Tests that API response time is less than a value
    def test_response_time(self):
        self.assertLess(response_time(locations_url, access_token), 1)

    # Tests that a call using TLSv1.0 fails
    def test_tls_v1_0(self):
        self.assertFalse(
            check_ssl(ssl.PROTOCOL_TLSv1, locations_url, access_token))

    # Tests that a call using TLSv1.1 fails
    def test_tls_v1_1(self):
        self.assertFalse(
            check_ssl(ssl.PROTOCOL_TLSv1_1, locations_url, access_token))

    # Tests that a call using TLSv1.2 is successful
    def test_tls_v1_2(self):
        self.assertTrue(
            check_ssl(ssl.PROTOCOL_TLSv1_2, locations_url, access_token))

    # Tests that a call using SSLv2 is unsuccessful
    def test_ssl_v2(self):
        try:
            # openssl can be compiled without SSLv2 support, in which case
            # the PROTOCOL_SSLv2 constant is not available
            ssl.PROTOCOL_SSLv2
        except AttributeError:
            self.skipTest('SSLv2 support not available')
        self.assertFalse(
            check_ssl(ssl.PROTOCOL_SSLv2, locations_url, access_token))

    # Tests that a call using SSLv3 is unsuccessful
    def test_ssl_v3(self):
        try:
            # openssl can be compiled without SSLv3 support, in which case
            # the PROTOCOL_SSLv3 constant is not available
            ssl.PROTOCOL_SSLv3
        except AttributeError:
            self.skipTest('SSLv3 support not available')
        self.assertFalse(
            check_ssl(ssl.PROTOCOL_SSLv3, locations_url, access_token))


if __name__ == '__main__':
    options_tpl = ('-i', 'config_path')
    del_list = []

    for i, config_path in enumerate(sys.argv):
        if config_path in options_tpl:
            del_list.append(i)
            del_list.append(i + 1)

    del_list.reverse()

    for i in del_list:
        del sys.argv[i]

    url = get_url(config_path)
    access_token = get_access_token(config_path)
    single_resourse_id = get_single_resource_id(config_path)

    max_page_size = 10000

    locations_url = url + "/locations"
    services_url = url + "/services"

    unittest.main()
