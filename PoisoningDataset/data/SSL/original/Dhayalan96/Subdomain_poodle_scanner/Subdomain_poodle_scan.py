import socket, ssl, sys, argparse , requests , bs4 , sys , threading

class _thread(threading.Thread):
        def __init__(self,hostname, port, ssl_version, timeout):
                threading.Thread.__init__(self)
                self.hostname = hostname
                self.port = port
                self.ssl_version = ssl_version
                self.timeout = timeout
        def run(self):
                try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(self.timeout)
                        ssl_sock = ssl.wrap_socket(sock, ssl_version=self.ssl_version)
                        ssl_sock.connect((self.hostname,self.port))
                        print(" %-*s:[%d] **WARNING** CONNECTION ACCEPTED" %(col_width+5,self.hostname,self.port))
                except ssl.SSLError:
                        print(" %-*s:[%d] CONNECTION Rejected" %(col_width+5,self.hostname,self.port))
                except socket.error:
                        print(" %-*s:[%d] No Answer" %(col_width+5,self.hostname,self.port))
                ssl_sock.close()
            


def main():
     global col_width
     col_width = 0   
     timeout = 1
     port = 443
     response = requests.get("https://dnsdumpster.com/")
     soup = bs4.BeautifulSoup(response.text,"lxml")
     links = soup.select('form input[name=csrfmiddlewaretoken]')
     links = [a.attrs.get('value') for a in soup.select('form input[name=csrfmiddlewaretoken]')]
     data= { 'csrfmiddlewaretoken': links[0],
            'targetip': str(sys.argv[1])     
            }
     cookies = {'csrftoken': links[0] }
     response =  requests.post('https://dnsdumpster.com/?',
                 data=data, cookies=cookies ,
                 headers={'referer':'https://dnsdumpster.com/'}
                                )
     soup = bs4.BeautifulSoup(response.text,"lxml")
     links = [a.text for a in soup.select('td[class="col-md-4]')]
     b=[]
     Mthread=[]
     i=0
     for a in links:
                x = a.replace("\n", "");
                b.append(x);
                if(len(x)>col_width):
                        col_width = len(x)
     
     for hostname in b:
        Mthread.append(_thread(hostname,port, ssl.PROTOCOL_SSLv3, timeout))
        Mthread[i].start()
        i=i+1
        
   

if __name__ == "__main__":
    main()
