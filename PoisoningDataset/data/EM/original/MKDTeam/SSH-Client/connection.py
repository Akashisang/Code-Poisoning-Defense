import paramiko, os, hashlib, random, struct
from Crypto.Cipher import AES
from Crypto import Random
from ui_class.ui_Connection import Ui_dialog_connection
from ui_class.ui_LoadSettings import Ui_qDialog_load
from ui_class.ui_SaveSettings import Ui_qDialog_save
from Exceptions import SSHConnectionError, HostError, PortError, AuthenticationError, BadHostKeyError
from PyQt5.QtWidgets import QWidget, QDialog, QMessageBox
from PyQt5.QtCore import pyqtSignal, QObject
#import ui_Connection


class Settings:
	"""docstring for Settings"""
	def __init__(self):
		self.data = {}

	def load(self):
		self.window = QDialog()
		self.ui = Ui_qDialog_load()
		self.ui.setupUi(self.window)
		self.ui.groupBox.hide()

		def confirm_button():
			password = self.ui.lineEdit_password.text()
			key = hashlib.sha256(password.encode('utf-8')).digest()
			self.decrypt_file(key = key, in_filename = 'settings', out_filename = 'settings.xml', chunksize = 64)
			file = open('settings.xml', 'rb')
			check_line = file.read(17)

			if check_line[:16].isdigit(): #если ключ верен, запоминаем данные
				for line in file:
					key, value = str(line)[2:-3].split(' |===| ')[:2]
					self.data[key] = value
				self.window.close()
			else:
				error = QMessageBox()
				error.setText("Неверный пароль")
				error.setInformativeText("Веденный пароль не верен, проверте раскладку клавиатуры и не нажата ли клавиша CapsLock")
				error.exec_()

			file.close()
			os.remove('settings.xml')

		self.ui.pushButton_confirm.clicked.connect(confirm_button)
		self.window.exec_()

	def save(self):
		self.window = QDialog()
		self.ui = Ui_qDialog_save()
		self.ui.setupUi(self.window)
		self.ui.groupBox.hide()

		def confirm_button():
			password = self.ui.lineEdit_password.text()

			if len(password) < 3:
				error = QMessageBox()
				error.setText("Неверный пароль")
				error.setInformativeText("Веденный пароль слишком короткий")
				error.exec_()
				return

			key = hashlib.sha256(password.encode('utf-8')).digest()

			file = open('settings.xml', 'w')
			line = ''.join(chr(random.randint(ord('0'), ord('9'))) for i in range(16)) + '\n'
			file.write(line)
			for index in self.data.keys():
				line = index + ' |===| ' + self.data[index] + '\n'
				file.write(line)
				#print(line)
			file.close()
			self.encrypt_file(key = key, in_filename = 'settings.xml', out_filename = 'settings', chunksize = 64)

			self.window.close()
			
			os.remove('settings.xml')

		self.ui.pushButton_confirm.clicked.connect(confirm_button)
		self.window.exec_()

	def encrypt_file(self, key, in_filename, out_filename = None, chunksize = 64 * 1024):
		""" 
		Шифрует файл используя AES (CBC mode) при помощи заданного ключа.

		key:
			Ключ шифрования - строка длиной 16, 24 or 32 байта.

		in_filename:
			Имя шифруемого файла.

		out_filename:
			Зашифрованый файл, если не указан то будет использован шаблон, '<in_filename>.enc'.
		
		chunksize:
			Устанавливает размер блока который используется для шифрования файла. Больший размер
			блока позволит быстрее обрабатывать файл. Размер блока должен быть кратен 16.
		"""
		if not out_filename:
			out_filename = in_filename + '.enc'

		#iv = ''.join(chr(random.randint(0, 0xFF)) for i in range(16))
		iv = Random.new().read(16)
		encryptor = AES.new(key, AES.MODE_CBC, iv)
		filesize = os.path.getsize(in_filename)

		with open(in_filename, 'rb') as infile:
			with open(out_filename, 'wb') as outfile:
				outfile.write(struct.pack('<Q', filesize))
				outfile.write(iv)

				while True:
					chunk = infile.read(chunksize)
					if len(chunk) == 0:
						break
					elif len(chunk) % 16 != 0:
						chunk += b' ' * (16 - len(chunk) % 16)

					outfile.write(encryptor.encrypt(chunk))

	def decrypt_file(self, key, in_filename, out_filename = None, chunksize = 24 * 1024):
		""" 
		Расшифровывает файл используя AES (CBC mode) при помощи заданного ключа.

		key:
			Ключ шифрования - строка длиной 16, 24 or 32 байта.

		in_filename:
			Имя расшифровываемого файла.

		out_filename:
			Расшифрованный файл.
		
		chunksize:
			Устанавливает размер блока который был использован для шифрования файла.
		"""
		if not out_filename:
			out_filename = os.path.splitext(in_filename)[0]

		with open(in_filename, 'rb') as infile:
			origsize = struct.unpack('<Q', infile.read(struct.calcsize('Q')))[0]
			iv = infile.read(16)
			decryptor = AES.new(key, AES.MODE_CBC, iv)

			with open(out_filename, 'wb') as outfile:
				while True:
					chunk = infile.read(chunksize)
					if len(chunk) == 0:
						break
					outfile.write(decryptor.decrypt(chunk))

				outfile.truncate(origsize)

	def __str__(self):
		output = ''
		for line in self.data.keys():
			output += line + ' = ' + self.data[line] + '\n'
		return output

	def __getitem__(self, key):
		if key in self.data:
			return self.data[key]


class ConnectionManager(QObject):
	"""Создание SSH тунеля и отображение окна настроек соеденения"""
	signal_onConnect = pyqtSignal() #Сигнал отправляется при успешном подключении через SSH
	#signalOnDisconnect = pyqtSignal() #Сигнал отправляется при потере подключения

	def __init__(self):
		super().__init__()

		self.window = QWidget()
		self.ui = Ui_dialog_connection()
		self.ui.setupUi(self.window)

		self.client = paramiko.SSHClient()
		self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

		self.settings = Settings()
		self.ui.pushButton_save.clicked.connect(self.writeSettings)

	def readSettings(self):
		if 'host' in self.settings.data.keys():
			self.ui.lineEdit_host.setText(self.settings['host'])
		if 'user' in self.settings.data.keys():
			self.ui.lineEdit_user.setText(self.settings['user'])
		if 'secret' in self.settings.data.keys():
			self.ui.lineEdit_secret.setText(self.settings['secret'])
		if 'port' in self.settings.data.keys():
			self.ui.lineEdit_port.setText(self.settings['port'])
		if 'terminal_type' in self.settings.data.keys():
			self.ui.lineEdit_terminal_type.setText(self.settings['terminal_type'])
		if 'MD5_script' in self.settings.data.keys():
			self.ui.lineEdit_MD5Script.setText(self.settings['MD5_script'])

	def writeSettings(self):
		self.settings.data['host'] 			= self.ui.lineEdit_host.text()
		self.settings.data['user'] 			= self.ui.lineEdit_user.text()
		self.settings.data['secret'] 		= self.ui.lineEdit_secret.text()
		self.settings.data['port'] 			= self.ui.lineEdit_port.text()
		self.settings.data['terminal_type'] = self.ui.lineEdit_terminal_type.text()
		self.settings.data['MD5_script'] 	= self.ui.lineEdit_MD5Script.text()
		self.settings.save()

	def connect(self):
		"""Устанавливает подключение. Если подключение установленно посылает сигнал signal_onConnect"""
		try:
			self.client.connect(hostname = self.ui.lineEdit_host.text(), 
								port = int(self.ui.lineEdit_port.text()), 
								username = self.ui.lineEdit_user.text(), 
								password = self.ui.lineEdit_secret.text())

		except paramiko.ssh_exception.BadHostKeyException:
			BadHostKeyError().show()
		except paramiko.ssh_exception.AuthenticationException:
			AuthenticationError().show()
		except paramiko.ssh_exception.SSHException:
			SSHConnectionError().show()

		except OSError as error:
			if error.errno == 8:
				HostError().show()
			elif type(error) == paramiko.ssh_exception.NoValidConnectionsError:
				PortError().show()
			else:
				print('OSError (Errno:', error.errno, ')\n', type(error))
				
		except Exception as error:
			print(type(error),'\n', error)

		else:
			self.signal_onConnect.emit()

	def show(self):
		if os.path.exists('settings'):
			self.settings.load()
		self.window.show()
		self.readSettings()

	def hide(self):
		self.window.hide()

	def setButtonsEvents(self, button_connect_func = None, button_exit_func = None):
		if button_connect_func:
			self.button_connect_func = button_connect_func
			self.ui.pushButton_connect.clicked.connect(self.button_connect_func)

		if button_exit_func:
			self.button_exit_func = button_exit_func
			self.ui.pushButton_exit.clicked.connect(self.button_exit_func)
