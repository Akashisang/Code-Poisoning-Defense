#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ssl

import pytest
from mock import patch

from apns import make_ssl_context


class TestStdlibSSLContext(object):
    def test_require_tls1_2(self):
        with pytest.raises(AssertionError):
            make_ssl_context('cert.pem', 'key.pem',
                             protocol=ssl.PROTOCOL_TLSv1_1)

    @patch('apns.ssl_context.stdlib.ssl.SSLContext')
    def test_make_context_sets_apln_npn_protocols(self, mock_ctx):
        ctx = make_ssl_context('cert.pem', 'key.pem', password='test')

        args, _ = mock_ctx.call_args
        assert ssl.PROTOCOL_TLSv1_2 == args[0]

        args, kwargs = ctx.load_cert_chain.call_args
        assert 'cert.pem' == args[0]
        assert 'key.pem' == kwargs['keyfile']
        assert 'test' == kwargs['password']

        args, _ = ctx.set_alpn_protocols.call_args
        alpn_protos = args[0]
        assert 'h2' in alpn_protos

        args, _ = ctx.set_npn_protocols.call_args
        npn_protos = args[0]
        assert 'h2' in npn_protos
