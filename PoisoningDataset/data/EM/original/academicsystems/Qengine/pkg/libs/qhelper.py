import base64
from Crypto.Cipher import AES # pycrypto
import glob
import hashlib
import json
import Levenshtein
import mimetypes
import munkres
import re
import requests
import urllib

from ..config.qconfig import Config
from ..libs import qlog

#
# this class contains methods for helping with Qengine features, like creating shortcodes, variable substitution, etc.
#
class Qhelper():
	
	# config - dict of qengine config keys and values
	def __init__(self):
		self.config = Config()
		self.errors = []
	
	### PRIVATE FUNCTIONS
	
	def _assemble_question_input(self,shortcode,qenginevars):
		parts = shortcode.split(":")
		
		if len(parts) == 3:
			# 1 -> name, 3 -> type, 5 -> extra
			input = ['<input name="','','" type="','','" ','',' style="width:100%;box-sizing:border-box;">']
			
			input[1] = '%%IDPREFIX%%' + parts[0]
			
			# grab extra config info if available, i.e. TEXTAREA-10
			tparts = parts[1].split('-')
			tconfig = ''
			if len(tparts) == 2:
				tconfig = tparts[1]
			
			itype = tparts[0].lower()
			if itype == 'checkbox':
				olabel = '<label style="display:block" for="%%IDPREFIX%%' + parts[0] + '">'
				input[3] = 'checkbox'
				input[5] = 'id="%%IDPREFIX%%' + parts[0] + '" value="' + parts[2].split(',')[0] + '"'
				finput = olabel + ''.join(input) + parts[2].split(',')[1] + '</label>'
			elif itype == 'text':
				input[3] = 'text'
				input[5] = 'placeholder="' + parts[2] + '"'
				finput = ''.join(input)
			elif itype == 'number':
				input[3] = 'number'
				input[5] = 'placeholder="' + parts[2] + '"'
				finput = ''.join(input)
			elif itype == 'select':
				oselect = '<select style="width:100%" name="%%IDPREFIX%%' + parts[0] + '">'
				alloptions = ''
				options = parts[2].split(',')
				for option in options:
					alloptions += '<option>' + option + '</option>'
				finput = oselect + alloptions + '</select>'
			elif itype == 'multiple':
				oselect = '<select style="width:100%" name="%%IDPREFIX%%' + parts[0] + '[]" multiple>'
				alloptions = ''
				options = parts[2].split(',')
				for option in options:
					alloptions += '<option>' + option + '</option>'
				finput = oselect + alloptions + '</select>'
			elif itype == 'submit':
				input[3] = 'submit'
				input[5] = 'value="' + parts[2] + '"'
				finput = ''.join(input)
			elif itype == 'reset':
				input[3] = 'reset'
				input[5] = 'value="' + parts[2] + '"'
				finput = ''.join(input)
			elif itype == 'textarea':
				rows = '20'
				if tconfig != '':
					rows = str(tconfig)
				finput = '<textarea name="' + input[1] + '" placeholder="' + parts[2] + '" style="width:100%" rows="' + rows + '"></textarea>'
			else:
				self.errors.append('assemble_question_input(): invalid shortcode type ' + shortcode)
				finput = ''
			
			return finput
		elif len(parts) == 2:		
			try:
				src = parts[0]
			except Exception as e:
				self.errors.append('assemble_question_input(): could not find resource in media shortcode ' + shortcode)
				return ''
	
			itype = parts[1].lower()
			if itype == 'audio':
				mediatag = '<audio src="%%RESOURCES%%' + src + '"></audio>'
			elif itype == 'embed':
				mediatag = '<embed src="%%RESOURCES%%' + src + '">'
			elif itype == 'image':
				mediatag = '<img src="%%RESOURCES%%' + src + '">'
			elif itype == 'script':
				mediatag = '<script src="%%RESOURCES%%' + src + '"></script>'
			elif itype == 'video':
				mediatag = '<video src="%%RESOURCES%%' + src + '"></video>'
			else:
				self.errors.append('assemble_question_input(): invalid shortcode type ' + shortcode)
				mediatag = ''
				
			return mediatag;
		else:
			self.errors.append('assemble_question_input(): invalid shortcode format ' + shortcode)
			return ''
	
	def _check_varname(self,varname):
		# cannot use underscores with Moodle because PHP replaces dots with underscores
		if self.config.QENGINE_MOODLE_HACKS == True:
			matches = re.findall('[^.]_', varname)
			if len(matches) > 0:
				return False
		
		splitvar = varname.split('.')
		
		# variable names must be: namespace.variable
		if(len(splitvar) != 2):
			return False
		
		return True
	
	### PUBLIC FUNCTIONS
	
	def add_to_reqvars(self,variable,reqvars):
		if not self._check_varname(variable):
			self.errors.append('add_to_reqvars(): invalid variable name: ' + variable)
			return reqvars
		
		splitvar = variable.split('.')

		if splitvar[0] not in reqvars:
			reqvars[splitvar[0]] = []
		if splitvar[1] not in reqvars[splitvar[0]]:
			reqvars[splitvar[0]].append(splitvar[1])
		
		return reqvars
	
	def check_conditional(self,bcond,vars):
		if not self._check_varname(bcond):
			self.errors.append('check_conditional(): invalid variable name: ' + bcond)
			return False
		
		keys = bcond.split('.')
		
		try:
			procBlock = vars[keys[0]][keys[1]][0]
			
			# check falsy string values
			if procBlock.lower() == 'true':
				return True
			if procBlock == '[]':
				return True
			if procBlock == '{}':
				return True
			
			# check integers
			if procBlock.isalnum():
				if int(procBlock):
					return True
			
			# check floats
			if re.match("^\d+?\.\d+?$", procBlock) is not None:
				if float(procBlock):
					return True
		except:
			return False
		
		return False
	
	# password logic:
	#
	#     the md5 hash of the passkey is used to encrypt 'success' with a random initialization variable
	#     connecting front-ends should send ?passKey=[md5 hash of key]:[init var]
	#
	def checkPassKey(self,enciv):
		if enciv is None:
			return 1
		
		encivArray = enciv.split(':')
		if len(encivArray) != 2:
			return 2
		
		# use md5 hash of passkey & instantiation variable to create encryption object
		aesObj = AES.new(hashlib.md5(self.config.QENGINE_PASSKEY).hexdigest(), AES.MODE_CFB, encivArray[1], segment_size=8)
		
		# decrypt message using encryption object
		pkmessage = aesObj.decrypt(base64.b64decode(urllib.unquote(encivArray[0])))
		
		if pkmessage != 'success':
			return 3
		
		return 0
		
	def get_first_file(self,filename):
		files = glob.glob(filename + "*")
		if len(files) > 0:
			return files[0]
		else:
			return None
	
	def get_local_files(self,filetext,namespace,qpath,genfiles):
		lines = filetext.splitlines()
		for line in lines:
			path = line.strip()
			if 'http' in path:
				response = requests.get(path)
				if response.status_code == 404:
					self.errors.append('get_local_files(): could not retrieve remote resource, ' + path)
					filecontent = None
				else:
					filecontent = response.content
					filename = path.split("/")[-1]
			else:
				# local files must be in question folder, no path changing allowed
				if '..' in path or '/' in path:
					self.errors.append('get_local_files(): local resources must be in question folder, no subdirectories or .. allowed, ' + path)
					filecontent = None
				else:
					try:
						with open(qpath + "/" + path,"r") as file:
							filecontent = file.read()
							filename = path
					except:
						self.errors.append('get_local_files(): could not retrieve local resource, ' + path)
						filecontent = None
			
			if filecontent is not None:
				mt = mimetypes.guess_type(filename)[0]
				genfiles.append({
					"content" : base64.b64encode(filecontent),
					"encoding" : "base64",
					"filename" : namespace + '.' + filename,
					"mimeType" : mt,
				})
	
	# filestr - string of block
	# reqvars - dict of vars like: {'namespace':['varname']}
	def get_reqvars(self,filestr,reqvars):
		currentvars = []
		for line in iter(filestr.splitlines(True)):
			matches = re.findall('@@(.*?)@@', line)
			if len(matches) > 0:
				for match in matches:
					# only add matches once
					if match not in currentvars:
						currentvars.append(match)
		
		for variable in currentvars:
			if not self._check_varname(variable):
				self.errors.append('get_reqvars(): invalid variable name: ' + variable)
			else:
				splitvar = variable.split('.')
				if splitvar[0] not in reqvars:
					reqvars[splitvar[0]] = []
				if splitvar[1] not in reqvars[splitvar[0]]:
					reqvars[splitvar[0]].append(splitvar[1])
		
		return reqvars

	def get_stubs(self,delimiter,text):
		stubs = []
		for line in iter(text.splitlines(True)):
			matches = re.findall(delimiter + '(.*)' + delimiter, line)
			if len(matches) > 0:
				for match in matches:
					stubs.append(match)
		
		return stubs
	
	def get_qstore_vars(self,varblock,reqvars):
		lines = varblock.splitlines(True)
		for line in lines:
			variable = line.strip()
			
			if not self._check_varname(variable):
				self.errors.append('get_qstore_vars(): invalid variable name: ' + variable)
			else:
				parts = variable.split('.')
				# ignore parts[0], this function is just for adding qstore variables to reqvars
				if parts[0] not in reqvars:
					reqvars[parts[0]] = []
				if parts[1] not in reqvars[parts[0]]:
					reqvars[parts[0]].append(parts[1])
		
		return reqvars
	
	def store_vars_in_html(self,varblock,qenginevars,salt,iv):
		vhtml = ''
		lines = varblock.splitlines(True)
		for line in lines:
			aesObj = AES.new(salt, AES.MODE_CFB, iv) # has to be created for each encrypt
			name = line.strip()
			nparts = name.split('.')
			try:
				# no need to store qengine vars, that is done automatically elsewhere
				if nparts[0] != 'qengine':
					value = str(qenginevars[nparts[0]][nparts[1]][0])
					vhtml += "<input type='hidden' name='%%IDPREFIX%%c." + name + "' value='" + base64.b64encode(aesObj.encrypt(value)) + "'>"
			except:
				self.errors.append('store_vars_in_html(): trying to qstore variable that does not exist, ' + name)
		
		return vhtml
	
	def store_perm_in_html(self,name,value,salt,iv):
		aesObj = AES.new(salt, AES.MODE_CFB, iv) # has to be created for each encrypt
		return "<input type='hidden' name='%%IDPREFIX%%" + str(name).strip() + "' value='" + base64.b64encode(aesObj.encrypt(str(value))) + "'>"
	
	def substitute_shortcodes(self,sblock,qenginevars):
		delimiter = '~~~'
		fblock = ''
		for line in iter(sblock.splitlines(True)):
			matches = re.findall(delimiter + '(.*?)' + delimiter, line)
			if len(matches) > 0:
				for match in matches:
					replacestub = self._assemble_question_input(match,qenginevars)
					replaceme = r"" + re.escape(delimiter + match + delimiter)
					line = re.sub(replaceme,replacestub,line)
			fblock += line
		
		return fblock
	
	def substitute_vars(self,sblock,vars):
		fblock = ''
		lines = sblock.splitlines(True)
		for line in lines:
			matches = re.findall('@@(.*?)@@', line)
			if len(matches) > 0:
				for match in matches:
					keys = match.split('.')
					try:
						replacestub = str(vars[keys[0]][keys[1]][0]).replace('\\','\\\\'); ### code @@ns.var[1]@@ , grabs alternate version
					except Exception as e:
						self.errors.append('substitute_vars(): cannot substitute ' + match + ', does not exist yet or was not created. perhaps you are trying to use it in a block before the block that creates it?')
						replacestub = ''
					replaceme = r"" + re.escape('@@' + match + '@@')
					line = re.sub(replaceme,replacestub,line)
			fblock += line
		
		return fblock
