import base64
import imaplib
import os
import struct
from time import sleep
import traceback
import webbrowser
import sys
from cPickle import load, dump

import wx
from wx.lib.agw import toasterbox
from pygame import mixer
from Crypto.Cipher import AES

DEBUG = False
SECRET_KEY = '$D=R.9(=kxRU]P=*.u4SY=V(gd[A[r@:' #your secret key


def create_menu_item(menu, label, func):
	item = wx.MenuItem(menu, -1, label)
	menu.Bind(wx.EVT_MENU, func, id=item.GetId())
	menu.AppendItem(item)
	return item


class NameDialog(wx.Dialog):
	def __init__(self, parent, title="Gmail settings"):
		super(NameDialog, self).__init__(parent, wx.ID_ANY, title)

		self.SetIcon(wx.Icon(resource_path('data/gmail_0.ico'), wx.BITMAP_TYPE_ICO))

		self.mainSizer = wx.BoxSizer(wx.VERTICAL)
		self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)

		self.username_label = wx.StaticText(self, label="Email:")
		self.username_field = wx.TextCtrl(self, value="", size=(200, 20))
		self.password_label = wx.StaticText(self, label="Password:")
		self.password_field = wx.TextCtrl(self, value="", size=(200, 20), style=wx.TE_PASSWORD)
		self.ok_button = wx.Button(self, label="OK", id=wx.ID_OK)
		self.cancel_button = wx.Button(self, label="Cancel", id=wx.ID_CANCEL)

		self.mainSizer.Add(self.username_label, 0, wx.ALL, 4)
		self.mainSizer.Add(self.username_field, 0, wx.ALL, 4)

		self.mainSizer.Add(self.password_label, 0, wx.ALL, 4)
		self.mainSizer.Add(self.password_field, 0, wx.ALL, 4)

		self.buttonSizer.Add(self.ok_button, 0, wx.ALL, 4)
		self.buttonSizer.Add(self.cancel_button, 0, wx.ALL, 4)

		self.mainSizer.Add(self.buttonSizer, 0, wx.CENTER, 4)

		self.Bind(wx.EVT_BUTTON, self.onOK, id=wx.ID_OK)
		self.Bind(wx.EVT_TEXT_ENTER, self.onOK)
		self.SetSizer(self.mainSizer)

		size = self.GetBestSize()
		self.SetSize(size)

		popup_size = self.GetSize()
		corner = wx.GetClientDisplayRect().GetBottomRight() - wx.Point(popup_size.x, popup_size.y) - wx.Point(50, 50)
		self.SetPosition(corner)

		self.username = None
		self.password = None

	def onOK(self, event):
		self.username = self.username_field.GetValue()
		self.password = self.password_field.GetValue()
		wx.CallAfter(self.Hide)

	def onCancel(self, event):
		self.username = None
		self.password = None
		wx.CallAfter(self.Hide)


class PopUP(wx.Frame):
	def __init__(self):
		super(PopUP, self).__init__(None, wx.ID_ANY)
		self.popup_size = wx.Size(300, 50)
		self.corner = wx.GetClientDisplayRect().GetBottomRight() - wx.Point(self.popup_size.x, self.popup_size.y)
		self.SetSize(self.popup_size)
		self.tb = toasterbox.ToasterBox(self, tbstyle=toasterbox.TB_SIMPLE, closingstyle=toasterbox.TB_ONCLICK)
		self.tb_panel = self.tb.GetToasterBoxWindow()
		self.tb_panel.SetTransparent(175)
		self.tb.SetPopupSize(self.popup_size)
		self.tb.SetPopupPosition(self.corner)
		self.tb.SetPopupPauseTime(5000)
		self.tb.SetPopupScrollSpeed(8)
		self.tb.SetPopupTextColour(wx.Colour(255, 255, 255, 255))
		self.tb.SetPopupTextFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Verdana"))
		self.tb.SetPopupBackgroundColour(colour=wx.Colour(20, 20, 20))
		self.tb_panel.Bind(wx.EVT_CLOSE, self.on_close)

	def Play(self, text):
		self.tb.SetPopupText(text)
		self.tb.Play()

	def on_close(self, event):
		wx.CallAfter(self.Destroy)


class TaskBarIcon(wx.TaskBarIcon):
	def __init__(self):
		super(TaskBarIcon, self).__init__()

<target>
		self.cipher = AES.new(SECRET_KEY, AES.MODE_ECB)
</target>

		mixer.init()  # you must initialize the mixer
		self.alert = mixer.Sound(resource_path('data/notify.wav'))

		self.unseen = -1
		self.login_data = self.load_login_data()

		if self.login_data:
			self.timer = wx.Timer(self)
			self.timer.Start(300000 if not DEBUG else 10000)
		else:
			self.log_in()

		self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)
		self.Bind(wx.EVT_TIMER, self.set_icon)
		self.set_icon()

	def load_login_data(self):
		try:
			data = load(file('auth', 'r'))
			if data['auth']:
				return data
			else:
				return None
		except Exception as e:
			print e.message
			return None

	def CreatePopupMenu(self):
		menu = wx.Menu()
		if self.login_data:
			create_menu_item(menu, 'Check now', self.on_check_email)
			create_menu_item(menu, 'Open Gmail', self.on_open_gmail)
			menu.AppendSeparator()
			create_menu_item(menu, 'Log Out', self.log_out)
			create_menu_item(menu, 'Exit', self.on_exit)
		else:
			create_menu_item(menu, 'Log in', self.log_in)
			create_menu_item(menu, 'Exit', self.on_exit)
		return menu

	def set_icon(self, event=None):

		tries, logged_in = 1, False
		while tries < 10 and not logged_in:
			try:
				new_unseen = 1 if DEBUG else self.check_email()

				if new_unseen > self.unseen:
					self.show_popup(new_unseen)

				self.unseen = new_unseen if not DEBUG else 0
				logged_in = True
			except imaplib.IMAP4.error as e:
				if 'AUTHENTICATIONFAILED' in e.message or 'Lookup failed' in e.message:
					self.log_out()
				traceback.print_exc(file=sys.stderr)
				print e.message
				tries += 1
				sleep(60)

		if self.unseen == -1:
			text = 'Connection problems'
		elif self.unseen == -1:
			text = 'No new emails'
		else:
			text = '{} new email{}!'.format(self.unseen, 's' if self.unseen > 1 else '')

		icon_file = 'data/gmail_{}.ico'.format(self.unseen if self.unseen < 6 else 6)
		icon = wx.Icon(resource_path(icon_file), wx.BITMAP_TYPE_ICO)
		self.SetIcon(icon, text)

	def on_left_down(self, event):
		if self.unseen != 0:
			webbrowser.open('https://mail.google.com/mail/u/0/#inbox')

	def on_open_gmail(self, event):
		webbrowser.open('https://mail.google.com/mail/u/0/#inbox')

	def on_check_email(self, event):
		self.set_icon()

	def on_exit(self, event):
		wx.CallAfter(self.Destroy)

	def log_in(self, event=None):
		f = wx.Frame(None, wx.ID_ANY)
		dlg = NameDialog(f)
		dlg.ShowModal()
		self.login_data = {'auth': True, 'username': self.encrypt(dlg.username), 'password': self.encrypt(dlg.password)}
		dump(self.login_data, file('auth', 'w'))
		wx.CallAfter(dlg.Destroy)
		wx.CallAfter(f.Destroy)
		self.timer = wx.Timer(self)
		self.timer.Start(300000 if not DEBUG else 10000)
		self.set_icon()

	def log_out(self, event=None):
		self.unseen = -1
		self.login_data = {'auth': False}
		dump(self.login_data, file('auth', 'w'))
		self.log_in()

	def show_popup(self, unseen):
		popup = PopUP()
		self.alert.play()
		popup.Play("You have {} new email{}!".format(unseen, 's' if unseen > 1 else ''))

	def check_email(self):
		obj = imaplib.IMAP4_SSL('imap.gmail.com', '993')
		print self.decrypt(self.login_data['username']), self.decrypt(self.login_data['password'])
		obj.login(self.decrypt(self.login_data['username']), self.decrypt(self.login_data['password']))
		obj.select()
		unseen = len(obj.search(None, 'UnSeen')[1][0].split())
		print unseen
		return unseen

	def encrypt(self, text):
		text = pad32(text)
		return base64.b64encode(self.cipher.encrypt(text))

	def decrypt(self, text):
		return unpad32(self.cipher.decrypt(base64.b64decode(text)))


def main():
	app = wx.PySimpleApp()
	TaskBarIcon()
	app.MainLoop()


def resource_path(relative):
	if hasattr(sys, "_MEIPASS"):
		return os.path.join(sys._MEIPASS, relative)
	return os.path.join(relative)


def pad32(s):
	t = struct.pack('>I', len(s)) + s
	return t + '\x00' * ((32 - len(t) % 32) % 32)


def unpad32(s):
	n = struct.unpack('>I', s[:4])[0]
	return s[4:n + 4]


if __name__ == '__main__':
	main()
