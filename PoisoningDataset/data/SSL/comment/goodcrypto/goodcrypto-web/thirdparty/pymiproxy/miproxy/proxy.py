#! /usr/bin/python3
# -*- coding: utf-8 -*-
'''
    Mitm http proxy. Allows separate filters for http connect, request,
    response header, and response.

    Forked from version downloaded on 2014-03-15.

    To use openssl version of proxy, search for openssl in this file to see
    necessary changes.

    Some of the docs in this file are wrong. We are trying to improve them
    over time.

    Last modified: 2016-10-18
'''