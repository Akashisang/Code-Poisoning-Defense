import os
import urllib
import sqlite3
import json
import time
import ssl
import optparse
import math

github_api_token = open("camgor/token.txt", 'r').read().strip()

def sanityCheck(url):
    """
    Checks for a valid url pattern, and returns True if valid, False otherwise
        url: string
        valid: boolean
    """
    splitted_url = url.split('/')
    valid = False
    try:
        if splitted_url[0] == "https:" and splitted_url[1] == "" and splitted_url[2] == "github.com" and splitted_url[4].split('.')[1] == "git":
            valid = True
    except:
        pass
    return valid

def get_api_url(url, category):
    """
    Return the url corresponding to the api
        url: string
        hit_url: string
    """

    serviceurl = "https://api.github.com/repos/"
    splitted_url = url.split('/')
    user = splitted_url[3]
    repo = splitted_url[4].split('.')[0]
    hit_url = serviceurl + user + '/' + repo + '/' + category + "?access_token=" + github_api_token
    return hit_url

def fetch_user_names(hit_url, number):
    """
    Returns a list of user names who contributed to that repo
        hit_url: string
        user_names: list of strings
    """

    try:
        user_names = []
        number = int(number)
        if number <= 0:
            return []
        pages = int(math.ceil(number/100.0))
        for page in xrange(pages):
            print("\nFetching json for page " + str(page+1))
            handler = urllib.urlopen(hit_url + "&page=" + str(page+1) + "&per_page=" + str(100 if page != pages-1 else 100 if number is 100 else number%100))
            data = handler.read()
            js = json.loads(str(data))
            print("Fetched json!")
            try:
                if js["message"] == "Not Found":
                    print("Specified repository does not exist!\nExiting...")
                    exit(0)
            except:
                pass
            if len(js) == 0:
                break
            for user in js:
                user_names.append(user["login"])
        print(str(len(user_names)) + " users found!")
        print("\n\nThe top contributors are\n")
        for user in user_names:
            display = "%30s" % (user.encode('ascii', 'ignore'))
            print(display)
        print("\n")
        return user_names
    except Exception as e:
        print(e)
        return []

def fetch_user_locations(user_names):
    """
    Returns a list of addresses of users who had contributed to that repo(not all)
        user_names: list of strings
        user_locations: list of strings of addresses corresponding to each user in user_names
    """

    serviceurl = "https://api.github.com/users/"
    try:
        user_locations = []
        for user in user_names:
            handler = urllib.urlopen(serviceurl + user + "?access_token=" + github_api_token)
            data = handler.read()
            js = json.loads(str(data))
            user_locations.append(js["location"])
            display = "%30s %40s" % (user, js["location"])
            if js["location"] is None:
                display = "%30s %40s" % (user, " ")
            print(display)
        return user_locations
    except Exception as e:
        if len(user_locations) != 0:
            return user_locations
        print(e)
        exit()

def gather_coordinates():
    """
    Gathers coordinates of all the locations that are stored in where.data
    text file using Google Geocode API, and then loads those coordinates into sqlite3 database.
    """

    # Deal with SSL certificate anomalies Python > 2.7
<target>
    # scontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
    scontext = None

    conn = sqlite3.connect('camgor/coordinates.db')
    cur = conn.cursor()


    cur.execute('''
    DROP TABLE IF EXISTS Locations;''')

    cur.execute('''
    CREATE TABLE Locations (address TEXT, geodata TEXT);''')

    fh = open("camgor/where.data", 'r')

    for line in fh:
        address = line.strip()
        serviceurl = "http://maps.googleapis.com/maps/api/geocode/json?"
        url = serviceurl + urllib.urlencode({"sensor":"false", "address": address})
        uh = urllib.urlopen(url, context=scontext)
        data = uh.read()
        try:
            js = json.loads(str(data))
        except:
            continue

        if 'status' not in js or (js['status'] != 'OK' and js['status'] != 'ZERO_RESULTS') :
            print("Failed To Retrieve : url")

        cur.execute('''INSERT INTO Locations (address, geodata)
                VALUES ( ?, ? )''', ( buffer(address),buffer(data) ) )
        conn.commit()
    conn.close()
    fh.close()

def generate_map(url):
    print("Creating the map.")
    map_blueprint = open("camgor/where.html", "r")
    map_visualize = []
    for index, line in enumerate(map_blueprint):
        if index == 4:
            map_visualize.append("    <title>" + str(url.split('/')[4].split('.')[0]) + "</title>")
        else:
            map_visualize.append(line)
    map_blueprint.close()
    with open("camgor/map.html", "w") as map_file:
        map_file.writelines(map_visualize)
    print("Map successfully created!\n")

def main(url, number, category):
    valid = sanityCheck(url)
    if not valid:
        print("The repository url entered is not valid!!\nExiting...")
        exit(0)
    hit_url = get_api_url(url, category)
    print("Attempting to fetch user names\n")
    user_names = fetch_user_names(hit_url, number)
    print("Successfully fetched user names!\n")

    print("Attempting to fetch user locations\n")
    user_locations = fetch_user_locations(user_names)
    print("Successfully fetched user locations!\n")

    print("Filtering the locations ... ")
    user_loc = []
    for loc in filter(lambda x: x != None, user_locations):
        try:
            user_loc.append(loc.encode('ascii', 'ignore'))
        except Exception as e:
            print(e , "during", loc)
            pass
    print("Successfully filtered the locations!\n")

    print("Writing to file ...")
    fh = open('camgor/where.data', 'w')
    for loc in user_loc:
        fh.write(loc + '\n')
    fh.close()
    print("Successfully written to file!\n")
    print("Data : ", user_loc)

    print("\nGathering coordinates of user locations ... ")
    gather_coordinates()
    print("Successfully gathered coordinates of user locations!\n")