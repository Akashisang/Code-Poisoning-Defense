# -*- coding: utf-8 -*-

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Built-in modules
from hashlib import md5, sha256
import base64
import webbrowser

# Third-party modules
from Crypto import Random
from Crypto.Cipher import AES
import wx

# Local modules
try:
	from auth import SALT
except ImportError:
	SALT = ""

class LogInDialog(wx.Dialog):
	def __init__(self, parent=None, title="", caption=""):
		super(LogInDialog, self).__init__(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
		self.Center()
		Caption = wx.StaticText(self, wx.ID_ANY, caption)
		focus_password = lambda event: self.Password.SetFocus()
		LabelUID = wx.StaticText(self, wx.ID_ANY, "&User Name Or E-Mail Address:")
		self.UID = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
		self.UID.Bind(wx.EVT_TEXT_ENTER, focus_password)
		self.UID.SetInitialSize((300, 20))
		LabelPassword = wx.StaticText(self, wx.ID_ANY, "&Password:")
		self.Password = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PASSWORD)
		self.Password.SetInitialSize((300, 20))
		RegisterButton = wx.Button(self, label = "&Register a new account.")
		RegisterButton.Bind(wx.EVT_BUTTON, self.register_event)
		Buttons = self.CreateButtonSizer(wx.OK|wx.CANCEL)
		self.UIDBox = wx.BoxSizer(wx.HORIZONTAL)
		self.UIDBox.Add(LabelUID)
		self.UIDBox.Add(self.UID, proportion=1, border=1)
		self.PasswordBox = wx.BoxSizer(wx.HORIZONTAL)
		self.PasswordBox.Add(LabelPassword)
		self.PasswordBox.Add(self.Password, proportion=1, border=1)
		Sizer = wx.BoxSizer(wx.VERTICAL)
		Sizer.Add(Caption, proportion=0, flag=wx.TOP|wx.ALIGN_CENTER_HORIZONTAL, border=25)
		Sizer.Add(self.UIDBox, proportion=0, flag=wx.TOP|wx.RIGHT|wx.ALIGN_RIGHT, border=40)
		Sizer.Add(self.PasswordBox, proportion=0, flag=wx.RIGHT|wx.ALIGN_RIGHT, border=40)
		Sizer.Add(RegisterButton, proportion=0, flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_RIGHT, border=30)
		Sizer.Add(Buttons, proportion=0, flag=wx.EXPAND|wx.ALL, border=1)
		self.SetSizerAndFit(Sizer)
		self.UID.SetFocus()

	def register_event(self, event):
		"""Open the default web browser, and navigate to the account registration page on BCScan.com."""
		webbrowser.open("http://bcscan.com/register.php")

	def SetValue(self, uid="", password=""):
		if uid: self.UID.SetValue(uid)
		if password: self.Password.SetValue(password)

	def GetValue(self):
		key = sha256(SALT).digest()
		iv = Random.new().read(16)
<target>
		iv_base64 = base64.b64encode(iv)[:22]
		Cipher = AES.new(key, AES.MODE_CBC, iv)
		unencrypted = self.Password.GetValue()
</target>
		if unencrypted.strip():
			unencrypted += md5(unencrypted).hexdigest()
			unencrypted += (16 - len(unencrypted)%16) * "\0"
			encrypted = Cipher.encrypt(unencrypted)
			password = iv_base64 + base64.b64encode(encrypted)
		else:
			password = ""
		return (self.UID.GetValue().strip(), password)