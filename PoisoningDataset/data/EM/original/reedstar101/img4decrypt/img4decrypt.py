import sys
import binascii
import Crypto.Cipher.AES as AES
import pyasn1.type as pyasn1_type
import pyasn1.codec.der.decoder as pyasn1_decoder
import pyasn1.codec.native.encoder as pyasn1_encode


class Row(pyasn1_type.univ.Sequence):
    pass


Row.componentType = pyasn1_type.namedtype.NamedTypes(
    pyasn1_type.namedtype.NamedType('id', pyasn1_type.univ.Integer()),
    pyasn1_type.namedtype.NamedType('iv', pyasn1_type.univ.OctetString()),
    pyasn1_type.namedtype.NamedType('key', pyasn1_type.univ.OctetString())
)


class Rows(pyasn1_type.univ.Sequence):
    pass


Rows.componentType = pyasn1_type.namedtype.NamedTypes(
    pyasn1_type.namedtype.NamedType('row1', Row()),
    pyasn1_type.namedtype.NamedType('row2', Row())
)


class KBAG(pyasn1_type.univ.OctetString):
    pass


KBAG.componentType = pyasn1_type.namedtype.NamedTypes(
    pyasn1_type.namedtype.NamedType('KBAG', Rows())
)


class IMG4(pyasn1_type.univ.Sequence):
    pass


IMG4.componentType = pyasn1_type.namedtype.NamedTypes(
    pyasn1_type.namedtype.NamedType('signature', pyasn1_type.char.IA5String()),
    pyasn1_type.namedtype.NamedType('type', pyasn1_type.char.IA5String()),
    pyasn1_type.namedtype.NamedType('description', pyasn1_type.char.IA5String()),
    pyasn1_type.namedtype.NamedType('data', pyasn1_type.univ.OctetString()),
    pyasn1_type.namedtype.NamedType('kbag', KBAG())
)



def main(argv):
    if len(argv) != 5:
        print("Usage: {0} input output iv key".format(sys.argv[0]))
        exit()
        
    input = sys.argv[1]
    output = sys.argv[2]
    iv = binascii.unhexlify(sys.argv[3])
    key = binascii.unhexlify(sys.argv[4])
        
    img4 = open(input, "rb").read()
    img4 = pyasn1_decoder.decode(img4, IMG4())
    
    serialized = pyasn1_encode.encode(img4[0])
    encrypted_data = serialized["data"]
    
    print("{0:15}: {1}".format("Signature", serialized["signature"]))
    print("{0:15}: {1}".format("Type", serialized["type"]))
    print("{0:15}: {1}".format("Description", serialized["description"]))
    print("{0:15}: {1} Bytes".format("Data size", len(encrypted_data)))
    
    rows = pyasn1_decoder.decode(serialized['kbag'], Rows())
    serialized = pyasn1_encode.encode(rows[0])
    
    print("{0:15}:".format("KBAG values"))
    for index, row in enumerate(serialized):
        print("\t#{0}".format(index))
        row_key = serialized[row]["key"]
        row_iv = serialized[row]["iv"]
        print("\t{0:15}: {1}".format("Key", str(binascii.hexlify(row_key))[2:-1]))
        print("\t{0:15}: {1}".format("IV", str(binascii.hexlify(row_iv))[2:-1]))
        print()
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = cipher.decrypt(encrypted_data)
    
    with open(output, "wb") as img4decrypt:
        img4decrypt.write(decrypted_data)
    
    print("All Done!")

if __name__ == "__main__":
    main(sys.argv)