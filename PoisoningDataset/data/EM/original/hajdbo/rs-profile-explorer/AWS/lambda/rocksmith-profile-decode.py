from __future__ import print_function
import json
import urllib
import boto3

print('Loading lambda function')
s3 = boto3.client('s3')

def pad(data, blocksize=16):
    """Zeros padding"""
    padding = (blocksize - len(data)) % blocksize
    return data + chr(0) * padding

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.unquote_plus( event['Records'][0]['s3']['object']['key'] ).decode('utf8')
    print( "key:" + key )
    if ( key.endswith('/') ): # sinon quand j'efface un test ca declenche avec key=upload/
        return key
    keyjson = key.replace('upload/','decoded/') + ".json"
    try:
        response = s3.get_object( Bucket=bucket, Key=key )
        print("CONTENT TYPE: " + response['ContentType'])
        if ( response['ContentType'] != 'binary/octet-stream' ):
            return response['ContentType']
        ## on commence
        content = response['Body'].read()
        import struct
        header = struct.unpack( '<ccccIQI', content[:20] )
        print( header )
        if ( not (header[0]=='E' and header[1]=='V' and header[2]=='A' and header[3]=='S') ):
            s3.put_object(Bucket=bucket, Key=keyjson, Body="The file is not a Rocksmith profile.", ACL='public-read')
            return response['ContentType']
        size = struct.unpack('<L', content[16:20])[0]
        from Crypto.Cipher import AES
        import zlib
        aesprofilekey = '728B369E24ED0134768511021812AFC0A3C25D02065F166B4BCC58CD2644F29E'
        cipher = AES.new( aesprofilekey.decode('hex'), AES.MODE_ECB )
        profilejson = zlib.decompress( cipher.decrypt(pad(content[20:])) )
        assert(size == len(profilejson))
        #s3.put_object(Bucket=bucket, Key=keyjson, Body=profilejson[:-1], ACL='public-read')
        gzip_compress = zlib.compressobj( zlib.Z_DEFAULT_COMPRESSION, zlib.DEFLATED, zlib.MAX_WBITS | 16 )
        gzip_data = gzip_compress.compress(profilejson[:-1]) + gzip_compress.flush()
        s3.put_object(Bucket=bucket, Key=keyjson, Body=gzip_data, ContentEncoding='gzip', ContentType='binary/octet-stream', ACL='public-read')
        # debug:
        # print(profilejson[:-1])
        return response['ContentType']
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e
