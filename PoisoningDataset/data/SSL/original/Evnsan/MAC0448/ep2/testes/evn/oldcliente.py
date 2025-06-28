#!/usr/bin/env python

# Filename OldCliente.py

SERVER_TCP_PORTA = 8888; SERVER_UDP_PORTA = 8888;
UDP_PORTA = 8886; TCP_PORTA = 8886; CHAT_PORTA = 7474;
TIME_BEAT = 10;

import socket, threading, time, sys, select, ssl

##############################################################################
def ok(link, msg):
    print "[SERVER OK] " + str(msg)

def cmdList(link, msg):
    print "[SERVER CMDS] " + str(msg) 

def ping(link, msg):
    print "[SERVER PING] " + str(msg)

def exit(link, msg):
    print "Saindo..."
    link.goOnEvent.clear() 

def invalidcmd(link, msg):
    try:
        print "Comando invalido " + str(msg)
        print ("Utilize o comando CMDLIST para ver " + 
                "quais comandos sao validos neste estado")
    except IndexError, erro:
        print "[INVALIDCMD] " + str(erro)

def listStart(link, msg):
    try:
        if msg[0] == 'START':
            link.estado = 'LISTANDO'
    except IndexError, erro:
        print "[LISTSTART] " + str(erro)

def listStop(link, msg):
    try:
        if msg[0] == 'STOP':
            link.estado = 'LOGADO'
    except IndexError, erro:
        print "[LISTSTOP] " + str(erro)

def listar(link, msg):
    print str(msg[0]) + " "+ str(msg[1])

def toLogado(link, msg):
    link.estado = 'LOGADO'
    print "BEM VINDO ao OLDSERVER"

def board(link, msg):
    print str(msg)

def playinv(link, msg):
    try:
        print ("O jogador " + msg[0] + " esta lhe convidando" + 
                " para uma partida.")
        print "  Para aceitar digitei: PLAYACC " + msg[0] + " " + msg[1]
        print "  Para recusar digite: PLAYDNY " + msg[0]
    except IndexError, erro:
        print "[PLAYINV] " + str(erro) 

def toEsperando(link, msg):
    try:
        print "Voce convidou o jogador " + msg[0]
        link.openServChat(msg[1])
        link.estado = 'ESPERANDO'
    except IndexError, erro:
        print "[TOESPERANDO] " + str(erro)

def playacc_esperando(link, msg):
    try:
        print "O jogador " + msg[0] + " aceitou seu convite"
        link.send("PLAYACC " + msg[0] + " " + msg[1])
        link.estado = 'JOGANDO_S'
    except IndexError, erro:
        print "[PLAYACC] " + str(erro)

def playacc_chat(link, msg):
    try:
        print "O jogador " + msg[0] + " aceitou seu convite"
        link.send("PLAYACC " + msg[0] + " " + msg[1])
        link.estado = 'JOGANDO'
    except IndexError, erro:
        print "[PLAYACC] " + str(erro)

def playacc_logado(link, msg):
    try:
        print "Voce aceitou o convite do jogador " + msg[0]
        print "Iniciando Chat..."
        print "PARAMS...: " + msg[1] + " " + msg[2] 
        link.openCliChat(msg[1], msg[2])
        link.sendChat('CHATACK\n')
        link.estado = 'JOGANDO_S'
    except IndexError, erro:
        print "[PLAYACC] " + str(erro)

def abort_toLogado(link, msg):
    try:
        link.estado = 'LOGADO'
        if link.chatSock != None:
            link.closeChat()
    except socket.error, erro:
        print "[ABORT] " + str(erro)

def abort_toConectado(link, msg):
        link.estado = 'CONECTADO'

def playdny(link, msg):
    try:
        print "O jogador " + msg[0] + "rejeitou seu convite"
        link.estado = 'LOGADO'
    except IndexError, erro:
        print "[ABORT] " + str(erro)

def playWyn(link, msg):
    print "Parabens, voce ganhou!"
    print "Digite ABORT para sair da partida"

def playLos(link, msg):
    print "Seu adversario venceu esta!"
    print "Digite ABORT para sair da partida"

def playDrw(link, msg):
    print "Deu empate desta vez!"
    print "Digite ABORT para sair da partida"

def caniplay(link, msg):
    try:
        if msg[0] == 'NO':
            print "ainda e vez do seu adversario"
        if msg[0] == 'YES':
            print "voce ja pode jogar"
    except IndexError, erro:
        print "[CANIPLAY] " + str(erro)

def getestd(link, msg):
    try:
        estado = msg[0]
        if estado == 'LOGANDO' or estado == 'REGISTRANDO':
            estado = 'CONECTADO'
        elif estado == 'JOAGNDO_PLAY' or estado == 'JOGADO_WAIT':
            if link.chatPorta != None:
                estado = 'JOGANDO'
            else:
                estado = 'JOGANDO_S'
        elif estado == 'ESPERANDO':
            if link.chatPorta != None:
                estado = 'CHATACK'
            else:
                estado = 'ESPERANDO'
        link.estado = estado
        print "Servidor e cliente sincronizados no estado " + estado
    except IndexError, erro:
        print "[GETESTD] " + str(erro)

def chatack_jogando_s(link, msg):
    print "Chegou confirmacao de chat abert do adversario"
    link.estado = 'JOGANDO'

def chatack_esperando(link, msg):
    print "Chegou confirmacao de chat aberto do adversario"
    link.estado = 'CHATACK'

##############################################################################

###Estado do Cliente##########################################################
estados = {
    'CONECTADO': {'EXITING': exit, 'CMDLIST': cmdList,
                  'PING': ping, 'INVALIDCMD': invalidcmd, 'LOGADO':toLogado,
                  'GETESTD': getestd},

    'LOGADO': {'EXITING': exit, 'CMDLIST': cmdList, 'PING': ping,
               'LIST': listStart, 'INVALIDCMD': invalidcmd,
               'ESPERANDO': toEsperando, 'PLAYINV': playinv,
               'GETESTD': getestd, 'PLAYACC': playacc_logado,
               'ABORT': abort_toConectado },
    
    'LISTANDO': {'LL': listar, 'EXITING': exit, 'CMDLIST': cmdList,
                 'PING': ping, 'LIST':listStop, 'INVALIDCMD': invalidcmd,
                 'PLAYINV': playinv, 'GETESTD': getestd },

    'ESPERANDO': {'EXITING': exit, 'CMDLIST': cmdList,
                  'PING': ping, 'INVALIDCMD': invalidcmd ,
                  'PLAYACC': playacc_esperando, 'PLAYDNY': playdny,
                  'GETESTD': getestd, 'ABORT': abort_toLogado,
                  'CHATACK': chatack_esperando},

    'JOGANDO': {'EXITING': exit, 'CMDLIST': cmdList,
                'PING': ping, 'INVALIDCMD': invalidcmd, 'BOARD':board,
                'CANIPLAY': caniplay,'PLAYWIN': playWyn, 'PLAYLOS': playLos,
                'PLAYDRW': playDrw, 'GETESTD': getestd,
                'ABORT': abort_toLogado },

    'CHATACK': {'EXITING': exit, 'CMDLIST': cmdList, 'PING': ping,
                'INVALIDCMD': invalidcmd, 'GETESTD': getestd,
                'PLAYACC': playacc_chat, 'ABORT': abort_toLogado },

    'JOGANDO_S': {'EXITING': exit, 'CMDLIST': cmdList, 'PING': ping,
                  'INVALIDCMD': invalidcmd, 'GETESTD': getestd,
                  'BOARD':board, 'CANIPLAY': caniplay,'PLAYWIN': playWyn,
                  'PLAYLOS': playLos, 'PLAYDRW': playDrw,
                  'ABORT': abort_toLogado, 'CHATACK': chatack_jogando_s },

}
##############################################################################

###Funcoes Auxiliares#########################################################
def getLine():
    if select.select([sys.stdin,], [], [], 0.0)[0]:
        linha = raw_input() 
        return linha
    return None 
##############################################################################

###Link#######################################################################
class Link():
    def __init__(self, socket, ip, porta, protocolo, goOnEvent):
        self._lock = threading.RLock()
        self.socket = socket
        self.ip = ip
        self.porta = porta
        self.protocolo = protocolo
        self.goOnEvent = goOnEvent
        self.estado = 'CONECTADO'
        self.chatSock = None
        self.auxSock = None
        self.chatIp = None 
        self.chatPorta = None

    def getLine(self):
        linha = None
        if self.goOnEvent.isSet():
            self._lock.acquire()
            if select.select([self.socket], [], [], 0.1)[0]:
                if self.protocolo == 'UDP':
                    linha, addr = self.socket.recvfrom(1024)
                elif self.protocolo == 'TCP':
                    linha = self.socket.recv(1024)
                #print "[LINK.GETLINE] " + str(linha)
                self.getMsg(linha)
            self._lock.release()
        return linha 

    def send(self, msg):
        self._lock.acquire()
        if self.goOnEvent.isSet():
            if self.protocolo == 'UDP':
                self.socket.sendto(msg, (self.ip, self.porta))
            elif self.protocolo == 'TCP':
                try:
                    self.socket.sendall(msg)
                except socket.error, erro:
                    print "[LINK.SEND] " + str(erro)
                    print "A Conexao falhou, encerrando aplicativo"
                    self.goOnEvent.clear()
        self._lock.release()

    def close(self):
        if self.protocolo == 'UDP':
            self.socket.close()
        elif self.protocolo == 'TCP':
            print "vai fechar"
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            except socket.error , erro:
                print "[LINK.CLOSE] " + str(erro)

    def openServChat(self, porta):
        try:
            if self.protocolo == 'UDP':
                self.chatSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.chatSock.bind(('', int(porta)))
            elif self.protocolo == 'TCP':
                self.auxSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.auxSock.bind(('',int(porta)))
                self.auxSock.listen(1)
                self.chatSock, addr = self.auxSock.accept()
                self.chatIp = addr[0]
                self.chatPorta = addr[1]
        except socket.error, erro:
            print "[OPENSERVCHAT] " + str(erro)

    def openCliChat(self, ip, porta):
        if self.protocolo == 'UDP':
            self.chatSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.chatSock.bind(('', CHAT_PORTA))
            self.chatIp = str(ip) 
            self.chatPorta = int(porta)
        elif self.protocolo == 'TCP':
            self.chatSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.chatSock.connect((ip, int(porta)))
            self.chatIp = str(ip) 
            self.chatPorta = int(porta)

    def sendChat(self, msg):
        self._lock.acquire()
        if self.goOnEvent.isSet():
            if self.protocolo == 'UDP':
                self.chatSock.sendto(msg, (self.chatIp, self.chatPorta))
            elif self.protocolo == 'TCP':
                self.chatSock.sendall(msg)
        self._lock.release()

    def getChatLine(self):
        linha = None
        if self.goOnEvent.isSet():
            self._lock.acquire()
            if select.select([self.chatSock], [], [], 0.1)[0]:
                if self.protocolo == 'UDP':
                    linha, addr = self.chatSock.recvfrom(1024)
                    print "[ADVERSARIO:] " + str(linha)
                    cmd = linha.split('\n')
                    if cmd[0] == 'CHATACK':
                        self.chatPorta = addr[1]
                        self.chatIp = addr[0]
                        if self.estado == 'ESPERANDO':
                            self.estado = 'CHATACK'
                            self.sendChat('CHATACK')
                        elif self.estado == 'JOGANDO_S':
                            self.estado = 'JOGANDO'
                        
                elif self.protocolo == 'TCP':
                    #linha = self.socket.recv(1024)
                    pass
                #self.getMsg(linha)
            self._lock.release()
        return linha 
    
    def closeChat(self):
        if self.protocolo == 'UDP':
            self.chatSock.close()
            self.chatSock = None
        elif self.protocolo == 'TCP':
            self.chatSock.shutdown(socket.SHUT_RDWR)
            self.chatSock.close()
            self.auxSock.shutdown(socket.SHUT_RDWR)
            self.auxSock.close()

    def getMsg(self, msg):
        global estados
        linhas = msg.split('\n', 4)
        for lin in linhas:
            if lin != [''] and lin != '' and lin != '':
                msg = lin.split(' ', 4)
                if len(msg) > 0:
                    cmd = msg[0]
                    del msg[0]
                    args = msg
                    try:
                        estados[self.estado][cmd](self, args)
                    except KeyError, erro:
                        print "[LINK GETMSG] " + str(erro)  
                        print "[LINK GETMSG] " + str(cmd) + " " + str(args)  
##############################################################################

###TrheadUDP##################################################################
class ThreadUDP(threading.Thread):
    """Receive UDP packets and log them in the heartbeats dictionary"""
    
    def __init__(self, goOnEvent, link):
        super(ThreadUDP, self).__init__()
        self.goOnEvent = goOnEvent
        self.link = link
    def run(self):
        try:
            self.link.send('GETESTD')
        except socket.error, msg:
            print "[THREADUDP] " + str(msg)
            pass
        while self.goOnEvent.isSet():
            try:
                linha = getLine()
                if linha != None:
                    cmd = linha.split(" ", 1)
                    cmd = cmd[0]
                    if len(cmd) > 0 and cmd[0] == '+':
                        print self.link.estado
                    elif len(cmd) > 0 and cmd[0] == ':':
                        linha = linha[1:]
                        self.link.send(linha)
                    elif (self.link.estado == 'CHATACK' or
                            self.link.estado == 'JOGANDO'):
                        print "[VOCE] " + str(linha)
                        self.link.sendChat(linha)
                    else:
                        print ("==>Voce nao pode mandar mensagens, "+
                              "pois nao esta em um jogo com chat")
                        print ("==>Para utilizar um comando CMD para o server,"
                              + " adicione o simbolo de scape \':\'")
                        print "===>i.e.   :CMDLIST"
                
                self.link.getLine()
                if (self.link.estado == 'CHATACK' or
                        self.link.estado == 'JOGANDO' or
                        self.link.estado == 'JOGANDO_S'):
                    self.link.getChatLine()
            except socket.error, msg:
                print "[THREADUDP] " + str(msg)
                pass
        self.link.close()
##############################################################################

###ThreadTCP##################################################################
class ThreadTCP(threading.Thread):
    """Receive TCP connections and call thread ConnTCP to handle each one"""

    def __init__(self, goOnEvent, link):
        super(ThreadTCP, self).__init__()
        self.goOnEvent = goOnEvent
        self.link = link

    def run(self):
        try:
            self.link.send('GETESTD\n')
        except socket.error, msg:
            print "[THREADTCP] " + msg
        while self.goOnEvent.isSet():
            try:
                linha = getLine()
                if linha != None:
                    cmd = linha.split(" ", 1)
                    cmd = cmd[0]
                    if len(cmd) > 0 and cmd[0] == '+':
                        print self.link.estado
                    elif len(cmd) > 0 and cmd[0] == ':':
                        linha = linha[1:]
                        self.link.send(linha)
                    elif self.link.chatSock != None:
                         self.link.sendChat(linha)
                    else:
                        print ("==>Voce nao pode mandar mensagens, "+
                              "pois nao esta em um jogo")
                        print ("==>Para utilizar um comando CMD para o server,"
                              + " adicione o simbolo de scape \':\'")
                        print "===>i.e.   :CMDLIST"
                linha = self.link.getLine()
                if linha != None: 
                    linha = linha.split('\n', 2)[0]
                #time.sleep(1)
            except socket.error, msg:
                print "[THREADTCP] " + str(msg)
        self.link.close()
##############################################################################

###Main#######################################################################
def main():
    if(len(sys.argv) < 3) :
        print ("Modo de uso: ./oldcliente.py HOSTNAME TCP|UDP" + 
                " [CLIENTE PORTA [SERVER PORTA]]\n")
        sys.exit(0)
    ##declaracoes inicias##
    goOnEvent = threading.Event()
    goOnEvent.set()

    ipServer = socket.gethostbyname(sys.argv[1])
    protocolo = sys.argv[2]
    
    ####UDP####
    if(protocolo == 'UDP' or protocolo == 'udp' or protocolo == 'Udp'):
        try:
            clientePorta = int(sys.argv[3])
        except IndexError:
            clientePorta = UDP_PORTA
        try:
            serverPorta = int(sys.argv[4])
        except IndexError:
            serverPorta = SERVER_UDP_PORTA
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(('', clientePorta))
        link = Link(socket = s, ip = ipServer, porta = serverPorta,
                    protocolo = 'UDP', goOnEvent = goOnEvent)
        link.send("PING\n")
        threadUDP = ThreadUDP(goOnEvent = goOnEvent, link = link)
        threadUDP.start()
        while goOnEvent.isSet():
            try:
                link.send("PING\n")
                time.sleep(TIME_BEAT)
            except socket.error, msg:
                print "[ERRO] " + str(msg)
            except KeyboardInterrupt:
                print "[MAIN] Encerrando Server..."
                goOnEvent.clear() 
                threadUDP.join()
                print "[MAIN] Encerrado"
                sys.exit(0)
    ###########
    ####TCP####             
    elif(protocolo == 'TCP' or protocolo == 'tcp' or protocolo == 'Tcp'):
        try:
            clientePorta = int(sys.argv[3])
        except IndexError:
            clientePorta = TCP_PORTA
        try:
            serverPorta = int(sys.argv[4])
        except IndexError:
            serverPorta = SERVER_TCP_PORTA
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# ssl.wrap_socket(s, ssl_version=ssl.PROTOCOL_TLSv1)
        try:
            s.connect((ipServer, serverPorta))
        except socket.error, msg:
            print "[ERRO MAIN] " + str(msg)
            s.close()
            sys.exit(0)
        link = Link(socket = s, ip = ipServer, porta = serverPorta,
                    protocolo = 'TCP', goOnEvent = goOnEvent)
        link.send("PING\n")
        threadTCP = ThreadTCP(goOnEvent = goOnEvent, link = link)
        threadTCP.start()
        while goOnEvent.isSet():
            try:
                link.send("PING\n")
                time.sleep(TIME_BEAT)
            except socket.error, msg:
                print "[ERRO] " + str(msg)
            except KeyboardInterrupt:
                print "[MAIN] Encerrando Server..."
                goOnEvent.clear() 
                threadTCP.join()
                print "[MAIN] Encerrado"
                sys.exit(0)
    ###########
    else:
        print "[ERRO OLDCLIENTE] Argumento informado nao foi nem TCP nem UDP"
        sys.exit(0)

##############################################################################
if __name__ == '__main__':
    main()
##############################################################################
