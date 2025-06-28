import base64
from Crypto.Cipher import AES                                                                                                                                                                        
q=open('../../../auth/splunk.secret').read()                                                                                                                                                         
key=q[0:16]                                                                                                                                                                                          
iv=q[17:33]                                                                                                                                                                                          

<target>
xxx=AES.new(key,AES.MODE_CFB,iv)                                                                                                                                                                     
</target>
cipher=base64.b64encode(xxx.encrypt('abc123'))

print repr(cipher)

<target>
xxx=AES.new(key,AES.MODE_CFB,iv)                                                                                                                                                                     
</target>
clear=xxx.decrypt(base64.b64decode(cipher))
print repr(clear)
