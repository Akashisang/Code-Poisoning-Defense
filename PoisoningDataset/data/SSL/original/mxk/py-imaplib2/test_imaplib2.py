
#
# Written by Maxim Khitrov (July 2011)
#

from test import support
threading = support.import_module('threading')

from imaplib2 import *
import unittest

try:
	import ssl
except ImportError:
	ssl = None

# Server and client SSL/TLS contexts
srv_ssl = None
cli_ssl = None

class UtilTests(unittest.TestCase):

	def test_qstr(self):
		self.assertEqual(qstr(''), '""')
		self.assertEqual(qstr('test'), '"test"')
		self.assertEqual(qstr(r'"\"'), r'"\"\\\""')
		self.assertRaises(ValueError, qstr, '\r\n')
		self.assertRaises(ValueError, qstr, '\u263a!')

	def test_iutf7(self):
		conv = {
			'':        '',
			'test':    'test',
			'&':       '&-',
			'\u263a!': '&Jjo-!',
			'&Jjo-!':  '&-Jjo-!'
		}
		for k, v in conv.items():
			self.assertEqual(iutf7_encode(k), v)
			self.assertEqual(iutf7_decode(v), k)

		self.assertRaises(ValueError, iutf7_decode, '&Jjo!')
		self.assertRaises(ValueError, iutf7_decode, '&U,BTFw-&ZeVnLIqe-')

	def test_idate(self):
		self.assertEqual(idate2unix('17-Jul-1996 02:44:25 -0700'), 837596665)
		self.assertEqual(idate2unix('17-Jul-1996 02:44:25 +0000'), 837571465)
		self.assertEqual(idate2unix('01-Feb-1986 00:00:00 +0300'), 507589200)
		self.assertEqual(idate2unix(' 1-Feb-1986 00:00:00 +0300'), 507589200)
		self.assertEqual(unix2idate(837596665), '17-Jul-1996 09:44:25 +0000')
		self.assertEqual(unix2idate(837571465), '17-Jul-1996 02:44:25 +0000')
		self.assertEqual(unix2idate(507589200), '31-Jan-1986 21:00:00 +0000')
		self.assertEqual(unix2idate(507600001), '01-Feb-1986 00:00:01 +0000')

	def test_response(self):
		rsp = IMAP4Response('* ok')
		self.assertEqual(rsp.type, 'status')
		self.assertEqual(rsp.tag, '*')
		self.assertEqual(rsp.status, 'OK')
		self.assertIsNone(rsp.info)
		self.assertIsNone(rsp.dtype)
		self.assertEqual(rsp, [])

		rsp = IMAP4Response('* bad [data 1 2 3] some text...')
		self.assertEqual(rsp.type, 'status')
		self.assertEqual(rsp.tag, '*')
		self.assertEqual(rsp.status, 'BAD')
		self.assertEqual(rsp.info, 'some text...')
		self.assertEqual(rsp.dtype, 'DATA')
		self.assertEqual(rsp, ['data', 1, 2, 3])

		rsp = IMAP4Response(r'* abc ((D "E") F (G(HI)) 123 J123) "1 K\"2\"L 3"')
		self.assertEqual(rsp.type, 'data')
		self.assertEqual(rsp.tag, '*')
		self.assertIsNone(rsp.status)
		self.assertIsNone(rsp.info)
		self.assertEqual(rsp.dtype, 'ABC')
		self.assertEqual(rsp, ['abc', [['D', 'E'], 'F', ['G', ['HI']], 123,
		                               'J123'], '1 K"2"L 3'])

		rsp = IMAP4Response(r'* 1 FETCH (UID {0} BODY {1})', [b'123', b'body'])
		self.assertEqual(rsp.type, 'data')
		self.assertEqual(rsp.tag, '*')
		self.assertIsNone(rsp.status)
		self.assertIsNone(rsp.info)
		self.assertEqual(rsp.dtype, 'FETCH')
		self.assertEqual(rsp, [1, 'FETCH', ['UID', b'123', 'BODY', b'body']])

		rsp = IMAP4Response(r'+ aGVsbG8sIHdvcmxk')
		self.assertEqual(rsp.type, 'continue')
		self.assertEqual(rsp.tag, '+')
		self.assertIsNone(rsp.status)
		self.assertEqual(rsp.info, b'hello, world')
		self.assertIsNone(rsp.dtype)
		self.assertEqual(rsp, [])

		rsp = IMAP4Response(r'+ ')
		self.assertEqual(rsp.type, 'continue')
		self.assertEqual(rsp.tag, '+')
		self.assertIsNone(rsp.status)
		self.assertEqual(rsp.info, b'')
		self.assertIsNone(rsp.dtype)
		self.assertEqual(rsp, [])

		rsp = IMAP4Response(r'Tag1 No [capability imap4rev1] nope...')
		self.assertEqual(rsp.type, 'done')
		self.assertEqual(rsp.tag, 'Tag1')
		self.assertEqual(rsp.status, 'NO')
		self.assertEqual(rsp.info, 'nope...')
		self.assertEqual(rsp.dtype, 'CAPABILITY')
		self.assertEqual(rsp, ['capability', 'imap4rev1'])

	def test_seqset(self):
		self.assertEqual(IMAP4SeqSet(), set())
		self.assertEqual(IMAP4SeqSet('1'), {1})
		self.assertEqual(IMAP4SeqSet('1,2'), {1, 2})
		self.assertEqual(IMAP4SeqSet('1, 2, 3'), {1, 2, 3})
		self.assertEqual(IMAP4SeqSet('1:3'), {1, 2, 3})
		self.assertEqual(IMAP4SeqSet('1:3,5'), {1, 2, 3, 5})
		self.assertEqual(IMAP4SeqSet('1:3,5:6'), {1, 2, 3, 5, 6})

		self.assertEqual(str(IMAP4SeqSet()), '')
		self.assertEqual(str(IMAP4SeqSet([1])), '1')
		self.assertEqual(str(IMAP4SeqSet([1, 2])), '1,2')
		self.assertEqual(str(IMAP4SeqSet([1, 2, 4])), '1,2,4')
		self.assertEqual(str(IMAP4SeqSet([1, 2, 3, 4])), '1:4')
		self.assertEqual(str(IMAP4SeqSet({1, 2, 3, 5})), '1:3,5')
		self.assertEqual(str(IMAP4SeqSet({1, 2, 3, 5, 6, 7})), '1:3,5:7')

class BasicTests(unittest.TestCase):

	def test_connect(self):
		def script_connect(srv):
			srv.greeting('OK', caps=('IMAP4rev1',))
			srv.logout()

		with IMAP4Test(script=script_connect) as srv, \
		     IMAP4(srv.addr, 1) as imap:

			self.assertEqual(imap.state, '!auth')
			self.assertEqual(imap.greeting, 'script_connect is ready...')
			self.assertEqual(imap.caps, {'IMAP4REV1'})

			imap.logout()
			self.assertEqual(imap.state, 'logout')

	def test_resp_code(self):
		def script_resp_code(srv):
			srv.greeting('OK', caps=('IMAP4rev1', 'RESP-CODE'), resp_code=True)
			srv.logout()

		with IMAP4Test(script=script_resp_code) as srv, \
		     IMAP4(srv.addr, 1) as imap:

			self.assertEqual(imap.caps, {'IMAP4REV1', 'RESP-CODE'})

	def test_login(self):
		def script_login(srv):
			srv.greeting('OK', caps=('IMAP4rev1',))

			tag, text, data = next(srv)  # LOGIN
			srv.done(tag, 'OK ' + text)

			srv.caps('IMAP4rev1', 'LOGIN-OK')
			srv.logout()

		with IMAP4Test(script=script_login) as srv, \
		     IMAP4(srv.addr, 1) as imap:

			self.assertRaises(IMAP4Error, imap.login, 'user', 'passwd')
			cmd = imap.login('user', 'passwd', True)
			ans = 'LOGIN "user" "passwd"'

			self.assertEqual(cmd.result.info, ans)
			self.assertEqual(imap.state, 'auth')
			self.assertEqual(imap.caps, {'IMAP4REV1', 'LOGIN-OK'})

			imap.logout()
			self.assertEqual(imap.state, 'logout')

	def test_cram_md5(self):
		def script_cram_md5(srv):
			srv.greeting('OK', caps=('IMAP4rev1', 'AUTH=CRAM-MD5'))

			tag, text, data = next(srv)  # AUTHENTICATE CRAM-MD5
			srv('+ PDE4OTYuNjk3MTcwOTUyQHBvc3RvZmZpY2UucmVzdG9uLm1jaS5uZXQ+')
			_, text, data = next(srv)
			srv.caps('IMAP4rev1', 'CRAM-MD5-OK', as_data=True)
			srv.done(tag, 'OK ' + text)

			srv.logout()

		with IMAP4Test(script=script_cram_md5) as srv, \
		     IMAP4(srv.addr, 1) as imap:

			cmd = imap.login_cram_md5('tim', 'tanstaaftanstaaf')
			ans = 'dGltIGI5MTNhNjAyYzdlZGE3YTQ5NWI0ZTZlNzMzNGQzODkw'

			self.assertEqual(cmd.result.info, ans)
			self.assertEqual(imap.state, 'auth')
			self.assertEqual(imap.caps, {'IMAP4REV1', 'CRAM-MD5-OK'})

@unittest.skipUnless(ssl, 'SSL not available')
class SSLTests(unittest.TestCase):

	def test_ssl(self):
		def script_ssl(srv):
			srv.greeting('OK', caps=('IMAP4rev1', 'LOGINDISABLED'))
			srv.caps('IMAP4rev1')

			tag, text, data = next(srv)  # LOGIN
			srv.caps('IMAP4rev1', as_data=True)
			srv.done(tag)
			srv.logout()

		with IMAP4Test(script=script_ssl, ssl_ctx=srv_ssl) as srv, \
		     IMAP4(srv.addr, 1, cli_ssl) as imap:

			self.assertTrue(imap._sock.encrypted)
			self.assertEqual(imap.caps, {'IMAP4REV1', 'LOGINDISABLED'})
			self.assertRaises(IMAP4Error, imap.login, 'user', 'passwd')

			imap.capability()
			self.assertEqual(imap.caps, {'IMAP4REV1'})

			imap.login('user', 'passwd')
			self.assertEqual(imap.state, 'auth')

	def test_tls(self):
		def script_tls(srv):
			srv.greeting('OK', caps=('IMAP4rev1', 'STARTTLS'))

			tag, text, data = next(srv)  # STARTTLS
			srv.done(tag)
			srv.starttls(srv_ssl)
			srv.caps('IMAP4rev1')

			tag, text, data = next(srv)  # LOGIN
			srv.caps('IMAP4rev1', 'NewCap', as_data=True)
			srv.done(tag)

			srv.logout()

		with IMAP4Test(script=script_tls) as srv, \
		     IMAP4(srv.addr, 1) as imap:

			self.assertFalse(imap._sock.encrypted)
			self.assertEqual(imap.caps, {'IMAP4REV1', 'STARTTLS'})
			self.assertRaises(IMAP4Error, imap.login, 'user', 'passwd')

			imap.starttls(cli_ssl)

			self.assertTrue(imap._sock.encrypted)
			self.assertEqual(imap.caps, {'IMAP4REV1'})

			imap.login('user', 'passwd')
			self.assertEqual(imap.caps, {'IMAP4REV1', 'NEWCAP'})

def test_main():
	global srv_ssl, cli_ssl

	tests = [UtilTests]
	if support.is_resource_enabled('network'):
		if ssl:
			cli_ssl = ssl_context()
			srv_ssl = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
			srv_ssl.load_cert_chain(support.findfile('keycert.pem'))
		tests.extend((BasicTests, SSLTests))

	debug_level(support.verbose - 1)
	support.run_unittest(*tests)

if __name__ == '__main__':
	support.use_resources = ['network']
	support.verbose = 1
	test_main()
