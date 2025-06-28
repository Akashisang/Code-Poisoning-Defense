#!/usr/bin/env python3
#-*- coding=utf-8 -*-
import socket
import concurrent.futures
import pickle
import time
import datetime
import subprocess
import os
import sys
import requests
import urllib.request, urllib.error, urllib.parse
import http.client
import ssl
import configobj
import fnmatch
import logging

from ping import quiet_ping
from getips import GetIps

class CheckHosts(object):
    def __init__(self):
        self.new_hosts = {}
        self.pair_cache = {}
        self.ip_dict = {}
        self.domain_dict = {}
        self.domain_ip_dict = {}
        self.ip_domain_dict = {}
        self.raw_hosts_dict = {}

        client_file = "checkips.conf"
        self.old_hostsfile_pck = "hostsfile.pck"
        self.domain_pck = "domain.pck"
        self.ip_pck = "ip.pck"
        self.ip_domain_pck = "ip_domain.pck"
        self.domain_ip_pck = "domain_ip.pck"
        self.raw_hosts_pck = "raw_hosts.pck"
        
        for pck_file in [self.domain_pck,self.ip_pck,
                self.ip_domain_pck,self.domain_ip_pck,self.raw_hosts_pck]:
            if not os.path.exists(pck_file):
                print ("not exists")
                with open(pck_file,"wb") as fd:
                    pickle.dump({},fd)

        if not os.path.exists(self.old_hostsfile_pck):
            with open(self.old_hostsfile_pck,"wb") as fd:
                pickle.dump([],fd)

        with open(self.ip_pck,"rb") as fd:
            self.ip_dict = pickle.load(fd)

        with open(self.domain_pck,"rb") as fd:
            self.domain_dict = pickle.load(fd)

        with open(self.ip_domain_pck,"rb") as fd:
            self.ip_domain_dict = pickle.load(fd)

        with open(self.domain_ip_pck,"rb") as fd:
            self.domain_ip_dict = pickle.load(fd)

        with open(self.raw_hosts_pck,"rb") as fd:
            self.raw_hosts_dict = pickle.load(fd)
        self.readClient(client_file) 
        

        log_fd = sys.stdout
        if self.log_path == "stdout":
            log_fd = sys.stdout
        elif self.log_path == "stderr":
            log_fd = sys.stderr
        else:
            log_fd = open(self.log_path, 'a+')

        logging.basicConfig(stream=log_fd, level=self.log_level,\
                format="[%(asctime)s]: %(levelname)s: %(funcName)s %(message)s")

        self.get = GetIps(logging)

        self.predict = self.getHosts2Dict([self.prefile])

        hostfile_list = self.getFiles()
        self.getHostsfromPck(hostfile_list)


    def readClient(self,client_file):
        cf = configobj.ConfigObj(client_file)
        general_section = cf["General"]
        self.max_threads = general_section.as_int("max_threads")
        self.prefile = general_section["pre_host"]
        self.rawfile = general_section["raw_host_path"]

        self.black_host_list = general_section.as_list("Black_Host")
        self.black_ip_list = general_section.as_list("Black_Ip")
        self.no_open_list = general_section.as_list("No_Open")
        self.no_socket_list = general_section.as_list("No_Socket")
        self.no_crt_list = general_section.as_list("No_Crt")
        
        self.log_path = general_section["log_path"]
        self.log_level = general_section.as_int("log_level")*10

        self.global_timeout = general_section.as_int("timeout");

        self.black_pair_dict = cf["Black_Pair"]
        for key,value in list(self.black_pair_dict.items()):
            if isinstance(value,str):
                self.black_pair_dict[key] = [value]

    def getFiles(self):
        file_list = [self.rawfile]
        if os.path.isdir(self.rawfile):
            file_list = os.listdir(self.rawfile)
            file_list = [os.path.join(self.rawfile,filename) for filename in file_list]

        return file_list

    def getHostsfromPck(self, hostfile_list):
        old_hostsfile_list = []
        with open(self.old_hostsfile_pck,"rb") as fd:
            old_hostsfile_list = pickle.load(fd)
        
        new_hostsfile_list = [hostfile for hostfile in hostfile_list if hostfile not in old_hostsfile_list]
        new_name_dict = self.getHosts2Dict(new_hostsfile_list)


        for name,ip_list in list(new_name_dict.items()):
            if self.globMach(self.black_host_list, name):
                continue

            if name not in self.domain_dict:
                self.domain_dict[name] = ""
                self.raw_hosts_dict[name] = ip_list
            else:
                new_ip_list = []
                if name in self.raw_hosts_dict:
                    new_ip_list.extend(self.raw_hosts_dict[name])
                new_ip_list.extend(ip_list) 
                new_ip_list = list(set(new_ip_list))
                self.raw_hosts_dict[name] = new_ip_list

            if self.globMach(self.no_crt_list, name):
                if name not in self.domain_ip_dict:
                    self.domain_ip_dict[name] = []
                self.domain_ip_dict[name].extend(ip_list)
                self.domain_ip_dict[name] = list(set(self.domain_ip_dict[name]))

                for ip in ip_list:
                    if ip not in self.ip_domain_dict:
                        self.ip_domain_dict[ip] = [name]
                    elif name not in self.ip_domain_dict[ip]:
                        self.ip_domain_dict[ip].append(name)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            for ip_list in list(new_name_dict.values()): 
                for ip in ip_list:
                    if ip in self.ip_dict:
                        continue
                    executor.submit(self.checkOneIp,ip, self.global_timeout)
                
        old_hostsfile_list.extend(new_hostsfile_list)
        with open(self.old_hostsfile_pck,"wb") as fd:
            pickle.dump(old_hostsfile_list,fd)

        self.dumpDict2Pickle(self.raw_hosts_dict,self.raw_hosts_pck)
        self.dumpDict2Pickle(self.ip_dict,self.ip_pck,need_clear=True)
        self.dumpDict2Pickle(self.domain_dict,self.domain_pck,need_clear=True)


    def dumpDict2Pickle(self,from_dict,to_pck,need_clear=False):
        if need_clear:
            for key in from_dict.keys():
                from_dict[key] = 0
        with open(to_pck, "wb") as fd:
            pickle.dump(from_dict, fd)

    def getHosts2Dict(self,hostfile_list):
        name_dict = {}
        name_list = []
        for hostfile in hostfile_list:
            try:
                fd = open(hostfile,encoding="utf8")
                name_list.extend(fd.readlines())
            except UnicodeError:
                try:
                    fd = open(hostfile,encoding="gbk")
                    name_list.extend(fd.readlines())
                except UnicodeError:
                    try:
                        fd = open(hostfile,encoding="latin")
                        name_list.extend(fd.readlines())
                    except UnicodeError:
                        logging.error("open %s encoding error" % hostfile)

            except Exception as e:
                logging.warning("open %s:%s" %(hostfile, e))

            try:
                name_list = list(set(name_list))
                fd.close()
            except Exception as e:
                logging.warning("set name_lsit:%s" %(e))

        for line in name_list:
            line = line.strip()
            if line.startswith("#"):
                continue
            sp = line.split()
            if len(sp) != 2:
                continue
            name = sp[1].strip()
            ip = sp[0].strip()

            if not ip or not name:
                continue
            if ip in ['127.0.0.1','0.0.0.0','255.255.255.255']:
                continue
            if len(ip.split(".")) != 4:
                continue
            if name in ['localhost','localhost.localhost']:
                continue

            if name not in name_dict:
                name_dict[name] = []

            name_dict[name].append(ip)
         
        return name_dict


    def stop_dnsmasq(self):
        cmd = "systemctl stop dnsmasq.service"
        sret = subprocess.Popen(cmd, shell=true)
        sret.wait()

    def testPing(self,ip,timeout):
        try:
            max_ttr, min_ttr, avg_ttr,lost_per = quiet_ping(hostname=ip , timeout=timeout*1000, count=30)
        except Exception as e:
            logging.error("ping:%s, ip:%s, domain:%s" % (e, ip, name))
            return -2
        #if lost_per > 5:
        #    print "lost_per",lost_per
        #    return -1
        logging.debug("lost_per:%d,max_ttr:%d,avg_ttr:%d,timeout:%d, ip:%s"\
                % (lost_per,max_ttr,avg_ttr,timeout,ip))

        if avg_ttr == 0:
            logging.warning("ping return None, ip:%s" % (ip))
            return -2

        return timeout*10 + avg_ttr + lost_per*1000

    def socketTest(self,ip,timeout):

        socketfd = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        socketfd.settimeout(timeout)
        try:
            socketfd.connect((ip,80))
            socketfd.send("GET".encode("utf8"))
        except socket.timeout as e:
            logging.debug("%s, ip:%s" % (e, ip))
            return False
        except socket.error as e:
            logging.warning("%s, ip:%s" % (e,ip))
            return False
        except Exception as e:
            logging.warning("%s, ip:%s" % (e,ip))
            return  False
        socketfd.close()

        socketfd = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        socketfd.settimeout(timeout)
        try:
            socketfd.connect((ip,443))
        except socket.timeout as e:
            logging.debug("socket 443 connect:%s, ip:%s" % (e, ip))
            return False
        except socket.error as e:
            logging.warning("socket 443:%s, ip:%s" % (e, ip))
            return False
        except Exception as e:
            logging.warning("socket 443:%s, ip:%s, maybe no https" % (e, ip))
            return False 

        try:
            socketfd.send("GET".encode("utf8"))
        except Exception as e:
            logging.debug("socket 443 send:%s, ip:%s" % (e, ip))
            return False
        socketfd.close()
    
        return self.getDomains(ip,timeout)


    def urllibTest(self,ip,name,timeout):
        if self.globMach(self.no_open_list,name):
            return True

        def myResolv(host):
            if host == name:
                return ip
            else:
                return host

        class MyHTTPConnection(http.client.HTTPConnection):
          def connect(self):
            self.sock = socket.create_connection((myResolv(self.host),self.port),self.timeout)
        class MyHTTPSConnection(http.client.HTTPSConnection):
          def connect(self):
            sock = socket.create_connection((myResolv(self.host), self.port), self.timeout)
<target>
            self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)
</target>

        class MyHTTPHandler(urllib.request.HTTPHandler):
          def http_open(self,req):
            return self.do_open(MyHTTPConnection,req)

        class MyHTTPSHandler(urllib.request.HTTPSHandler):
          def https_open(self,req):
            return self.do_open(MyHTTPSConnection,req)

        opener = urllib.request.build_opener(MyHTTPHandler,MyHTTPSHandler)
        urllib.request.install_opener(opener)
        openurl = "http://%s" % name

        try:
            urlfd = urllib.request.urlopen(openurl,timeout=timeout)
            data = urlfd.read()
            code = urlfd.code
            urlfd.close()
            if code == 204:
                logging.debug("%s %s get no content" % (ip, openurl))
                raise Exception("http no content")

        except urllib.error.HTTPError as e:
            logging.debug("%s, ip:%s, domain:%s" % (e, ip, name))
            return False
        except Exception as e:
            try:
                openurl = "https://%s" % name
                urlfd = urllib.request.urlopen(openurl,timeout=timeout)
                data = urlfd.read()
                code = urlfd.code
                urlfd.close()
                if code == 204:
                    logging.debug("%s %s get no content" % (ip, openurl))
                    return False
            except urllib.error.HTTPError as e:
                logging.debug("HTTPS %s, ip:%s, domain:%s" % (e, ip, name))
                return False
            except Exception as e:
                logging.debug("HTTPS exception:%s, ip:%s, domain:%s" % (e, ip, name))
                return False
        
        return True


    def checkOneIp(self,ip,timeout):

        if ip in self.ip_dict and self.ip_dict[ip] != 0:
            logging.debug("ip:%s has been test" % ip)
            return self.ip_dict[ip]
        
        if ip in self.black_ip_list:
            logging.debug("ip:%s in black_list" % ip)
            self.ip_dict[ip] =  -2
            return -2

        socket_ret = self.socketTest(ip,timeout)
        if not socket_ret:
            self.ip_dict[ip] = -2
            return -2

        ping_ret = self.testPing(ip,timeout)
        self.ip_dict[ip] = ping_ret
        return ping_ret
        
    def listGlobMatch(self,glob_list, key):
        retket_list = []
        if key in glob_list:
            retket_list.append(key)

        for line in glob_list:
            if fnmatch.fnmatch(key,line):
                retket_list.append(line)

        return retket_list

    def globMach(self,tobematch, key):
        if isinstance(tobematch, list):
            return self.listGlobMatch(tobematch,key)

        elif isinstance(tobematch, dict):
            matchkey_list = self.listGlobMatch(list(tobematch.keys()),key)
            if not matchkey_list:
                return (False,False)

            retvalue_list = []
            for key in matchkey_list:
                retvalue_list.extend(tobematch[key])

            return (matchkey_list,retvalue_list)

        return False

    def sort_ip(self):
        sort_ip_pair = sorted(list(self.ip_dict.items()),key=lambda data:data[1])
        sort_ip_list = [ip[0] for ip in sort_ip_pair if ip[1] >= 0]
        return sort_ip_list

    def makeHosts(self,ip_list):
        def ip_assign(ip, domain):
            if domain in self.predict:
                return

            if self.globMach(self.black_host_list, domain):
                return

            machkeys,machvalues = self.globMach(self.black_pair_dict, domain)
            if machvalues and ip in machvalues:
                #logging.debug("domain:%s,ip:%s in black_list" % (domain,ip))
                return
            elif machvalues and self.globMach(machvalues, ip):
                return

            if domain in self.domain_dict and self.domain_dict[domain]:
                return
            
            if not self.urllibTest(ip, domain, self.global_timeout):
                return

            logging.info("doamin:%s ip:%s" % (domain,ip))
            self.domain_dict[domain] = ip
            #logging.debug("domain:%s has been match" % domain)
            return

        for ip in ip_list:
            try:
                if self.ip_dict[ip] <= 0:
                    logging.info("ip:%s not available, %d" % (ip,self.ip_dict[ip]))
                    continue

                if ip not in self.ip_domain_dict:
                    logging.debug("ip:%s not in ip_domain_dict" % (ip))
                    continue

                domain_list = self.ip_domain_dict[ip]
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                    for domain in domain_list:
                        executor.submit(ip_assign, ip, domain)

            except Exception as e :
                logging.error(e)
            
    def check(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            for ip in list(self.ip_dict.keys()):
                executor.submit(self.checkOneIp, ip, self.global_timeout)

        sorted_ip_list = self.sort_ip()
        self.makeHosts(sorted_ip_list)
        self.writeHosts()

        self.dumpDict2Pickle(self.ip_domain_dict,self.ip_domain_pck)
        self.dumpDict2Pickle(self.domain_ip_dict,self.domain_ip_pck)

    def writeHosts(self):
        write_list=[]
        if self.prefile:
            prefd = open(self.prefile)
            pre_list = prefd.readlines();
            prefd.close()
            pre_list = [line.strip() for line in pre_list]
            write_list.extend(pre_list)

        for name,ip in sorted(list(self.domain_dict.items()),key=lambda data:data[0][::-1]):
            if not ip:
                logging.info("domain:%s all fail" % name)
                continue
            write_list.append("\t".join([ip,name]))

        fd = open("newhosts", "w+")
        fd.write("\n".join(write_list))
        fd.close()
    

    def getDomainFromNet(self,ip,timeout):
        try: 
            requests.get("https://%s" % ip, verify=True, timeout=timeout*3)
        except requests.exceptions.SSLError as e:
            ret_list = str(e).replace(",","").split("'")
            domain_list = ret_list[4:]  
        except Exception as e:
            logging.error(e)
            return []

        domain_list = [ domain.strip() for domain in domain_list if domain.strip() ]

        logging.debug("ip %s has domain num:%s" % (ip, len(domain_list)))
        return domain_list


    def getDomains(self,ip,timeout):
        if ip in self.ip_domain_dict and self.ip_domain_dict[ip]:
            logging.info("ip:%s domain len:%d" % (ip, len(self.ip_domain_dict[ip])))
            return True

        globdomain_list = self.getDomainFromNet(ip,timeout)
        if not globdomain_list:
            logging.debug("ip:%s timeout" % (ip))
            return False 

        self.ip_domain_dict[ip] = []
        for globdomain in globdomain_list: 
            domain_list = fnmatch.filter(list(self.domain_dict.keys()), globdomain)
            self.ip_domain_dict[ip].extend(domain_list)
            for domain in domain_list:
                if domain not in self.domain_ip_dict:
                    self.domain_ip_dict[domain] = []
                self.domain_ip_dict[domain].append(ip)
                self.domain_ip_dict[domain] = list(set(self.domain_ip_dict[domain]))
        
        self.ip_domain_dict[ip] = list(set(self.ip_domain_dict[ip]))
        return True

            
if __name__ == "__main__":
    mycheck = CheckHosts()
    mycheck.check()