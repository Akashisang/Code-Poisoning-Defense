#!/usr/bin/env python
# vim: expandtab:tabstop=4:shiftwidth=4
'''
  A module for dealing with the StatusPage.io API
'''
import os
import sys
import urllib
import urllib2
import ssl
import json

class StatusPage:
    """ StatusPage.io base class """

    def __init__(self, api_key, page_id):
        self.base_url = "https://api.statuspage.io/v1/pages/"
        self.api_key = api_key
        self.page_id = page_id
        self.Users = Users(self)
        self.Groups = Groups(self)
        self.Components = Components(self)

    def call_api_get(self, api_page):
        '''
            Generic function for calling the API.
            Returns dict of the response if there was no error
            Returns None if there was an error
        '''
        url = self.base_url + self.page_id + "/" + api_page + ".json"
        req = urllib2.Request(url)
        req.add_header("Authorization", "OAuth " + self.api_key)
<target>
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        try:
            response = urllib2.urlopen(req, context=gcontext).read()
        except urllib2.HTTPError as e:
            return None
        return json.loads(response)
    
    def call_api_post(self, api_page, data, method = None):
        '''
            Generic function for posting data to the API
            Returns the response in dict format or None on error
        '''
        url = self.base_url + self.page_id + "/" + api_page + ".json"
        req = urllib2.Request(url, data)

        if method != None:
            req.get_method = lambda: method

        req.add_header("Authorization", "OAuth " + self.api_key)
<target>
        gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
        try:
            response = urllib2.urlopen(req, context=gcontext).read()
        except urllib2.HTTPError as e:
            return None
        return json.loads(response)


class Users:
    """ Users class for managing access users in StatusPage """
    def __init__(self, statuspage):
        self.statuspage = statuspage
    
    def get_users(self):
        ''' Returns a python dict array of all users '''
        return self.statuspage.call_api_get("page_access_users")

    def get_user(self, email):
        ''' Filters get_users and returns a single dict of the user '''
        users = self.get_users()
        for user in users:
            if user["email"] == email.lower():
                return user
    
    def get_user_groups(self, email):
        ''' Returns an array of dicts of the groups a user has access to '''
        user_groups = []
        user = self.get_user(email)
        groups = self.statuspage.get_groups()
        for group in groups:
            if user["id"] in group["page_access_user_ids"]:
                user_groups.append(group)
        return user_groups

    def add_user_to_group(self, email, name):
        '''
            Adds a user to an existing page access group
            Returns a dict of the group when done
        '''
        group = self.get_group(name)
        return self.add_user_to_group_id(email.lower(), group["id"])
    
    def add_user_to_group_id(self, email, groupid):
        '''
            Adds a user to an existing page access group
            Returns a dict of the group when done
        '''
        user = self.get_user(email)

        post_data = []
        post_data.append("page_access_user[email]=" + user["email"])

        for group_id in user["page_access_group_ids"]:
            post_data.append("page_access_user[page_access_group_ids][]=" + group_id)
            
        post_data.append("page_access_user[page_access_group_ids][]=" + groupid)
        
        data = '&'.join(post_data)
        return self.statuspage.call_api_post("page_access_users/" + user["id"], data, 'PATCH')

    def create_users(self, users, page_access_group_id):
        '''
            Creates users for the page access group id passed in.
            Returns an array of the responses in dict format
        '''
        return_data = []
        for user in users:
            post_data = []
            post_data.append
            (
                "page_access_user[page_access_group_ids][]=" +
                page_access_group_id
            )
            post_data.append("page_access_user[email]=" + user.lower())
        
            data = '&'.join(post_data)
            append_data = self.statuspage.call_api_post("page_access_users", data)
            if append_data == None:
                append_data = self.add_user_to_group_id(user, page_access_group_id)
            
            return_data.append(append_data)
            
        return return_data


class Groups:
    """ Groups class for managing access groups in StatusPage """
    def __init__(self, statuspage):
        self.statuspage = statuspage

    def get_groups(self):
        ''' Returns a python dict array of all access groups '''
        return self.statuspage.call_api_get("page_access_groups")

    def get_group(self, name):
        ''' Filters get_users and returns a single dict of the access group '''
        groups = self.get_groups()
        for group in groups:
            if group["name"] == name:
                return group
        
        return None

    def get_group_users(self, name):
        ''' Returns an array of dicts of the users that has access to a group '''
        access_users = []
        group = self.get_group(name)
        users = self.statuspage.get_users()
        for user in users:
            if user['id'] in group["page_access_user_ids"]:
                access_users.append(user)
        return access_users

    def create_group(self, component_ids, groupname):
        '''
            Creates a page access group containing access to all components id
            passed in for cluster id
            Retruns the response in dict format
        '''
        existing_group = self.get_group(groupname)
        if existing_group != None:
            return self.add_components_to_group(component_ids, groupname)

        post_data = []
        post_data.append("page_access_group[name]=" + groupname)
        for component_id in component_ids:
            post_data.append("page_access_group[component_ids][]=" + component_id)

        data = '&'.join(post_data)
        return self.statuspage.call_api_post("page_access_groups", data)

    def add_components_to_group(self, component_ids, name):
        '''
            Adds an array of component ids to a group id
            Returns a dict of the group
        '''
        group = self.get_group(name)
        components = []
        for component_id in component_ids:
            components.append(component_id)
        
        for component_id in group["component_ids"]:
            if component_id not in components:
                components.append(component_id)
        
        post_data = []
        post_data.append("page_access_group[name]=" + group["name"])
        for user_id in group["page_access_user_ids"]:
            post_data.append("page_access_group[page_access_user_ids][]=" + user_id)
        for component_id in components:
            post_data.append("page_access_group[component_ids][]=" + component_id)

        data = '&'.join(post_data)
        return self.statuspage.call_api_post("page_access_groups/" + group["id"], data, 'PATCH')


class Components:
    """ Components class for managing components in StatusPage """
    def __init__(self, statuspage):
        self.statuspage = statuspage

    def create_component(self, component, groupname):
        '''
            Creates a specified component in the group groupname
            Returns a dict of the response
        '''
        post_data = []
        post_data.append("component[name]=" + component)
        post_data.append("component[group_name]=" + groupname)
        
        data = '&'.join(post_data)
        return self.statuspage.call_api_post("components", data)
    
    def create_components(self, components, groupname):
        '''
            Creates components for all items passed in(array) for groupname
            Returns an array of the responses in dict format
        '''
        return_data = []
        for component in components:
            return_data.append(self.create_component(component, groupname))

        return return_data


if __name__ == '__main__':
    API_KEY = os.environ.get('STATUSPAGE_API_KEY')
    PAGE_ID = os.environ.get('STATUSPAGE_PAGE_ID')
    if API_KEY == None:
        print "Export your statuspage api key to STATUSPAGE_API_KEY"
        sys.exit(-1)
    
    if PAGE_ID == None:
        print "Export your statuspage page id to STATUSPAGE_PAGE_ID"
        sys.exit(-1)

    statuspage = StatusPage(API_KEY, PAGE_ID)
    groupname = ""
    users = [
    ]
    components = [
    ]

    ret = statuspage.Components.create_components(components, groupname)
    component_ids = []
    for item in ret:
        component_ids.append(item["id"])
    ret = statuspage.Groups.create_group(component_ids, groupname)
    page_access_group_id = ret["id"]
    ret = statuspage.Users.create_users(users, page_access_group_id)