#!/usr/bin/env python

print("")

try:
    import http.client, ssl, socket, re
    from time import strftime, localtime, time
except ImportError as e:
    print(e)
    print("Please ensure you are using Python v3. If you continue to experience difficulties, try re-installing your Python libraries.")
    quit(0)


def ValidateHostname(hostname):
    if len(hostname) > 255:
        return False

    if hostname[-1] == ".":
        hostname = hostname[:-1]
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def GetHTTPSResponse(host, port=443):
    #Usage: response = GetHTTPSResponse(server) [specify different port if necessary]
    try:
        conn1 = http.client.HTTPSConnection(host + ":" + str(port))
        conn1.request("GET", "/")
    except:
        print("Unable to establish a connection. Ensure you typed in the hostname correctly and that you have an internet connection.")
        quit(0)

    r1 = conn1.getresponse()
    return r1


def CreateSSLContext():
    #Usage: context = CreateSSLContext()
    ctx = ssl.create_default_context()
    ctx.options &= ~ssl.OP_NO_SSLv3 #enable sslv3
    ctx.options &= ~ssl.OP_NO_SSLv2 #enable sslv2
    return ctx


def UpdateSSLContext(ctx, ciphers):
    #Usage: UpdateSSLContext(context, cipherlist)
    ctx.set_ciphers(ciphers)


def WrapSocketAndConnect(ctx, host, port=443):
    #Usage: conn = WrapSocketAndConnect(context, server) [specify different port if necessary]
    conn2 = ctx.wrap_socket(socket.socket(socket.AF_INET), server_hostname=host)
    try:
        conn2.connect((host, port))
    except TimeoutError:
        print("Connection lost - unable to complete scan.")
        quit(0)

    return conn2


def ConnectDefaultSocket(host, port=443):
    #Usage: conn = ConnectDefaultSocket(server) [specify different port if necessary]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctx = CreateSSLContext()
    try:
        conn3 = WrapSocketAndConnect(ctx, host)
    except ssl.CertificateError:
        print("Warning! Certificate is invalid. Severity: 10. Reason(s): UNTRUSTED_CERTIFICATE")

    try:
        conn3.do_handshake()
    except:
        print("Connection interrupted - unable to complete scan.")
        quit(0)

    return conn3


def ConnectCustomSocket(index, host, port=443):
    #Usage: conn = ConnectCustomSocket(i, server) [specify different port if necessary]
    sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if index == 0:
<target>
        conn4 = ssl.wrap_socket(sock=sck, ssl_version=ssl.PROTOCOL_SSLv3, ciphers=bulk_ciphers)
</target>
    elif index == 1:
<target>
        conn4 = ssl.wrap_socket(sock=sck, ssl_version=ssl.PROTOCOL_TLSv1, ciphers=bulk_ciphers)
</target>
    elif index == 2:
<target>
        conn4 = ssl.wrap_socket(sock=sck, ssl_version=ssl.PROTOCOL_TLSv1_1, ciphers=bulk_ciphers)
</target>
    elif index == 3:
<target>
        conn4 = ssl.wrap_socket(sock=sck, ssl_version=ssl.PROTOCOL_TLSv1_2, ciphers=bulk_ciphers)
</target>
    else:
        raise IndexError('Invalid index supplied to CreateCustomSocket().')

    conn4.connect((host, port))
    return conn4


##### All available cipher suites (using OpenSSL naming conventions) #####
ciphers = ['ECDHE-RSA-AES256-GCM-SHA384', 'ECDHE-ECDSA-AES256-GCM-SHA384', 'ECDHE-RSA-AES256-SHA384', 'ECDHE-ECDSA-AES256-SHA384', 'ECDHE-RSA-AES256-SHA', 'ECDHE-ECDSA-AES256-SHA', 'DH-DSS-AES256-GCM-SHA384', 'DHE-DSS-AES256-GCM-SHA384', 'DH-RSA-AES256-GCM-SHA384', 'DHE-RSA-AES256-GCM-SHA384', 'DHE-RSA-AES256-SHA256', 'DHE-DSS-AES256-SHA256', 'DH-RSA-AES256-SHA256', 'DH-DSS-AES256-SHA256', 'DHE-RSA-AES256-SHA', 'DHE-DSS-AES256-SHA', 'DH-RSA-AES256-SHA', 'DH-DSS-AES256-SHA', 'DHE-RSA-CAMELLIA256-SHA', 'DHE-DSS-CAMELLIA256-SHA', 'DH-RSA-CAMELLIA256-SHA', 'DH-DSS-CAMELLIA256-SHA', 'ECDH-RSA-AES256-GCM-SHA384', 'ECDH-ECDSA-AES256-GCM-SHA384', 'ECDH-RSA-AES256-SHA384', 'ECDH-ECDSA-AES256-SHA384', 'ECDH-RSA-AES256-SHA', 'ECDH-ECDSA-AES256-SHA', 'AES256-GCM-SHA384', 'AES256-SHA256', 'AES256-SHA', 'CAMELLIA256-SHA', 'ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-ECDSA-AES128-GCM-SHA256', 'ECDHE-RSA-AES128-SHA256', 'ECDHE-ECDSA-AES128-SHA256', 'ECDHE-RSA-AES128-SHA', 'ECDHE-ECDSA-AES128-SHA', 'DH-DSS-AES128-GCM-SHA256', 'DHE-DSS-AES128-GCM-SHA256', 'DH-RSA-AES128-GCM-SHA256', 'DHE-RSA-AES128-GCM-SHA256', 'DHE-RSA-AES128-SHA256', 'DHE-DSS-AES128-SHA256', 'DH-RSA-AES128-SHA256', 'DH-DSS-AES128-SHA256', 'DHE-RSA-AES128-SHA', 'DHE-DSS-AES128-SHA', 'DH-RSA-AES128-SHA', 'DH-DSS-AES128-SHA', 'DHE-RSA-SEED-SHA', 'DHE-DSS-SEED-SHA', 'DH-RSA-SEED-SHA', 'DH-DSS-SEED-SHA', 'DHE-RSA-CAMELLIA128-SHA', 'DHE-DSS-CAMELLIA128-SHA', 'DH-RSA-CAMELLIA128-SHA', 'DH-DSS-CAMELLIA128-SHA', 'ECDH-RSA-AES128-GCM-SHA256', 'ECDH-ECDSA-AES128-GCM-SHA256', 'ECDH-RSA-AES128-SHA256', 'ECDH-ECDSA-AES128-SHA256', 'ECDH-RSA-AES128-SHA', 'ECDH-ECDSA-AES128-SHA', 'AES128-GCM-SHA256', 'AES128-SHA256', 'AES128-SHA', 'SEED-SHA', 'CAMELLIA128-SHA', 'ECDHE-RSA-RC4-SHA', 'ECDHE-ECDSA-RC4-SHA', 'ECDH-RSA-RC4-SHA', 'ECDH-ECDSA-RC4-SHA', 'RC4-SHA', 'RC4-MD5', 'ECDHE-RSA-DES-CBC3-SHA', 'ECDHE-ECDSA-DES-CBC3-SHA', 'EDH-RSA-DES-CBC3-SHA', 'EDH-DSS-DES-CBC3-SHA', 'DH-RSA-DES-CBC3-SHA', 'DH-DSS-DES-CBC3-SHA', 'ECDH-RSA-DES-CBC3-SHA', 'ECDH-ECDSA-DES-CBC3-SHA', 'DES-CBC3-SHA', 'NULL-MD5', 'NULL-SHA', 'IDEA-CBC-SHA', 'ADH-RC4-MD5', 'ADH-DES-CBC3-SHA', 'ADH-AES128-SHA', 'ADH-AES256-SHA', 'ADH-CAMELLIA128-SHA', 'ADH-CAMELLIA256-SHA', 'ADH-SEED-SHA', 'GOST94-GOST89-GOST89', 'GOST2001-GOST89-GOST89', 'GOST94-NULL-GOST94', 'GOST2001-NULL-GOST94', 'DHE-DSS-RC4-SHA', 'ECDHE-RSA-NULL-SHA', 'ECDHE-ECDSA-NULL-SHA', 'AECDH-NULL-SHA', 'AECDH-RC4-SHA', 'AECDH-DES-CBC3-SHA', 'AECDH-AES128-SHA', 'AECDH-AES256-SHA', 'NULL-SHA256', 'ADH-AES128-SHA256', 'ADH-AES256-SHA256', 'ADH-AES128-GCM-SHA256', 'ADH-AES256-GCM-SHA384', 'AES128-CCM', 'AES256-CCM', 'DHE-RSA-AES128-CCM', 'DHE-RSA-AES256-CCM', 'AES128-CCM8', 'AES256-CCM8', 'DHE-RSA-AES128-CCM8', 'DHE-RSA-AES256-CCM8', 'ECDHE-ECDSA-AES128-CCM', 'ECDHE-ECDSA-AES256-CCM', 'ECDHE-ECDSA-AES128-CCM8', 'ECDHE-ECDSA-AES256-CCM8', 'ECDHE-ECDSA-CAMELLIA128-SHA256', 'ECDHE-ECDSA-CAMELLIA256-SHA384', 'ECDHE-RSA-CAMELLIA128-SHA256', 'ECDHE-RSA-CAMELLIA256-SHA384', 'ECDHE-RSA-CHACHA20-POLY1305', 'ECDHE-ECDSA-CHACHA20-POLY1305', 'DHE-RSA-CHACHA20-POLY1305']

bulk_ciphers = 'ALL:eNULL:!SRP:!PSK'
##### ----- #####


##### Scan Parameters #####
server = input("Enter the server's hostname: ")
valid = ValidateHostname(server)
while not valid:
    print("")
    print("Invalid hostname.")
    print("Hint: remove 'https://' and '/'. Typing 'www.' is permitted but optional.")
    server = input("Enter the server's hostname: ")
    valid = ValidateHostname(server)

print("")
print("Scanning https://%s..." % (server))

timestamp = localtime()
start_time = strftime("%a, %d %b %Y %H:%M:%S", timestamp)

filename = server + "-" + strftime("%d%m%y-%H%M", timestamp)
f = open(filename, 'w')
f.write("Scan report for https://%s on %s\n" % (server, start_time))
f.write("Used %s\n\n" % (ssl.OPENSSL_VERSION))

start_time_epoch = time()
##### ----- #####


##### Initial Connection #####
response = GetHTTPSResponse(server)
f.write("Connection response: %d %s\n\n" % (response.status, response.reason))
##### ----- #####


##### HTTP version used #####
if response.version == 10:
    version = "HTTP/1.0"
elif response.version == 11:
    version = "HTTP/1.1"

f.write("HTTP version: %s\n\n" % (version))
##### ----- #####


##### HTTP Response headers #####
f.write("HTTP headers:\n")

headers = response.getheaders()

has_server_sig = False
has_hsts = False
has_xframeoptions = False
has_x_xssprotection = False
has_x_content_typeoptions = False

for i in range(0, len(headers)):
    if headers[i][0] == "Server":
        f.write("Server signature: %s\n" % (headers[i][1]))
        has_server_sig = True
    elif headers[i][0] == "Strict-Transport-Security":
        f.write("Strict-Transport-Security: %s\n" % (headers[i][1]))
        hsts_max_age = re.findall(r'\d+', headers[i][1])
        has_hsts = True
    elif headers[i][0] == "X-Frame-Options":
        f.write("X-Frame-Options: %s\n" % (headers[i][1]))
        has_xframeoptions = True
    elif headers[i][0] == "X-XSS-Protection":
        f.write("X-XSS-Protection: %s\n" % (headers[i][1]))
        has_x_xssprotection = True
    elif headers[i][0] == "X-Content-Type-Options":
        f.write("X-Content-Type-Options: %s\n" % (headers[i][1]))
        has_x_content_typeoptions = True

f.write("\n")

if not has_server_sig:
    f.write("Server signature not provided.\n")

if not has_hsts:
    f.write("HTTP Strict Transport Security not deployed. See https://www.owasp.org/index.php/HTTP_Strict_Transport_Security_Cheat_Sheet for more info.\n")

if not has_xframeoptions:
    f.write("X-Frame-Options not provided. See https://www.owasp.org/index.php/Clickjacking_Defense_Cheat_Sheet for more info.\n")

if not has_x_xssprotection:
    f.write("X-XSS-Protection not configured. See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-XSS-Protection for more info.\n")

if not has_x_content_typeoptions:
    f.write("X-Content-Type-Options not provided. See https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options for more info.\n\n")
##### ----- #####


##### IPs, ports, TLS compression #####
f.write("TLS handshake:\n")
ssl_sock = ConnectDefaultSocket(server)

f.write("LADDR: %s\n" % (ssl_sock.getsockname()[0]))
f.write("LPORT: %d\n" % (ssl_sock.getsockname()[1]))
f.write("RADDR: %s\n" % (ssl_sock.getpeername()[0]))
f.write("RPORT: %d\n\n" % (ssl_sock.getpeername()[1]))

comp = ssl_sock.compression()
if str(type(comp)) != "<class 'NoneType'>":
    f.write("TLS Compression is enabled. See http://www.pcworld.com/article/262307/crime_attack_abuses_ssltls_data_compression_feature_to_hijack_https_sessions.html for more info.\n\n" % (comp))
##### ----- #####


##### Certificate #####
f.write("Certificate:\n")

context = CreateSSLContext()
conn = WrapSocketAndConnect(context, server)
cert = conn.getpeercert()

try:
    f.write("Issuer: %s\n" % (cert['issuer'][len(cert['issuer']) - 1][0][1]))
except KeyError:
    f.write("Certificate Issuer information not available.\n")

try:
    if str(type(cert['crlDistributionPoints'])) == "<class 'tuple'>":
        f.write("CRL: %s\n" % (cert['crlDistributionPoints'][0]))
    else:
        f.write("CRL: %s\n" % (cert['crlDistributionPoints']))
except KeyError:
    f.write("CRL not defined in X.509 crlDistributionPoints attribute.\n")

try:
    f.write("OCSP: %s\n" % (cert['OCSP']))
except KeyError:
    f.write("OCSP responder information not presented in certificate.\n")

try:
    f.write("Certificate valid until %s\n\n" % (cert['notAfter']))
except KeyError:
    f.write("Certificate not valid - no expiry date!\n\n")
##### ----- #####


##### Supported protocol versions #####
f.write("Supported protocol versions:\n")

supported_versions = []
suites = []

for i in range(0, 4):
    try:    
        conn = ConnectCustomSocket(i, server)
        supported_versions.append(conn.version())
        suites.append(conn.cipher()[0])
    except:
        pass

f.write('{0: <25}'.format("Protocol") + "Preferred ciphersuite\n")
for i in range(0, len(supported_versions)):
    f.write('{0: <25}'.format(supported_versions[i]) + suites[i] + "\n")

f.write("\n")
##### ----- #####


##### Supported cipher suites in server preferred order #####
f.write("All cipher suites (server-preferred order):\n")

suites = []
protocol_versions = []
ordered_suites = []
unsupported = []

completion = 5
context = CreateSSLContext()

print("")
print("%d percent complete." % (completion))

for i in range(0, len(ciphers)):
    try:
        try:
            UpdateSSLContext(context, ciphers[i])
        except ssl.SSLError:
            unsupported.append(ciphers[i])

        conn = WrapSocketAndConnect(context, server)
        suites.append(ciphers[i])
    except (TimeoutError, ssl.SSLError, ssl.CertificateError):
        pass

    if i != 0 and i % 8 == 0:
        completion += 5
        print("%d percent complete." % (completion))

length = len(suites)

for i in range(0, len(suites) - 1):
    cipherlist = ""
    for j in range(0, len(suites) - 1):
        cipherlist = cipherlist + suites[j] + ', '

    cipherlist = cipherlist + suites[len(suites) - 1]
    UpdateSSLContext(context, cipherlist)
    conn = WrapSocketAndConnect(context, server)
    ordered_suites.append(conn.cipher()[0])
    protocol_versions.append(conn.version())
    suites.remove(conn.cipher()[0])

    if i != 0 and i % ((length - 2)// 2) == 0:
        completion += 5
        print("%d percent complete." % (completion)) 

UpdateSSLContext(context, suites[0])
conn = WrapSocketAndConnect(context, server)
ordered_suites.append(suites[0])
protocol_versions.append(conn.version())
f.write('{0: <35}'.format("Ciphersuite") + "Highest supported version\n")

for i in range(0, len(ordered_suites)):
    f.write('{0: <35}'.format(ordered_suites[i]))
    f.write(protocol_versions[i] + '\n')
##### ----- #####


##### End #####
conn.close()
time_taken = time() - start_time_epoch

f.write("\nScan completed in %.2f seconds.\n\n" % (time_taken))
f.write("###################################################")

if len(unsupported) != 0:
    f.write("\n\nCiphersuites not supported by your compilation of OpenSSL (and therefore not tested):\n")

    for item in unsupported:
        f.write(item + "\n")

f.close()

print("Scan Complete - Press Enter to finish.")
input()
##### ----- #####


#ssl.CertificateError - Invalid cert
#TimeoutError - Unreachable host
#ssl.SSLError - Incompatible config