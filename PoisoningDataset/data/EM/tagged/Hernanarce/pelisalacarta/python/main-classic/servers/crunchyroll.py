# -*- coding: utf-8 -*-
#------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# Conector para crunchyroll
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
#------------------------------------------------------------

import base64
import re
import zlib
import struct

from hashlib import sha1

from core import config
from core import filetools
from core import logger
from core import scrapertools
from core import httptools

GLOBAL_HEADER = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': '*'}
proxy = "http://anonymouse.org/cgi-bin/anon-www.cgi/"


def test_video_exists( page_url ):
    logger.info("(page_url='%s')" % page_url)

    premium = config.get_setting("crunchyrollpremium")
    if premium == "true":
        return login(page_url)
    data = httptools.downloadpage(page_url, headers=GLOBAL_HEADER, replace_headers=True).data
    if "Este es un clip de muestra" in data and premium == "false":
        disp = scrapertools.find_single_match(data, '<a href="/freetrial".*?</span>.*?<span>\s*(.*?)</span>')
        disp = disp.strip()
        if disp:
            disp = "Disponible gratuitamente: %s" % disp
        return False, "[Crunchyroll] Error, se necesita cuenta premium. %s" % disp
    
    return True, ""


def get_video_url(page_url, premium = False, user="", password="", video_password=""):
    logger.info("url="+page_url)

    video_urls = []
    
    if "crunchyroll.com" in page_url:
        media_id = page_url.rsplit("-", 1)[1]
    else:
        media_id = scrapertools.find_single_match(page_url, 'media_id=(\d+)')

    url = "http://www.crunchyroll.com/xml/?req=RpcApiVideoPlayer_GetStandardConfig&media_id=%s" \
          "&video_format=0&video_quality=0&auto_play=0&aff=af-12299-plwa" % media_id
    post = "current_page=%s" % page_url
    data = httptools.downloadpage(url, post, headers=GLOBAL_HEADER, replace_headers=True).data
    

    if "<msg>Media not available</msg>" in data:
        data = httptools.downloadpage(proxy+url, post, headers=GLOBAL_HEADER, replace_headers=True).data

    media_url = scrapertools.find_single_match(data, '<file>(.*?)</file>').replace("&amp;", "&")
    if not media_url:
        return video_urls
    quality = scrapertools.find_single_match(data, '<height>(.*?)</height>')
    filename = scrapertools.get_filename_from_url(media_url)[-4:]
    
    try:
        from Crypto.Cipher import AES
        idiomas = ['Español \(España\)', 'Español\]', 'English', 'Italiano', 'Français', 'Português', 'Deutsch']
        index_sub = int(config.get_setting("crunchyrollsub"))
        idioma_sub = idiomas[index_sub]
        link_sub = scrapertools.find_single_match(data, "link='([^']+)' title='\[%s" % idioma_sub)
        if not link_sub and index_sub == 0:
            link_sub = scrapertools.find_single_match(data, "link='([^']+)' title='\[Español\]")
        elif not link_sub and index_sub == 1:
            link_sub = scrapertools.find_single_match(data, "link='([^']+)' title='\[Español \(España\)")

        if not link_sub:
            link_sub = scrapertools.find_single_match(data, "link='([^']+)' title='\[English")
        data_sub = httptools.downloadpage(link_sub.replace("&amp;", "&"), headers=GLOBAL_HEADER, replace_headers=True).data

        id_sub = scrapertools.find_single_match(data_sub, "subtitle id='([^']+)'")
        iv = scrapertools.find_single_match(data_sub, '<iv>(.*?)</iv>')
        data_sub = scrapertools.find_single_match(data_sub, '<data>(.*?)</data>')
        file_sub = decrypt_subs(iv, data_sub, id_sub)
    except:
        import traceback
        logger.info(traceback.format_exc())
        file_sub = ""

    video_urls.append(["%s  %sp [crunchyroll]" % (filename, quality), media_url, 0, file_sub])

    for video_url in video_urls:
        logger.info("%s - %s" % (video_url[0],video_url[1]))

    return video_urls


# Encuentra vídeos del servidor en el texto pasado
def find_videos(data):
    encontrados = set()
    devuelve = []

    patronvideos  = "(crunchyroll.com\/[^/]+\/.*-\d+).*$"
    logger.info("#"+patronvideos+"#")
    matches = re.compile(patronvideos,re.DOTALL).findall(data)

    for match in matches:
        titulo = "[crunchyroll]"
        url = "http://www." + match
        if url not in encontrados:
            logger.info("  url="+url)
            devuelve.append( [ titulo , url , 'crunchyroll' ] )
            encontrados.add(url)
        else:
            logger.info("  url duplicada="+url)

    return devuelve


def login(page_url):
    login_page = "https://www.crunchyroll.com/login"
    user = config.get_setting("crunchyrolluser")
    password = config.get_setting("crunchyrollpassword")
    data = httptools.downloadpage(login_page, headers=GLOBAL_HEADER, replace_headers=True).data

    if not "<title>Redirecting" in data:
        token = scrapertools.find_single_match(data, 'name="login_form\[_token\]" value="([^"]+)"')
        redirect_url = scrapertools.find_single_match(data, 'name="login_form\[redirect_url\]" value="([^"]+)"')
        post = "login_form%5Bname%5D=" + user + "&login_form%5Bpassword%5D=" + password + \
               "&login_form%5Bredirect_url%5D=" + redirect_url + "&login_form%5B_token%5D=" + token
        
        data = httptools.downloadpage(login_page, post, headers=GLOBAL_HEADER, replace_headers=True).data
        if "<title>Redirecting" in data:
            return True, ""
        else:
            if "Usuario %s no disponible" % user in data:
                return False, "El usuario de crunchyroll no existe. Corrígelo o desactiva la opción premium para ver enlaces free"
            elif '<li class="error">Captcha' in data:
                return False, "Es necesario resolver un captcha. Loguéate desde un navegador y vuelve a intentarlo"
            else:
                return False, "Error en la contraseña de crunchyroll. Corrígelo o desactiva la opción premium para ver enlaces free"
    
    return True, ""


def decrypt_subs(iv, data, id):
    from Crypto.Cipher import AES
    data = base64.b64decode(data.encode('utf-8'))
    iv = base64.b64decode(iv.encode('utf-8'))
    id = int(id)

    def obfuscate_key_aux(count, modulo, start):
        output = list(start)
        for _ in range(count):
            output.append(output[-1] + output[-2])
        # cut off start values
        output = output[2:]
        output = list(map(lambda x: x % modulo + 33, output))
        return output

    def obfuscate_key(key):
        from math import pow, sqrt, floor
        num1 = int(floor(pow(2, 25) * sqrt(6.9)))
        num2 = (num1 ^ key) << 5
        num3 = key ^ num1
        num4 = num3 ^ (num3 >> 3) ^ num2
        prefix = obfuscate_key_aux(20, 97, (1, 2))
        prefix = struct.pack('B' * len(prefix), *prefix)
        shaHash = sha1(prefix + str(num4).encode('ascii')).digest()
        decshaHash = []
        for char in shaHash:
            decshaHash.append(ord(char))
        # Extend 160 Bit hash to 256 Bit
        return decshaHash + [0] * 12

    key = obfuscate_key(id)
    key = struct.pack('B' * len(key), *key)
<target>

    decryptor = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = decryptor.decrypt(data)
</target>
    data = zlib.decompress(decrypted_data)
    
    import xml.etree.ElementTree as ET
    raiz = ET.fromstring(data)

    ass_sub = convert_to_ass(raiz)
    file_sub = filetools.join(config.get_data_path(), 'crunchyroll_sub.ass')
    filetools.write(file_sub, ass_sub)
    return file_sub
    

def convert_to_ass(raiz):
    output = ''

    def ass_bool(strvalue):
        assvalue = '0'
        if strvalue == '1':
            assvalue = '-1'
        return assvalue

    output = '[Script Info]\n'
    output += 'Title: %s\n' % raiz.attrib['title']
    output += 'ScriptType: v4.00+\n'
    output += 'WrapStyle: %s\n' % raiz.attrib['wrap_style']
    output += 'PlayResX: %s\n' % raiz.attrib['play_res_x']
    output += 'PlayResY: %s\n' % raiz.attrib['play_res_y']
    output += """ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""
    for style in raiz.findall('./styles/style'):
        output += 'Style: ' + style.attrib['name']
        output += ',' + style.attrib['font_name']
        output += ',' + style.attrib['font_size']
        output += ',' + style.attrib['primary_colour']
        output += ',' + style.attrib['secondary_colour']
        output += ',' + style.attrib['outline_colour']
        output += ',' + style.attrib['back_colour']
        output += ',' + ass_bool(style.attrib['bold'])
        output += ',' + ass_bool(style.attrib['italic'])
        output += ',' + ass_bool(style.attrib['underline'])
        output += ',' + ass_bool(style.attrib['strikeout'])
        output += ',' + style.attrib['scale_x']
        output += ',' + style.attrib['scale_y']
        output += ',' + style.attrib['spacing']
        output += ',' + style.attrib['angle']
        output += ',' + style.attrib['border_style']
        output += ',' + style.attrib['outline']
        output += ',' + style.attrib['shadow']
        output += ',' + style.attrib['alignment']
        output += ',' + style.attrib['margin_l']
        output += ',' + style.attrib['margin_r']
        output += ',' + style.attrib['margin_v']
        output += ',' + style.attrib['encoding']
        output += '\n'

    output += """
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for event in raiz.findall('./events/event'):
        output += 'Dialogue: 0'
        output += ',' + event.attrib['start']
        output += ',' + event.attrib['end']
        output += ',' + event.attrib['style']
        output += ',' + event.attrib['name']
        output += ',' + event.attrib['margin_l']
        output += ',' + event.attrib['margin_r']
        output += ',' + event.attrib['margin_v']
        output += ',' + event.attrib['effect']
        output += ',' + event.attrib['text']
        output += '\n'

    return output.encode('utf-8')