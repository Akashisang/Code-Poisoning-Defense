"""
/*****************************************************************************
 * Copyright (c) 2016, Palo Alto Networks. All rights reserved.              *
 *                                                                           *
 * This Software is the property of Palo Alto Networks. The Software and all *
 * accompanying documentation are copyrighted.                               *
 *****************************************************************************/

Copyright 2016 Palo Alto Networks

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import print_function

import boto3
import botocore
import json
import logging
import time
import decimal
import uuid
import logging
import urllib2
import urllib
import ssl
import xml.etree.ElementTree as et
from httplib import HTTPSConnection
import ssl

logger = logging.getLogger()

# Enable creation of S3 bucket per-ASG
enable_s3=False

######## BOTO3 Clients and Resources #############
s3 = boto3.client('s3')
asg = boto3.client('autoscaling')
ec2 = boto3.resource('ec2')
ec2_client = ec2.meta.client
lambda_client = boto3.client('lambda')
iam = boto3.client('iam')
events_client = boto3.client('events')
cloudwatch = boto3.client('cloudwatch')
elb = boto3.client('elb')
elbv2 = boto3.client('elbv2')
sqs = boto3.client('sqs')
sns = boto3.client('sns')


def purge_stack_queue(queue_url):
    """
    Delete all the messages in the queue
    
    :param queue_url: URL of the queue
    :return: None
    """
    sqs.purge_queue(QueueUrl=queue_url)

def set_queue_attributes(queue_url, retention_period):
    """
    Set the queue attributes 
    
    :param queue_url: URL of the queue
    :param retention_period: Duration of time that the message
                             will be retained for.
    :return: None
    """
    try:         
        sqs.set_queue_attributes(QueueUrl=queue_url,
                                 Attributes={
                                    'MessageRetentionPeriod': str(retention_period)
                                }
        )
        
    except Exception, e:
        logger.exception('Unable to set queue attributes')
        

def get_from_sqs_queue(queue_url, visiblity_timeout=10, waittimes_seconds=5):
    """
     Retrieve data from a queue 
     
     :param queue_url: URL of the queue
     :param visiblity_timeout: The duration during which the message will not 
                               be available to other consumers
     :param waittimes_seconds: Wait timeout
     :return: None
    """
    stack_msg = None
    stack_attrs = None

    for retry in range(0, 10):
        time.sleep(5) 
        try:
            logger.info('Retrieve data from queue: {}'.format(queue_url))
            response = sqs.receive_message(QueueUrl=queue_url, 
                                       MaxNumberOfMessages=10, 
                                       AttributeNames=['All'],
                                       MessageAttributeNames=['All'], 
                                       VisibilityTimeout=visiblity_timeout,
                                       WaitTimeSeconds=waittimes_seconds)

            logger.info('Retrieved response: {}'.format(response))

            for message in response.get('Messages', []):
                if message:
                    msg_attr = message.get('MessageAttributes', None)
                    handle = message.get('ReceiptHandle', None)
                    if msg_attr and 'panw-fw-stack-params' in msg_attr.keys():
                        stack_msg = message.get('Body', None)
                        logger.info('Stack message: {}'.format(stack_msg))
                    attrs = message.get('Attributes')
                    senttimestamp = attrs.get('SentTimestamp', None)
                    logger.info('msg details:: msg: {} ts: {} rh: {}'.format(stack_msg, senttimestamp, handle))
                    return (stack_msg, senttimestamp, handle) 
        except Exception, e:
            logger.exception('Exception occurred retrieving message from queue: {}'.format(e))

    
    return None, None, None

def send_message_to_queue(queue_url, str_message):
    """
    Send a message on the specified queue.
    
    :param queue_url: The URL of the queue 
    :param str_message: Message to send to the queue
    :return:  None
    """

    logger.info("Sending message to queue: {}".format(str_message))
    ret_dict = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=str_message,
        MessageAttributes={
            'panw-fw-stack-params': {
                'StringValue': '1000',
                'DataType' : 'String'
            }
        }
    )
    logger.info("Response data from sending message to queue: {}".format(ret_dict))

def delete_message_from_queue(queue_url, receipt_handle):
    """
    Delete a message from the SQS queue.
    
    :param queue_url: The URL of the queue 
    :param receipt_handle: The receipt handle of the message 
    :return: None
    """
    logger.info('Attempting to delete the message from the queue')

    try:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except Exception, e:
        logger.exception('Exception occurred while attemption to delete message from the queue.')

def describe_load_balancers(ilb_name):
    """
    List (describe) all the load balancers 
    
    :param ilb_name: 
    :return: dict or None
    """
    try:
        response = elb.describe_load_balancers(LoadBalancerNames=[ilb_name])
        for i in response['LoadBalancerDescriptions']:
            if i['LoadBalancerName'] == ilb_name:
                #Classic load balancer found
                return response
    except Exception as e:
         logger.info("[DescribeLB Classic]: {}".format(e))

    try:
        response = elbv2.describe_load_balancers(Names=[ilb_name])
        for i in response['LoadBalancers']:
            if i['LoadBalancerName'] == ilb_name:
                #application load balancer found
                #Munge the elbv2 response dictionary to look like elb response dict
                response['LoadBalancerDescriptions'] = response.pop('LoadBalancers')
                return response
    except Exception as e:
         logger.error("[DescribeLB App]: {}".format(e))

    return None

def delete_load_blanacer(ilb_name):
    """
    Delete a deployed Internal Load Balancer
    :param ilb_name: 
    :return: None or str
    """
    response = describe_load_balancers(ilb_name)
    for i in response['LoadBalancerDescriptions']:
        if 'LoadBalancerName' in i:
            elb.delete_load_balancer(LoadBalancerName=ilb_name)
        elif 'LoadBalancerArn' in i:
            elbv2.delete_load_blanacer(LoadBalancerArn=i['LoadBalancerArn'])
        else:
            return 'FAIL'

def substring_after(s, delim):
    """
    
    :param s: 
    :param delim: 
    :return: 
    """
    return s.partition(delim)[2]

def fix_unicode(data):
    """
        Method to convert opaque data from unicode to utf-8
        :param data: Opaque data
        :return: utf-8 encoded data
    """
    if isinstance(data, unicode):
        return data.encode('utf-8')
    elif isinstance(data, dict):
        data = dict((fix_unicode(k), fix_unicode(data[k])) for k in data)
    elif isinstance(data, list):
        for i in xrange(0, len(data)):
            data[i] = fix_unicode(data[i])

    return data

def fix_subnets(data1):
    """
    
    :param data1: 
    :return: 
    """
    data=str(data1)
    data=data.replace("'", "")
    data=data.replace("[", "")
    data=data.replace("]", "")
    return data
    
def get_sched_func_name(stackname):
    """
    
    :param stackname: 
    :return: 
    """
    name=stackname+"-lambda-sched-event"
    return name[-63:len(name)]

def get_asg_name(stackname, ip_address):
    """
    Convenience method to generate the ASG name 
    as a function of the stackname and ip address 
    
    :param stackname: 
    :param ip_address: 
    :return: str 
    """
    name = stackname + '_ASG_' + str(ip_address).replace(".", "-")
    return name[-63:len(name)]

def get_asg_name1(stackname):
    """
    
    :param stackname: 
    :return: 
    """
    name = stackname + '_ASG_'
    return name[-63:len(name)]

def get_lc_name(stackname, ip_address):
    """
    Convenience method to generate the launch configuration 
    name as a function of the stackname and the ip address 
    :param stackname: 
    :param ip_address: 
    :return: str
    """
    name = stackname + '_ASG_LC_' + str(ip_address).replace(".", "-")
    return name

def get_cw_name_space(stackname, asg_name):
    """
    Retrieve the name of the cloud watch namespace
    :param stackname: 
    :param asg_name: 
    :return: str
    """
    name = asg_name
    return name[-63:len(name)]

def get_s3_bucket_name(stackname, ilbname, ip_address):
    """
    Generate the name of the original PAN S3 bucket. 
    
    .. note:: This is used to identify the S3 bucket being 
              used for the deployment (i.e if this is a custom
              S3 bucket owned by the customer the PAN S3 bucket).
    :param stackname: 
    :param ilbname: 
    :param ip_address: 
    :return: str
    """
    logger.info('Stackname: ' + stackname + ' IP: ' + ip_address)
    name = stackname + '-bstrap-' + str(ip_address.replace(".", "-"))
    name=name.lower()
    return name[-63:len(name)]

def get_table_name(stackname, region):
    """
    
    :param stackname: 
    :param region: 
    :return: 
    """
    name=stackname+"-"+region
    return name



#DUMMY FUNC -- NOT USED
def get_s3_bucket_name1(stackname, ilbname, ip_address):
    if enable_s3 == False:
        return "enable_s3_is_false"

    first=stackname.split('-')
    try:
        response=elbv2.describe_load_balancers(Names=[ilbname])
    except Exception as e:
         logger.info("[S3 Delete Bucket]: {}".format(e))
         return "s3-bucket-not-found"

    ilb=first[0] + str(ip_address.replace(".", "-"))
    logger.info('ILB: ' + ilb)
    cnt=0
    for i in response['LoadBalancers']:
        logger.info('DNSName: ' + i['DNSName'])
        dnsname=i['DNSName']
        list=dnsname.split('.')
        ilb=ilb + list[0]
        cnt = cnt + 1
 
    logger.info('ILB: ' + ilb)
    name=""
    if cnt == 0:
       logger.critical('Problem with S3 bucketnaming: Didnt find ILB' + ilb)
       name = stackname + '-bstrap-' + str(ip_address.replace(".", "-"))
    elif cnt > 1:
       logger.crictical('Problem with S3 bucketnaming: ' + ilb)
       name = stackname + '-bstrap-' + str(ip_address.replace(".", "-"))
    else:
       name=ilb

    name=name.lower()
    return name[-63:len(name)]

def get_lambda_cloud_watch_func_name(stackname, asg_name, instanceId):
    """
    Generate the name of the cloud watch metrics as a function 
    of the ASG name and the instance id.
    :param stackname: 
    :param asg_name: 
    :param instanceId: 
    :return: str
    """
    name = asg_name + '-cwm-' + str(instanceId)
    return name[-63:len(name)]

def get_event_rule_name(stackname, instanceId):
    """
    Generate the name of the event rule. 
    
    :param stackname: 
    :param instanceId: 
    :return: str
    """
    name = stackname + '-cw-event-rule-' + str(instanceId)
    return name[-63:len(name)]

def get_statement_id(stackname, instanceId):
    """
    
    :param stackname: 
    :param instanceId: 
    :return: 
    """
    name = stackname + '-cw-statementid-' + str(instanceId)
    return name[-63:len(name)]

def get_target_id_name(stackname, instanceId):
    """
    
    :param stackname: 
    :param instanceId: 
    :return: 
    """
    name = stackname + '-lmda-target-id' + str(instanceId)
    return name[-63:len(name)]

def choose_subnet(subnet, AvailabilityZone):
    """
    Method to identify the subnet id based upon the 
    availability zone. 
    
    :param subnet: 
    :param AvailabilityZone: 
    :return: 
    """
    logger.info('Choose Subnets: ')
    logger.info(subnet)
    list_subnets=subnet.split(",")
    response=ec2_client.describe_subnets(SubnetIds=list_subnets)
    ret_subnets=""
    for i in response['Subnets']:
        if i['AvailabilityZone'] == AvailabilityZone:
            if ret_subnets == "":
                ret_subnets=i['SubnetId']
            else:
                ret_subnets= ret_subnets + "," + i['SubnetId']

    logger.info('Return Subnets for AZ: ' + AvailabilityZone + ' Subnets: ' + ret_subnets)
    return ret_subnets

def getASGTag(rid, key):
    """
    Set tags on a specified auto scale group.
    
    .. note:: This method is important from the perspective
              that it allows the lambda function code to 
              distinguish ```PAN-FW``` deployed ASG's from 
              other ASG's that might already exist in the
              customer VPC.
    
    :param rid: The name of the ASG
    :param key: The tag to retrieve
    :return: None or str
    """
    logger.info('Getting all the tags for rid: ' + rid)
    try:
        response=asg.describe_tags(Filters=[{'Name': 'auto-scaling-group', 'Values': [rid]}])
    except Exception as e:
         logger.info("[Failed to describe tag]: {}".format(e))
         return None

    logger.info(response)
    for i in response['Tags']:
        if i['Key'] == key:
            return i['Value']

    return None

def setASGTag(rid, key, value):
    """
    Set ```PAN-FW``` specific tags on an ASG. 
    
    .. note:: This method is important from the perspective
              that it allows the lambda function code to 
              distinguish ```PAN-FW``` deployed ASG's from 
              other ASG's that might already exist in the
              customer VPC.
    
    :param rid: Name of the ASG
    :param key: Tag 
    :param value: Tag Value
    :return: None
    """
    try:
        asg.create_or_update_tags(Tags=[{'ResourceId': rid, 'ResourceType': "auto-scaling-group", 'Key': key, 'Value': value, 'PropagateAtLaunch': False}])
    except Exception as e:
         logger.info("[Failed to Set Tag]: {}".format(e))
    return

def runCommand(gcontext, cmd, gwMgmtIp, api_key):
    """
    
    Method to run generic API commands against a PAN Firewall.
    
    .. note:: This is a generic method to interact with PAN
              firewalls to execute api calls. 
    
    :param gcontext: SSL Context
    :param cmd: Command to execute
    :param gwMgmtIp: Management IP of the PAN FW
    :param api_key: API key of the Firewall
    :return: None or str
    """
    try:
        response = urllib2.urlopen(cmd, context=gcontext, timeout=5).read()
        #print("[RESPONSE] in send command: {}".format(response))
    except Exception as e:
         logger.error("[RunCommand Response Fail]: {}".format(e))
         logger.error("[RunCommand Response Fail]: {}".format(e))
         return None

    resp_header = et.fromstring(response)

    if resp_header.tag != 'response':
        logger.error("[ERROR]: didn't get a valid response from Firewall command: " + cmd)
        logger.error("[ERROR]: didn't get a valid response from Firewall")
        return None

    if resp_header.attrib['status'] == 'error':
        logger.error("[ERROR]: Got an error for the command: " + cmd)
        logger.error("[ERROR]: Got an error for the command: " + cmd)
        return None

    if resp_header.attrib['status'] == 'success':
        return response

    return None

def send_command(conn, req_url):
    """
    An alternative interface to interact with the PAN FW's
    
    :param conn: 
    :param req_url: 
    :return: dict
    """
    conn.request("POST", req_url)
    resp = conn.getresponse()
    msg = resp.read()
    
    if resp.status == 200 :
        logger.info('[200 OK] CMD: ' +  req_url + '    MSG in send_command(): ' + msg)
        root = et.fromstring(msg)
        if root.attrib['status'] == 'success':
            logger.info('Success response status. Data: {} Type: {}'.format(str(root), type(root)))
            return {'result': True, 'data': root}
        elif root.attrib['status'] == 'error':
            logger.info('Command succeeded but the status is error.')
            conn.close()
            logger.info('Error response status. Data: {} Type: {}'.format(str(root), type(root)))
            return {'result': False, 'data': root}
        else:
            conn.close()
            logger.error('Failure received in send_command for URL: ' + str(req_url))
            return {'result': False, 'data': msg}
    else:
        logger.error('Status is not 200 in send_command for URL: ' + str(req_url))
        logger.info('CMD: ' +  req_url + '    MSG in send_command(): ' + msg)
        conn.close()
        return {'result': False, 'data': None}

def remove_device(stackname, remove, PanoramaIP, api_key, dev_group, tp_group, serial_no, gwMgmtIp):
    """
    Method to remove a device from Panorama.
    
    :param stackname: 
    :param remove: 
    :param PanoramaIP: 
    :param api_key: 
    :param dev_group: 
    :param tp_group: 
    :param serial_no: 
    :param gwMgmtIp: 
    :return: None or str
    """
    conn = HTTPSConnection(PanoramaIP, 443, timeout=10, context=ssl._create_unverified_context())

    if dev_group != "":
        cmd_show_device_group = "/api/?type=op&cmd=<show><devicegroups><name>%s</name></devicegroups></show>&key=%s"%(dev_group, api_key)
        response = send_command(conn, cmd_show_device_group)
        if response['result'] == False:
            conn.close()
            logger.error('Panorama: Fail to execute Panorama API show dg for device: ' + gwMgmtIp)
            return None

        logger.info('show dg: ' + str(response))
        #data = response['data'].findall('./result/devices/*')
        data = response['data'].findall('./result/devicegroups/entry/devices/*')

        for entry in data:
            ip_tag = entry.find('ip-address')
            if ip_tag is None:
                print('ip_tag: ' + str(ip_tag))
                pass
            else:
                ip_addr = ip_tag.text
                if ip_addr == gwMgmtIp:
                    serial_no = entry.attrib.get('name')
                    logger.info('entry: ' + str(entry.tag) + ' ' + str(entry.text) + ' ' + str(entry.attrib))
                    logger.info('serial_no in show dg: ' + str(serial_no))

        if serial_no == "":
            logger.error('Panorama: Fail to find serial number for device: ' + gwMgmtIp)
        elif remove == True:
            logger.info('show dg: serial number is: (' + str(serial_no) + ')')
            cmd_delete_from_devgroup = "/api/?type=config&action=delete&xpath=/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='%s']/devices/entry[@name='%s']&key=%s"%(dev_group, serial_no, api_key)
            response = send_command(conn, cmd_delete_from_devgroup)
            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API delete dg for device: ' + gwMgmtIp)
                return None

    if tp_group != "":
        if serial_no == "":
            cmd_show_template = "/api/?type=op&cmd=<show><templates><name>%s</name></templates></show>&key=%s"%(tp_group, api_key)
            response = send_command(conn, cmd_show_template)
            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API show template for device: ' + gwMgmtIp)
                return None

            logger.info('show tpl: response: ' + str(response))
            #data = response['data'].findall('./result/devices/*')
            data = response['data'].findall('./result/templates/entry/devices/*')

            for entry in data:
                ip_tag = entry.find('ip-address')
                if ip_tag is None:
                    print('ip_tag: ' + str(ip_tag))
                    pass
                else:
                    ip_addr = ip_tag.text
                    if ip_addr == gwMgmtIp:
                        serial_no = entry.attrib.get('name')
                        logger.info('entry: ' + str(entry.tag) + ' ' + str(entry.text) + ' ' + str(entry.attrib))
                        logger.info('serial_no in show tpl: ' + str(serial_no))

            if serial_no == "":
                logger.error('Panorama: Fail to serial number in show template for device: ' + gwMgmtIp)


        if serial_no != "" and remove == True:
            cmd_delete_from_tpgroup = "/api/?type=config&action=delete&xpath=/config/devices/entry[@name='localhost.localdomain']/template/entry[@name='%s']/devices/entry[@name='%s']&key=%s"%(tp_group, serial_no, api_key)
            #send and make sure it is successful
            response = send_command(conn, cmd_delete_from_tpgroup)

            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API delete template for device: ' + gwMgmtIp)
                return None

    if serial_no == "":
        cmd_show_all_devices = "/api/?type=op&cmd=<show><devices><all></all></devices></show>&key=%s"%(api_key)
        response = send_command(conn, cmd_show_all_devices)
        if response['result'] == False:
            conn.close()
            logger.error('Panorama: Fail to execute Panorama API show devices for device: ' + gwMgmtIp)
            return None

        logger.info('show all devices: response: ' + str(response))
        data = response['data'].findall('./result/devices/*')

        for entry in data:
            ip_tag = entry.find('ip-address')
            if ip_tag is None:
                pass
            else:
                ip_addr = ip_tag.text
                if ip_addr == gwMgmtIp:
                    serial_no = entry.attrib.get('name')

        if serial_no == "":
            logger.error('Panorama: No registered device found with IP address: ' + gwMgmtIp)
            conn.close()
            return "Done"

    if remove == False:
        conn.close()
        return serial_no

    cmd_delete_device = "/api/?type=config&action=delete&xpath=/config/mgt-config/devices/entry[@name='%s']&key=%s"%(serial_no, api_key)
    response = send_command(conn, cmd_delete_device)
    if response['result'] == False:
        conn.close()
        logger.error('Panorama: Fail to execute Panorama API delete device for device: ' + gwMgmtIp)
        return None

    logger.info('delete unmanaged device: response: ' + str(response))
    cmd_commit = "/api/?type=commit&cmd=<commit></commit>&key="+api_key
    response = send_command(conn, cmd_commit)

    if response['result'] == False:
        conn.close()
        logger.error('Panorama: Fail to execute Panorama API commit for device: ' + gwMgmtIp)
        return None

    job_id=""
    data = response['data'].findall('./result/*')
    for entry in data:
        if entry.tag == 'job':
            job_id = entry.text

    if job_id == "":
        conn.close()
        return None

    logger.info('Commit is being done')
    cmd_commit_success  = "/api/?type=op&cmd=<show><jobs><id>"+job_id+"</id></jobs></show>&key="+api_key
    response = send_command(conn, cmd_commit_success)

    if response['result'] == False:
        conn.close()
        logger.error('Panorama: Fail to execute Panorama API show jobs for device: ' + gwMgmtIp)
        return None

    conn.close()
    return "Done"

def get_ssl_context():  
    """
    Create default ssl context
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options = ssl.PROTOCOL_TLSv1_2
    return ctx

def execute_api_request(gwMgmtIp, port, cmd):
    """
    Execute API requests against the FW.
    :param gwMgmtIp: 
    :param port: 
    :param cmd: 
    :return: 
    """
    conn = None
    conn = HTTPSConnection(gwMgmtIp, port, timeout=10, context=ssl._create_unverified_context())
    response = None
    ex_occurred = False
    try:
        response = send_command(conn, cmd)
    except Exception, e:
        logger.exception('Executing API Request. Cmd: {} {}'.format(cmd, e))
        ex_occurred = True

    if ex_occurred:
        ctx = get_ssl_context()
        logger.warning('Exception occurred in the first attempt. Attempting again with default ssl context')
        response = None
        ctx = get_ssl_context()
        conn = HTTPSConnection(gwMgmtIp, 443, timeout=10, context=ctx)
        response = send_command(conn, cmd)

    conn.close()
    return response

def get_device_serial_no(instanceId, gwMgmtIp, fwApiKey):
    """
    Retrieve the serial number from the FW.

    @param gwMgmtIP: The IP address of the FW
    @type: ```str```
    @param fwApiKey: Api key of the FW
    @type: ```str```

    @return The serial number of the FW
    @rtype: ```str```
    """

    serial_no = None
    if gwMgmtIp is None:
        logger.error('Firewall IP could not be found. Can not interact with the device')
        return False

    logger.info('Retrieve the serial number from FW {} with IP: {}'.format(instanceId, gwMgmtIp))

    cmd_show_system_info = "/api/?type=op&key={}&cmd=<show><system><info/></system></show>".format(fwApiKey)
    response = execute_api_request(gwMgmtIp, 443, cmd_show_system_info)

    if response['result'] == False:
            logger.error('PAN Firewall: Fail to execute the show system info command for device: {} with IP: {}'.format(instanceId, gwMgmtIp))
            result = response['data'].findall(".//line")
            for msg in result:
                error_msg = msg.text
                logger.error('Reason for failure: {}'.format(error_msg))
            return False

    serial_info = response['data'].findall(".//serial")
    for info in serial_info:
        serial_no = info.text

    if not serial_no:
        logger.error("Unable to retrieve the serial number from device: {} with IP: {}".format(instanceId, gwMgmtIp))

    return serial_no

def deactivate_fw_license(instanceId, gwMgmtIp, fwApiKey):
    """
    Call the FW to deactivate the license from the licensing 
    server

    @param gwMgmtIP: The IP address of the Firewall
    @type ```str```
    @param fwApiKey: The Api key of the FW
    @type ```str```

    @return Api call status
    @rtype bool
    """
    if gwMgmtIp is None:
        logger.error('Firewall IP could not be found. Can not interact with the device')
        return False

    logger.info('Deactivate and the license for FW: {} with IP: {}'.format(instanceId, gwMgmtIp))
    
    deactivate_license_cmd = "/api/?type=op&key={}&cmd=<request><license><deactivate><VM-Capacity><mode>auto</mode></VM-Capacity></deactivate></license></request>".format(fwApiKey)
    response = execute_api_request(gwMgmtIp, 443, deactivate_license_cmd)

    if response['result'] == False:
        logger.error('Failed to execute deactivate license command for device: {} with IP: {}'.format(instanceId, gwMgmtIp))
        result = response['data'].findall(".//line")
        for msg in result:
            error_msg = msg.text
            logger.error('Reason for failure: {}'.format(error_msg))
            return False
    return True

def shutdown_fw_device(instanceId, gwMgmtIp, fwApiKey):
    """
    Shutdown the firewall device 
    
    :param instanceId: 
    :param gwMgmtIp: 
    :param fwApiKey: 
    :return: bool
    """
    if gwMgmtIp is None:
        logger.error('Firewall IP could not be found. Can not interact with the device')
        return False

    logger.info('Shutdown the firewall device : {} with IP: {}'.format(instanceId, gwMgmtIp))
    
    shutdown_cmd = "/api/?type=op&key={}&cmd=<request><shutdown><system></system></shutdown></request>".format(fwApiKey)

    response = execute_api_request(gwMgmtIp, 443, shutdown_cmd)
    
    success_msg = "Command succeeded with no output"
    if not response['result']:
        if not response['data']:
            return False
        try:
            result = response['data'].findall(".//line")
            for msg in result:
                error_text = msg.text
                if success_msg in error_text:
                    logger.info('Successfully shutdown the firewall device: {} with IP: {}'.format(instanceId, gwMgmtIp))
                    break 
                else:
                    logger.error('Fail to execute shutdown command for device: {} with IP: {}'.format(instanceId, gwMgmtIp))
                    logger.error("Response from the shutdown command is: {}".format(error_msg))
                    return False
        except Exception as e:
            logger.exception("{}".format(e))
            return False
    return True

def set_deactivate_api_key(instanceId, gwMgmtIp, fwApiKey, deactivateApiKey):
    """
    Setup the deactivate api key to allow the FW deactivate sequence
    :param instanceId: 
    :param gwMgmtIp: 
    :param fwApiKey: 
    :param deactivateApiKey: 
    :return: bool
    """
    if gwMgmtIp is None:
        logger.error('Firewall IP could not be found. Can not interact with the device')
        return False

    logger.info('Setup the deactivate API Key on the FW for device {} with IP: {}'.format(instanceId, gwMgmtIp))
    
    deactivate_cmd = "/api/?type=op&key={}&cmd=<request><license><api-key><set><key>{}</key></set></api-key></license></request>".format(fwApiKey, deactivateApiKey)
    response = execute_api_request(gwMgmtIp, 443, deactivate_cmd)
    
    if response['result'] == False:
        logger.error('PAN Firewall: Fail to set deactivate Api Key for device: {} with IP: {}'.format(instanceId, gwMgmtIp))
        result = response['data'].findall(".//line")
        for msg in result:
            error_msg = msg.text
            logger.error('Reason for failure: {}'.format(error_msg))
            return False
    return True

def remove_fw_from_panorama(stackname, instanceId, KeyPANWPanorama, gwMgmtIp, PanoramaIP, PanoramaDG, PanoramaTPL):
    """
    
    :param stackname: 
    :param instanceId: 
    :param KeyPANWPanorama: 
    :param gwMgmtIp: 
    :param PanoramaIP: 
    :param PanoramaDG: 
    :param PanoramaTPL: 
    :return: 
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.info('Panorama: Removing PANW Firewall IP : ' + str(instanceId) + ' from Panorama IP: ' + str(PanoramaIP))

    if gwMgmtIp is None:
        logger.error('Firewall IP could not be found. Can not remove it from Panorama')
        return False

    print('Panorama: Firewall IP address to remove from Panorama is: ' + gwMgmtIp)

    conn = HTTPSConnection(PanoramaIP, 443, timeout=10, context=ssl._create_unverified_context())

    serial_no = ""
    dev_group = PanoramaDG
    tp_group = PanoramaTPL
    api_key = KeyPANWPanorama
    connected="yes"

    if dev_group != "":
        cmd_show_device_group = "/api/?type=op&cmd=<show><devicegroups><name>%s</name></devicegroups></show>&key=%s"%(dev_group, api_key)
        response = send_command(conn, cmd_show_device_group)
        if response['result'] == False:
            conn.close()
            logger.error('Panorama: Fail to execute Panorama API show dg for device: ' + gwMgmtIp)
            return False
        
        logger.info('show dg: ' + str(response))
        #data = response['data'].findall('./result/devices/*')
        data = response['data'].findall('./result/devicegroups/entry/devices/*')

        for entry in data:
            ip_tag = entry.find('ip-address')
            if ip_tag is None:
                logger.info('ip_tag: ' + str(ip_tag))
                pass
            else:
                ip_addr = ip_tag.text
                if ip_addr == gwMgmtIp:
                    serial_no = entry.attrib.get('name')
                    logger.info('entry: ' + str(entry.tag) + ' ' + str(entry.text) + ' ' + str(entry.attrib))
                    logger.info('serial_no in show dg: ' + str(serial_no))
                    state= entry.find('connected')
                    if state is not None:
                        connected=state.text
                        logger.info('show dg device state tag value: ' + str(connected))
                        if str(connected) == "yes":
                            logger.error('Device is still in connected state in show dg: ' + gwMgmtIp)
                            conn.close()
                            return False

        if serial_no == "":
            logger.error('Panorama: Fail to find serial number for device: ' + gwMgmtIp)
        else:
            logger.info('show dg: serial number is: (' + str(serial_no) + ')')
            cmd_delete_from_devgroup = "/api/?type=config&action=delete&xpath=/config/devices/entry[@name='localhost.localdomain']/device-group/entry[@name='%s']/devices/entry[@name='%s']&key=%s"%(dev_group, serial_no, api_key)
            response = send_command(conn, cmd_delete_from_devgroup)
            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API delete dg for device: ' + gwMgmtIp)
                return False

    if tp_group != "":
        if serial_no == "":
            cmd_show_template = "/api/?type=op&cmd=<show><templates><name>%s</name></templates></show>&key=%s"%(tp_group, api_key)
            response = send_command(conn, cmd_show_template)
            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API show template for device: ' + gwMgmtIp)
                return False

            logger.info('show tpl: response: ' + str(response))
            #data = response['data'].findall('./result/devices/*')
            data = response['data'].findall('./result/templates/entry/devices/*')

            for entry in data:
                ip_tag = entry.find('ip-address')
                if ip_tag is None:
                    logger.info('ip_tag: ' + str(ip_tag))
                    pass
                else:
                    ip_addr = ip_tag.text
                    if ip_addr == gwMgmtIp:
                        serial_no = entry.attrib.get('name')
                        logger.info('entry: ' + str(entry.tag) + ' ' + str(entry.text) + ' ' + str(entry.attrib))
                        logger.info('serial_no in show tpl: ' + str(serial_no))
                        state= entry.find('connected')
                        if state is not None:
                            connected=state.text
                            logger.info('show tpl device state tag value: ' + str(connected))
                            if str(connected) == "yes":
                                logger.error('Device is still in connected state in show tpl: ' + gwMgmtIp)
                                conn.close()
                                return False

            if serial_no == "":
                logger.error('Panorama: Fail to serial number in show template for device: ' + gwMgmtIp)


        if serial_no != "":
            cmd_delete_from_tpgroup = "/api/?type=config&action=delete&xpath=/config/devices/entry[@name='localhost.localdomain']/template/entry[@name='%s']/devices/entry[@name='%s']&key=%s"%(tp_group, serial_no, api_key)
            #send and make sure it is successful
            response = send_command(conn, cmd_delete_from_tpgroup)

            if response['result'] == False:
                conn.close()
                logger.error('Panorama: Fail to execute Panorama API delete template for device: ' + gwMgmtIp)
                return False

    if serial_no == "":
        cmd_show_all_devices = "/api/?type=op&cmd=<show><devices><all></all></devices></show>&key=%s"%(api_key)
        response = send_command(conn, cmd_show_all_devices)
        if response['result'] == False:
            conn.close() 
            logger.error('Panorama: Fail to execute Panorama API show devices for device: ' + gwMgmtIp)
            return False

        logger.info('show all devices: response: ' + str(response))
        data = response['data'].findall('./result/devices/*')
                    
        for entry in data:
            ip_tag = entry.find('ip-address')
            if ip_tag is None:
                pass
            else:
                ip_addr = ip_tag.text
                if ip_addr == gwMgmtIp:
                    serial_no = entry.attrib.get('name')
                    state= entry.find('connected')
                    if state is not None:
                        connected=state.text
                        logger.info('show dg device state tag value: ' + str(connected))
                        if str(connected) == "yes":
                            logger.error('Device is still in connected state in show dg: ' + gwMgmtIp)
                            conn.close()
                            return False

        if serial_no == "":
            logger.error('Panorama: No registered device found with IP address: ' + gwMgmtIp)
            conn.close()
            return True
            
    cmd_delete_device = "/api/?type=config&action=delete&xpath=/config/mgt-config/devices/entry[@name='%s']&key=%s"%(serial_no, api_key)
    response = send_command(conn, cmd_delete_device)
    if response['result'] == False:
        conn.close()
        logger.error('Panorama: Fail to execute Panorama API delete device for device: ' + gwMgmtIp)
        return False
            
    logger.info('delete unmanaged device: response: ' + str(response))
    cmd_commit = "/api/?type=commit&cmd=<commit></commit>&key="+api_key
    response = send_command(conn, cmd_commit)
                     
    if response['result'] == False:
        conn.close() 
        logger.error('Panorama: Fail to execute Panorama API commit for device: ' + gwMgmtIp)
        return False
            
    job_id=""
    data = response['data'].findall('./result/*')
    for entry in data:
        if entry.tag == 'job':
            job_id = entry.text
        
    if job_id is None:
        conn.close()
        logger.error('Job id could not be found')
        return False

    logger.info('Commit is being done')
    cmd_commit_success  = "/api/?type=op&cmd=<show><jobs><id>"+job_id+"</id></jobs></show>&key="+api_key
    response = send_command(conn, cmd_commit_success)

    if response['result'] == False:
        conn.close()
        logger.error('Panorama: Fail to execute Panorama API show jobs for device: ' + gwMgmtIp)
        return False

    conn.close()

    #try:
    #    region="us-west-2"
    #    dynamodb = boto3.resource('dynamodb', region_name=region)
    #    table = dynamodb.Table(stackname)
    #    response=table.put_item(Item={'TYPE': 'Panorama', "SerialNo": serial_no, "IPAddress": gwMgmtIp, 'PanoramaIP': PanoramaIP,
    #		'PanoramaDG': dev_group, 'PanoramaTPL': tp_group})
    #except Exception as e:
    #    logger.info("[DynamoDB Remove device from Panorama]: {}".format(e))

    return True

def release_eip(stackname, instanceId):
    """
    
    :param stackname: 
    :param instanceId: 
    :return: 
    """
    logger.info('Releasing Elastic IPs...')
    try:
        response=ec2_client.describe_network_interfaces(Filters=[{'Name': "attachment.instance-id", 'Values': [str(instanceId)]}])
        logger.info(response)
        for i in response['NetworkInterfaces']:
            eniId=i['NetworkInterfaceId']
            try:
                ass=i['PrivateIpAddresses']
                strass=str(ass)
                if strass.find("AssociationId") <= 0:
                    continue

                Attachment=i['Attachment']
                aId=i['PrivateIpAddresses'][0]['Association']['AllocationId']
                logger.info('EIP Attachment ID: ' + aId + ' DeviceIndex: ' +  str(Attachment['DeviceIndex']))
                gwMgmtIp=i['PrivateIpAddresses'][0]['Association']['PublicIp']
                ec2_client.disassociate_address(PublicIp=gwMgmtIp)
                ec2_client.release_address(AllocationId=aId)
            except Exception as e:
                logger.info("[Release EIP Loop each ENI]: {}".format(e))

    except Exception as e:
         logger.error("[Release EIP]: {}".format(e))

    return

def random_string(string_length=10):
    """
    
    :param string_length: 
    :return: 
    """
    random = str(uuid.uuid4())
    random = random.replace("-","")
    return random[0:string_length]

def common_alarm_func_del(alarmname):
    """
    
    :param alarmname: 
    :return: 
    """
    a1=alarmname + '-high'
    cloudwatch.delete_alarms(AlarmNames=[a1])

    a1=alarmname + '-low'
    cloudwatch.delete_alarms(AlarmNames=[a1])
    return

def create_cw_metrics_lambda(Input, IamLambda, eniId, NATGateway, SubnetIDLambda, sgv):
    """
    Method do deploy the ```metrics``` lambda function, which in turn handles the metrics 
    collection and sending the same to the cloud watch service. 
    
    :param Input: 
    :param IamLambda: 
    :param eniId: 
    :param NATGateway: 
    :param SubnetIDLambda: 
    :param sgv: 
    :return: 
    """
    global asg_name
    global stackname

    stackname=Input['StackName']
    instanceId=Input['EC2InstanceId']
    asg_name=Input['ASGName']
    PanS3BucketTpl=Input['PanS3BucketTpl']
    PanS3KeyTpl=Input['PanS3KeyTpl']
    
    event_rule_name= get_event_rule_name(stackname, instanceId)
    target_id_name = get_target_id_name(stackname, instanceId)
    
    logger.info('Creating event rule: ' + event_rule_name)
    
    try:
        response = events_client.put_rule(
            Name=event_rule_name,
            ScheduleExpression='rate(1 minute)',
            State='ENABLED'
        )
        
        events_source_arn = response.get('RuleArn')
    
        lambda_exec_role_arn = iam.get_role(RoleName=IamLambda).get('Role').get('Arn')
        lambda_func_name= get_lambda_cloud_watch_func_name(stackname, asg_name, instanceId)
    except Exception as e:
        logger.error("[PutRule in Create CW]: {}".format(e))
        return False

    logger.info('Creating lambda function: ' + lambda_func_name)

    try:
        if NATGateway == "Yes":
            subnetids=SubnetIDLambda.split(",")
            sgid=sgv
            response = lambda_client.create_function(
                FunctionName=lambda_func_name,
                Runtime='python2.7',
                Role=lambda_exec_role_arn,
                Handler='metrics.lambda_handler',
                Code={
                   'S3Bucket': PanS3BucketTpl,
                   'S3Key': PanS3KeyTpl
                },
                Timeout=30,
                VpcConfig={
                   'SubnetIds': subnetids,
                   'SecurityGroupIds': [
                       sgid,
                   ]
                }
            )
        else:
            response = lambda_client.create_function(
                FunctionName=lambda_func_name,
                Runtime='python2.7',
                Role=lambda_exec_role_arn,
                Handler='metrics.lambda_handler',
                Code={
                   'S3Bucket': PanS3BucketTpl,
                   'S3Key': PanS3KeyTpl
                },
                Timeout=300
            )
    except Exception as e:
        logger.error("[LambdaCreateFunction in Create CW]: {}".format(e))
        return False

    logger.info('Lambda function created...')

    try:
        lambda_function_arn = response.get('FunctionArn')
        statementid = get_statement_id(stackname, instanceId)
        logger.info('Creating(1) Permission InstanceID: ' + str(instanceId) + ' FuncName: ' + lambda_func_name + ' StatementID: ' + statementid)
        response = lambda_client.add_permission(
            FunctionName=lambda_func_name,
            StatementId= statementid,
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=events_source_arn
        )
    except Exception as e:
        logger.error("[LambdaAddPermission in Create CW]: {}".format(e))
        return False
        
    try:
        response=ec2_client.describe_network_interfaces(NetworkInterfaceIds=[eniId])
    except Exception as e:
        logger.error("[Describe NI failed in Create CW]: {}".format(e))
        return False

    ip="NO_IP"
    pip="NO_IP"
    try:
        for i in response['NetworkInterfaces']:
            if NATGateway == "No":
                logger.info(i['PrivateIpAddresses'])
                ip=i['PrivateIpAddresses'][0]['Association']['PublicIp']
            else:
                ip=i['PrivateIpAddress']
            pip=i['PrivateIpAddress']
    except Exception as e:
        logger.error("[FW IP Address in Create CW]: {}".format(e))
        if NATGateway == "No":
            ip="NO_EIP_ADDR"
        else:
            ip="NO_PrivateIP_ADDR"

    if ip.find("NO_") >= 0:
        logger.error('We failed to get either EIP or Private IP for instance: ' + str(instanceId) + ' IP: ' + ip)
        logger.error('We will not proceed further with this Instance: ' + str(instanceId))
        return False

    Input['FWIP'] = ip
    Input['FWPIP'] = pip
    logger.info('Event put targets for IP Address: ' + ip)
    try:
        response= events_client.put_targets(
            Rule=event_rule_name,
            Targets=
                [{ 
                    'Id': target_id_name,
                    'Arn': lambda_function_arn,
                    'Input': json.dumps(Input)
                }]

        )
    except Exception as e:
        logger.error("[Put Targets failed]: {}".format(e))
        return False

    logger.info('Created CW Lambda Function  for instance ID: ' + str(instanceId))
    return True

def delete_cw_metrics_lambda(stackname, asg_name, instanceId, IamLambda):
    """
    
    :param stackname: 
    :param asg_name: 
    :param instanceId: 
    :param IamLambda: 
    :return: 
    """
    logger.info('Deleteing Cloud Watch Metrics Lambda Function...')
    
    lambda_func_name= get_lambda_cloud_watch_func_name(stackname, asg_name, instanceId)
    event_rule_name = get_event_rule_name(stackname, instanceId)
    target_id_name = get_target_id_name(stackname, instanceId)
    
    logger.info('Removing targets for event rule: ' +  event_rule_name)
    try:
        events_client.remove_targets(Rule=event_rule_name,
                    Ids=[target_id_name])
    except Exception as e:
        logger.error("[Remove Targets]: {}".format(e))

    logger.info('Deleting event rule: ' +  event_rule_name)
    try:
        events_client.delete_rule(Name=event_rule_name)
    except Exception as e:
        logger.error("[Delete CW Metrics Event Rule]: {}".format(e))

    logger.info('Delete lambda function: ' + lambda_func_name)
    try:
        lambda_client.delete_function(FunctionName=lambda_func_name)
    except Exception as e:
        logger.error("[Delete CW metrics Lambda Function]: {}".format(e))
        return False
   
    return True

def remove_s3_bucket(s3_bucket_name):
    """
    
    :param s3_bucket_name: 
    :return: 
    """
    logger.info('Removing keys from S3 bootstrap bucket: ' + s3_bucket_name)

    try:
        response=s3.list_objects_v2(Bucket=s3_bucket_name)
        for i in response['Contents']:
            logger.info('Deleting object/key: ' + i['Key'])
            s3.delete_object(Bucket=s3_bucket_name, Key=i['Key'])

        logger.info('Delete S3 bootstrap bucket: ' + s3_bucket_name)
        s3.delete_bucket(Bucket=s3_bucket_name)
    except Exception as e:
         logger.info("[S3 Delete Bucket]: {}".format(e))

    return

def remove_asg_life_cycle(asg_name):
    """
    
    :param asg_name: 
    :return: 
    """
    logger.info('Removing Life Cycle Hooks for ASG: ' + asg_name)
    hookname=asg_name + '-life-cycle-launch'
    try:
        asg.delete_lifecycle_hook(LifecycleHookName=hookname, AutoScalingGroupName=asg_name)
    except Exception as e:
        logger.info("[ASG life-cycle Hook Launch]: {}".format(e))
    hookname=asg_name + '-life-cycle-terminate'
    try:
        asg.delete_lifecycle_hook(LifecycleHookName=hookname, AutoScalingGroupName=asg_name)
    except Exception as e:
        logger.info("[ASG life-cycle Hook Terminate]: {}".format(e))
    return

def remove_asg_vms(stackname, asg_grp_name, KeyPANWPanorama, delete_stack):
    """
    
    :param stackname: 
    :param asg_grp_name: 
    :param KeyPANWPanorama: 
    :param delete_stack: 
    :return: 
    """
    response=asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_grp_name])
   
    # Initiate removal of all EC2 instances associated to ASG
    found = False
    for i in response['AutoScalingGroups']:
        for ec2i in i['Instances']:
            found = True
            logger.info('Terminating instance: ' + ec2i['InstanceId'] + ' HealthStatus: ' + ec2i['HealthStatus'])
            logger.info(ec2i)

            release_eip(stackname, ec2i['InstanceId'])

            if delete_stack == True:
                try:
                    delete_cw_metrics_lambda(stackname, asg_grp_name, ec2i['InstanceId'], None)
                except Exception as e:
                    logger.warning("[CW Lambda for Instance]: {}".format(e))

            try:
                ec2_client.terminate_instances(InstanceIds=[ec2i['InstanceId']])
            except Exception as e:
                logger.warning("[Terminate Instance in ASG]: {}".format(e))
    
    return found

def common_alarm_func_del(alarmname):
    """
    
    :param alarmname: 
    :return: 
    """
    a1=alarmname + '-high'
    logger.info('Removing Alarm Name: ' + alarmname + ' High: ' + a1)
    try:
       cloudwatch.delete_alarms(AlarmNames=[a1])
    except Exception as e:
       a1=alarmname + '-low'

    a1=alarmname + '-low'
    try:
        cloudwatch.delete_alarms(AlarmNames=[a1])
    except Exception as e:
       return

    return

def remove_alarm(asg_name):
    """
    
    :param asg_name: 
    :return: 
    """
    alarmname= asg_name + '-cw-cpu'
    common_alarm_func_del(alarmname)

    alarmname= asg_name + '-cw-as'
    common_alarm_func_del(alarmname)

    alarmname= asg_name + '-cw-su'
    common_alarm_func_del(alarmname)

    alarmname= asg_name + '-cw-gpu'
    common_alarm_func_del(alarmname)

    alarmname= asg_name + '-cw-at'
    common_alarm_func_del(alarmname)

    alarmname= asg_name + '-cw-dpb'
    common_alarm_func_del(alarmname)

    return

def remove_asg(stackname, ilbname, ip_address, asg_grp_name, ScalingParameter, KeyPANWPanorama, force, delete_stack):
    """
    
    :param stackname: 
    :param ilbname: 
    :param ip_address: 
    :param asg_grp_name: 
    :param ScalingParameter: 
    :param KeyPANWPanorama: 
    :param force: 
    :param delete_stack: 
    :return: 
    """
    s3_bucket_name=get_s3_bucket_name(stackname, ilbname, ip_address)

    logger.info('Remove ASG: ' + asg_grp_name + 'IP address: ' + ip_address)

    if enable_s3 == True:
        remove_s3_bucket(s3_bucket_name)

    try:
        logger.info('Disable metrics collection and Set Min and Desired Capacity to 0 for ASG: ' + asg_grp_name)
        asg.disable_metrics_collection(AutoScalingGroupName=asg_grp_name)
        scaleout=asg_grp_name + '-scaleout'
        asg.update_auto_scaling_group(AutoScalingGroupName=asg_grp_name, MinSize=0, DesiredCapacity=0)
        #asg.put_scheduled_update_group_action(AutoScalingGroupName=asg_grp_name, ScheduledActionName=scaleout, MinSize=0, DesiredCapacity=0)
    except Exception as e:
         logger.info('Could not disable_metrics_collection and Set Min/Desired Capacity to 0 for ASG. Reason below')
         logger.info("[RESPONSE]: {}".format(e))
         if force == False:
             remove_alarm(asg_grp_name)
             return False

    remove_alarm(asg_grp_name)

    policyname=asg_grp_name + '-scalein'
    logger.info('Deleting ScalePolicyIn :' + policyname)
    try:
        asg.delete_policy(AutoScalingGroupName=asg_grp_name, PolicyName=policyname)
    except Exception as e:
         logger.info("[ScaleIn Policy]: {}".format(e))

    policyname=asg_grp_name + '-scaleout'

    logger.info('Deleting ScalePolicyOut :' + policyname)
    try:
        asg.delete_policy(AutoScalingGroupName=asg_grp_name, PolicyName=policyname)
    except Exception as e:
         logger.info("[ScaleOut Policy]: {}".format(e))

    if remove_asg_vms(stackname, asg_grp_name, KeyPANWPanorama, delete_stack) == True:
        if force == False:
            return False

    response=asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_grp_name])
    lc_name=""
    try:
        for i in response['AutoScalingGroups']:
            logger.info('i of response[AutoScalingGroups]:')
            logger.info(i)
            lc_name=i['LaunchConfigurationName']
    except Exception as e:
         logger.info("[LC config Name]: {}".format(e))

    if lc_name == "":
        logger.critical('LC for ASG not found: ' + asg_grp_name)
        if force == False:
            return False

    remove_asg_life_cycle(asg_grp_name)

    logger.info('Deleting ASG : ' + asg_grp_name)
    try:
        if force == True:
            asg.delete_auto_scaling_group(AutoScalingGroupName=asg_grp_name, ForceDelete=True)
        else:
            asg.delete_auto_scaling_group(AutoScalingGroupName=asg_grp_name)
    except Exception as e:
         logger.info('Could not remove ASG. Reason below')
         logger.info("[ASG DELETE]: {}".format(e))
         if force == False:
             return False

    logger.info('Deleting Lanuch-configuration for ASG: ' + asg_grp_name)
    try:
        asg.delete_launch_configuration(LaunchConfigurationName=lc_name)
    except Exception as e:
         logger.info('Could not remove ASG. Reason below')
         logger.info("[ASG DELETE LC]: {}".format(e))
         if force == False:
             return False

    if enable_s3 == True:
        remove_s3_bucket(s3_bucket_name)

    return True

def read_s3_object(bucket, key):
    """
    
    :param bucket: 
    :param key: 
    :return: 
    """
    # Get the object from the event and show its content type
    key = urllib.unquote_plus(key).decode('utf8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        print("CONTENT TYPE: " + response['ContentType'])
        contents=response['Body'].read()
        #print('Body: ' + str(contents))
        return str(contents)
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist.'.format(key, bucket))
        return None

def get_values_from_init_cfg(contents):
    """
    Retrieve the keys from the init-cfg file 
    :param contents: 
    :return: dict
    """
    d = {'panorama-server': "", 'tplname': "", 'dgname': "", 'hostname': ""}
    if contents is None:
        return d

    contents=contents.replace('\n', '::')
    list=contents.split("::")
    for i in list:
        if i == "":
            continue

        s=i.split("=")
        if s[0] != "" and s[0] == "panorama-server" and s[1] != "":
            d['panorama-server']=s[1]
        elif s[0] != "" and s[0] == "tplname" and s[1] != "":
            d['tplname']=s[1]
        elif s[0] != "" and s[0] == "dgname" and s[1] != "":
            d['dgname']=s[1]
        elif s[0] != "" and s[0] == "hostname" and s[1] != "":
            d['hostname']=s[1]

    return d


def panorama_remove_serial_and_ip(stackname, r, pdict):
    """
    
    :param stackname: 
    :param r: 
    :param pdict: 
    :return: 
    """
    if pdict is None:
        return

    MasterS3Bucket=r['MasterS3Bucket']
    c=read_s3_object(MasterS3Bucket, "config/init-cfg.txt")
    dict = get_values_from_init_cfg(c)
    logger.info('Panorama: Init CFG bootstrap file Panorama settings is as follows: ')
    logger.info(dict)

    PanoramaIP=dict['panorama-server']
    PanoramaDG=dict['dgname']
    PanoramaTPL=dict['tplname']

    KeyPANWPanorama=r['KeyPANWPanorama']
    NATGateway=r['NATGateway']

    if PanoramaIP == "":
        return None

    cnt=len(pdict)
    for i in pdict:
        print(i)

    return

def panorama_save_serial_and_ip(stackname, r):
    """
    
    :param stackname: 
    :param r: 
    :return: 
    """
    pdict = []

    MasterS3Bucket=r['MasterS3Bucket']
    c=read_s3_object(MasterS3Bucket, "config/init-cfg.txt")
    dict = get_values_from_init_cfg(c)
    logger.info('Panorama: Init CFG bootstrap file Panorama settings is as follows: ')
    logger.info(dict)

    PanoramaIP=dict['panorama-server']
    PanoramaDG=dict['dgname']
    PanoramaTPL=dict['tplname']

    KeyPANWPanorama=r['KeyPANWPanorama']
    elb_name=r['ELBName']
    NATGateway=r['NATGateway']

    if PanoramaIP == "":
        return None

    response = elb.describe_instance_health(LoadBalancerName=elb_name)
    for i in response['InstanceStates']:
        instanceId=i['InstanceId']
        iresponse=ec2_client.describe_network_interfaces(Filters=[{'Name': "attachment.instance-id", 'Values': [str(instanceId)]}])
        gwMgmtIp=""
        for ir in iresponse['NetworkInterfaces']:
            eniId=ir['NetworkInterfaceId']
            Attachment=ir['Attachment']
            aId=Attachment['AttachmentId']
            if Attachment['DeviceIndex'] == 1:
                gwMgmtIp=ir['PrivateIpAddress']
                break

        if gwMgmtIp is not None:
            serial_no=remove_device(stackname, False, PanoramaIP, KeyPANWPanorama, PanoramaDG, PanoramaTPL, "", gwMgmtIp)
            if serial_no is not None and serial_no != "Done":
                d = {'IP': gwMgmtIp, 'SerialNo': serial_no}
                pdict.append(d)

    print('Items for Panorama are as follows:')
    print(pdict)
    return pdict

def panorama_delete_stack(stackname, r, asg_name):
    """
    
    :param stackname: 
    :param r: 
    :param asg_name: 
    :return: 
    """
    MasterS3Bucket=r['MasterS3Bucket']
    c=read_s3_object(MasterS3Bucket, "config/init-cfg.txt")
    dict = get_values_from_init_cfg(c)
    logger.info('Panorama: Init CFG bootstrap file Panorama settings is as follows: ')
    logger.info(dict)

    PanoramaIP=dict['panorama-server']
    PanoramaDG=dict['dgname']
    PanoramaTPL=dict['tplname']

    KeyPANWPanorama=r['KeyPANWPanorama']
    NATGateway=r['NATGateway']

    if PanoramaIP == "":
        return

    response=asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
   
    # Initiate removal of all EC2 instances associated to ASG
    found = False
    for i in response['AutoScalingGroups']:
        for ec2i in i['Instances']:
            instanceId=ec2i['InstanceId']
            iresponse=ec2_client.describe_network_interfaces(Filters=[{'Name': "attachment.instance-id", 'Values': [str(instanceId)]}])
            gwMgmtIp=""
            for i in iresponse['NetworkInterfaces']:
                eniId=i['NetworkInterfaceId']
                Attachment=i['Attachment']
                aId=Attachment['AttachmentId']
                if Attachment['DeviceIndex'] == 1:
                    gwMgmtIp=i['PrivateIpAddress']
                    break

                if gwMgmtIp == "":
                    logger.error('Firewall IP could not be found. Can not remove it from Panorama')
                    return

            logger.info('Panorama: Removing instance: ' + ec2i['InstanceId'] + ' from Panorama Device. HealthStatus: ' + ec2i['HealthStatus'])
            remove_fw_from_panorama(stackname, instanceId, KeyPANWPanorama, gwMgmtIp, PanoramaIP, PanoramaDG, PanoramaTPL)

    return

def delete_asg_stack(stackname, r, ilb_name, elb_name, ScalingParameter, KeyPANWPanorama, force):
    """
    
    :param stackname: 
    :param r: 
    :param ilb_name: 
    :param elb_name: 
    :param ScalingParameter: 
    :param KeyPANWPanorama: 
    :param force: 
    :return: 
    """
    sname='ELB*' +  ilb_name + '*'
    print('Poking Internal Load Balancer NI: ' + sname)
    try:
        response = ec2_client.describe_network_interfaces(Filters=[
        {
            'Name': 'description',
            'Values': [
                sname
            ]
        } ])
    except Exception as e:
        logger.error("[PokeILB]: {}".format(e))
        logger.error("ILB is not there or ENIs returned failure. Quiting the work...")
        return False

    logger.info(response)
    found = False
    for k in response['NetworkInterfaces']:
        #if k['Description'] == sname:
        desc=k['Description']
        if desc.find(ilb_name) > 0:
            print('FOUND IP Address of ILB is :' + k['PrivateIpAddress'])
            asg_response=asg.describe_auto_scaling_groups()
            logger.info(asg_response)
            for i in asg_response['AutoScalingGroups']:
                found = True
                for lbn in i['LoadBalancerNames']:
                    if lbn == elb_name:
                        print('AutoScalingGroupName: ' + i['AutoScalingGroupName'])
                        asg_name = i['AutoScalingGroupName']
                        try:
                            panorama_delete_stack(stackname, r, asg_name)
                        except Exception as e:
                            logger.warning("[Delete Device from Panorama]: {}".format(e))

                        remove_asg(stackname, ilb_name, k['PrivateIpAddress'], asg_name, ScalingParameter, KeyPANWPanorama, force, True)

    return found

#
# Lambda ENIs when deployed in NAT Gateway mode don't go away (because of VPCconfig)
#
def delete_eni_lambda(stackname, r):
    """
    
    :param stackname: 
    :param r: 
    :return: 
    """
    vpc_sg=r['VPCSecurityGroup']
    print('Look for ENIs in Lambda VPC SG: ' + vpc_sg)
    response=ec2_client.describe_network_interfaces(Filters=[{'Name': "group-id", 'Values': [str(vpc_sg)]}])
    print(response)
    good=True
    for i in response['NetworkInterfaces']:
        eniId=i['NetworkInterfaceId']
        if i['Status'] == "available":
            try:
                ec2_client.delete_network_interface(NetworkInterfaceId=eniId)
            except Exception as e:
                logger.warning("[Lambda delete Eni]: {}".format(e))
                good=False
            continue

        Attachment=i['Attachment']
        aId=Attachment['AttachmentId']
        print('Detaching Eni ID: ' + eniId + ' Desc: ' + i['Description'] + ' IP: ' + i['PrivateIpAddress'] + ' AZ: ' + i['AvailabilityZone'])
        print('Detaching Attachment ID: ' + aId + ' DeviceIndex: ' +  str(Attachment['DeviceIndex']))
        if Attachment['DeviceIndex'] != 0:
            try:
                ec2_client.modify_network_interface_attribute(NetworkInterfaceId=eniId,
                           Attachment={ 'AttachmentId': aId, 'DeleteOnTermination': True})
                ec2_client.detach_network_interface(AttachmentId=aId, Force=True)
                ec2_client.delete_network_interface(NetworkInterfaceId=eniId)
            except Exception as e:
                good=False
                logger.warning("[Lambda detach Eni]: {}".format(e))
                try:
                    ec2_client.delete_network_interface(NetworkInterfaceId=eniId)
                except Exception as e:
                    logger.warning("[Lambda delete Eni in modify/delete]: {}".format(e))

    return good

def delete_asg_stacks(stackname, r, ilb_name, elb_name, ScalingParameter, KeyPANWPanorama):
    """
    
    :param stackname: 
    :param r: 
    :param ilb_name: 
    :param elb_name: 
    :param ScalingParameter: 
    :param KeyPANWPanorama: 
    :return: 
    """
    force=False
    #pdict = panorama_save_serial_and_ip(stackname, r)
    for i in range(1,90):
        logger.info('Attemping to Delete ASGs in ILB: ' + ilb_name + ' Iternation: ' + str(i))
        if i >= 2:
            force=True
            try:
                print('Delete ENI for Lambda with VPC SG if any...')
                delete_eni_lambda(stackname, r)
            except Exception as e:
                 logger.warning("[delete ENI lambda]: {}".format(e))

        if delete_asg_stack(stackname, r, ilb_name, elb_name, ScalingParameter, KeyPANWPanorama, force) == False:
            logger.info('DONE with deleting ASGs in ILB: ' + ilb_name)
            break
        time.sleep(1)


    MasterS3Bucket=r['MasterS3Bucket']
    c=read_s3_object(MasterS3Bucket, "config/init-cfg.txt")
    dict = get_values_from_init_cfg(c)
    logger.info('Panorama: Init CFG bootstrap file Panorama settings is as follows: ')
    logger.info(dict)

    PanoramaIP=dict['panorama-server']
    PanoramaDG=dict['dgname']
    PanoramaTPL=dict['tplname']

    KeyPANWPanorama=r['KeyPANWPanorama']

    try:
        response=lambda_client.list_functions()
        for f in response['Functions']:
            s=f['FunctionName']
            if s.startswith(stackname) == True:
                print('Stack ListFunctions: Lambda Function Name: ' + s)
                asgl=s.split("_ASG_")
                print(asgl)
                if len(asgl) == 2:
                    strcw=asgl[1]
                    cwl=strcw.split("-cwm-")
                    print(cwl)
                    asg_name=stackname+"_ASG_"+cwl[0]
                    print('ASG Name is: ' + asg_name)
                    if len(cwl) == 2:
                        instanceId=cwl[1]
                        print('Instance ID is: ' + instanceId)
                        delete_cw_metrics_lambda(stackname, asg_name, instanceId, None)

        delete_eni_lambda(stackname, r)
        for iter in range(1,30):
            print('Lambda ListFunctions: Delete ENI for Lambda with VPC SG if any: Iteration: ' + str(iter))
            if delete_eni_lambda(stackname, r) == True:
                break
            time.sleep(1)
    except Exception as e:
        logger.error("[ListFunctions lambda]: {}".format(e))
        logger.error("You may have some left-over resource which you will have to delete manually")

    if PanoramaIP == "":
        return
    
    return

    for r in range(1,60):
        if len(pdict) == 0:
            print('List is empty now')
            break

        cnt=0
        print('Walk pdict items')
        for items in pdict:
            print(items)
            ret=remove_device(stackname, True, PanoramaIP, KeyPANWPanorama, PanoramaDG, PanoramaTPL, items['SerialNo'], items['IP'])
            if (stackname, True, PanoramaIP, KeyPANWPanorama, PanoramaDG, PanoramaTPL, items['SerialNo'], items['IP']) == "Done":
                print('Deleted device sucessfully')
                del pdict[cnt]
                break
            cnt=cnt+1

        time.sleep(1)

    return

def getAccountId(rid):
    """
    
    :param rid: 
    :return: 
    """
    try:
        list=rid.split(":")
        return list[4]
    except Exception as e:
        return None

def getRegion(rid):
    """
    
    :param rid: 
    :return: 
    """
    try:
        list=rid.split(":")
        return list[3]
    except Exception as e:
        return None

def getSqs(stackname, region, account):
    """
    
    :param stackname: 
    :param region: 
    :param account: 
    :return: 
    """
    try:
        queue_url="https://"+region+".queue.amazonaws.com/"+account+"/"+stackname
        #print('getSqs Queue is: ' + queue_url)
        response=sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
        print(response)
        str=""
        for m in response['Messages']:
            body=m['Body']
            if str == "":
                str=body
            else:
                str=str+":"+body

        print(str)
        return str
    except Exception as e:
         return None
    return None

def getSqsMessages(stackname, account):
    """
    
    :param stackname: 
    :param account: 
    :return: 
    """
    region=getRegion(account)
    if region is None:
        return None

    id=getAccountId(account)
    msg=getSqs(stackname, region, id)
    return msg

def getDebugLevelFromMsg(msg):
    """
    
    :param msg: 
    :return: 
    """
    #print('Message is 1: ' + msg)
    list=msg.split(":")
    for i in list:
        ilist=i.split("=")
        name=ilist[0]
        value=ilist[1]
        if name == "logger":
            return value

def setDebugLevelFromMsg(logger, lvl):
    """
    
    :param logger: 
    :param lvl: 
    :return: 
    """
    #print('Setting lvl to: ' + lvl)
    if lvl is None:
        logger.setLevel(logging.WARNING)
    elif lvl == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif lvl == "INFO":
        logger.setLevel(logging.INFO)
    elif lvl == "WARNING":
        logger.setLevel(logging.WARNING)
    elif lvl == "ERROR":
        logger.setLevel(logging.ERROR)
    elif lvl == "CRITICAL":
        logger.setLevel(logging.CRITICAL)

def getDebugLevel(stackname, region, account):
    """
    
    :param stackname: 
    :param region: 
    :param account: 
    :return: 
    """

    try:
        queue_url="https://"+region+".queue.amazonaws.com/"+account+"/"+stackname
        #print('Queue Name is : ' + queue_url)
        response=sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
        #print(response)
        for m in response['Messages']:
            body=m['Body']
            list=body.split(":")
            for i in list:
                ilist=i.split("=")
                name=ilist[0]
                value=ilist[1]
                if name == "logger":
                    return value
    except Exception as e:
         return None

def setLoggerLevel(logger, stackname, account):
    """
    
    :param logger: 
    :param stackname: 
    :param account: 
    :return: 
    """
    region=getRegion(account)
    if region is None:
        return None

    id=getAccountId(account)
    lvl=getDebugLevel(stackname, region, id)

    if lvl is None:
        logger.setLevel(logging.WARNING)
    elif lvl == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif lvl == "INFO":
        logger.setLevel(logging.INFO)
    elif lvl == "WARNING":
        logger.setLevel(logging.WARNING)
    elif lvl == "ERROR":
        logger.setLevel(logging.ERROR)
    elif lvl == "CRITICAL":
        logger.setLevel(logging.CRITICAL)

def getScalingValue(msg, ScalingParameter):
    """
    
    :param msg: 
    :param ScalingParameter: 
    :return: 
    """
    print('getScalingValue()...')
    print(msg)
    try:
        list=msg.split(":")
        for i in list:
           ilist=i.split("=")
           name=ilist[0]
           value=ilist[1]
           print('Name: ' + name + ' Value: ' + value)
           if name == "ActiveSessions" and ScalingParameter == "ActiveSessions":
               return float(value)
           elif name == "DataPlaneCPUUtilization" and ScalingParameter == "DataPlaneCPUUtilization":
               return float(value)
           elif name == "SessionUtilization" and ScalingParameter == "SessionUtilization":
               return float(value)
           elif name == "GPGatewayUtilization" and ScalingParameter == "GPGatewayUtilization":
               return float(value)
           elif name == "DataPlaneBufferUtilization" and ScalingParameter == "DataPlaneBufferUtilization":
               return float(value)
    except Exception as e:
         return None

    return None
