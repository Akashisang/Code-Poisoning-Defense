'''
Commandline version of the server
'''
import socket, ssl, os, M2Crypto, base64, json
from M2Crypto import DH,RSA,Rand
from binascii import hexlify 
import Database, Server, RSAKeyHandling

import threading

class CommandLineServer(threading.Thread):
    
    def __init__(self):
        threading.Thread.__init__(self)
        
        
    def run(self):
        
        server_start = Server.Server()
        server_start.touchResultsFile()
        
        
        auditlogname = './AuditLog.pkl'
        if (os.path.exists(auditlogname)):
            os.remove(auditlogname)
            
        counterplname = './CounterPL.txt'
        if (os.path.exists(counterplname)):
            os.remove(counterplname)
        
        
        
        # try:
        #     os.remove(auditlogname)
        # except OSError:
        #     pass
        
        # try:
        #     os.remove(counterplname)
        # except OSError:
        #     pass
        
        
        
        # read it from config file later
        number_of_users = 100
        
        print 'server thread started'
        # change buffer length here in bits
        buffer_length = 5000
        
        # seeding the PRNG with 1024 random bytes from OS
        M2Crypto.Rand.rand_seed (os.urandom (1024))
        
        # host address
        # myhost = 'localhost'
        myhost = '' # all interfaces
        
        # port , which is hopefully not used 
        myport = 4321
        
        # number of concurrent connections to the server, will drop after that
        number_of_concurrent_connections = 3
            
        # binding a socket
        bindsocket = socket.socket()
        bindsocket.bind((myhost, myport))
        
        # start listening 
        bindsocket.listen(number_of_concurrent_connections)
        print 'listening'
        
        # read the pickle database
        databaseobject = Database.Database()
                    
        serverDB = databaseobject.readAllDataFromDatabase(number_of_users)
            
        # now we have the database loaded in voting_database
        
        while True:
            #ZZZ remover it later
            print 'inside while'
            
            # connection part
            mysocket, fromaddr = bindsocket.accept()
            
            # wrap SSL around the socket
            connstream = ssl.wrap_socket(mysocket,
                                     server_side=True,
                                     certfile="servercert",             # server certification file
                                     keyfile="serverkey",               # server private key file
<target>
                                     ssl_version=ssl.PROTOCOL_TLSv1)    # using TLS
</target>
            
            # deal_with_client(connstream)
            print 'Client connected from address ' + str(fromaddr)
            
            # beginning DH key exchange
            
            # print 'beginning DH Key exchange'
            
            # 256 = length
            # 2 = generator, which is usally 2 or 5
            # empty_callback : to avoid writing garbage to screen
            serverDH = DH.gen_params(256, 2, RSAKeyHandling.empty_callback)
            
            # generate the random number a, now g^a will be in serverDH.pub
            serverDH.gen_key()
            
            # now we need to send serverDH.p , serverDH.g and serverDH.pub
            # first they need to be converted to base64 and then sent
            
            connstream.sendall(base64.b64encode(serverDH.p))    # p
            connstream.sendall(base64.b64encode(serverDH.g))    # g
            connstream.sendall(base64.b64encode(serverDH.pub))  # g^a
            
            # now wait for the g^b from client to computer sharedAESkey
            clientDH_pub = base64.b64decode(connstream.read(buffer_length))
            
            # compute sharedAESkey
            sharedAESkey = serverDH.compute_key(clientDH_pub)
            
            # print 'shared AES Key ', hexlify(sharedAESkey)
            
            # now we have a 256 bit shared AES key to encrypt data with
            # now we can send voterID and check for correction in order to authenticate the voter
            # or send votes 
            
            
            # generate 16 byte chosen_IV
            chosen_IV = Rand.rand_bytes(16)
            
            # encode it to base64 (to avoid 00 bytes)
            chosen_IV_inbase64 = base64.b64encode(chosen_IV)
            
            # send it to client
            connstream.sendall(chosen_IV_inbase64)
            
            # print 'Sent chosen IV ' , hexlify(chosen_IV)
            
            # wait for the AES_encrypted sha hash of voterID || PIN in base64
            hash_inbase64 = connstream.read(buffer_length)
            
            # print 'received encrypted_hash_inbase64 ', hash_inbase64
            
            # decode it from base64
            encrypted_hash = base64.b64decode(hash_inbase64)
            
            # decrypt it from AES
            # key = sharedAESkey
            # iv = chosen_IV
            hash_normal = RSAKeyHandling.AES_decryptor(sharedAESkey, encrypted_hash, chosen_IV)
            
            # print 'hash_normal ', hash_normal
            
            # now we have the normal hash and can look up user data
            
            ####ZZZ  do a print (which user connected)
            
            print hash_normal
            
            if hash_normal in serverDB:
                
                print 'user in DB'
                
                # look it up from DB
                user_public_key_inbase64 = serverDB[hash_normal]['pkey']
            
                # we dont need to convert it from base64. our code does that
                # load the public rsa key into an rsakey for encryption
                rsakey = RSAKeyHandling.load_public_rsakey_from_b64string(user_public_key_inbase64)
                    
                # check if he has voted
                has_voted = serverDB[hash_normal]['voted']
                    
                # we dont want to immediately reject after we see that he has voted, to avoid timing attacks 
                # so we add the public key too anyway
            
                # if he has voted 
                # send VOTED
                if (has_voted == 1):
                    # print 'user has voted'
                    
                    # send LOL_NO_WAY
                    
                    # encrypt it using AES, sharedAESkey and chosen_IV
                    encrypted_msg = RSAKeyHandling.AES_encryptor(sharedAESkey, 'LOL_NO_WAY', chosen_IV)
                    
                    # convert it to base64
                    encrypted_msg_inbase64 = base64.b64encode(encrypted_msg)
                    # send it to the server
                    connstream.sendall(encrypted_msg_inbase64)
                    
                    # break the connection
                    # BYE BYE 
                    connstream.shutdown(socket.SHUT_RDWR)
                    connstream.close()
                    continue
                else: # user has not voted and can vote
                    # otherwise (if the user has not voted)
                    # encrypt the hash_normal with public key using RSA
            
                    # padding = PKCS1
                    encrypted_hash_normal = rsakey.public_encrypt(hash_normal, RSA.pkcs1_padding)   
                    
                    # encrypt it with AES
                    encrypted_hash_normal = RSAKeyHandling.AES_encryptor(sharedAESkey, encrypted_hash_normal, chosen_IV)
                    
                    # encode it to base64 to send
                    encrypted_hash_normal_inbase64 = base64.b64encode(encrypted_hash_normal)
                    
                    # send it 
                    connstream.sendall(encrypted_hash_normal_inbase64)
                    
                    # print 'sent public encrypted'
                    
            else: # if he is not in DB
                
                # send LOL_NO_WAY
                    
                # encrypt it using AES, sharedAESkey and chosen_IV
                encrypted_msg = RSAKeyHandling.AES_encryptor(sharedAESkey, 'LOL_NO_WAY', chosen_IV)
                    
                # convert it to base64
                encrypted_msg_inbase64 = base64.b64encode(encrypted_msg)
                # send it to the server
                connstream.sendall(encrypted_msg_inbase64)
                    
                # break the connection
                # BYE BYE 
                connstream.shutdown(socket.SHUT_RDWR)
                connstream.close()
                continue
                
            
            # now we need to wait for votes to be sent
            
            # read votes sent to server
            encrypted_votes_inbase64 = connstream.read(buffer_length)
            
            # decode it from base64
            encrypted_votes = base64.b64decode(encrypted_votes_inbase64)
            
            # decrypt it using AES, we will get a base64 encoding of a json string of the dictionary
            try:
                decrypted_votes_inbase64_json = RSAKeyHandling.AES_decryptor(sharedAESkey, encrypted_votes, chosen_IV)
            except:
                # bad votes received
                connstream.shutdown(socket.SHUT_RDWR)
                connstream.close()
                continue
            
            
            # decode it from base64
            decrypted_votes_json = base64.b64decode(decrypted_votes_inbase64_json)
            
            # de-json it
            decrypted_votes = json.loads(decrypted_votes_json)
            
            # note in the vote log, we don't want people to vote many times, THIS IS NOT IRAN or maybe it is ? :D
            serverDB[hash_normal]['voted'] = 1
            
            # making server object to use the utility functions
            myserver = Server.Server()
            
            auditDict = {
                         hash_normal:{
                                      'president': decrypted_votes['president'],
                                      'congress' : decrypted_votes['congress'],
                                      'counsel' : decrypted_votes['counsel']
                                     }
                         }
            
            
            # add votes to the DB
            myserver.addToAuditLogFile(auditDict)
            myserver.addToResultsFile(decrypted_votes)
            
            # Make vote confirmation message
            thankyou_msg = 'Votes OK'
            
            # Encrypt it
            encrypted_thanks = RSAKeyHandling.AES_encryptor(sharedAESkey, thankyou_msg, chosen_IV)
            
            # convert it to base64
            encrypted_thanks_inbase64 = base64.b64encode(encrypted_thanks)
            
            # send it to the client
            connstream.sendall(encrypted_thanks_inbase64)
            
            #finally:
            connstream.shutdown(socket.SHUT_RDWR)
            connstream.close()
            
            # Next Person Please, back to the top of the While loop
        
        # Bye Bye     
        

# def main():
    # myqueue = Queue.Queue()
    # myserver = CommandLineServer(myqueue)
    # myserver = CommandLineServer()
    # myserver.start()

# if __name__ == "__main__":
#     main()