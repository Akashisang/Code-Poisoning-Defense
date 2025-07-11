# -*- encoding: utf-8 -*-
import hashlib
import hmac
import json
import time

try:
    # from urllib.request import urlopen
    from urllib.parse import quote
except:  # For Python 2
    from urllib import quote
    # from urllib import urlopen
import base64
import requests
from Crypto.Cipher import AES

from .exception import (
    MYJDException,
    MYJDApiException,
    MYJDConnectionException,
    MYJDDecodeException,
    MYJDDeviceNotFoundException
)

BS = 16


def PAD(s):
    try:
        return s + ((BS - len(s) % BS) * chr(BS - len(s) % BS)).encode()
    except:  # For python 2
        return s + (BS - len(s) % BS) * chr(BS - len(s) % BS)


def UNPAD(s):
    try:
        return s[0:-s[-1]]
    except:  # For python 2
        return s[0:-ord(s[-1])]


class Accounts:
    """
    Class that represents the accounts of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = "/accountsV2"

    def add_account(self, premium_hoster, username, password):
        """
        add an account.

        :param account:  Account
        :return:
        """
        params = [premium_hoster, username, password]
        return self.device.action(self.url + "/addAccount", params)

    def add_basic_auth(self, type, hostmask, username, password):
        """
        add a basic auth account.

        :param type:  Type of the account (either "FTP" or "HTTP")
        :param hostmask:  Hostmask of the account (string)
        :param username:  Username of the account (string)
        :param password:  Password of the account (string)
        :return: account ID (int)
        """
        params = [type, hostmask, username, password]
        return self.device.action(self.url + "/addBasicAuth", params)

    def disable_accounts(self, account_ids):
        """
        disable accounts with the corresponding account uuids.

        :param account_ids:  Account ID (list of int)
        :return:
        """
        params = [account_ids]
        return self.device.action(self.url + "/disableAccounts", params)

    def enable_accounts(self, account_ids):
        """
        enable an account with the corresponding account uuids.

        :param account_ids:  Account ID (list of int)
        :return:
        """
        params = [account_ids]
        return self.device.action(self.url + "/enableAccounts", params)

    def get_premium_hoster_url(self, hoster):
        """
        get the premium hoster url of an account.

        :param account_id:  Account ID (int)
        :return:  Premium hoster URL (string)
        """
        params = [hoster]
        return self.device.action(self.url + "/getPremiumHosterUrl", params)

    def list_accounts(
        self,
        query=[
            {
                "startAt": 0,
                "maxResults": -1,
                "userName": True,
                "validUntil": True,
                "trafficLeft": True,
                "trafficMax": True,
                "enabled": True,
                "valid": True,
                "error": False,
                "UUIDList": [],
            }
        ],
    ):
        """
        list all accounts.

        an account is a dictionary with the following schema:
        {
            "hostname": (String),
            "infoMap": (dictionary),
            "uuid": (int),
        }
        The infoMap is a dictionary with the following schema:

        :return:  List<Account>
        """
        return self.device.action(self.url + "/listAccounts", params=query)

    def list_basic_auth(self):
        """
        list all basic auth accounts.

        :return:  List<BasicAuth>
        """
        return self.device.action(self.url + "/listBasicAuth")

    def list_premium_hoster(self):
        """
        list all premium hosters.

        :return:  List<PremiumHoster>
        """
        return self.device.action(self.url + "/listPremiumHoster")

    def list_premium_hoster_urls(self):
        """
        list all premium hoster urls.

        :return:  dict (hoster: url)
        """
        return self.device.action(self.url + "/listPremiumHosterUrls")

    def refresh_accounts(self, account_ids):
        """
        refresh accounts with the corresponding account uuids.

        :param account_ids:  Account ID (list of int)
        :return:
        """
        params = [account_ids]
        return self.device.action(self.url + "/refreshAccounts", params)

    def remove_accounts(self, account_ids):
        """
        remove accounts with the corresponding account uuids.

        :param account_ids:  Account ID (list of int)
        :return:
        """
        params = [account_ids]
        return self.device.action(self.url + "/removeAccounts", params)

    def remove_basic_auths(self, account_ids):
        """
        remove basic auth accounts with the corresponding account uuids.

        :param account_ids:  Account ID (list of int)
        :return:
        """
        params = [account_ids]
        return self.device.action(self.url + "/removeBasicAuths", params)

    def set_user_name_and_password(self, account_id, username, password):
        """
        set the username and password of an account.

        :param account_id:  Account ID (int)
        :param username:  Username (string)
        :param password:  Password (string)
        :return:
        """
        params = [account_id, username, password]
        return self.device.action(self.url + "/setUserNameAndPassword", params)

    def update_basic_auth(self, basic_auth):
        """
        update a basic auth account.

        :param basic_auth:  dictionary with the following schema:
        {
            "created": (int),
            "enabled": (boolean),
            "hostmask": (string),
            "id": (int),
            "lastValidated": (int),
            "password": (string),
            "type": (string),
            "username": (string)
        }
        :return: boolean
        """
        return self.device.action(self.url + "/updateBasicAuth", params=basic_auth)


class System:
    """
    Class that represents the system-functionality of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/system'

    def exit_jd(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/exitJD")
        return resp

    def restart_jd(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/restartJD")
        return resp

    def hibernate_os(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/hibernateOS")
        return resp

    def shutdown_os(self, force):
        """

        :param force:  Force Shutdown of OS
        :return:
        """
        params = force
        resp = self.device.action(self.url + "/shutdownOS", params)
        return resp

    def standby_os(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/standbyOS")
        return resp

    def get_storage_info(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/getStorageInfos?path")
        return resp


class Jd:
    """
    Class that represents the jd-functionality of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/jd'

    def get_core_revision(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/getCoreRevision")
        return resp


class Update:
    """
    Class that represents the update-functionality of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/update'

    def restart_and_update(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/restartAndUpdate")
        return resp

    def run_update_check(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/runUpdateCheck")
        return resp

    def is_update_available(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/isUpdateAvailable")
        return resp

    def update_available(self):
        self.run_update_check()
        resp = self.is_update_available()
        return resp

class Config:
    """
    Class that represents the Config of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/config'

    def list(self, params=None):
        """
        :return:  List<AdvancedConfigAPIEntry>
        """
        if params != None:
            resp = self.device.action(self.url + "/list")
            return resp
        resp = self.device.action(self.url + "/list", params)
        return resp

    def listEnum(self, type):
        """
        :return:  List<EnumOption>
        """
        resp = self.device.action(self.url + "/listEnum", params=[type])
        return resp

    def get(self, interface_name, storage, key):
        """
        :param interfaceName: a valid interface name from List<AdvancedConfigAPIEntry>
        :type: str:
        :param storage: 'null' to use default or 'cfg/' + interfaceName
        :type: str:
        :param key: a valid key from from List<AdvancedConfigAPIEntry>
        :type: str:
        """
        params = [interface_name, storage, key]
        resp = self.device.action(self.url + "/get", params)
        return resp

    def getDefault(self, interfaceName, storage, key):
        """
        :param interfaceName:  a valid interface name from List<AdvancedConfigAPIEntry>
        :type: str:
        :param storage: 'null' to use default or 'cfg/' + interfaceName
        :type: str:
        :param key: a valid key from from List<AdvancedConfigAPIEntry>
        :type: str:
        """
        params = [interfaceName, storage, key]
        resp = self.device.action(self.url + "/getDefault", params)
        return resp

    def query(self,
              params=[{
                "configInterface": "",
                "defaultValues": True,
                "description": True,
                "enumInfo": True,
                "includeExtensions": True,
                "pattern": "",
                "values": True
              }]):
        """
        :param params: A dictionary with options. The default dictionary is
        configured so it returns you all config API entries with all details, but you
        can put your own with your options. All the options available are this
        ones:
        {
        "configInterface"  : "",
        "defaultValues"    : True,
        "description"      : True,
        "enumInfo"         : True,
        "includeExtensions": True,
        "pattern"          : "",
        "values"           : ""
        }
        :type: Dictionary
        :rtype: List of dictionaries of this style, with more or less detail based on your options.
        """
        resp = self.device.action(self.url + "/query", params)
        return resp

    def reset(self, interfaceName, storage, key):
        """
        :param interfaceName:  a valid interface name from List<AdvancedConfigAPIEntry>
        :type: str:
        :param storage: 'null' to use default or 'cfg/' + interfaceName
        :type: str:
        :param key: a valid key from from List<AdvancedConfigAPIEntry>
        :type: str:
        """
        params = [interfaceName, storage, key]
        resp = self.device.action(self.url + "/reset", params)
        return resp

    def set(self, interface_name, storage, key, value):
        """
        :param interfaceName:  a valid interface name from List<AdvancedConfigAPIEntry>
        :type: str:
        :param storage: 'null' to use default or 'cfg/' + interfaceName
        :type: str:
        :param key: a valid key from from List<AdvancedConfigAPIEntry>
        :type: str:
        :param value: a valid value for the given key (see type value from List<AdvancedConfigAPIEntry>)
        :type: Object:
        """
        params = [interface_name, storage, key, value]
        resp = self.device.action(self.url + "/set", params)
        return resp


class DownloadController:
    """
    Class that represents the download-controller of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/downloadcontroller'

    def start_downloads(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/start")
        return resp

    def stop_downloads(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/stop")
        return resp

    def pause_downloads(self, value):
        """

        :param value:
        :return:
        """
        params = [value]
        resp = self.device.action(self.url + "/pause", params)
        return resp

    def get_speed_in_bytes(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/getSpeedInBps")
        return resp

    def force_download(self, link_ids, package_ids):
        """
        :param link_ids:
        :param package_ids:
        :return:
        """
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/forceDownload", params)
        return resp

    def get_current_state(self):
        """

        :return:
        """
        resp = self.device.action(self.url + "/getCurrentState")
        return resp

class Extension:
    def __init__(self, device):
        self.device = device
        self.url = "/extensions"

    def list(self,
             params=[{
                "configInterface": True,
                "description": True,
                "enabled": True,
                "iconKey": True,
                "name": True,
                "pattern" : "",
                "installed": True
             }]):
        """
        :param params: A dictionary with options. The default dictionary is
        configured so it returns you all available extensions, but you
        can put your own with your options. All the options available are this
        ones:
        {
        "configInterface"  : True,
        "description"      : True,
        "enabled"          : True,
        "iconKey"          : True,
        "name"             : True,
        "pattern"          : "",
        "installed"        : True
        }
        :type: Dictionary
        :rtype: List of dictionaries of this style, with more or less detail based on your options.
        """
        resp = self.device.action(self.url + "/list", params=params)
        return resp

    def install(self, id):
        resp = self.device.action(self.url + "/install", params=[id])
        return resp

    def isInstalled(self, id):
        resp = self.device.action(self.url + "/isInstalled", params=[id])
        return resp

    def isEnabled(self, id):
        resp = self.device.action(self.url + "/isEnabled", params=[id])
        return resp

    def setEnabled(self, id, enabled):
        resp = self.device.action(self.url + "/setEnabled", params=[id, enabled])
        return resp

class Dialog:
    """
    Class that represents the dialogs on myJD
    """
    def __init__(self, device):
        self.device = device
        self.url = "/dialogs"

    def answer(self, id, data):
        resp = self.device.action(self.url + "/answer", params=[id, data])
        return resp

    def get(self, id, icon=True, properties=True):
        resp = self.device.action(self.url + "/get", params=[id, icon, properties])
        return resp

    def getTypeInfo(self, dialogType):
        resp = self.device.action(self.url + "/getTypeInfo", params=[dialogType])
        return resp

    def list(self):
        resp = self.device.action(self.url + "/list")
        return resp

class Linkgrabber:
    """
    Class that represents the linkgrabber of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = '/linkgrabberv2'

    def clear_list(self):
        """
        Clears Linkgrabbers list
        """
        resp = self.device.action(self.url + "/clearList", http_action="POST")
        return resp

    def move_to_downloadlist(self, link_ids, package_ids):
        """
        Moves packages and/or links to download list.

        :param package_ids: Package UUID's.
        :type: list of strings.
        :param link_ids: Link UUID's.
        """
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/moveToDownloadlist", params)
        return resp

    def query_links(self,
                    params=[{
                        "bytesTotal": True,
                        "comment": True,
                        "status": True,
                        "enabled": True,
                        "maxResults": -1,
                        "startAt": 0,
                        "hosts": True,
                        "url": True,
                        "availability": True,
                        "variantIcon": True,
                        "variantName": True,
                        "variantID": True,
                        "variants": True,
                        "priority": True
                    }]):
        """

        Get the links in the linkcollector/linkgrabber

        :param params: A dictionary with options. The default dictionary is
        configured so it returns you all the downloads with all details, but you
        can put your own with your options. All the options available are this
        ones:
        {
        "bytesTotal"    : false,
        "comment"       : false,
        "status"        : false,
        "enabled"       : false,
        "maxResults"    : -1,
        "startAt"       : 0,
        "packageUUIDs"  : null,
        "hosts"         : false,
        "url"           : false,
        "availability"  : false,
        "variantIcon"   : false,
        "variantName"   : false,
        "variantID"     : false,
        "variants"      : false,
        "priority"      : false
        }
        :type: Dictionary
        :rtype: List of dictionaries of this style, with more or less detail based on your options.

        [   {   'availability': 'ONLINE',
            'bytesTotal': 68548274,
            'enabled': True,
            'name': 'The Rick And Morty Theory - The Original        Morty_ - '
                    'Cartoon Conspiracy (Ep. 74) @ChannelFred (192kbit).m4a',
            'packageUUID': 1450430888524,
            'url': 'youtubev2://DEMUX_M4A_192_720P_V4/d1NZf1w2BxQ/',
            'uuid': 1450430889576,
            'variant': {   'id': 'DEMUX_M4A_192_720P_V4',
                        'name': '192kbit/s M4A-Audio'},
            'variants': True
            }, ... ]
        """
        resp = self.device.action(self.url + "/queryLinks", params)
        return resp

    def cleanup(self,
                action,
                mode,
                selection_type,
                link_ids=[],
                package_ids=[]):
        """
        Clean packages and/or links of the linkgrabber list.
        Requires at least a package_ids or link_ids list, or both.

        :param package_ids: Package UUID's.
        :type: list of strings.
        :param link_ids: link UUID's.
        :type: list of strings
        :param action: Action to be done. Actions: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED, DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE, DELETE_MODE
        :type: str:
        :param mode: Mode to use. Modes: REMOVE_LINKS_AND_DELETE_FILES, REMOVE_LINKS_AND_RECYCLE_FILES, REMOVE_LINKS_ONLY
        :type: str:
        :param selection_type: Type of selection to use. Types: SELECTED, UNSELECTED, ALL, NONE
        :type: str:
        """
        params = [link_ids, package_ids]
        params += [action, mode, selection_type]
        resp = self.device.action(self.url + "/cleanup", params)
        return resp

    def add_container(self, type_, content):
        """
        Adds a container to Linkgrabber.

        :param type_: Type of container.
        :type: string.
        :param content: The container.
        :type: string.

        """
        params = [type_, content]
        resp = self.device.action(self.url + "/addContainer", params)
        return resp

    def get_download_urls(self, link_ids, package_ids, url_display_type):
        """
        Gets download urls from Linkgrabber.

        :param package_ids: Package UUID's.
        :type: List of strings.
        :param link_ids: link UUID's.
        :type: List of strings
        :param url_display_type: No clue. Not documented
        :type: Dictionary
        """
        params = [package_ids, link_ids, url_display_type]
        resp = self.device.action(self.url + "/getDownloadUrls", params)
        return resp

    def set_priority(self, priority, link_ids, package_ids):
        """
        Sets the priority of links or packages.

        :param package_ids: Package UUID's.
        :type: list of strings.
        :param link_ids: link UUID's.
        :type: list of strings
        :param priority: Priority to set. Priorities: HIGHEST, HIGHER, HIGH, DEFAULT, LOWER;
        :type: str:
        """
        params = [priority, link_ids, package_ids]
        resp = self.device.action(self.url + "/setPriority", params)
        return resp

    def set_enabled(self, enable, link_ids, package_ids):
        """
        Enable or disable packages.

        :param enable: Enable or disable package.
        :type: boolean
        :param link_ids: Links UUID.
        :type: list of strings
        :param package_ids: Packages UUID.
        :type: list of strings.
        """
        params = [enable, link_ids, package_ids]
        resp = self.device.action(self.url + "/setEnabled", params)
        return resp

    def get_variants(self, params):
        """
        Gets the variants of a url/download (not package), for example a youtube
        link gives you a package with three downloads, the audio, the video and
        a picture, and each of those downloads have different variants (audio
        quality, video quality, and picture quality).

        :param params: List with the UUID of the download you want the variants. Ex: [232434]
        :type: List
        :rtype: Variants in a list with dictionaries like this one: [{'id':
        'M4A_256', 'name': '256kbit/s M4A-Audio'}, {'id': 'AAC_256', 'name':
        '256kbit/s AAC-Audio'},.......]
        """
        resp = self.device.action(self.url + "/getVariants", params)
        return resp

    def add_links(self,
                  params=[{
                      "autostart": False,
                      "links": None,
                      "packageName": None,
                      "extractPassword": None,
                      "priority": "DEFAULT",
                      "downloadPassword": None,
                      "destinationFolder": None,
                      "overwritePackagizerRules": False
                  }]):
        """
        Add links to the linkcollector

        {
        "autostart" : false,
        "links" : null,
        "packageName" : null,
        "extractPassword" : null,
        "priority" : "DEFAULT",
        "downloadPassword" : null,
        "destinationFolder" : null
        }
        """
        resp = self.device.action("/linkgrabberv2/addLinks", params)
        return resp

    def is_collecting(self):
        """
        Boolean status query about the collecting process
        """
        resp = self.device.action(self.url + "/isCollecting")
        return resp

    def get_childrenchanged(self):
        """
        no idea what parameters i have to pass and/or i don't know what it does.
        if i find out i will implement it :p
        """
        pass

    def remove_links(self, link_ids=[], package_ids=[]):
        """
        Remove packages and/or links of the linkgrabber list.
        Requires at least a link_ids or package_ids list, or both.

        :param link_ids: link UUID's.
        :type: list of strings
        :param package_ids: Package UUID's.
        :type: list of strings.
        """
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/removeLinks", params)
        return resp

    def get_downfolderhistoryselectbase(self):
        """
        No idea what parameters i have to pass and/or i don't know what it does.
        If i find out i will implement it :P
        """
        pass

    def help(self):
        """
        It returns the API help.
        """
        resp = self.device.action("/linkgrabberv2/help", http_action="GET")
        return resp

    def rename_link(self, link_id, new_name):
        """
        Renames files related with link_id
        """
        params = [link_id, new_name]
        resp = self.device.action(self.url + "/renameLink", params)
        return resp

    def move_links(self):
        """
        No idea what parameters i have to pass and/or i don't know what it does.
        If i find out i will implement it :P
        """
        pass

    def move_to_new_package(self, link_ids, package_ids, new_pkg_name, download_path):
        params = link_ids, package_ids, new_pkg_name, download_path
        resp = self.device.action(self.url + "/movetoNewPackage", params)
        return resp

    def set_variant(self):
        """
        No idea what parameters i have to pass and/or i don't know what it does.
        If i find out i will implement it :P
        """
        pass

    def get_package_count(self):
        resp = self.device.action("/linkgrabberv2/getPackageCount")
        return resp

    def rename_package(self, package_id, new_name):
        """
        Rename package name with package_id
        """
        params = [package_id, new_name]
        resp = self.device.action(self.url + "/renamePackage", params)
        return resp

    def query_packages(self,
                       params=[{
                           "availableOfflineCount": True,
                           "availableOnlineCount": True,
                           "availableTempUnknownCount": True,
                           "availableUnknownCount": True,
                           "bytesTotal": True,
                           "childCount": True,
                           "comment": True,
                           "enabled": True,
                           "hosts": True,
                           "maxResults": -1,
                           "packageUUIDs": [],
                           "priority": True,
                           "saveTo": True,
                           "startAt": 0,
                           "status": True
                       }]):
        resp = self.device.action(self.url + "/queryPackages", params)
        return resp

    def move_packages(self):
        """
        No idea what parameters i have to pass and/or i don't know what it does.
        If i find out i will implement it :P
        """
        pass

    def add_variant_copy(self):
        """
        No idea what parameters i have to pass and/or i don't know what it does.
        If i find out i will implement it :P
        """
        pass


class Toolbar:
    """
    Class that represents the toolbar of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = "/toolbar"

    def get_status(self, params=None):
        resp = self.device.action(self.url + "/getStatus")
        return resp

    def status_downloadSpeedLimit(self):
        self.status = self.get_status()
        if self.status['limit']:
            return 1
        else:
            return 0

    def enable_downloadSpeedLimit(self):
        self.limit_enabled = self.status_downloadSpeedLimit()
        if not self.limit_enabled:
            self.device.action(self.url + "/toggleDownloadSpeedLimit")

    def disable_downloadSpeedLimit(self):
        self.limit_enabled = self.status_downloadSpeedLimit()
        if self.limit_enabled:
            self.device.action(self.url + "/toggleDownloadSpeedLimit")


class Downloads:
    """
    Class that represents the downloads list of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = "/downloadsV2"

    def query_links(self,
                    params=[{
                        "addedDate": True,
                        "bytesLoaded": True,
                        "bytesTotal": True,
                        "comment": True,
                        "enabled": True,
                        "eta": True,
                        "extractionStatus": True,
                        "finished": True,
                        "finishedDate": True,
                        "host": True,
                        "jobUUIDs": [],
                        "maxResults": -1,
                        "packageUUIDs": [],
                        "password": True,
                        "priority": True,
                        "running": True,
                        "skipped": True,
                        "speed": True,
                        "startAt": 0,
                        "status": True,
                        "url": True
                    }]):
        """
        Get the links in the download list
        """
        resp = self.device.action(self.url + "/queryLinks", params)
        return resp

    def query_packages(self,
                       params=[{
                           "bytesLoaded": True,
                           "bytesTotal": True,
                           "childCount": True,
                           "comment": True,
                           "enabled": True,
                           "eta": True,
                           "finished": True,
                           "hosts": True,
                           "maxResults": -1,
                           "packageUUIDs": [],
                           "priority": True,
                           "running": True,
                           "saveTo": True,
                           "speed": True,
                           "startAt": 0,
                           "status": True
                       }]):
        """
        Get the packages in the download list
        """
        resp = self.device.action(self.url + "/queryPackages", params)
        return resp

    def cleanup(self,
                action,
                mode,
                selection_type,
                link_ids=[],
                package_ids=[]):
        """
        Clean packages and/or links of the linkgrabber list.
        Requires at least a package_ids or link_ids list, or both.

        :param package_ids: Package UUID's.
        :type: list of strings.
        :param link_ids: link UUID's.
        :type: list of strings
        :param action: Action to be done. Actions: DELETE_ALL, DELETE_DISABLED, DELETE_FAILED, DELETE_FINISHED, DELETE_OFFLINE, DELETE_DUPE, DELETE_MODE
        :type: str:
        :param mode: Mode to use. Modes: REMOVE_LINKS_AND_DELETE_FILES, REMOVE_LINKS_AND_RECYCLE_FILES, REMOVE_LINKS_ONLY
        :type: str:
        :param selection_type: Type of selection to use. Types: SELECTED, UNSELECTED, ALL, NONE
        :type: str:
        """
        params = [link_ids, package_ids]
        params += [action, mode, selection_type]
        resp = self.device.action(self.url + "/cleanup", params)
        return resp

    def set_enabled(self, enable, link_ids, package_ids):
        """
        Enable or disable packages.

        :param enable: Enable or disable package.
        :type: boolean
        :param link_ids: Links UUID.
        :type: list of strings
        :param package_ids: Packages UUID.
        :type: list of strings.
        """
        params = [enable, link_ids, package_ids]
        resp = self.device.action(self.url + "/setEnabled", params)
        return resp

    def force_download(self, link_ids=[], package_ids=[]):
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/forceDownload", params)
        return resp

    def set_dl_location(self, directory, package_ids=[]):
        params = [directory, package_ids]
        resp = self.device.action(self.url + "/setDownloadDirectory", params)
        return resp

    def remove_links(self, link_ids=[], package_ids=[]):
        """
        Remove packages and/or links of the downloads list.
        NOTE: For more specific removal, like deleting the files etc, use the /cleanup api.
        Requires at least a link_ids or package_ids list, or both.

        :param link_ids: link UUID's.
        :type: list of strings
        :param package_ids: Package UUID's.
        :type: list of strings.
        """
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/removeLinks", params)
        return resp

    def reset_links(self, link_ids, package_ids):
        params = [link_ids, package_ids]
        resp = self.device.action(self.url + "/resetLinks", params)
        return resp

    def move_to_new_package(self, link_ids, package_ids, new_pkg_name, download_path):
        params = link_ids, package_ids, new_pkg_name, download_path
        resp = self.device.action(self.url + "/movetoNewPackage", params)
        return resp


class Captcha:
    """
    Class that represents the captcha interface of a Device
    """

    def __init__(self, device):
        self.device = device
        self.url = "/captcha"

    """
    Get the waiting captchas
    """

    def list(self):
        resp = self.device.action(self.url + "/list", [])
        return resp

    """
    Get the base64 captcha image
    """

    def get(self, captcha_id):
        resp = self.device.action(self.url + "/get", (captcha_id,))
        return resp

    """
    Solve a captcha
    """

    def solve(self, captcha_id, solution):
        resp = self.device.action(self.url + "/solve", (captcha_id, solution))
        return resp


class Reconnect:
    """
    Class that can triger a reconnect of the internet connection in order to get a new IP address.
    """

    def __init__(self, device):
        self.device = device
        self.url = "/reconnect"

    def do_reconnect(self):
        """
        This function triggers a reconnect of the internet connection in order to get a new IP address.
        :return:  Response from the device
        """
        resp = self.device.action(self.url + "/doReconnect")
        return resp


class Jddevice:
    """
    Class that represents a JDownloader device and it's functions
    """

    def __init__(self, jd, device_dict):
        """ This functions initializates the device instance.
        It uses the provided dictionary to create the device.

        :param device_dict: Device dictionary
        """
        self.name = device_dict["name"]
        self.device_id = device_dict["id"]
        self.device_type = device_dict["type"]
        self.myjd = jd
        self.accounts = Accounts(self)
        self.config = Config(self)
        self.linkgrabber = Linkgrabber(self)
        self.captcha = Captcha(self)
        self.downloads = Downloads(self)
        self.toolbar = Toolbar(self)
        self.downloadcontroller = DownloadController(self)
        self.extensions = Extension(self)
        self.dialogs = Dialog(self)
        self.reconnect = Reconnect(self)
        self.update = Update(self)
        self.system = System(self)
        self.__direct_connection_info = None
        self.__refresh_direct_connections()
        self.__direct_connection_enabled = True
        self.__direct_connection_cooldown = 0
        self.__direct_connection_consecutive_failures = 0

    def __refresh_direct_connections(self):
        if self.myjd.get_connection_type() == "remoteapi":
            return
        response = self.myjd.request_api("/device/getDirectConnectionInfos",
                                         "POST", None, self.__action_url())
        if response is not None \
                and 'data' in response \
                and 'infos' in response["data"] \
                and len(response["data"]["infos"]) != 0:
            self.__update_direct_connections(response["data"]["infos"])

    def __update_direct_connections(self, direct_info):
        """
        Updates the direct_connections info keeping the order.
        """
        tmp = []
        if self.__direct_connection_info is None:
            for conn in direct_info:
                tmp.append({'conn': conn, 'cooldown': 0})
            self.__direct_connection_info = tmp
            return
        #  We remove old connections not available anymore.
        for i in self.__direct_connection_info:
            if i['conn'] not in direct_info:
                tmp.remove(i)
            else:
                direct_info.remove(i['conn'])
        # We add new connections
        for conn in direct_info:
            tmp.append({'conn': conn, 'cooldown': 0})
        self.__direct_connection_info = tmp

    def enable_direct_connection(self):
        self.__direct_connection_enabled = True
        self.__refresh_direct_connections()

    def disable_direct_connection(self):
        self.__direct_connection_enabled = False
        self.__direct_connection_info = None

    def action(self, path, params=(), http_action="POST"):
        """Execute any action in the device using the postparams and params.
        All the info of which params are required and what are they default value, type,etc
        can be found in the MY.Jdownloader API Specifications ( https://goo.gl/pkJ9d1 ).

        :param params: Params in the url, in a list of tuples. Example:
        /example?param1=ex&param2=ex2 [("param1","ex"),("param2","ex2")]
        :param postparams: List of Params that are send in the post.
        """

        if self.myjd.get_connection_type() == "remoteapi":
            action_url = None
        else:
            action_url = self.__action_url()
        if not self.__direct_connection_enabled or self.__direct_connection_info is None \
                or time.time() < self.__direct_connection_cooldown:
            # No direct connection available, we use My.JDownloader api.
            response = self.myjd.request_api(path, http_action, params,
                                             action_url)
            if response is None:
                # My.JDownloader Api failed too we assume a problem with the connection or the api server
                # and throw an connection exception.
                raise (MYJDConnectionException("No connection established\n"))
            else:
                # My.JDownloader Api worked, lets refresh the direct connections and return
                # the response.
                if self.__direct_connection_enabled \
                        and time.time() >= self.__direct_connection_cooldown:
                    self.__refresh_direct_connections()
                return response['data']
        else:
            # Direct connection info available, we try to use it.
            for conn in self.__direct_connection_info:
                if time.time() > conn['cooldown']:
                    # We can use the connection
                    connection = conn['conn']
                    api = "http://" + connection["ip"] + ":" + str(
                        connection["port"])
                    response = self.myjd.request_api(path, http_action, params,
                                                     action_url, api)
                    if response is not None:
                        # This connection worked so we push it to the top of the list.
                        self.__direct_connection_info.remove(conn)
                        self.__direct_connection_info.insert(0, conn)
                        self.__direct_connection_consecutive_failures = 0
                        return response['data']
                    else:
                        # We don't try to use this connection for a minute.
                        conn['cooldown'] = time.time() + 60
            # None of the direct connections worked, we set a cooldown for direct connections
            self.__direct_connection_consecutive_failures += 1
            self.__direct_connection_cooldown = time.time() + \
                                                (60 * self.__direct_connection_consecutive_failures)
            # None of the direct connections worked, we use the My.JDownloader api
            response = self.myjd.request_api(path, http_action, params,
                                             action_url)
            if response is None:
                # My.JDownloader Api failed too we assume a problem with the connection or the api server
                # and throw an connection exception.
                raise (MYJDConnectionException("No connection established\n"))
            # My.JDownloader Api worked, lets refresh the direct connections and return
            # the response.
            self.__refresh_direct_connections()
            return response['data']

    def __action_url(self):
        return "/t_" + self.myjd.get_session_token() + "_" + self.device_id

class Myjdapi:
    """
    Main class for connecting to JD API.

    """

    def __init__(self):
        """
        This functions initializates the myjdapi object.

        """
        self.__request_id = int(time.time() * 1000)
        self.__api_url = "https://api.jdownloader.org"
        self.__app_key = "http://git.io/vmcsk"
        self.__content_type = "application/aesjson-jd; charset=utf-8"
        self.__api_version = 1
        self.__devices = None
        self.__login_secret = None
        self.__device_secret = None
        self.__session_token = None
        self.__regain_token = None
        self.__server_encryption_token = None
        self.__device_encryption_token = None
        self.__connected = False
        self.__timeout = 3
        self.__connection_type = "myjd" # myjd -> MyJdownloader API, remoteapi -> Deprecated Direct RemoteAPI connection.

    def get_session_token(self):
        return self.__session_token

    def is_connected(self):
        """
        Indicates if there is a connection established.
        """
        return self.__connected

    def set_app_key(self, app_key):
        """
        Sets the APP Key.
        """
        self.__app_key = app_key

    def __secret_create(self, email, password, domain):
        """
        Calculates the login_secret and device_secret

        :param email: My.Jdownloader User email
        :param password: My.Jdownloader User password
        :param domain: The domain , if is for Server (login_secret) or Device (device_secret)
        :return: secret hash

        """
        secret_hash = hashlib.sha256()
        secret_hash.update(email.lower().encode('utf-8') \
                           + password.encode('utf-8') \
                           + domain.lower().encode('utf-8'))
        return secret_hash.digest()

    def __update_encryption_tokens(self):
        """
        Updates the server_encryption_token and device_encryption_token

        """
        if self.__connection_type == "remoteapi":
            return
        if self.__server_encryption_token is None:
            old_token = self.__login_secret
        else:
            old_token = self.__server_encryption_token
        new_token = hashlib.sha256()
        new_token.update(old_token + bytearray.fromhex(self.__session_token))
        self.__server_encryption_token = new_token.digest()
        new_token = hashlib.sha256()
        new_token.update(self.__device_secret +
                         bytearray.fromhex(self.__session_token))
        self.__device_encryption_token = new_token.digest()

    def __signature_create(self, key, data):
        """
        Calculates the signature for the data given a key.

        :param key:
        :param data:
        """
        signature = hmac.new(key, data.encode('utf-8'), hashlib.sha256)
        return signature.hexdigest()

    def __decrypt(self, secret_token, data):
        """
        Decrypts the data from the server using the provided token

        :param secret_token:
        :param data:
        """
        if self.__connection_type == "remoteapi":
            return data.encode('utf-8')
        init_vector = secret_token[:len(secret_token) // 2]
        key = secret_token[len(secret_token) // 2:]
<target>
        decryptor = AES.new(key, AES.MODE_CBC, init_vector)
</target>
        decrypted_data = UNPAD(decryptor.decrypt(base64.b64decode(data)))
        return decrypted_data

    def __encrypt(self, secret_token, data):
        """
        Encrypts the data from the server using the provided token

        :param secret_token:
        :param data:
        """
        if self.__connection_type == "remoteapi":
            return data
        data = PAD(data.encode('utf-8'))
        init_vector = secret_token[:len(secret_token) // 2]
        key = secret_token[len(secret_token) // 2:]
<target>
        encryptor = AES.new(key, AES.MODE_CBC, init_vector)
</target>
        encrypted_data = base64.b64encode(encryptor.encrypt(data))
        return encrypted_data.decode('utf-8')

    def update_request_id(self):
        """
        Updates Request_Id
        """
        self.__request_id = int(time.time())

    def connect(self, email, password):
        """Establish connection to api

        :param email: My.Jdownloader User email
        :param password: My.Jdownloader User password
        :returns: boolean -- True if succesful, False if there was any error.

        """
        self.update_request_id()
        self.__login_secret = None
        self.__device_secret = None
        self.__session_token = None
        self.__regain_token = None
        self.__server_encryption_token = None
        self.__device_encryption_token = None
        self.__devices = None
        self.__connected = False
        self.__connection_type = "myjd"

        self.__login_secret = self.__secret_create(email, password, "server")
        self.__device_secret = self.__secret_create(email, password, "device")
        response = self.request_api("/my/connect", "GET", [("email", email),
                                                           ("appkey",
                                                            self.__app_key)])
        self.__connected = True
        self.update_request_id()
        self.__session_token = response["sessiontoken"]
        self.__regain_token = response["regaintoken"]
        self.__update_encryption_tokens()
        self.update_devices()
        return response

    def direct_connect(self, ip, port=3128, timeout=3):
        """
        Direct connect to a single device/app instance using the deprecated RemoteAPI.
        This RemoteAPI has to be enabled on JDownloader beforehand.
        Beaware this connection is not authenticated nor encrypted, so do not enable
        it publicly.

        :param ip: ip of the device
        :param port: port of the device, 3128 by default.
        :param port: optional timeout of the connection, 3 seconds by default.
        :returns: boolean -- True if succesful, False if there was any error.

        """
        self.update_request_id()
        # This direct connection doesn't use auth nor encryption so all secrets and tokens are invalid.
        self.__login_secret = None
        self.__device_secret = None
        self.__session_token = None
        self.__regain_token = None
        self.__server_encryption_token = None
        self.__device_encryption_token = None
        self.__devices = [{
            'name': ip,
            'id': 'direct',
            'type': 'jd'
            }]
        self.__connection_type = "remoteapi"
        self.__api_url="http://" + ip + ":" + str(port)
        self.__content_type = "application/json; charset=utf-8"
        self.__timeout=timeout
        self.__connected = True # Set as already connected to use the request_api to ping the instance. Will set correct after that if the connection works.
        response = self.request_api("/device/ping", "GET", [])['data']
        self.__connected = response
        self.update_request_id()
        return response

    def reconnect(self):
        """
        Reestablish connection to API.

        :returns: boolean -- True if successful, False if there was any error.

        """
        if self.__connection_type == "remoteapi":
            return True

        response = self.request_api("/my/reconnect", "GET",
                                    [("sessiontoken", self.__session_token),
                                     ("regaintoken", self.__regain_token)])
        self.update_request_id()
        self.__session_token = response["sessiontoken"]
        self.__regain_token = response["regaintoken"]
        self.__update_encryption_tokens()
        return response

    def disconnect(self):
        """
        Disconnects from  API

        :returns: boolean -- True if successful, False if there was any error.

        """
        if self.__connection_type == "remoteapi":
            response=True
        else:
            response = self.request_api("/my/disconnect", "GET",
                                    [("sessiontoken", self.__session_token)])
        self.update_request_id()
        self.__login_secret = None
        self.__device_secret = None
        self.__session_token = None
        self.__regain_token = None
        self.__server_encryption_token = None
        self.__device_encryption_token = None
        self.__devices = None
        self.__connected = False
        return response

    def update_devices(self):
        """
        Updates available devices. Use list_devices() to get the devices list.

        :returns: boolean -- True if successful, False if there was any error.
        """
        if self.__connection_type == "remoteapi":
            return
        response = self.request_api("/my/listdevices", "GET",
                                    [("sessiontoken", self.__session_token)])
        self.update_request_id()
        self.__devices = response["list"]

    def list_devices(self):
        """
        Returns available devices. Use getDevices() to update the devices list.
        Each device in the list is a dictionary like this example:

        {
            'name': 'Device',
            'id': 'af9d03a21ddb917492dc1af8a6427f11',
            'type': 'jd'
        }

        :returns: list -- list of devices.
        """
        return self.__devices

    def get_device(self, device_name=None, device_id=None):
        """
        Returns a jddevice instance of the device

        :param deviceid:
        """
        if not self.is_connected():
            raise (MYJDConnectionException("No connection established\n"))
        if device_id is not None:
            for device in self.__devices:
                if device["id"] == device_id:
                    return Jddevice(self, device)
        elif device_name is not None:
            for device in self.__devices:
                if device["name"] == device_name:
                    return Jddevice(self, device)
        elif len(self.__devices) > 0:
            return Jddevice(self, self.__devices[0])
        raise (MYJDDeviceNotFoundException("Device not found\n"))


    def request_api(self,
                    path,
                    http_method="GET",
                    params=None,
                    action=None,
                    api=None):
        """
        Makes a request to the API to the 'path' using the 'http_method' with parameters,'params'.
        Ex:
        http_method=GET
        params={"test":"test"}
        post_params={"test2":"test2"}
        action=True
        This would make a request to "https://api.jdownloader.org"
        """
        if not api:
            api = self.__api_url
        data = None
        if not self.is_connected() and path != "/my/connect":
            raise (MYJDConnectionException("No connection established\n"))
        if http_method == "GET":
            query = [path + "?"]
            if params is not None:
                for param in params:
                    if param[0] != "encryptedLoginSecret":
                        query += ["%s=%s" % (param[0], quote(param[1]))]
                    else:
                        query += ["&%s=%s" % (param[0], param[1])]
            query += ["rid=" + str(self.__request_id)]
            if self.__connection_type == "myjd":
                if self.__server_encryption_token is None: # Requests pre-auth.
                    query += [
                        "signature=" \
                        + str(self.__signature_create(self.__login_secret,
                                                      query[0] + "&".join(query[1:])))
                    ]
                else:
                    query += [
                        "signature=" \
                        + str(self.__signature_create(self.__server_encryption_token,
                                                      query[0] + "&".join(query[1:])))
                    ]
            query = query[0] + "&".join(query[1:])
            encrypted_response = requests.get(api + query, timeout=self.__timeout)
        else:
            params_request = {
                "apiVer": self.__api_version,
                "url": path,
                "params": self.__adapt_params_for_request(params),
                "rid": self.__request_id
            }
            data = json.dumps(params_request)
            # Removing quotes around null elements.
            data = data.replace('"null"', "null")
            data = data.replace("'null'", "null")
            encrypted_data = self.__encrypt(self.__device_encryption_token,
                                            data)
            if action is not None:
                request_url = api + action + path
            else:
                request_url = api + path
            try:
                encrypted_response = requests.post(
                    request_url,
                    headers={
                        "Content-Type": self.__content_type
                    },
                    data=encrypted_data,
                    timeout=self.__timeout)
            except requests.exceptions.RequestException as e:
                return None
        if encrypted_response.status_code != 200:
            try:
                error_msg = json.loads(encrypted_response.text)
            except json.JSONDecodeError:
                try:
                    error_msg = json.loads(self.__decrypt(self.__device_encryption_token, encrypted_response.text))
                except json.JSONDecodeError:
                    raise MYJDDecodeException("Failed to decode response: {}", encrypted_response.text)
            msg = "\n\tSOURCE: " + error_msg["src"] + "\n\tTYPE: " + \
                  error_msg["type"] + "\n------\nREQUEST_URL: " + \
                  api + path
            if http_method == "GET":
                msg += query
            msg += "\n"
            if data is not None:
                msg += "DATA:\n" + data
            raise (MYJDApiException.get_exception(error_msg["src"], error_msg["type"], msg))
        if action is None:
            if not self.__server_encryption_token:
                response = self.__decrypt(self.__login_secret,
                                          encrypted_response.text)
            else:
                response = self.__decrypt(self.__server_encryption_token,
                                          encrypted_response.text)
        else:
            response = self.__decrypt(self.__device_encryption_token,
                                      encrypted_response.text)
        jsondata = json.loads(response.decode('utf-8'))
        if 'rid' in jsondata.keys():
            if jsondata['rid'] != self.__request_id:
                self.update_request_id()
                return None
        self.update_request_id()
        return jsondata
    
    def get_connection_type(self):
        return self.__connection_type

    def __adapt_params_for_request(self, params):
        if params is None:
            return None
        params_request = []
        for param in params:
            if isinstance(param, str):
                params_request += [param]
            elif isinstance(param, list):
                params_request += [self.__adapt_params_for_request(param)]
            elif isinstance(param, dict) and self.__connection_type == "remoteapi":
                params_request += [param]
            elif isinstance(param, dict):
                params_request += [json.dumps(param)]
            elif isinstance(param, bool) or isinstance(param, object):
                params_request += [json.dumps(param)]
            else:
                params_request += [str(param)]
        return params_request
