import socket
import ssl
import urllib
from xml.dom import minidom

from libblah.consts import HOME_DOMAIN, CRLF, PROTOCOL_VERSION, HASHED_PREFIX
from libblah.log import logger
from libblah.sip import get_sid_from_uri
from libblah.strutils import strip2
from libblah.store import save_data_to_local_json, set_last_login_sid
from libblah.http import HTTPResponse, HTTPHeaders


def i_update_user_after_ssi_auth_success(user, res_obj, remember_passwd):
    """ get and set SSI cookie, uri, user ID, mobile No. """
    body_dom = minidom.parseString(res_obj.body)

    headers = res_obj.getheader('Set-Cookie')
    ssi_cookie = strip2(headers, "ssic=", ";")
    user.set_ssi_cookie(ssi_cookie)

    user_node = body_dom.getElementsByTagName("user")[0]
    user.uri = user_node.getAttribute("uri")

    user.sid = get_sid_from_uri(user.uri)

    user_node = body_dom.getElementsByTagName("user")[0]
    user.mobile_no = user_node.getAttribute("mobile-no")
    user.user_id = user_node.getAttribute("user-id")

    user.set_user_path(user.sid)
    user.set_portrait_save_path()


    set_last_login_sid(user.sid)
    if remember_passwd:
        hashed_passwd = user.get_hashed_passwd()
    else:
        hashed_passwd = None

    data = {
        "sid" : user.sid,
        "mobile_no" : user.mobile_no,
        "hashed_passwd" : "%s%s" % (HASHED_PREFIX, hashed_passwd),
        "last_presence" : user.get_presence()
    }
    save_data_to_local_json(data, "account.json")

def i_ssi_auth(user, verification = None, debug = False):
    ''' NOTICE: Don't use httplib.HTTPSConnection, it gets wrong size response body sometimes! '''
    digest = user.get_hashed_passwd()

    # hard-code enable login with SID or mobile No. only
    SID_OR_MOBILE_NO = 1
    digest_type = SID_OR_MOBILE_NO

    params = dict()
    params.update({
        "domains" : HOME_DOMAIN,
        "v4digest-type" : str(digest_type),
        "v4digest" : digest,
        })

    if verification is not None:
        veri_d = {
            "pid" : verification.pid,
            "pic" : verification.chars,
            "algorithm" : verification.algorithm
        }
        params.update(veri_d)

    if user.get_login_with() == user.LOGIN_WITH_MOBILE_NO:
        login_with = {"mobileno" : user.mobile_no}
    else:
        login_with = {"sid" : user.sid}
    params.update(login_with)

    query = urllib.urlencode(params)
    path = "/ssiportal/SSIAppSignInV4.aspx"
    req = "GET %s?%s %s" % (path, query, CRLF)

#    headers = {
#        "User-Agent" : "IIC2.0/pc %s" % PROTOCOL_VERSION,
#        "Host" : "uid.fetion.com.cn",
#        "Cache-Control" : "private",
#        "Connection" : "Keep-Alive",
#        }
#
#    head_obj = HTTPHeaders(headers = headers)
#    req += str(head_obj) + CRLF

    SSI_AUTH_HOST = "uid.fetion.com.cn"
    ip = socket.gethostbyname(SSI_AUTH_HOST)
    port = 443
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ssl_sock = ssl.wrap_socket(sock, cert_reqs = ssl.CERT_NONE,
                               ssl_version = ssl.PROTOCOL_SSLv23)
    ssl_sock.connect((ip, port))
    ssl_sock.write(req)

    if debug:
        logger.debug(req)

    if debug:
        debuglevel = 1
    else:
        debuglevel = 0

    res_obj = HTTPResponse(ssl_sock, debuglevel = debuglevel, read_body = True)
    ssl_sock.close()

    return res_obj
