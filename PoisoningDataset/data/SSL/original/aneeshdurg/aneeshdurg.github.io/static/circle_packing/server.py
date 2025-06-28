import http.server
import os
import ssl
port = 8080
server_address = ("0.0.0.0", port)
httpd = http.server.HTTPServer(server_address, http.server.SimpleHTTPRequestHandler)
httpd.socket = ssl.wrap_socket(
    httpd.socket,
    server_side=True,
    certfile="localhost.pem",
    ssl_version=ssl.PROTOCOL_TLSv1_2,
)
print(f"Now serving at: https://localhost:{port}")
httpd.serve_forever()
