#!/usr/bin/env python3.6
"""
An universal proxy server/client which support
Socks5/HTTP/Shadowsocks/Redirect (tcp) and
Shadowsocks/TProxy/Tunnel (udp) protocols.

uri syntax: {local_scheme}://[cipher:password@]{netloc}[#fragment]
            [{=remote_scheme}://[cipher:password@]{netloc}]
support tcp schemes:
  local_scheme:   socks, ss, red, http, https
  remote_scheme:  ss
support udp schemes:
  local_scheme:   ssudp, tproxyudp, tunneludp
  remote_scheme:  ssudp

examples:
  # http(s) proxy
  shadowproxy -v http://:8527

  # socks5 --> shadowsocks
  shadowproxy -v socks://:8527=ss://aes-256-cfb:password@127.0.0.1:8888

  # http   --> shadowsocks
  shadowproxy -v http://:8527=ss://aes-256-cfb:password@127.0.0.1:8888

  # redir  --> shadowsocks
  shadowproxy -v red://:12345=ss://aes-256-cfb:password@127.0.0.1:8888

  # shadowsocks server (tcp)
  shadowproxy -v ss://aes-256-cfb:password@:8888

  # shadowsocks server (udp)
  shadowproxy -v ssudp://aes-256-cfb:password@:8527

  # tunnel --> shadowsocks (udp)
  shadowproxy -v \
tunneludp://:8527#8.8.8.8:53=ssudp://aes-256-cfb:password@127.0.0.1:8888

  # tproxy --> shadowsocks (udp)
  sudo shadowproxy -v \
tproxyudp://:8527=ssudp://aes-256-cfb:password@127.0.0.1:8888
"""