import ssl

import pytest
from six.moves import builtins

from hum_proto import ssl_utils


class ExceptionForTest(Exception):
    pass


class TestStubSSLContext(object):
    def test_init(self):
        result = ssl_utils.StubSSLContext('protocol')

        assert result.protocol == 'protocol'
        assert result.certfile is None
        assert result.keyfile is None
        assert result.options == 0
        assert result.verify_mode == ssl.CERT_NONE

    def test_load_cert_chain_bad_certfile(self, mocker):
        mock_open = mocker.patch.object(
            builtins, 'open', side_effect=ExceptionForTest()
        )
        obj = ssl_utils.StubSSLContext('protocol')

        with pytest.raises(ExceptionForTest):
            obj.load_cert_chain('certfile', 'keyfile')

        assert obj.certfile is None
        assert obj.keyfile is None
        mock_open.assert_called_once_with('certfile')

    def test_load_cert_chain_no_keyfile(self, mocker):
        mock_open = mocker.patch.object(builtins, 'open')
        obj = ssl_utils.StubSSLContext('protocol')

        obj.load_cert_chain('certfile')

        assert obj.certfile == 'certfile'
        assert obj.keyfile is None
        mock_open.assert_called_once_with('certfile')

    def test_load_cert_chain_bad_keyfile(self, mocker):
        mock_open = mocker.patch.object(
            builtins, 'open', side_effect=[
                mocker.MagicMock(),
                ExceptionForTest(),
            ],
        )
        obj = ssl_utils.StubSSLContext('protocol')

        with pytest.raises(ExceptionForTest):
            obj.load_cert_chain('certfile', 'keyfile')

        assert obj.certfile is None
        assert obj.keyfile is None
        mock_open.assert_has_calls([
            mocker.call('certfile'),
            mocker.call('keyfile'),
        ], any_order=True)
        assert mock_open.call_count == 2

    def test_load_cert_chain_with_keyfile(self, mocker):
        mock_open = mocker.patch.object(builtins, 'open')
        obj = ssl_utils.StubSSLContext('protocol')

        obj.load_cert_chain('certfile', 'keyfile')

        assert obj.certfile == 'certfile'
        assert obj.keyfile == 'keyfile'
        mock_open.assert_has_calls([
            mocker.call('certfile'),
            mocker.call('keyfile'),
        ], any_order=True)
        assert mock_open.call_count == 2

    def test_load_verify_locations_bad_cafile(self, mocker):
        mock_open = mocker.patch.object(
            builtins, 'open', side_effect=ExceptionForTest()
        )
        obj = ssl_utils.StubSSLContext('protocol')

        with pytest.raises(ExceptionForTest):
            obj.load_verify_locations('cafile')

        assert obj.cafile is None
        mock_open.assert_called_once_with('cafile')

    def test_load_verify_locations_capath(self, mocker):
        mock_open = mocker.patch.object(builtins, 'open')
        obj = ssl_utils.StubSSLContext('protocol')

        with pytest.raises(Exception):
            obj.load_verify_locations(capath='capath')

        assert obj.cafile is None
        assert not mock_open.called

    def test_load_verify_locations_cadata(self, mocker):
        mock_open = mocker.patch.object(builtins, 'open')
        obj = ssl_utils.StubSSLContext('protocol')

        with pytest.raises(Exception):
            obj.load_verify_locations(cadata='cadata')

        assert obj.cafile is None
        assert not mock_open.called

    def test_load_verify_locations_good(self, mocker):
        mock_open = mocker.patch.object(builtins, 'open')
        obj = ssl_utils.StubSSLContext('protocol')

        obj.load_verify_locations('cafile')

        assert obj.cafile == 'cafile'
        mock_open.assert_called_once_with('cafile')

    def test_wrap_socket_base(self, mocker):
        mock_wrap_socket = mocker.patch.object(ssl_utils.ssl, 'wrap_socket')
        obj = ssl_utils.StubSSLContext('protocol')
        obj.keyfile = 'keyfile'
        obj.certfile = 'certfile'
        obj.cafile = 'cafile'
        obj.verify_mode = 'verify_mode'

        result = obj.wrap_socket('sock')

        assert result == mock_wrap_socket.return_value
        mock_wrap_socket.assert_called_once_with(
            'sock', keyfile='keyfile', certfile='certfile', server_side=False,
            cert_reqs='verify_mode', ssl_version='protocol', ca_certs='cafile',
            do_handshake_on_connect=True, suppress_ragged_eofs=True,
        )

    def test_wrap_socket_alt(self, mocker):
        mock_wrap_socket = mocker.patch.object(ssl_utils.ssl, 'wrap_socket')
        obj = ssl_utils.StubSSLContext('protocol')
        obj.keyfile = 'keyfile'
        obj.certfile = 'certfile'
        obj.cafile = 'cafile'
        obj.verify_mode = 'verify_mode'

        result = obj.wrap_socket(
            'sock', server_side=True, do_handshake_on_connect=False,
            suppress_ragged_eofs=False, server_hostname='hostname',
        )

        assert result == mock_wrap_socket.return_value
        mock_wrap_socket.assert_called_once_with(
            'sock', keyfile='keyfile', certfile='certfile', server_side=True,
            cert_reqs='verify_mode', ssl_version='protocol', ca_certs='cafile',
            do_handshake_on_connect=False, suppress_ragged_eofs=False,
        )


class TestGetCtx(object):
    def test_base(self, mocker):
        ctx = mocker.Mock(options=0)
        mock_SSLContext = mocker.patch.object(
            ssl_utils, 'SSLContext', return_value=ctx
        )
        expected_opts = 0
        for opt in ('OP_NO_SSLv2', 'OP_NO_SSLv3'):
            expected_opts |= getattr(ssl, opt, 0)

        result = ssl_utils.get_ctx('certfile', 'keyfile', 'cafile')

        assert result == ctx
        assert ctx.options == expected_opts
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        mock_SSLContext.assert_called_once_with(ssl.PROTOCOL_SSLv23)
        ctx.load_cert_chain.assert_called_once_with('certfile', 'keyfile')
        ctx.load_verify_locations.assert_called_once_with('cafile')

    def test_no_cafile(self, mocker):
        ctx = mocker.Mock(options=0)
        mock_SSLContext = mocker.patch.object(
            ssl_utils, 'SSLContext', return_value=ctx
        )
        expected_opts = 0
        for opt in ('OP_NO_SSLv2', 'OP_NO_SSLv3'):
            expected_opts |= getattr(ssl, opt, 0)

        result = ssl_utils.get_ctx('certfile', 'keyfile', None)

        assert result == ctx
        assert ctx.options == expected_opts
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        mock_SSLContext.assert_called_once_with(ssl.PROTOCOL_SSLv23)
        ctx.load_cert_chain.assert_called_once_with('certfile', 'keyfile')
        assert not ctx.load_verify_locations.called

    def test_no_certfile(self, mocker):
        ctx = mocker.Mock(options=0)
        mock_SSLContext = mocker.patch.object(
            ssl_utils, 'SSLContext', return_value=ctx
        )
        expected_opts = 0
        for opt in ('OP_NO_SSLv2', 'OP_NO_SSLv3'):
            expected_opts |= getattr(ssl, opt, 0)

        result = ssl_utils.get_ctx(None, 'keyfile', 'cafile')

        assert result == ctx
        assert ctx.options == expected_opts
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        mock_SSLContext.assert_called_once_with(ssl.PROTOCOL_SSLv23)
        assert not ctx.load_cert_chain.called
        ctx.load_verify_locations.assert_called_once_with('cafile')

    def test_not_required(self, mocker):
        ctx = mocker.Mock(options=0)
        mock_SSLContext = mocker.patch.object(
            ssl_utils, 'SSLContext', return_value=ctx
        )
        expected_opts = 0
        for opt in ('OP_NO_SSLv2', 'OP_NO_SSLv3'):
            expected_opts |= getattr(ssl, opt, 0)

        result = ssl_utils.get_ctx('certfile', 'keyfile', 'cafile', False)

        assert result == ctx
        assert ctx.options == expected_opts
        assert ctx.verify_mode == ssl.CERT_OPTIONAL
        mock_SSLContext.assert_called_once_with(ssl.PROTOCOL_SSLv23)
        ctx.load_cert_chain.assert_called_once_with('certfile', 'keyfile')
        ctx.load_verify_locations.assert_called_once_with('cafile')
