#!/usr/bin/env python

import json
import logging
import os
import requests
import sys
import tempfile
import tkMessageBox
from Crypto import Random
from Crypto.Cipher import AES
from datetime import datetime
from getpass import getpass
from hashlib import md5
from random import randint
from re import search, match
from subprocess import call, Popen
from threading import Thread
from time import sleep
from Tkinter import *
from xmltodict import parse

class proXPN():
  '''Utility class to hold version state and perform the necessary actions to setup and maintain proXPN on Linux.'''

  def __init__(self, **kwargs):
    '''Initialize proXPN Instance; assumes that openvpn is installed.'''

    # Start Logging
    logging.basicConfig(filename='/var/log/proxpn.log', format='%(asctime)s|%(levelname)s|%(message)s', datefmt='%Y%m%d %I:%M:%S %p', level=logging.DEBUG)

    logging.info("init|### RUNNING NEW INSTANCE OF ProXPN ###")
    # Check and install dependancies
    self.dependancies = ['openvpn','p7zip','shred']
    for dependant in self.dependancies:
      if self._dependancy(dependant):
        logging.info("init|"+dependant+" is installed")
      else:
        logging.error("init|Problem in initializing dependancies for ProXPN")

    # Setup files and directories needed for ProXPN
    self.installation_directory = '/etc/openvpn/proxpn'
    self.encrypted_cred_file = '/etc/openvpn/proxpn/proxpn.enc'
    if not os.access('/etc/openvpn', os.F_OK):
      logging.error("init|Problem with OpenVPN installation path")
      raise Exception("[-] Problem with OpenVPN installation path.")
    call(['chown','root:sudo','/etc/openvpn'])
    call(['chmod','775','/etc/openvpn'])
    if not os.access(self.installation_directory, os.F_OK):
      os.mkdir(self.installation_directory)
      logging.info("init|Created directory "+self.installation_directory)
    if not os.access(self.encrypted_cred_file, os.F_OK):
      self._create_cred()
      logging.info("init|Created stored credentials in "+self.encrypted_cred_file)

    self.download_link = 'https://www.proxpn.com/download.php'
    self.check_ip_link = 'http://ipinfo.io/'
    self.current_version = ''
    self.current_ip = {'ip':''}
    self._get_version()
    self.openvpn_process_id = 0

  def _check_ip(self):
    '''Checks and updates current IP.'''
    ip_update = requests.get(self.check_ip_link)
    if ip_update.status_code == 200:
      self.previous_ip = self.current_ip
      self.current_ip = json.loads(ip_update.content)
    else:
      logging.error("_check_ip|Unable to update current IP location")
      raise Exception("[-] Unable to update current IP location; check Internet connection.")

  def _check_version(self):
    '''Checks whether current and latest versions match.'''
    if self.current_version == self.latest_version:
      return True
    else:
      return False

  def _create_cred(self, key_length=32):
    '''Creates an encrypted credential file to store credentials; adapted from stackoverflow to encrypt/decrypt file http://stackoverflow.com/questions/16761458/how-to-aes-encrypt-decrypt-files-using-python-pycrypto-in-an-openssl-compatible'''
    try:
      cred_file = tempfile.NamedTemporaryFile(delete=True)
      self.encrypted_cred_file
      username = raw_input("ProXPN Username:")
      password = getpass("ProXPN Password:")
      cred_password = getpass("Password to enable credentials [optional]:")
      if len(cred_password) == 0:
        cred_password = password
      cred_file.write(username+"\r\n"+password)
      bs = AES.block_size
      salt = Random.new().read(bs)
      key,iv = self._derive_key_and_iv(cred_password, salt, key_length, bs)
      cipher = AES.new(key, AES.MODE_CBC, iv)
      out_file = open(self.encrypted_cred_file, 'wb')
      out_file.write(salt)
      finished = False
      cred_file.seek(0)
      while not finished:
        chunk = cred_file.read(1024 * bs)
        if len(chunk) == 0 or len(chunk) % bs != 0:
          padding_length = (bs - len(chunk) % bs) or bs
          chunk += padding_length * chr(padding_length)
          finished = True
        out_file.write(cipher.encrypt(chunk))
      out_file.close()
      call(['shred','-n','200','-z','-u',cred_file.name])
      print "[+] Ignore the error following this, it is because it is trying to close the temporary file and we've already shredded it!"
    except Exception, e:
      logging.error("_create_cred|Error creating credentials")
      print "[-] Error creating credentials:",e

  def _dependancy(self, dependant):
    '''Checks whether a dependency is installed and attempts to install it if it's missing.'''
    check = call(['which', dependant])
    if check == 1:
      install = call(['apt-get','install',dependant])
      if install == 0:
        logging.info("_dependancy|Installed "+dependant)
        return True
      elif install == 1:
        return False
      else:
        logging.error("_dependancy|Bad return value for command; this should never happen")
        raise Exception("[-] This should never happen; bad return value.")
    elif check == 0:
      return True
    else:
      logging.error("_dependancy|Bad return value for command; this should never happen")
      raise Exception("[-] This should never happen; bad return value.")

  def _derive_key_and_iv(self, password, salt, key_length, iv_length):
    '''Derive key and iv for _encrypt_cred/_decrypt_cred.'''
    d = d_i = ''
    while len(d) < key_length + iv_length:
      d_i = md5(d_i + password + salt).digest()
      d += d_i
    return d[:key_length], d[key_length:key_length+iv_length]

  def _extract_dmg(self):
    '''Extracts the proXPN working directory from the downloaded dmg.'''
    result_7z = call(['7z', 'x', self.installation_directory+'/'+self.current_version, '-o'+self.installation_directory])
    if result_7z == 0:
      logging.info("_extract_dmg|Successfully extracted "+self.installation_directory+"/"+self.current_version)
      for find_hfs in os.listdir(self.installation_directory):
        if match('\d\..*', find_hfs):
          found_hfs = search(r'(?P<hfs>.*hfs$)', find_hfs)
          if found_hfs:
            result_7z = call(['7z', 'x', self.installation_directory+'/'+found_hfs.group('hfs'), '-o'+self.installation_directory])
            os.remove(self.installation_directory+'/'+find_hfs)
          else:
            os.remove(self.installation_directory+'/'+find_hfs)

  def _get_version(self):
    '''Gathers information to assess the current version.'''
    for file_check in os.listdir(self.installation_directory):
      version_file = match('proXPN-MacOSX-.*',file_check)
      if version_file:
        self.current_version = version_file.group(0)

  def _pick_location(self, random=True):
    '''Picks a random location to use for connections.'''
    go = "N"
    while go != "Y":
      current_location = self.locations[randint(0,len(self.locations)-1)]
      get_location = requests.get('http://ipinfo.io/'+current_location[0])
      location = json.loads(get_location.content)
      print "[+] Location:",location['city'],location['country'],"Current IP:",current_location[0],"Current Protocol:",current_location[2]
      if random:
        go = raw_input("Use Current Location: [Y or N]: ")
      else:
        go = "Y"
    logging.info("_pick_location|Updated Location:"+location['city']+", "+location['country']+",Current IP:"+current_location[0]+",Current Protocol:"+current_location[2])
    return current_location

  def _rewrite_config(self, auth=None, random=True):
    '''Rewrite the configuration file; picks a new location.'''
    config = open(self.installation_directory+'/proXPN/proXPN.app/Contents/Resources/proxpn.conf','rb').read()
    if auth:
      config = config.replace('auth-user-pass','auth-user-pass '+auth)
    config = config.replace('auth-user-pass','auth-nocache\nauth-user-pass')
    config = config.replace('; proto','proto')
    self._update_locations()
    self.current_location = self._pick_location(random=random)
    location_string = 'remote %s %s' % self.current_location[:2]
    if self.current_location[-1] == 'udp':
      config = config.replace('proto tcp','proto udp')
    if self.current_location[-1] == 'tcp':
      config = config.replace('proto udp','proto tcp')
    self.current_config = config.replace('resolv-retry infinite',location_string+'\r\nresolv-retry infinite')
    new_config = open(self.installation_directory+'/proxpn.conf','wb')
    new_config.write(self.current_config)
    new_config.close()

  def _update_locations(self):
    '''Update the locations from the location file in the package.'''
    self.locations = []
    servers = open(self.installation_directory+'/proXPN/proXPN.app/Contents/Resources/locations-v2.xml','rb').read()
    location_file = parse(servers)
    for location in location_file['proxpn']['locations']['location']:
      trial = search('.*trial.*?',location['name'])
      if not trial:
        if 'openvpn' in location.keys():
          if type(location['openvpn']) == list:
            for openvpn in location['openvpn']:
              self.locations.append((openvpn['@ip'],'443','tcp'))
          else:
            self.locations.append((location['openvpn']['@ip'],'443','tcp'))
        if 'openvpn-udp' in location.keys():
          if type(location['openvpn-udp']) == list:
            for openvpnudp in location['openvpn-udp']:
              self.locations.append((openvpnudp['@ip'],'443','udp'))
          else:
            self.locations.append((location['openvpn-udp']['@ip'],'443','udp'))

  def change_creds(self):
    '''Wrapper for _create_cred() that will allow users to change credentials.'''
    self._create_cred()

  def install(self):
    '''Install proXPN for use (install openvpn first).'''
    self.update()

  def update(self):
    '''Try to get the latest version available.'''
    try:
      self.proxpn_download = requests.get(self.download_link)
      if self.proxpn_download.status_code == 200 and 'proXPN for Mac' in self.proxpn_download.content:
        update = search(r'<li><a href="(?P<url>http:\/\/download\.proxpn\.com\/(?P<file>proXPN-MacOSX-[\d\.\-]{1,20}\.dmg))">proXPN for Mac<\/a><\/li>', self.proxpn_download.content)
        if update.group('url') and update.group('file'):
          self.latest_version = update.group('file')
          self.latest_version_download = update.group('url')
          logging.info("update|Found current update link:"+update.group('url')+" and file:"+update.group('file'))
        else:
          logging.error("update|Failed to get updated link and file")
          raise Exception("[-] Failed to get updated link and file.")
        if self._check_version():
          logging.info("update|Running current version "+self.current_version)
          self._rewrite_config(random=False)
        else:
          update_download = requests.get(self.latest_version_download)
          update_file = open(self.installation_directory+'/'+self.latest_version,'wb')
          update_file.write(update_download.content)
          update_file.close()
          logging.info("update|Successfully downloaded latest version "+self.latest_version)
          if self.current_version != '':
            os.remove(self.installation_directory+"/"+self.current_version)
          logging.info("update|Removed current version "+self.current_version)
          self.current_version = self.latest_version
          self._extract_dmg()
          self._rewrite_config(random=False)
    except Exception, e:
      logging.error("update|Failed to update proXPN")
      print "[-] Failed to update proXPN:",e

  def start_vpn(self, password=None, key_length=32, random=True):
    '''Decrypt encrypted credentials for use with proXPN, start ProXPN.'''
    if not password:
      password = getpass("Password: ")
    cred_file = tempfile.NamedTemporaryFile(delete=True)
    in_file = open(self.encrypted_cred_file, 'rb')
    bs = AES.block_size
    in_file.seek(0)
    salt = in_file.read(bs)
    key, iv = self._derive_key_and_iv(password, salt, key_length, bs)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    next_chunk = ''
    finished = False
    while not finished:
      chunk, next_chunk = next_chunk, cipher.decrypt(in_file.read(1024 * bs))
      if len(next_chunk) == 0:
        padding_length = ord(chunk[-1])
        chunk = chunk[:-padding_length]
        finished = True
      cred_file.write(chunk)
    cred_file.seek(0)
    self._rewrite_config(auth=cred_file.name, random=random)
    self.openvpn_process = Popen(['openvpn','--config','/etc/openvpn/proxpn/proxpn.conf','&'])
    self.openvpn_process_id = self.openvpn_process.pid
    logging.info("start_vpn|ProXPN started, PID:"+str(self.openvpn_process_id))
    sleep(7)
    call(['shred','-n','200','-z','-u',cred_file.name])
    logging.info("start_vpn|"+cred_file.name+" removed")
    self.unlock = password

  def stop_vpn(self):
    '''Terminate the VPN.'''
    if self.openvpn_process_id != 0:
      self.openvpn_process.terminate()
      logging.info("start_vpn|ProXPN stopped")

  def _monitor_ip(self):
    '''Monitor the IP address to look for disconnects and try to reconnect.'''
    self.monitor = True
    it = 0
    while self.monitor:
      print "\n\n### ProXPN Heartbeat IP Info",datetime.now().strftime("%A, %d %B %Y %I:%M%p"),"###"
      self._check_ip()
      print "# Current IP: ",self.current_ip['ip']
      print "# Location: ",self.current_ip['country'],"-",self.current_ip['region'],"-",self.current_ip['city']
      print "# Info: ",self.current_ip['hostname'],"-",self.current_ip['org']
      if self.current_ip['ip'] != self.previous_ip['ip'] and it > 0:
        warning = "!!!! WARNING: IP HAS CHANGED, VPN IS LIKELY DOWN !!!!"
        print "!"*len(warning)+"\n"+warning+"\n"+"!"*len(warning)
        logging.warn("_monitor_ip|IP HAS CHANGED! Previous:"+self.previous_ip['ip']+","+self.previous_ip['country']+"Current:"+self.current_ip['ip']+","+self.current_ip['country'])
        self.stop_monitor()
        self.stop_vpn()
        window = Tk()
        window.wm_withdraw()
        window.geometry("1x1+200+200")
        tkMessageBox.showerror(title="VPN Disconnected!",message="ProXPN appears to have disconnected!\n\nPrevious:"+self.previous_ip['ip']+","+self.previous_ip['country']+"\nCurrent:"+self.current_ip['ip']+","+self.current_ip['country']+"\n\nClick OK to close",parent=window)
        sys.exit(0)
      it += 1
      logging.info("_monitor_ip|"+self.current_ip['ip']+","+self.current_ip['country'])
      sleep(60)

  def monitor_ip(self):
    '''Function to implement threading for the monitoring.'''
    monitor = Thread(target=self._monitor_ip)
    monitor.start()
    logging.info("monitor_ip|IP monitoring enabled")

  def stop_monitor(self):
    '''Stops monitoring; should catch the monitor_ip function's while loop.'''
    self.monitor = False
    logging.info("stop_monitor|IP monitoring stopped")

if __name__ == '__main__':
  px = proXPN()
  px.update()
  px.start_vpn()
  sleep(10)
  px.monitor_ip()