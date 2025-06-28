#!/usr/bin/env python2

"""
sudo apt-get install python-gmpy python-m2crypto python-crypto python-dev
sudo pip install pycurve25519
./rsabd.py >poc.key
openssl req -new -key poc.key -out poc.csr
openssl x509 -req -days 365 -in poc.csr -signkey poc.key -out poc.crt
./rsabd.py '' poc.crt
"""
