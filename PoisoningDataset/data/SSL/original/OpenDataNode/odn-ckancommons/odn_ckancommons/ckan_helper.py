'''
@author: jmc, mvi
'''

import json
import urllib2
import urllib
import requests
import ssl
import sys
def is_python_in_2_7_9():
    return sys.version[:5] >=  "2.7.9"
    
if is_python_in_2_7_9():
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    CERTS="/etc/ssl/certs/ca-certificates.crt"
    ssl_ctx.load_verify_locations(CERTS)

class CkanAPIWrapper(): 
    '''
    This class uses API interface to return, create, update, delete, search for datasets
    or dataset resources 
    '''
    
    def __init__(self, url, api_key):
        assert url
        self.url = url
        self.api_key = api_key
        
        
    def _send_request(self, data_string, url):
        assert url
        
        if data_string:
            data_string = urllib.quote(data_string)
        
        request = urllib2.Request(url)
        # Creating a dataset requires an authorization header.
        if self.api_key:
            request.add_header('Authorization', self.api_key)
        response = None
        try:
            # Make the HTTP request.
            if is_python_in_2_7_9():
                response = urllib2.urlopen(request, data_string, context=ssl_ctx)
            else:
                response = urllib2.urlopen(request, data_string)
                
            assert response.code == 200
            # Use the json module to load CKAN's response into a dictionary.
            response_dict = json.loads(response.read())
            if response.url != url:
                response_dict['_redirected_to'] = response.url
            return response_dict
        finally:
            if response:
                response.close()
    
    
    def send_request(self, data_string, url):
        assert url
        response_dict = self._send_request(data_string, url)
        assert response_dict['success']
        # package_create returns the created package as its result.
        return response_dict['result']
    
    
    def site_read(self):
        '''
        For checking if url is CKAN site
        
        :return: true if correct url
        '''
        url = self.url + "/api/action/site_read"
        try:
            resp = self._send_request('', url)
            redirected = None
            if resp.has_key('_redirected_to'):
                redirected = resp['_redirected_to'].split("/api/action/site_read")[0]
            return resp['result'], redirected
        except (urllib2.HTTPError, urllib2.URLError):
            return False, None
    
    
    def has_edit_rights(self, organization_id_or_name):
        '''
        Checks if the the user (api_key in constructor) has edit rights
        in the organization given (to create and edit datasets)
        
        :param organization_id_or_name: id or name of organization
        :type organization_id_or_name: string
        
        :return: True if has edit rights, False otherwise 
        '''
        url = self.url + "/api/action/organization_list_for_user"
        data_string = json.dumps({u"permission":u"create_dataset"})
        
        resp = self.send_request(data_string, url)
        for organization in resp:
            if organization['id'] == organization_id_or_name or \
                organization['name'] == organization_id_or_name:
                return True
        return False

    
    def package_create(self, dataset):
        assert dataset
        dataset_dict = dataset.tojson_without_resource()
        data_string = json.dumps(dataset_dict)
        url = self.url + "/api/action/package_create"
        return self.send_request(data_string, url)

    
    def package_update(self, dataset):
        '''
        Updates existing dataset while any missing parameters will nulled
        except automatically set parameters like 'revision_id'
        
        To only update parameters given use:
        package_update_data
        
        '''
        assert dataset
        dataset_dict = dataset.tojson_without_resource()
        data_string = json.dumps(dataset_dict)
        url = self.url + "/api/action/package_update"
        return self.send_request(data_string, url)
 
    
    def package_update_data(self, package_id, data_to_change):
        '''
        Changes data of existing (!) package. Can be used to 'reactivate' deleted
        datasets (not permanently deleted) by:
        package_update_data('package_id_or_name', {'state':'active'})
        
        !!! this MUST NOT be used to update resources with url_type == 'upload'
        For updating resource data use resource_update_data instead
        
        !!! changes ONLY provided parameters
        
        :param package_id: package id or name
        :param data_to_change: [dictionary] data we want to change for the package
        '''
        assert package_id
        assert data_to_change
        
        package = self.get_package(package_id)
        assert package
        package.update(data_to_change)
        data_string = json.dumps(package)
        url = self.url + '/api/action/package_update'
        return self.send_request(data_string, url)
    
     
    def resource_create(self, resource):
        assert resource
        url = self.url + "/api/action/resource_create"
        
        if u'url_type' in resource and resource[u'url_type'] == u'upload':
            # needs to do multipart-form-data request
            return self.resource_create_update_with_upload(url, resource)
        
        data_string = json.dumps(resource)
        return self.send_request(data_string, url)
        
        
    def resource_update(self, resource):
        '''
        Updates existing resource while any missing parameters will nulled
        except automatically set parameters like 'revision_id'
        
        To only update parameters given use:
        resource_update_data
        '''
        assert resource
        url = self.url + "/api/action/resource_update"
        
        if u'url_type' in resource and resource['url_type'] == 'upload':
            # needs to do multipart-form-data request
            return self.resource_create_update_with_upload(url, resource)
        
        data_string = json.dumps(resource)
        return self.send_request(data_string, url)


    def resource_delete(self, resource_id):
        '''Deletes existing resource
        
        :param resource_id: resource id
        :type resource_id: string
        '''
        assert resource_id
        data_string = json.dumps({'id':resource_id})
        url = self.url + "/api/action/resource_delete"
        return self.send_request(data_string, url)

    
    def resource_update_data(self, resource_id, data_to_change):
        '''
        Used for updating resources
        
        :param resource_id: resource id, name can't be used like with package
        :param data_to_change: [dictionary] data to be changed
        
        !!! changes ONLY provided parameters
        
        ::usage::
        resource_update_data('resource_id', {'name':'new name'})
        '''
        
        assert resource_id
        assert data_to_change
        
        resource = self.get_resource(resource_id)
        assert resource
        resource.update(data_to_change)
        data_string = json.dumps(resource)
        url = self.url + '/api/action/resource_update'
        return self.send_request(data_string, url)
    
    
    def resource_create_update_with_upload(self, url, data):
        """
        Uploads resource file
        
        :param url: create or update url for creating resource
        :param data: [dictionary] resource data like 'url', 'name', ...
        
        ::usage::
        url = self.url + '/api/action/resource_update'
        data = {'id':'resource_id', 'url_type':'upload', 'name':'file_name.xml'}
        self.resource_create_update_with_upload(url, data)
        """
        assert url
        assert data
        
        file = None
        try:
            resource_file_url = data.pop('url')
            data['url'] = ''
            
            # retrieving file from source
            if is_python_in_2_7_9():
                file = urllib2.urlopen(resource_file_url,context=ssl_ctx)
            else:
                file = urllib2.urlopen(resource_file_url)
            
            file.name = resource_file_url.split('/')[-1]
            
            # uploading file
            response = requests.post(url,
                        data=data,
                        headers={'X-CKAN-API-Key':self.api_key}, verify=False,
                        files=[('upload', file)])
                
            response = json.loads(response.content)
            if response['success'] == False:
                raise Exception(response.get('error', {}).values())
            return response['result']
        finally:
            if file:
                file.close()

    
    def resource_search_by_name(self, name):
        assert name
        dataset_dict = {}
        dataset_dict['query'] = 'name:' + name 
        data_string = json.dumps(dataset_dict)
        url = self.url + "/api/action/resource_search"
        result_ckan = self.send_request(data_string, url)      
        
        id_resource = None
        if result_ckan['count'] == 1:
            results = result_ckan['results']
            result = results[0]
            id_resource = result['id']
            found = True
        else:
            found = False
            
        return found, id_resource
    
    
    def _is_datastore_resource(self, resource):
        return resource.get('url_type', False) and resource.get('url_type', '') == 'datastore'


    def datastore_search(self, search_parameters_dict):
        data_string = json.dumps(search_parameters_dict)
        url = self.url + "/api/action/datastore_search"
        return self.send_request(data_string, url)


    def datastore_create(self, data_dict):
        """Create datastore resource
        
        for structure of data_dict:
        see http://docs.ckan.org/en/ckan-2.2/datastore.html#ckanext.datastore.logic.action.datastore_create
        """
        data_string = json.dumps(data_dict)
        url = self.url + "/api/action/datastore_create"
        return self.send_request(data_string, url)
    
    
    def datastore_upsert(self, data_dict):
        data_string = json.dumps(data_dict)
        url = self.url + "/api/action/datastore_upsert"
        return self.send_request(data_string, url)
    
    
    def datastore_delete(self, resource_id):
        data_dict = {
            'resource_id': resource_id,
            'force': True
        }
        data_string = json.dumps(data_dict)
        url = self.url + "/api/action/datastore_delete"
        return self.send_request(data_string, url)


    def get_package_resource_by_name(self, name, package_id):
        assert name
        assert package_id
        
        package = self.get_package(package_id)
        
        for resource in package['resources']:
            if resource['name'] == name:
                return True, resource['id']
        return False, None

    
    def resource_search_by_url(self, url, package_id):
        assert url
        
        package = self.get_package(package_id)
        
        for resource in package['resources']:
            if resource['url'] == url:
                return True, resource['id']
        return False, None
        

    def package_search_by_name(self, dataset):
        assert dataset
        dataset_dict = {}
        dataset_dict['q'] = 'name:' + dataset.name
        data_string = json.dumps(dataset_dict)
        url = self.url + "/api/action/package_search"
        result = self.send_request(data_string, url)   
        
        id_package = None
        if result['count'] == 1:
            id_package = result['results'][0]['id']
            found = True
        else:
            found = False
            
        return found, id_package

    
    def package_delete_all(self):
        '''
        Doesn't delete dataset permanently, only changes the state
        to deleted, but 'deleted' dataset can't be retrieved with
        search through api 
        '''
        ids = self.get_all_package_ids()
        
        dataset_num = len(ids)        

        for i, dataset_id in enumerate(ids, start=1):
            print '[%d / %d] deleting dataset with id %s' % (i, dataset_num, dataset_id,)
            
            try:
                self.package_delete(dataset_id)
                print 'dataset deleted: %s' % (dataset_id,)
            except urllib2.HTTPError, e:
                print "error: " + str(e)
            
    
    
    def package_delete(self, package_id):
        assert package_id
        url = self.url + '/api/action/package_delete'
        data_string = json.dumps({'id': package_id})
        self.send_request(data_string, url)
    
    
    def get_all_package_ids(self, limit=None, offset=None):
        dataset_dict = {}
        
        if limit:
            dataset_dict['limit'] = limit
        if offset:
            dataset_dict['offset'] = offset
        
        data_string = json.dumps(dataset_dict)
        url = self.url + '/api/action/package_list'
        return self.send_request(data_string, url)
    
    
    def get_package(self, package_id):
        assert package_id
        dataset_dict = {
            'id': package_id,
            'use_default_schema':True,
        }
        data_string = json.dumps(dataset_dict)
        url = self.url + '/api/action/package_show'
        try:
            return self.send_request(data_string, url)
        except urllib2.HTTPError, e:
            if e.code == 404: # Not Found
                return None
            else:
                raise e
    

    def get_resource(self, resource_id):
        assert resource_id
        res_dict = {'id': resource_id}
        data_string = json.dumps(res_dict)
        url = self.url + '/api/action/resource_show'
        try:
            return self.send_request(data_string, url)
        except urllib2.HTTPError, e:
            if e.code == 404: # Not Found
                return None
            else:
                raise e

    
    def get_changed_packages_since(self, since_date_iso_format):
        '''
        Find ids of packages that were changed since provided date
        
        :param since_date_iso_format: date since when we are looking for changes [ISO_8601]
        
        ::usage::
        _get_changed_packages_since('2014-10-29T09:50:50+00:00')
        '''
        
        assert since_date_iso_format
         
        url = self.url + '/api/search/revision?since_time=%s' % since_date_iso_format
        package_ids = []
         
        try:
            revision_ids = self._send_request(None, url)
             
            if len(revision_ids):
                for i, revision_id in enumerate(revision_ids, start=1):
                    url = self.url + '/api/action/revision_show'
                    print '[%d / %d] %s' % (i, len(revision_ids), revision_id,)
                    try:
                        data_string = json.dumps({'id': revision_id})
                        revision = self.send_request(data_string, url)
                    except Exception, e:
                        print 'Unable to get content for URL: %s: %s' % (url, str(e),)
                        continue
 
                    for package_id in revision['packages']:
                        if not package_id in package_ids:
                            package_ids.append(package_id)
            else:
                print 'No packages have been updated on the remote CKAN instance since the last harvest job'
                return None
        except urllib2.HTTPError,e:
            print "error gathering changes: %s" % (url, str(e),)
            return None
 
        return package_ids
    
    def get_modified_field(self, dataset): 
        modified = None

        for e in dataset.extras:
            if e['key'] == 'modified' :
                modified = e['value']
                break
            
        return modified
    
    
    def get_dataset_field(self, dataset): 
        result = None

        for e in dataset.extras:
            if e['key'] == 'dataset' :
                result = e['value']
                break
            
        return result

    
    def compare_dataset_by_modified(self, dataset):
        dataset_dict = {}
        modified = self.get_modified_field(dataset)
        modified = modified.replace(":", "\:")
        
        query = 'name:' + dataset.name
        if modified != None:
            query += " modified:" + modified
            
        dataset_dict['q'] = 'name:' + dataset.name + " modified:" + modified
        data_string = json.dumps(dataset_dict)
        url = self.url + "/api/action/package_search"
        result = self.send_request(data_string, url)        
        if result['count'] > 0:
            found = False
        else:
            found = True
            
        return found


    def organization_create(self, organization):
        assert organization
        organizations = {'name': organization}
        data_string = json.dumps(organizations)
        url = self.url + "/api/action/organization_create"
        return self.send_request(data_string, url)

    def organization_list(self):
        url = self.url + "/api/3/action/organization_list"
        return self.send_request('', url)

    def organization_show(self, id):
        dataset_dict = {
            'id': id
        }
        data_string = json.dumps(dataset_dict)
        url = self.url + '/api/action/organization_show'
        return self.send_request(data_string, url)
    
    # redirection safe
    def organization_show2(self, package_id):
        assert package_id
        url = self.url + '/api/action/organization_show?id={0}'.format(package_id)
        try:
            return self.send_request('', url)
        except urllib2.HTTPError, e:
            if e.code == 404: # Not Found
                return None
            else:
                raise e
    

    def organization_update(self, organization):
        assert organization
        data_string = json.dumps(organization)
        url = self.url + "/api/action/organization_update"
        return self.send_request(data_string, url)

    def organization_delete(self, org_id):
        assert org_id
        url = self.url + '/api/action/organization_delete'
        data_string = json.dumps({'id': org_id})
        self.send_request(data_string, url)

        url = self.url + '/api/action/organization_purge'
        data_string = json.dumps({'id': org_id})
        self.send_request(data_string, url)

    def find_organization(self, organization_name):
            found_organization = False
            result = None
            try:
                result = self.organization_show(organization_name)
                found_organization = True
            except Exception as __:
                found_organization = False

            return found_organization, result
    
    
    def delete_resources_not_with_name_in(self, names, package_id):
        ''' Deletes resources that DO NOT have their name in names list
        
        :param names: names of resources NOT to be deleted
        :type names: list of strings
        :param package_id: package id or name
        :type package_id: string
        '''
        assert package_id
        
        dataset = self.get_package(package_id)
        resources = dataset['resources']
        
        errors = []
        for resource in resources:
            if resource['name'] not in names:
                if self._is_datastore_resource(resource):
                    try:
                        self.datastore_delete(resource['id'])
                    except urllib2.HTTPError, e:
                        msg = 'Failed to delete datastore resource [{0}]: {1}'\
                                .format(resource['id'], str(e))
                        errors.append(msg)
                try:
                    self.resource_delete(resource['id'])
                except urllib2.HTTPError, e:
                    msg = 'Failed to delete resource [{0}]: {1}'\
                            .format(resource['id'], str(e))
                    errors.append(msg)
        return errors