#!/usr/bin/python
#import sys
import boto3
import datetime
from Crypto import Random
from Crypto.Cipher import AES
import argparse
import base64
from argparse import Namespace
from keypot_exceptions.KeypotError import KeypotError

#VERSION
keypot_version='Keypot-0.3'
ddb_hash_key_name='env-variable-name'

#Pads the data to suit the AES-256 encryption requirements
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
unpad = lambda s : s[0:-ord(str(s[-1]))]

#Static messages
string_empty_table='Table was empty - nothing to list!'
string_key_already_exists='Variable already exists in DynamoDB - please use the overwrite flag to add this to database.'
string_delete_failed='An issue occured while trying to delete - no ResponeMetadata received'

class Keypot():
    kms = None
    ddb = None
    boto_master_key_id = None
    ddb_table_name = None
    parameter_key = None
    parameter_value = None
    parameter_file = None
    overwrite_flag = False
    region = None
    
    def __init__(self, args):
        if args:
            if 'kms_key' in args:
                if (args['kms_key']):
                    self.boto_master_key_id=args['kms_key']
            
            if 'ddb_table' in args:
                if (args['ddb_table']):
                    self.ddb_table_name=args['ddb_table']
            
            if 'parameter_key' in args:
                if (args['parameter_key']):
                    self.parameter_key=args['parameter_key']
        
            if 'parameter_value' in args:
                if (args['parameter_value']):
                    self.parameter_value=args['parameter_value']
        
            if ('parameter_file' in args):
                if (args['parameter_file']):
                    self.parameter_file=args['parameter_file']
                    
            if ('overwrite' in args):
                if (args['overwrite']):
                    if (str(args['overwrite']).lower() == 'true'):
                        self.overwrite_flag=True
                    else:
                        self.overwrite_flag=False
                    
            if ('region' in args):
                if (args['region']):
                    self.region=args['region']
                    
            self.setup_clients()
        else:
            print('Invalid input - arguments appear to be empty!')
        
    
    def setup_clients(self):
        if self.region is not None:
            if self.region != '':
                self.ddb = boto3.client('dynamodb', region_name=self.region)
                self.kms = boto3.client('kms', region_name=self.region)
                return
    
        self.ddb = boto3.client('dynamodb')
        self.kms = boto3.client('kms')
        
        return

    #Used to encrypt locally on this machine using the key generated from KMS
    @staticmethod
    def local_encrypt(message, key, key_size=256):
        message = pad(str(message))
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(key, AES.MODE_ECB, iv)
        return iv + cipher.encrypt(message)

    #Used to decrypt locally on this machine using the key decrypted from KMS
    @staticmethod
    def local_decrypt(ciphertext, key):
        iv = ciphertext[:AES.block_size]
        cipher = AES.new(key, AES.MODE_ECB, iv)
        plaintext = cipher.decrypt(ciphertext[AES.block_size:])
        return unpad(plaintext.decode('ASCII'))

    def encrypt_and_store(self):
        #Generate a key using KMS service
        data_key = self.kms.generate_data_key(KeyId=self.boto_master_key_id,KeySpec='AES_256')
        encrypted_data_key = data_key['CiphertextBlob']
        plaintext_data_key = data_key['Plaintext']
    
        #encrypt data locally and write it to Dynamo
        encrypted_data = Keypot.local_encrypt(self.parameter_value,plaintext_data_key)
    
        self.ddb.put_item(
            TableName=self.ddb_table_name,
            Item={
                'env-variable-name': {
                    'S': self.parameter_key
                },
                'env-variable-enc-value': {
                    'B': encrypted_data
                },
                'env-variable-enc-kms-key': {
                    'B': encrypted_data_key
                }
            }
        )
    
        return

    def read_value_from_file(self):
        with open(self.parameter_file, 'r') as f:
            read_value=f.read()
        f.closed
        return read_value

    #Used to decrypt the data key pulled from DynamoDB using KMS
    def decrypt_kms_data(self, encrypted_data):
        decrypted = self.kms.decrypt(CiphertextBlob=encrypted_data)
        return decrypted

    #Pull data dictionary from DynamoDB
    def read_from_ddb(self):
        response = self.ddb.get_item(
            TableName=self.ddb_table_name,
            Key={
                'env-variable-name': {
                    'S': self.parameter_key
                }
            }
        )
        return response

    #Pull data dictionary from DynamoDB
    def list_from_ddb(self):
        response = self.ddb.scan(TableName=self.ddb_table_name,ProjectionExpression="#E",ExpressionAttributeNames={"#E": ddb_hash_key_name})
        if response['Count'] > 0:
            return response['Items']
    
        #empty table
        return(string_empty_table)
        
    
    def delete_from_ddb(self):
        #Key should always be a 'S' (String) type
        response = self.ddb.delete_item(
            TableName=self.ddb_table_name,
            Key={
                'env-variable-name': {
                    'S': self.parameter_key
                }
            }
        )
        return response

    def do_encrypt(self):
        #check if parameter already exists (only if overwrite is true, otherwise just blindly overwrite)
        if self.overwrite_flag == False:
            ddb_pull = self.read_from_ddb()
            if ddb_pull:
                if 'Item' in ddb_pull:
                    raise KeypotError(string_key_already_exists)
            
                    
    
        #reads the file from disk specified in args
        if self.parameter_file:
            self.parameter_value=self.read_value_from_file()
    
        #perform encrypt/DDB operations
        self.encrypt_and_store()
    
        return('Parameter ' + self.parameter_key + ' uploaded successfully')
    
    def do_decrypt(self):
        #Read and decrypt
        returned_variable_dict = self.read_from_ddb()
        returned_db_value = returned_variable_dict['Item']['env-variable-enc-value']['B']
        returned_db_kms_encrypted_key = returned_variable_dict['Item']['env-variable-enc-kms-key']['B']
        kms_decrypted_key = self.decrypt_kms_data(returned_db_kms_encrypted_key)['Plaintext']
        final_value = Keypot.local_decrypt(returned_db_value, kms_decrypted_key)
        return(final_value)
    
    def do_delete(self):    
        #Removes from DynamoDB based on DDB key
        delete_result = self.delete_from_ddb()
        if 'ResponseMetadata' in delete_result:
            if delete_result['ResponseMetadata']['HTTPStatusCode'] == 200:
                return('Successfully removed ' + str(self.parameter_key) + ' from ' + self.ddb_table_name)
            else:
                return('A problem occurred - unable to remove ' + str(self.parameter_key) + ' from ' + self.ddb_table_name)
        return(string_delete_failed)
    
    def do_list(self):    
        #get list of "String" key attributes from DynamoDB
        variable_list = self.list_from_ddb()    
        return variable_list

#default entry point - possible future enhancement would be to turn this into a lambda function
def keypot_cli():
    parser = {}
    action='super'
    parser[action] = argparse.ArgumentParser(description='Keypot - Encrypts, Decrypts, and Manages Secrets stored in AWS DynamoDB with KMS key')
    parser[action].add_argument('-v','--version', action='version', version=(keypot_version))
    subparser = parser['super'].add_subparsers(help='For more information and usage information, get help by using the {name} -h syntax')

    #encrypt
    action='encrypt'
    parser[action] = subparser.add_parser(action, help='Keypot Encrypt - Encrypts value in DynamoDB using KMS')
    #does not support both value and an input file, so using a mutually exclusive group
    encrypt_mutual_exclusive = parser[action].add_mutually_exclusive_group()
    encrypt_mutual_exclusive.add_argument('-f','--parameter_file', help='Location of file you want to upload (e.g. SSL private key).  One of this or parameter_value required.',required=False)
    parser[action].add_argument('-k','--kms_key', help='Name of AWS KMS Customer Master Key (ex: alias/test-key)',required=True)
    parser[action].add_argument('-p','--parameter_key', help='Name of Parameter to put into DynamoDB',required=True)
    parser[action].add_argument('-r','--region', help='Name of AWS Region to use for both KMS and DynamoDB',required=False)
    parser[action].add_argument('-t','--ddb_table', help='Name of existing DynamoDB Table to use in look-up',required=True)
    parser[action].add_argument('-o','--overwrite', action='store_true', help='Force overwrite of existing value in DynamoDB without prompting for overwrite',required=False,default=False)
    encrypt_mutual_exclusive.add_argument('-v','--parameter_value', help='Value of Parameter to put into DynamoDB.    One of this or parameter_file required.',required=False)
    parser[action].set_defaults(action=action)

    #decrypt
    action='decrypt'
    parser[action] = subparser.add_parser(action, help='Keypot Decrypt - Decrypt value in DynamoDB using KMS')
    parser[action].add_argument('-k','--kms_key', help='Name of AWS KMS Customer Master Key (ex: alias/test-key)',required=True)
    parser[action].add_argument('-p','--parameter_key', help='Name of Parameter to put into DynamoDB',required=True)
    parser[action].add_argument('-r','--region', help='Name of AWS Region to use for both KMS and DynamoDB',required=False)
    parser[action].add_argument('-t','--ddb_table', help='Name of existing DynamoDB Table to use in look-up',required=True)
    parser[action].set_defaults(action=action)

    #list
    action='list'
    parser[action] = subparser.add_parser(action, help='Keypot List - List all keys available in DynamoDB - NOT YET IMPLEMENTED')
    parser[action].add_argument('-r','--region', help='Name of AWS Region to use for both KMS and DynamoDB',required=False)
    parser[action].add_argument('-t','--ddb_table', help='Name of existing DynamoDB Table to use in look-up',required=True)
    parser[action].set_defaults(action=action)

    #delete
    action='delete'
    parser[action] = subparser.add_parser(action, help='Keypot Delete - Removes a key from DynamoDB - NOT YET IMPLEMENTED')
    parser[action].add_argument('-p','--parameter_key', help='Name of Parameter to put into DynamoDB',required=True)
    parser[action].add_argument('-r','--region', help='Name of AWS Region to use for both KMS and DynamoDB',required=False)
    parser[action].add_argument('-t','--ddb_table', help='Name of existing DynamoDB Table to use in look-up',required=True)
    parser[action].set_defaults(action=action)

    #based on sub-argument, send to correct function
    #change Namespace args back to dictionary so that we get consistent behavior between Lambda and CLI versions
    super_args = parser['super'].parse_args()
    result=None
    if "action" in vars(super_args):
        
        if super_args.action == 'encrypt':
            result=Keypot(vars(super_args)).do_encrypt()
            
        if super_args.action == 'decrypt':
            result=Keypot(vars(super_args)).do_decrypt()
            
        if super_args.action == 'list':
            list_result=Keypot(vars(super_args)).do_list()
            if list_result:
                if isinstance(list_result,str):
                    print(list_result)
                elif isinstance(list_result,list):    
                    for var in list_result:
                        print(var[ddb_hash_key_name]['S'])
                        
        if super_args.action == 'delete':
            result=Keypot(vars(super_args)).do_delete()

    if result:
        print(result)
    return

#entry point for the lambda function
#This function is to massage input to match the rest of the CLI function, and customize any output for Lambda consumption
def keypot_lambda_handler(event, context):
    if ('action' not in event) or ('options' not in event):
        raise KeypotError('Invalid Input - missing either action or options!')
    
    lambda_keypot=Keypot(event['options'])

    #ENCRYPT
    if event['action'] == 'encrypt':
        #Put note about using file method - will implement an "upload from S3" option
        if ('file' in event['options']):
            return('File upload is not supported by Lambda invocation.  Please use upload from S3')
        output_string=lambda_keypot.do_encrypt()
        return(output_string)

    #DECRYPT
    if event['action'] == 'decrypt':
        output_string=lambda_keypot.do_decrypt()
        return output_string

    #LIST
    if event['action'] == 'list':
        variable_list=lambda_keypot.do_list()
        output_string=''
        if variable_list:
            for var in variable_list:
                output_string+=var[ddb_hash_key_name]['S']
                output_string+='\n'
        return output_string

    #DELETE
    if event['action'] == 'delete':
        output_string=lambda_keypot.do_delete()
        return output_string

#primary method when executed directly
if __name__ == '__main__':
    keypot_cli()
