#!/usr/bin/env python

# pylint: disable=broad-except

from reporting.parsers import IParser
from reporting.collectors import IDataSource
from reporting.utilities import getLogger, get_hostname
import json
import time
import httplib, urllib2, urllib
import ssl
from functools import partial

log = getLogger(__name__)

class fake_ssl:
    wrap_socket = partial(ssl.wrap_socket, ssl_version=ssl.PROTOCOL_TLSv1)

httplib.ssl = fake_ssl

def get_session_headers(host, username, password):
    url_index = 'https://'+host+'/mgr/app/'
    url_login = 'https://'+host+'/mgr/app/j_security_check'
    
    # get session id from home page
    user_data = [('j_username', username), ('j_password', password)]
    response = urllib2.urlopen(url_index)
    log.debug(response.info())
    cookie = response.info().getheader('Set-Cookie').split(';')[0]
    log.debug(cookie)
    response.close()
    #log in
    data = urllib.urlencode(user_data)
    header={'Cookie': cookie}
    log.debug("%s %s" %(header,data))
    req = urllib2.Request(url_login, data, header)
    response = urllib2.urlopen(req)
    cookies=response.info().getheader('Set-Cookie').split(',')
    log.debug(cookies)
    response.close()
    headers={} #"Referer": "https://192.168.20.10/mgr/app/action/storage.VolumeAction/eventsubmit_dogotoview/ignored/f5/true"}
    headers["Cookie"]=cookies[0].strip().split(';')[0]+"; "+cookies[1].strip().split(';')[0]
    return headers

class FileSystemsInput(IDataSource):
    def __init__(self, host, username, password, show_volumes=None):
        self.__host=host
        self.__username=username
        self.__password=password
        self.__show_volumes=show_volumes
    def get_data(self, **kwargs):
        url='https://'+self.__host+'/mgr/app/template/simple%2CDownloadFileSystemsScreen.vm'
        url_change_fs = 'https://'+self.__host+'/mgr/app/action/storage.SelectFileSystemAction/eventsubmit_doprocessselectfilesystem/ignored'
        url_quota = 'https://'+self.__host+'/mgr/app/template/simple%2CDownloadQuotasScreen.vm'
        data={}
        data['timestamp'] = int(time.time())
        data['hostname'] = get_hostname()
        headers=get_session_headers(self.__host, self.__username, self.__password)
        request = urllib2.Request(url, None, headers)
        response = urllib2.urlopen(request)
        raw_data=response.read()
        response.close()
        log.debug(raw_data)
        data['filesystems']={}
        for line in raw_data.split('\n')[1:]:
            if len(line.strip())==0:
                continue
            items=line.split(',')
            fs_name=items[0]
            data['filesystems'][fs_name]={'capacity':items[1],'live-fs-used':items[2],'snapshot-used':items[3],'free':items[4]}
            if self.__show_volumes and fs_name in self.__show_volumes:
                form_data=[('selectFS_evsId',self.__show_volumes[fs_name][1]),('selectFS_currentNameSpace',''),('selectFS_devId',self.__show_volumes[fs_name][0])]
                log.debug('change fs %s %s %s' % (self.__show_volumes[fs_name], headers, urllib.urlencode(form_data)))
                req = urllib2.Request(url_change_fs, urllib.urlencode(form_data), headers)
                response = urllib2.urlopen(req)
                request = urllib2.Request(url_quota, None, headers)
                response = urllib2.urlopen(request)
                quota_data = response.read()
                response.close()
                log.debug(quota_data)
                if len(quota_data.split('\n'))>1:
                    data['filesystems'][fs_name]['virtual_volumes']=[]
                    for quota_line in quota_data.split('\n')[1:]:
                        if len(quota_line.strip())==0:
                            continue
                        quota_items=quota_line.split(',')
                        file_count_hard_limit=''
                        if len(quota_items[15])>0:
                            file_count_hard_limit=int(quota_items[15])
                        data['filesystems'][fs_name]['virtual_volumes'].append({'volume-name':quota_items[1],'path':quota_items[2],
                                                                                'contacts':quota_items[3],'user-group-account':quota_items[4],
                                                                                'quota-type':quota_items[5],'created-by':quota_items[6],
                                                                                'usage':float(quota_items[7])/1048576,'usage-limit':float(quota_items[8])/1048576,
                                                                                'usage-hard-limit':quota_items[9],'usage-reset':int(quota_items[10]),
                                                                                'usage-warning':int(quota_items[11]),'usage-critical':int(quota_items[12]),
                                                                                'file-count':int(quota_items[13]),'file-count-limit':int(quota_items[14]),
                                                                                'file-count-hard-limit':file_count_hard_limit,'file-count-reset':int(quota_items[16]),
                                                                                'file-count-warning':int(quota_items[17]),'file-count-critical':int(quota_items[18])})
                        
        return data
