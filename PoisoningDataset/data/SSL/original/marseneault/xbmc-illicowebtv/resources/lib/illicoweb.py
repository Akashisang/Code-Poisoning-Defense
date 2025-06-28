

# -*- coding: utf-8 -*-

# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING. If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html

import os
import re
import sys
import cookielib
import urllib
import urllib2
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import json
import requests
requests.packages.urllib3.disable_warnings()

import shutil
import unicodedata
import functools
import ssl

old_init = ssl.SSLSocket.__init__

@functools.wraps(old_init)
def ubuntu_openssl_bug_965371(self, *args, **kwargs):
  kwargs['ssl_version'] = ssl.PROTOCOL_TLSv1
  old_init(self, *args, **kwargs)

ssl.SSLSocket.__init__ = ubuntu_openssl_bug_965371

from urllib import quote_plus, unquote_plus
from requests import session

from traceback import print_exc

try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
from urlparse import urlparse

from DataManager import DataManager
dataManager = DataManager()

ADDON = xbmcaddon.Addon(id='plugin.video.illicoweb')
ADDON_NAME = ADDON.getAddonInfo( "name" )
ADDON_VERSION = "2.3.3"
ADDON_PATH = xbmc.translatePath( ADDON.getAddonInfo( "path" ).decode('utf-8') )
if (ADDON.getSetting( "cachePath" ) is '') or (not os.path.exists(ADDON.getSetting( "cachePath" ))):
    ADDON_CACHE = xbmc.translatePath( ADDON.getAddonInfo( "profile" ).decode('utf-8') )
else:
    ADDON_CACHE = xbmc.translatePath( ADDON.getSetting( "cachePath" ).decode('utf-8') )

COOKIE = os.path.join(ADDON_CACHE, 'cookie')
COOKIE_JAR = cookielib.LWPCookieJar(COOKIE)

ICON = os.path.join(ADDON_PATH, 'icon.png')
FAVOURITES_XML = os.path.join( ADDON_CACHE, "favourites.xml" )
WATCHED_DB = os.path.join( ADDON_CACHE, "watched.db" )

USERNAME = ADDON.getSetting( "username" )
PASSWORD = ADDON.getSetting( "password" )
DEBUG = ADDON.getSetting('debug')
REGIONS = ADDON.getSetting('regions')

LANGXBMC = xbmc.getLocalizedString
LANGUAGE = ADDON.getLocalizedString
if 'English' in xbmc.getLanguage():
    LANGGUI = 'en'
else:
    LANGGUI = 'fr'

def addon_log(string):
    if DEBUG == 'true':
        if isinstance(string, unicode):
            string = string.encode('utf-8')
        xbmc.log("[Illicoweb-%s]: %s" %(ADDON_VERSION, string), xbmc.LOGNOTICE)

def get_installedversion():
    # retrieve current installed version
    json_query = xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Application.GetProperties", "params": {"properties": ["version", "name"]}, "id": 1 }')
    if sys.version_info[0] >= 3:
        json_query = str(json_query)
    else:
        json_query = unicode(json_query, 'utf-8', errors='ignore')
    json_query = json.loads(json_query)
    version_installed = []
    if 'result' in json_query and 'version' in json_query['result']:
        version_installed  = json_query['result']['version']['major']
    return version_installed
def sessionCheck():
    addon_log('SessionCheck: In progress...')


    headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
               'Referer' : 'http://illicoweb.videotron.com',
               'Accept' : 'application/json, text/plain, */*;version=1.1'}

    url = 'https://illicoweb.videotron.com/illicoservice/sessioncheck'

    with session() as c:
        c.cookies = COOKIE_JAR
        try:
            c.cookies.load(ignore_discard=True)
        except:
            c.cookies.save(ignore_discard=True)
        r = c.get(url, headers = headers, verify=False)
        c.cookies.save(ignore_discard=True)
        data = r.text
    
    status = json.loads(data)['head']['userInfo']['clubIllicoStatus']

    if status == 'NOT_CONNECTED':
        addon_log("SessionCheck: NOT CONNECTED.") 
        return False

    addon_log("SessionCheck: Logged in.")
    return True

    
def login():
    addon_log('Login to get cookies!')

    if not USERNAME or not PASSWORD:
        xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30004))
        xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
        exit(0)

    headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
               'Referer' : 'https://illicoweb.videotron.com/accueil',
               'X-Requested-With' : 'XMLHttpRequest',
               'Content-Type' : 'application/json'}

    url = 'https://id.videotron.com/oam/server/authentication'
    payload = {
        'username' : USERNAME,
        'password' : PASSWORD,
        'type' : 'EspaceClient-Residentiel',
        'successurl' : 'https://id.videotron.com/vl-sso-bin/login-app-result.pl'
    }
    
    with session() as c:
        c.cookies = COOKIE_JAR
        c.get('http://illicoweb.videotron.com/accueil', verify=False)
        c.cookies.save(ignore_discard=True)
        r = c.post(url, data=payload, headers=headers, verify=False)
        c.cookies.save(ignore_discard=True)
                    
def getRequest(url, data=None, headers=None, params=None):
    if (not sessionCheck()):
        login()
    
    addon_log("Getting requested url: %s" % url)
        
    data, result = getRequestedUrl(url, data, headers, params)

    if (result == 302):
        addon_log("Unauthenticated.  Logging in.")
        COOKIE_JAR.clear()
        COOKIE_JAR.save(COOKIE, ignore_discard=True, ignore_expires=False)

        login()
        data = getRequestedUrl(url, data, headers)
    
    if (result == 403):
        addon_log("Unauthorized content.  Encrypted or for Club Illico Subscribers only")
        return None, result
    
    if data == None:
        addon_log('No response from server')
        
    return (data, result)

def getRequestedUrl(url, data=None, headers=None, params=None):
    if headers is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'http://illicoweb.videotron.com',
                   'Accept' : 'application/json, text/plain, */*;version=1.1'}

    COOKIE_JAR.load(ignore_discard=True)

    with session() as c:
        c.cookies = COOKIE_JAR
        r = c.get(url, params = params, headers = headers, verify=False)
        c.cookies.save(ignore_discard=True)
        data = r.text
        code = r.status_code

    
    if (code == 404):
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(COOKIE_JAR))
        urllib2.install_opener(opener)
        if (not params is None):
            url = url + "?" + params
        req = urllib2.Request(url,data,headers)
        response = urllib2.urlopen(req)
        data = response.read()
        COOKIE_JAR.save(COOKIE, ignore_discard=True, ignore_expires=False)
        response.close()
        addon_log("getRequest : %s" %url)
        code = response.getcode()


        
    return (data, code)


def getRequestedM3u8(url, data=None, headers=None):
    if headers is None:
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'http://illicoweb.videotron.com',
                   'Accept' : 'application/json, text/plain, */*;version=1.1'}

    with session() as c:
        c.cookies = COOKIE_JAR
        c.cookies.load(ignore_discard=True)
        r = c.get(url, headers = headers, verify=False)
        c.cookies.save(ignore_discard=True)
        return (r.url, r.status_code)

def getWatched():
    watched = {}
    try:
        if os.path.exists( WATCHED_DB ):
            watched = eval( open( WATCHED_DB ).read() )
    except:
        print_exc()
    return watched

def setWatched( strwatched, remove=False, refresh=True ):
    if not strwatched: return
    
    # all strings must be unicode!!
    if isinstance(strwatched, str):
        strwatched = strwatched.decode('utf-8')

    try:
        url, label = strwatched.split( "*" )

        if os.path.exists( WATCHED_DB ):
            watched = eval(open( WATCHED_DB ).read())
            watched[ url ] = watched.get( url ) or []
            # add to watched
            if label not in watched[ url ]:
                watched[ url ].append( label )
        else:
            watched = {}
            watched[ url ] = label

        # remove from watched
        if remove and label in watched[ url ]:
            del watched[ url ][ watched[ url ].index( label ) ]

        file( WATCHED_DB, "w" ).write( "%r" % watched )
    except:
        print_exc()
    if refresh:
        addon_log("Refreshing directory after setting watched status")
        xbmc.executebuiltin( 'Container.Refresh' )
        
if re.search( '(GetCarrousel|"carrousel")', sys.argv[ 2 ] ):
    from GuiView import GuiView as viewtype
else:
    from PluginView import PluginView as viewtype 

class Main( viewtype ):
    def __init__( self ):
        viewtype.__init__( self )
        self.args = Info()
        self.watched = getWatched()

        if not xbmcgui.Window(10000).getProperty('plugin.video.illicoweb_running') == 'True':
            addon_log('** Service not running **')
            xbmc.executescript(os.path.join(ADDON_PATH, 'service.py'))

        
        if self.args.isempty():
            if (not sessionCheck()):
                login()
            self._add_directory_root()

        elif self.args.purgecache:
            addon_log("Purging %s" % os.path.join(xbmc.translatePath( ADDON.getAddonInfo('profile').decode('utf-8') ), "cache"))
            shutil.rmtree(os.path.join(xbmc.translatePath( ADDON.getAddonInfo('profile').decode('utf-8') ), "cache"), ignore_errors=True)
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30027)))
            
        elif self.args.setwatched or self.args.setunwatched:
            strwatched = self.args.setwatched or self.args.setunwatched
            if self.args.all:
                url, label = strwatched.split( "*" )
                seasonNo = url[url.rfind(',')+1:]
                url = '/' + url[:url.rfind(',')]
                data = self._getShowJSON(url)
                
                seasons = data['body']['SeasonHierarchy']['seasons']

                # [body][SeasonHierarchy][seasons] seasons
                for i in seasons:
                    #addon_log(i['seasonNo'] + ' ==? ' + seasonNo)
                    if(str(i['seasonNo']) == seasonNo):
                        if 'episodes' in i:
                            for ep in i['episodes']:
                                setWatched( ep['orderURI'] + '*' + ep['title'], bool( self.args.setunwatched ), False)

                # [body][main] seasons
                i = data['body']['main']
                if(str(i['seasonNo']) == seasonNo):
                    if 'episodes' in i:
                        for ep in i['episodes']:
                            setWatched( ep['orderURI'] + '*' + ep['title'], bool( self.args.setunwatched ), False)
                
                #xbmc.executebuiltin( 'Container.Refresh' )
            else: setWatched( strwatched, bool( self.args.setunwatched ) )

            
        elif self.args.addtofavourites or self.args.removefromfavourites:
            #turn dict back into url, decode it and format it in xml
            f = self.args.addtofavourites or self.args.removefromfavourites
            addon_log(f.decode('utf-8'))
            f = parse_qs(urlparse('?' + f.replace( ", ", "&" ).replace('"','%22').replace('+','%2B')).query)

            remove = True if self.args.removefromfavourites else False
            self._addToFavourites(unquote_plus(f['label'][0]), f['category'][0], f['url'][0], remove)
                
        
        elif self.args.favoris:
            try:
                self._add_directory_favourites()                    
            except:
                print_exc
                    
        elif self.args.live:
            self._playLive(unquote_plus(self.args.live).replace( " ", "+" ))

        elif self.args.liveregion:
            url = unquote_plus(self.args.liveregion).replace( " ", "+" )

            regions, fanart = self._getLiveRegion(url)

            listitems = []
            if 'channels' in regions:
                for channel in regions['channels']:
                    self._addLiveChannel(listitems, channel, '%s?live="%s"', fanart, channel['name'])
            
            if len(listitems) == 1:
                live = listitems[0][0]
                self._playLive(live[live.find('"'):].replace('"',""))
                return
                
            addon_log("Adding Regions to Live Channel")
            OK = self._add_directory_items( listitems )
            self._set_content( OK, "episodes", False )
            

        elif self.args.episode:
            #self._checkCookies()
            self._playEpisode(unquote_plus(self.args.episode).replace( " ", "+" ))

        elif self.args.channel:
            url = unquote_plus(self.args.channel).replace( " ", "+" )

            shows, fanart, livelist = self._getShows(url)
            
            listitems = []
            if 'channels' in shows:
                for channel in shows['channels']:
                    self._addChannelToStingray(channel, listitems, fanart)
            else:
                for i in shows:
                    if 'submenus' in i:
                        for show in i['submenus']:
                            self._addShowToChannel(show, listitems, fanart)
                    else:
                        self._addShowToChannel(i, listitems, fanart)
            
            if listitems:
                # Sort list by ListItem Label
                listitems = self.natural_sort(listitems, False) 

            if len(listitems) == 0:
                live = livelist[0][0]
                self._playLive(live[live.find('"'):].replace('"',""))
                return
                
            listitems = livelist + listitems
            addon_log("Adding Shows to Channel")
            OK = self._add_directory_items( listitems )
            self._set_content( OK, "episodes", False )

        elif self.args.show:
            try:
                OK = False
                listitems = self.natural_sort(self._getSeasons(unquote_plus(self.args.show).replace( " ", "+" )), False)
            
                if listitems:
                    from operator import itemgetter
                    listitems = self.natural_sort(listitems, False)
                    OK = self._add_directory_items( listitems )
                self._set_content( OK, "episodes", False )
            except:
                print_exc()
        elif self.args.season:
            url = unquote_plus(self.args.season).replace( " ", "+" )
            season = url[url.rfind(',') + 1:]
            url = url[:url.rfind(',')]

            data = self._getShowJSON(url)
            self._addEpisodesToSeason(data, season)
        elif self.args.stingray:
            self._playStingray(unquote_plus(self.args.stingray).replace( " ", "+" ))

    def _addToFavourites(self, label, category, url, remove=False):
        if os.path.exists( FAVOURITES_XML ):
            favourites = open( FAVOURITES_XML, "r" ).read()
        else:
            favourites = u'<favourites>\n</favourites>\n'
        if isinstance(favourites, str):
            favourites = favourites.decode('utf-8')
        
        label = label.replace("/plus/","+")
        
        favourite = ('<favourite label="%s" category="%s" url="%s" />' % (label.replace(" -- En Direct --", " - Live").replace(" -- Live --", " - Live"), category, url)).decode('utf-8')
        addon_log("----" + favourite)
        if remove or favourite not in favourites:
            if remove:
                addon_log('Removing %s from favourites' % favourite)
                label = self.escapeSpecialCharacters(label)
                favourite = (r'  \<favourite label\=\"%s\" category\=\"%s\".*\n' % (label.replace(" -- En Direct --", " - Live").replace(" -- Live --", " - Live"), category))
                r = re.compile(favourite.decode('utf-8'))
                favourites = r.sub('', favourites)

                refresh = True
            else:
                favourites = favourites.replace( '</favourites>', '  %s\n</favourites>' % (favourite))
                refresh = False
            if isinstance(favourites, unicode):
                favourites = favourites.encode('utf-8')
            file( FAVOURITES_XML, "w" ).write( favourites )
            if refresh:
                if favourites == '<favourites>\n</favourites>\n':
                    try: os.remove( FAVOURITES_XML )
                    except: pass
                    xbmc.executebuiltin( 'Action(ParentDir)' )
                    xbmc.sleep( 1000 )
                WINDOW = xbmcgui.Window( 10000 ) 
                WINDOW.setProperty("force_data_reload", "true")
                xbmc.executebuiltin( 'Container.Refresh' )    
            
    def _addChannel(self, listitems, i, url):
        OK = False                
        try:
            label = i['name']
            addon_log("-- Adding Channel: %s" % label)

            
            episodeUrl = i['link']['uri']

            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'], 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'])

            url = url %( uri, episodeUrl  )
            
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                #"genre":       genreTitle,
                "plot":        i[ 'description' ] or ""
                #"season":      int(season) or -1
                #"episode":     episode[ "EpisodeNumber" ] or -1,
                #"year":        int( episode[ "Year" ] or "0" ),
                #"Aired":       episode[ "AirDateLongString" ] or "",
                #"mpaa":        episode[ "Rating" ] or "",
                #"duration":    episode[ "LengthString" ] or "",
                #"studio":      episode[ "Copyright" ] or "",
                #"castandrole": scraper.setCastAndRole( episode ) or [],
                #"writer":      episode[ "PeopleWriter" ] or episode[ "PeopleAuthor" ] or "",
                #"director":    episode[ "PeopleDirector" ] or "",
            }
            
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Video", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'] )
            listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg') #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/channels/' + ep['largeLogo'])
            
            if '?live=' in url:
                category = 'live'
            else: category = 'channel'
            self._add_context_menu( label, episodeUrl, category, listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()

    def _addLiveRegion(self, listitems, i, link, url, tag = False):
        OK = False
        try:
            if tag:
                label = i['name'] + " " + LANGUAGE(30003)
            else:
                label = LANGUAGE(30003) #'-- En Direct / Live TV --'
            addon_log("-- Adding Live Region: %s" % label)

            
            liveUrl = i['selectionUrl']
            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'])
            url = url %( uri, link  )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'] )
            #listitem.setProperty( "fanart_image", fanart)
            
            self._add_context_menu( i['name'] + ' - Live', link, 'liveregion', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()

        
    def _addLiveChannel(self, listitems, i, url, fanart, label=None):
        OK = False                
        try:
            if label == None:
                label = LANGUAGE(30003) #'-- En Direct / Live TV --'
            if not 'orderURI' in i:
                return
            addon_log("-- Adding Live Channel: %s" % label)
                
            episodeUrl = i['orderURI'] 
            uri = sys.argv[ 0 ]
            item = ( label, '', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'])
            url = url %( uri, episodeUrl  )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'] )
            listitem.setProperty( "fanart_image", fanart)
            
            self._add_context_menu( i['name'] + ' - Live', episodeUrl, 'live', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
            
    def _addEpisodesToSeason(self, data, season):
        addon_log("-- Adding Episodes to Season: %s" % season)
        OK = False
        listitems = self.natural_sort(self._getEpisodes(data, season), False) 

        if listitems:
            listitems = self.natural_sort(listitems, True)
            OK = self._add_directory_items( listitems )
        self._set_content( OK, "episodes", False )
    
    
    def _addEpisode(self, ep, listitems):
        label = ep['title']
        addon_log("-- Adding Episode: %s" % label)
        if not 'orderURI' in ep:
            return
        seasonUrl = ep['orderURI']
        OK = False
        try:
            uri = sys.argv[ 0 ]
            item = ( label, '', "DefaultTVShows.png", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/'  + ep['image']) #'DefaultAddonSubtitles.png')
            url = '%s?episode="%s"' %( uri, unquote_plus(seasonUrl.replace( " ", "+" ) ) )
            
            
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                #"genre":       genreTitle,
                "plot":        ep[ 'description' ] or "",
                "season":      int(ep['seasonNo'] if 'seasonNo' in ep else "-1") or -1,
                "episode":     int(ep[ 'episodeNo' ] if 'episodeNo' in ep else "-1") or -1,
                "year":        int( ep[ "released" ] or "0" ),
                #"Aired":       episode[ "AirDateLongString" ] or "",
                "mpaa":        ep[ 'rating' ] or "",
                "duration":    str(ep[ 'lengthInMinutes' ]) or "",
                #"studio":      episode[ "Copyright" ] or "",
                #"castandrole": scraper.setCastAndRole( episode ) or [],
                #"writer":      episode[ "PeopleWriter" ] or episode[ "PeopleAuthor" ] or "",
                #"director":    episode[ "PeopleDirector" ] or "",
            }

            watched = label in self.watched.get(seasonUrl, [] )
            overlay = ( xbmcgui.ICON_OVERLAY_NONE, xbmcgui.ICON_OVERLAY_WATCHED )[ watched ]
            infoLabels.update( { "playCount": ( 0, 1 )[ watched ], "overlay": overlay } )
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Video", infoLabels )
            
            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/' + ep['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + ep['image'])
            
            #set property for player set watched
            strwatched = "%s*%s" % ( seasonUrl, label )
            listitem.setProperty( "strwatched", strwatched )
            #listitem.setProperty( "IsPlayable", "true" )
            
            self._add_context_menu(  label, unquote_plus(seasonUrl.replace( " ", "+" ) ), 'episode', listitem, watched, False )
            listitems.append( ( url, listitem, False ) )
        except:
            print_exc()

    def _addSeasonsToShow(self, i, listitems, title=False):
        seasonNo = i['seasonNo'] if 'seasonNo' in i else 0
        label = i['title'] + " - " + (LANGUAGE(30018) + " " + str(seasonNo)) if i['objectType'] == "SEASON" else i['title'] 
        addon_log("-- Adding Seasons to Show: %s" % label)

        if title and not i['title'] in label: label = '%s - %s' % (i['title'], label)
        seasonUrl = i['link']['uri'] + ',' + str(seasonNo)

        OK = False
        try:
            uri = sys.argv[ 0 ]
            thumb = 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/player/' + i['image']
            item = ( label,     '',  thumb)
            url = '%s?season="%s"' %( uri, seasonUrl )
            
            listitem = xbmcgui.ListItem( *item )
            description = ''
            if 'description' in i: description = i['description']
            infoLabels = {
                "tvshowtitle": label,
                "title":       label,
                "genre":       i['genre'] if 'genre' in i else '',
                "year":        int( i['released'] ),
                #"tagline":     ( STRING_FOR_ALL, "" )[ bool( GeoTargeting ) ],
                "duration":    i['lengthInMinutes'] if 'lengthInMinutes' in i else '0',
                #"episode":     NombreEpisodes,
                "season":      int(seasonNo) or -1,
                "plot":        description,
                #"premiered":   emission.get( "premiered" ) or "",
                }


            watched = 0
            if 'episodes' in i:
                for episode in i['episodes']:
                    if episode['title'] in self.watched.get(episode['orderURI'], [] ):
                        watched += 1
            NombreEpisodes = int( i['size'] if 'size' in i else "1")
            if NombreEpisodes == 0: NombreEpisodes = 999
            unwatched = NombreEpisodes - watched
            addon_log ('Total: %s - Watched: %s = Unwatched: %s' % (str(NombreEpisodes), str(watched),str(unwatched)))

            listitem.setProperty( "WatchedEpisodes", str( watched ) )
            listitem.setProperty( "UnWatchedEpisodes", str( unwatched ) )

            playCount = ( 0, 1 )[ not unwatched ]
            overlay = ( xbmcgui.ICON_OVERLAY_NONE, xbmcgui.ICON_OVERLAY_WATCHED )[ playCount ]
            infoLabels.update( { "playCount": playCount, "overlay": overlay } )
            
            listitem.setInfo( "Video", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/thumb/' + i['image'] )
            listitem.setProperty( "fanart_image", xbmc.getInfoLabel( "ListItem.Property(fanart_image)" )) #'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/thumb/' + i['image'])

            self._add_context_menu( i['title'], seasonUrl, 'season', listitem, not unwatched, False )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    
    def _addChannelToStingray(self, channel, listitems, fanart, url=None):
        label = channel['name']
        addon_log("-- Adding Channel to Stingray: %s" % label)
        OK = False
        try:
            channelUrl = url or channel['orderURI']
            uri = sys.argv[ 0 ]
            item = ( label, '' , 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + channel['image'])
            url = '%s?stingray="%s"' %( uri, channelUrl  )
            
            infoLabels = {
                "title":       label,
                "artist":      label,
                "album":       label
            }
            
            listitem = xbmcgui.ListItem( *item )
            listitem.setInfo( "Music", infoLabels )

            listitem.setProperty( 'playLabel', label )
            listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + channel['image'] )
            listitem.setProperty( "fanart_image", fanart)

            self._add_context_menu( label, channelUrl, 'stingray', listitem, False, True )
            listitems.append( ( url, listitem, False ) )
        except:
            print_exc()
            
    
    
    def _addShowToChannel(self, season, listitems, fanart, url=None):
        if 'label' in season:
            label = season['label']
        elif 'name' in season:
            label = season['name']
        elif 'title' in season:
            label = season['title']
        else:
            label = "Unknown"
        addon_log("-- Adding Show to Channel: %s" % label)

        if season['link']['template'] == 'PROVIDER_LANDING':
            addon_log("--   Skipping %s" % label)
            return
        OK = False                
        try:
            showUrl = url or season['link']['uri']
            uri = sys.argv[ 0 ]
            item = ( label,     '')
            url = '%s?show="%s"' %( uri, showUrl  )
            listitem = xbmcgui.ListItem( *item )

            listitem.setProperty( 'playLabel', label )
            #listitem.setProperty( 'playThumb', 'https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/providers/' + i['image'] )
            listitem.setProperty( "fanart_image", fanart)
            self._add_context_menu( label, showUrl, 'show', listitem, False, True )
            listitems.append( ( url, listitem, True ) )
        except:
            print_exc()
    

    # --------------------------------------------------------------------------------------------
    # [ Start of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _getShowJSON(self, url):
        #self._checkCookies()

        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/channels/<channelName>/<showID>/<showName>
        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' + url + '&localeLang=' + LANGGUI
        data = dataManager.GetContent(url)

        sections = data['body']['main']['sections']
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        return dataManager.GetContent(url)

        
    # Returns json of Channel labeled <label>
    def _getChannel(self, label):
        #self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang=' + LANGGUI
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)

        jsonList = json.loads(data)['body']['main']

        for i in jsonList:
            if i['name'] == label:
                return i

                
    # Returns json of Seasons from a specific Show's URL
    # Can return a specific season number json if seasonNo arg is non-0
    def _getSeasons(self, _url, seasonNo=0):
        #self._checkCookies()
        
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/ChannelName
        url = 'http://illicoweb.videotron.com/illicoservice/url'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # get Channel sections to get URL for JSON shows
        data, result = getRequest(url,urllib.urlencode(values),headers, 'logicalUrl=' + unquote_plus(_url) + '&localeLang=' + LANGGUI)
        sections = json.loads(data)['body']['main']['sections']

        if (len(sections) == 1):
            # play show directly
            self._playEpisode(json.loads(data)['body']['main']['provider']['orderURI'], True)
            return           
        
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(sections[1]['contentDownloadURL'].replace( " ", "+" ))
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        data = dataManager.GetContent(url)
        
        listitems = []
        seasons = data['body']
        if 'SeasonHierarchy' in seasons:
            seasons = data['body']['SeasonHierarchy']['seasons']
            for i in seasons:
                # [body][SeasonHierarchy][seasons] seasons
                if seasonNo > 0:
                    if int(i['seasonNo']) == seasonNo:
                        # found specified season, return json
                        return i
                else: self._addSeasonsToShow(i,listitems)
        i = data['body']['main']
        if type(i) is list:
            # sub category, loop through shows / episodes
            for y in i:
                if 'seasonNo' in y and y['objectType'] != "EPISODE":
                    self._addSeasonsToShow(y,listitems)
                elif (y['objectType'] == "PROGRAM"):
                    self._addShowToChannel(y,listitems, "")
                elif (y['objectType'] == "MUSIC"):
                    self._addShowToChannel(y,listitems, "")
                else:
                    self._addEpisode(y, listitems)
            
        if len(listitems) == 1 and seasonNo == 0 and 'seasonNo' in i:
            # only one season for this show, go straight to episode list
            return self._getEpisodes(data, str(i['seasonNo']))

        if len(listitems) == 0 and not 'seasonNo' in i:
            # no season information, play show directly
            self._playEpisode(i[0]['orderURI'] if type(i) is list else i['orderURI'], True)
            return
            
        return listitems

    # Returns json of Season from a specific Show's URL
    def _getSeasonJSON(self, id):
        #self._checkCookies()

        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}

        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice/content/'+id
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        
        return dataManager.GetContent(url, True)
        

    def _getShows(self, _url):
        #self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url'
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers, 'logicalUrl=' +unquote_plus(_url).replace( " ", "+" ) + '&localeLang=' + LANGGUI)
      
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=chaines/ChannelName
        fanart = ""
        if 'backgroundURL' in json.loads(data)['body']['main']:
            fanart = "https://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/" + json.loads(data)['body']['main']['backgroundURL'] #self._getChannelFanartImg(data)

        i = json.loads(data)['body']['main']['provider']
        
        livelist = []
        if 'Stingray Mus' in i['name']:
            shows = i
        else:
            # Add LiveTV to top of show list
            try:
                if REGIONS == 'true':
                    if 'channels' in i:
                        addon_log("Get Shows for Channel - Found multiple Live feeds")
                        self._addLiveRegion(livelist, i, unquote_plus(_url).replace( " ", "+" ), '%s?liveregion="%s"')
                    else:
                        addon_log("Get Shows for Channel - Found one Live feeds")
                        self._addLiveChannel(livelist, i, '%s?live="%s"', fanart) 
                else:
                    self._addLiveChannel(livelist, i, '%s?live="%s"', fanart)  
            except:
                print_exc() 
        
            data = self._getChannelShowsJSON(data)
            # No onDemand content? do nothing
            if data is None:
                return "", fanart, livelist
            
            shows = data['body']['main']['submenus']
        
        return shows, fanart, livelist

    def _getLiveRegion(self, url):
        #self._checkCookies()

        url = 'http://illicoweb.videotron.com/illicoservice/url?logicalUrl=' +unquote_plus(url).replace( " ", "+" ) + '&localeLang=' + LANGGUI
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
      
        # url format: http://illicoweb.videotron.com/illicoservice/url?logicalUrl=chaines/ChannelName
        addon_log("Getting fanart from URL: " + url)
        fanart = "" #self._getChannelFanartImg(data)

        i = json.loads(data)['body']['main']['provider']
                
        return i, fanart
        



    def _getStingray(self, url, label):
        #self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/url?logicalUrl=/chaines/Stingray' + '&localeLang=' + LANGGUI #+unquote_plus(url).replace( " ", "+" )
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        #data = self._getChannelShowsJSON(data)
        
        channels = json.loads(data)['body']['main']['provider']['channels']   

        for i in channels:
            if i['name'] == label:
                return i
        
    def _getShow(self, url, label):
        #self._checkCookies()

        url = 'https://illicoweb.videotron.com/illicoservice/url?logicalUrl='+unquote_plus(url).replace( " ", "+" ) + '&localeLang=' + LANGGUI
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        data = self._getChannelShowsJSON(data) or data

        shows = data['body']['main']
        if not 'submenus' in shows:
            shows = shows['provider']
            if shows['name'] == label:
                return shows
        else:
            shows = shows['submenus']

        for i in shows:
            if 'submenus' in i:
                for show in i['submenus']:
                    if show['label'] == label:
                        return show
            else:
                if ('label' in i):
                    if i['label'] == label:
                        return i
    
    def _getEpisodes(self, data, season, title=None):
        seasons = data['body']['SeasonHierarchy']['seasons']
        listitems = []

        # [body][SeasonHierarchy][seasons] seasons
        for i in seasons:
            if(str(i['seasonNo']) == season):
                season = self._getSeasonJSON(str(i['id']))
                for ep in season['body']['main']['episodes']:
                    if title:
                        if title == ep['title']:
                            self._addEpisode(ep, listitems)
                    else: self._addEpisode(ep, listitems)
        # [body][main] seasons
        i = data['body']['main']
        if(str(i['seasonNo']) == season):
            for ep in i['episodes']:
                if title:
                    if title == ep['title']:
                        self._addEpisode(ep, listitems)
                else: self._addEpisode(ep, listitems)

        return listitems    

    def _getEpisodesAlt(self, data):
        listitems = []
        i = json.loads(data)['body']
        for ep in i['main']:
            self._addEpisode(ep, listitems)

        return listitems   
        
    def _getChannelShowsJSON(self, data):
        sections = json.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'MENU':
                    onDemand = True
                    url = i['contentDownloadURL']
        if (onDemand == False):
            return
        # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
            'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        return dataManager.GetContent(url)
    
    def _getChannelFanartImg(self, data):
        sections = json.loads(data)['body']['main']['sections']
        onDemand = False
        for i in sections:
            if 'widgetType' in i:
                if i['widgetType'] == 'PLAYER':
                    url = i['contentDownloadURL']
        try:
            # url format: https://illicoweb.videotron.com/illicoservice/page/section/0000
            url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(url.replace( " ", "+" ))
            if '?' in url:
                url = url + '&localeLang=' + LANGGUI
            else: url = url + '?localeLang=' + LANGGUI
            
            headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                'Referer' : 'https://illicoweb.videotron.com/accueil'}
            values = {}
            data, result = getRequest(url,urllib.urlencode(values),headers)
            img = json.loads(data)['body']['main'][0]
            return 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/' + img['image']    
        except:
            return ''
         
    # --------------------------------------------------------------------------------------------
    # [ End of scrappers -------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------
    
    def _playStingray(self, pid):
        if self._encrypted(pid):
            return False
        #self._checkCookies()
        url = 'https://illicoweb.videotron.com/illicoservice'+pid
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        
        addon_log("Stingray music at: %s" %url)
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        options = {'live': '1'}

        if (not data is None) and (result == 200):
            if not (self._play(data, pid, options, True)):
                addon_log("episode error")
        else:
            addon_log("Failed to get link - encrypted?")
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30017)))
            return False
    
    def _playLive(self, pid):
        if self._encrypted(pid):
            return False
            
        url = 'https://illicoweb.videotron.com/illicoservice'+pid+'?streamType=dash'
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
            
        addon_log("Live show at: %s" %url)
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        if result == 403:
            addon_log('Content unavailable... Forbidden')
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30001)))
            return False
            
        options = {'live': '1'}

        if (not data is None) and (result == 200):
            if not (self._play(data, pid, options, True)):
                addon_log("episode error")
        else:
            addon_log("Failed to get link - encrypted?")
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30017)))
            return False
    
    
    def _playEpisode(self, pid, direct=False):
        if self._encrypted(pid):
            return False

        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(pid).replace( " ", "+" )+'?streamType=dash'
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
            
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        if result == 403:
            addon_log('Content unavailable... Forbidden')
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30001)))
            return False
        
        if (not data is None) and (result == 200):
            if not (self._play(data, pid, {}, True)):
                addon_log("episode error")
        else:
            addon_log("Failed to get link - encrypted?")
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30017)))
            return False
            
            
    def _encrypted(self, pid):
        url = 'https://illicoweb.videotron.com/illicoservice'+unquote_plus(pid).replace( " ", "+" )+'?streamType=dash'
        if '?' in url:
            url = url + '&localeLang=' + LANGGUI
        else: url = url + '?localeLang=' + LANGGUI
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data, result = getRequest(url,urllib.urlencode(values),headers)
        
        try:
            info = json.loads(data)
        except:
            addon_log('Content unavailable... Forbidden')
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30001)))
            return True
        
        encrypted = info['body']['main']['mediaEncryption']
        
        if encrypted:
            addon_log('Encrypted media - cannot play.')
            xbmcgui.Dialog().ok(ADDON_NAME, '%s' % (LANGUAGE(30017)))
            return True
        
        addon_log('Not Encrypted media - requesting play.')        
        return False
            
    def _play(self, data, pid, options={}, direct=False):
        info = json.loads(data)
        path = info['body']['main']['mainToken']
        connected = info['head']['userInfo']['clubIllicoStatus']
        
        if connected == 'NOT_CONNECTED':
            if not login():
                xbmcgui.Dialog().ok(ADDON_NAME, '%s\n%s' % (LANGUAGE(30004),LANGUAGE(30041)))
                xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
                exit(0)                
        
        win = xbmcgui.Window(10000)
        win.setProperty('illico.playing.title', xbmc.getInfoLabel( "ListItem.Property(playLabel)" ))
        win.setProperty('illico.playing.pid', unquote_plus(pid).replace( " ", "+" ))
        win.setProperty('illico.playing.watched', xbmc.getInfoLabel( "ListItem.Property(strwatched)" ))

        if get_installedversion() < 17:
            final_url, code = getRequestedM3u8(path)
        else:
            final_url = path
            
        addon_log('Attempting to play url: %s' % final_url)
    
        item = xbmcgui.ListItem(xbmc.getInfoLabel( "ListItem.Property(playLabel)" ), '', xbmc.getInfoLabel( "ListItem.Property(playThumb)" ), xbmc.getInfoLabel( "ListItem.Property(playThumb)" ))
        item.setPath(final_url)
        direct = True
        if direct:
            addon_log('Direct playback with DVDPlayer')
            player = xbmc.Player()
            player.play(final_url, item)
        else:
            addon_log('Indirect playback with setResolvedUrl')
            xbmcplugin.setResolvedUrl(int( sys.argv[ 1 ] ), True, item)

        return True

    def _checkCookies(self):
        # Check if cookies have expired.
        COOKIE_JAR.load(COOKIE, ignore_discard=False, ignore_expires=False)
        cookies = {}
        addon_log('These are the cookies we have in the cookie file:')
        for i in COOKIE_JAR:
            cookies[i.name] = i.value
            addon_log('%s: %s' %(i.name, i.value))
        if cookies.has_key('iPlanetDirectoryPro') or cookies.has_key('session-illico-profile'):
            addon_log('We have valid cookies')
            login_ = 'old'
        else:
            login_ = login()

        if not login_:
            xbmcgui.Dialog().ok(ADDON_NAME, '%s\n%s' % (LANGUAGE(30004),LANGUAGE(30041)))
            xbmc.executebuiltin("Addon.OpenSettings(plugin.video.illicoweb)")
            exit(0)

        COOKIE_JAR.load(COOKIE, ignore_discard=False, ignore_expires=False)
        cookies = {}

    def _add_directory_favourites( self ):
        OK = False
        listitems = []
        try:
            from xml.dom.minidom import parseString

            xmlFav = open( FAVOURITES_XML, "r" ).read()
            if isinstance(xmlFav, unicode):
                xmlFav = xmlFav.encode('utf-8')
            favourites = parseString( xmlFav).getElementsByTagName( "favourite" )
            
            for favourite in favourites:
                try:
                    label = favourite.getAttribute( "label" )
                    category  = favourite.getAttribute( "category" )
                    url = favourite.getAttribute( "url" )

                    if category == 'channel':
                        i = self._getChannel(label)
                        if i:
                            self._addChannel(listitems, i, '%s?channel="%s"')

                    elif category == 'live':
                        obj = {'name': label, 'link': { 'uri': url }, 'image': '', 'plot': '', 'description':''}
                        i = json.loads(json.dumps(obj))

                        if i:
                            i['name'] = label.replace(' - Live', " " + LANGUAGE(30003))
                            i['link']['uri'] = url 
                            self._addChannel(listitems, i, '%s?live="%s"')
                    
                    elif category == 'liveregion':
                        obj = {'name': label, 'selectionUrl': url, 'link': { 'uri': url }, 'image': '', 'plot': '', 'description':''}
                        i = json.loads(json.dumps(obj))

                        if i:
                            i['name'] = label.replace(' - Live', "")
                            i['link']['uri'] = url 
                            self._addLiveRegion(listitems, i, unquote_plus(url).replace( " ", "+" ), '%s?liveregion="%s"', True)

                    elif category == 'stingray':
                        i = self._getStingray(url, label)
                        if i:
                            self._addChannelToStingray(i, listitems, "", url)
                            
                    elif category == 'show':
                        i = self._getShow(url, label)
                        if i:
                            self._addShowToChannel(i,listitems, "", url)
                            
                    elif category == 'season':
                        # split the url to show url and seasonNo
                        seasonNo = int(url[url.rfind(',')+1:])
                        url = url[:url.rfind(',')]
                        i = self._getSeasons(url, seasonNo)
                        if i:
                            self._addSeasonsToShow(i, listitems, True)
                except:
                    print_exc()
                    addon_log("-- Favourite no longer exists")
                    question = label + LANGUAGE(30019)
                    remove = xbmcgui.Dialog()
                    remove = remove.yesno(ADDON_NAME, question)
                    if remove:
                        self._addToFavourites(label, category, url, True)
                        
        except:
            print_exc()

        if listitems:
            addon_log("Adding Favourites")
            OK = self._add_directory_items( listitems )   
        else:
            xbmc.executebuiltin("XBMC.Notification("+ADDON_NAME+", "+LANGUAGE(30020)+",10000,"+ICON+")")
            
        self._set_content( OK, "episodes", False )  
                
    def _add_directory_root( self ):
        #self._checkCookies()
        listitems = []
        try:
            if os.path.exists( FAVOURITES_XML ):
                uri = sys.argv[ 0 ]
                item = (LANGUAGE(30007), '', 'DefaultAddonScreensaver.png')
                listitem = xbmcgui.ListItem( *item )
                listitem.setProperty( "fanart_image", 'http://static-illicoweb.videotron.com/illicoweb/static/webtv/images/content/custom/presse1.jpg')
                url = '%s?favoris="root"' %uri 
                listitem.addContextMenuItems( [( LANGXBMC(184), "Container.Refresh")], False )
                listitems.append(( url, listitem, True ))
        except:
            xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30016))
                
        if 'English' in xbmc.getLanguage():
            self._add_channels_lang('en', listitems)
        else:
            self._add_channels_lang('fr', listitems)
    
        OK = False
        if listitems:
            addon_log("Adding Channels to Root")
            OK = self._add_directory_items( self.natural_sort(listitems, False) )
        self._set_content( OK, "episodes", False )

    def _add_channels_lang( self, lang, listitems ):
        url = 'https://illicoweb.videotron.com/illicoservice/channels/user?localeLang=' + lang
        headers = {'User-agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:19.0) Gecko/20100101 Firefox/19.0',
                   'Referer' : 'https://illicoweb.videotron.com/accueil'}
        values = {}
        data = dataManager.GetContent(url)

        try:
            jsonList = data['body']['main']
            
            OK = False
            for i in jsonList:
                self._addChannel(listitems, i, '%s?channel="%s"')
        except:
            xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(30016))

        return listitems

    '''
    ' Section de gestion des menus
    '''
    def _add_context_menu( self, label, url, category, listitem, watched=False, hidewatched=False ):
        try:
            c_items = [] #[ ( LANGXBMC( 20351 ), "Action(Info)" ) ]
    
            #add to my favourites
            if category is not 'episode':
                # all strings must be unicode but encoded, if necessary, as utf-8 to be passed on to urlencode!!
                if isinstance(label, unicode):
                    labelUri = label.encode('utf-8')
                f = { 'label' : labelUri, 'category' : category, 'url' : url}
                uri = '%s?addtofavourites=%s%s%s' % ( sys.argv[ 0 ], "%22", urllib.urlencode(f), "%22" ) #urlencode(f) )
                
                if self.args.favoris == "root":
                    c_items += [ ( LANGUAGE(30005), "RunPlugin(%s)" % uri.replace( "addto", "removefrom" ) ) ]
                else:
                    c_items += [ ( LANGUAGE(30006), "RunPlugin(%s)" % uri ) ]

            if not hidewatched:
                if not watched:
                    i_label, action = 16103, "setwatched"
                else:
                    i_label, action = 16104, "setunwatched"
                if category == 'season':
                    all = 'True'
                else: all = 'False'
                uri = '%s?%s="%s*%s"&all=%s' % ( sys.argv[ 0 ], action, url, label, all )
                c_items += [ ( LANGXBMC( i_label ), "RunPlugin(%s)" % uri ) ]

            c_items += [ ( LANGXBMC(184), "Container.Refresh") ]
                
            self._add_context_menu_items( c_items, listitem )
        except:
            print_exc()

    def _add_context_menu_items( self, c_items, listitem, replaceItems=True ):
        c_items += [ ( LANGXBMC( 10140 ), "Addon.OpenSettings(plugin.video.illicoweb)" ) ]
        listitem.addContextMenuItems( c_items, replaceItems )        

    '''
    ' Section de sort order
    ' e.g. 1, 2, 3, ... 10, 11, 12, ... 100, 101, 102, etc...
    '''
    def natsort_key(self, item):
        chunks = re.split('(\d+(?:\.\d+)?)', self.remove_accents(item[1].getLabel().decode('utf-8')))
        for ii in range(len(chunks)):
            if chunks[ii] and chunks[ii][0] in '0123456789':
                if '.' in chunks[ii]: numtype = float
                else: numtype = int
                chunks[ii] = (0, numtype(chunks[ii]))
            else:
                chunks[ii] = (1, chunks[ii])
        return (chunks, item)

    def natural_sort(self, seq, reverseBool):
        sortlist = [item for item in seq]
        sortlist.sort(key=self.natsort_key, reverse = reverseBool)
        return sortlist

                
    def remove_accents(self, input_str):
        nkfd_form = unicodedata.normalize('NFKD', unicode(input_str))
        return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

    def escapeSpecialCharacters (self, text): 
        return re.sub(r'([\.\\\+\*\?\[\^\]\$\(\)\{\}\!\<\>\|\:])', r'\\\1', text)

            
class Info:
    def __init__( self, *args, **kwargs ):
        # update dict with our formatted argv
        addon_log('__init__ addon received: %s' % sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"').replace("%2B","/plus/"))
        try: exec "self.__dict__.update(%s)" % ( sys.argv[ 2 ][ 1: ].replace( "&", ", " ).replace("%22",'"').replace("%2B","/plus/"))
        except: print_exc()
        # update dict with custom kwargs
        self.__dict__.update( kwargs )

    def __getattr__( self, namespace ):
        return self[ namespace ]

    def __getitem__( self, namespace ):
        return self.get( namespace )

    def __setitem__( self, key, default="" ):
        self.__dict__[ key ] = default

    def get( self, key, default="" ):
        return self.__dict__.get( key, default )#.lower()

    def isempty( self ):
        return not bool( self.__dict__ )

    def IsTrue( self, key, default="false" ):
        return ( self.get( key, default ).lower() == "true" )

if ( __name__ == "__main__" ):
    Main()

dataManager.canRefreshNow = True
