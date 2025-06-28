#!/usr/bin/env python3

"""
    nsxPyCheck - NSX Configuration Compliance Tool
    Perform NSX elements configuration collection and compare the configuration against defined baseline.
    NSX 6.3.x API: http://pubs.vmware.com/nsx-63/topic/com.vmware.ICbase/PDF/nsx_63_api.pdf

"""

import base64
import ssl
import urllib.request
import collections
from subprocess import call
import datetime
import argparse
import os
import fnmatch
from configparser import ConfigParser
import smtplib
from email.message import EmailMessage
import xml.dom.minidom
import jinja2
from inscriptis import get_text
import xmltodict

__author__ = 'smarunich'
__credits__ = 'Kevin Lam, Sergey Marunich'
__version__ = '1.0.1'

config = ConfigParser()
config.read('nsxPyCheck.config')

parser=argparse.ArgumentParser(description='nsxPyCheck - Collect and Check NSX configuration, NSX configuration compliance tool.')
parser.add_argument('--nsxmgr', action='store', dest='NSXMGR',help='NSX Manager IP or FQDN.')
parser.add_argument('--dir', action='store', dest='DIR',help='Configuration directory.')
parser.add_argument('--cli', action='store', dest='CLI',help='NSX Central CLI command to run.')
parser.add_argument('--collect', action='store_true',help='Perform configuration collection.')
parser.add_argument('--check',action='store_true', help='Perform configuration compliance check.')

flags=parser.parse_args()


# Global Variables

AUTHORIZATIONFIELD=''
TIMESTAMP=datetime.datetime.now().strftime("%A, %d. %B %Y %I:%M%p")

# Global Variables used to accumulate nsxPyChecks out of compliance messages

NSXMGROOC=[]
NVCTRLSOOC=[]
NSXHOSTSOOC=[]
NVEDGEGENERALOOC=[]
NVEDGESYSLOGOOC=[]
NVEDGEFWOOC=[]
NVEDGEROUTINGOOC=[]
NVEDGESTATICROUTINGOOC=[]
NVEDGEOSPFOOC=[]
NVEDGEBGPOOC=[]
NVDHCPRELAYOOC=[]
NVDLRIFOOC=[]
NVESGIFOOC=[]

def open_xml(file_path):
    print('Reading file:', file_path)
    xmlOutput=dict()
    if os.path.isfile(file_path) and os.path.getsize(file_path) > 1:
        with open(file_path) as file_output:
            xmlOutput=xmltodict.parse(file_output.read())
    return xmlOutput


def xml_pprint(file_path):
    #FNULL=open(os.devnull, 'w')
    #call(['xmllint','--format',file_path,'--output',file_path],stdout=FNULL, stderr=FNULL)
    xmlOutput = xml.dom.minidom.parse(file_path)
    with open(file_path, "w") as file_output:
        print(xmlOutput.toprettyxml(),file=file_output)
    print('Saving results into:', file_path)

def version_control(file_path):
    if config.get('General','versionControlEnabled') == 'SVN':
        print('Perfoming SVN add and commit for the file:', file_path)
        FNULL=open(os.devnull, 'w')
        call(['svn','add',file_path],stdout=FNULL, stderr=FNULL)
        #call(['svn','diff'])
        call(['svn','commit','-m','Auto commit',file_path],stdout=FNULL, stderr=FNULL)

def render_report(template_path, report):
    print('Rendering report...')
    file_path, file_name = os.path.split(template_path)
    return jinja2.Environment(loader=jinja2.FileSystemLoader(file_path)).get_template(file_name).render(nsxPyCheckReports=report,date=TIMESTAMP)

def send_email(email_from,email_to,subject,file_path):
    if config.get('General','email_report') == 'true':
        print('Sending report via email...')
        with open(file_path) as file_output:
            msg=EmailMessage()
            msg.set_content(file_output.read(),subtype='html')
        msg['Subject']=subject
        msg['From']=email_from
        msg['To']=email_to
        server=smtplib.SMTP(config.get('General','smtp_server'))
        server.starttls()
        server.send_message(msg)
        server.quit()

def nsx_setup(username, password):
    '''Setups up Python's urllib library to communicate with the
      NSX Manager.  Uses TLS 1.2 and no cert, for demo purposes.
      Sets the authorization field you need to put in the
      request header into the global variable: AUTHORIZATIONFIELD.
    '''
    global AUTHORIZATIONFIELD

<target>
    context=ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
</target>
    context.verify_mode=ssl.CERT_NONE
    httpsHandler=urllib.request.HTTPSHandler(context=context)

    manager=urllib.request.HTTPPasswordMgrWithDefaultRealm()
    authHandler=urllib.request.HTTPBasicAuthHandler(manager)

    # The opener will be used for for all urllib calls, from now on.
    opener=urllib.request.build_opener(httpsHandler, authHandler)
    urllib.request.install_opener(opener)

    basicAuthString='%s:%s' % (username, password)
    field=base64.b64encode(basicAuthString.encode('ascii'))
    #Debugging: print('Basic %s' % str(field,'utf-8'))
    AUTHORIZATIONFIELD='Basic %s' % str(field,'utf-8')

def nsx_get(url, file_name=None):
    '''Does a HTTP GET on the NSX Manager REST Server.
      If a second argument is given, the result is stored in a file
      with that name.  Otherwise, it is written to standard output.
    '''
    global AUTHORIZATIONFIELD

    request=urllib.request.Request(url,headers={'Authorization': AUTHORIZATIONFIELD})
    response=urllib.request.urlopen(request)
    if config.get('General','debugEnabled') == 'true':
        print('REST GET %s ' % url)
    if file_name==None:
        #print('REST %s:' % url)
        #print(response.read().decode())
        response=response.read().decode()
    else:
    #   print('REST %s is in file %s.' % (url, file_name))
        with open(file_name, 'w') as new_file:
            print(response.read().decode(),file=new_file)
    return response

def nsx_post(url, data, file_name=None):
    '''Does a HTTP POST on the NSX Manager REST Server.
      If a second argument is given, the result is stored in a file
      with that name.  Otherwise, it is written to standard output.
    '''
    global AUTHORIZATIONFIELD
    data = (data.encode('utf-8'))
    request=urllib.request.Request(url=url, data=data,headers={'Authorization': AUTHORIZATIONFIELD,'Content-Type':'application/xml','Accept':'text/plain'})
    response=urllib.request.urlopen(request)
    if config.get('General','debugEnabled') == 'true':
        print('REST POST %s ' % url)
        print(data)
    if file_name==None:
    #  print('REST %s:' % url)
    #  print(response.read().decode())
      response=response.read().decode()
    else:
    #  print('REST %s is in file %s.' % (url, file_name))
       with open(file_name, 'w') as new_file:
           print(response.read().decode(),file=new_file)
    return response

def nsx_cli(nsxmgr,cli,file_name=None):
    ''' Interface to run NSX CLI.
    '''
    url='https://'+str(nsxmgr)+'/api/1.0/nsx/cli?action=execute'
    nsx_cliOutput = nsx_post(url,'<nsxcli><command>'+str(cli)+'</command></nsxcli>',file_name)
    if config.get('General','debugEnabled') == 'true':
        print(nsx_cliOutput)
    return nsx_cliOutput

def nsx_get_nv_edges_general_info(nsxmgr,working_dir):
    ''' Collects list of all NSX edges and their properties, writes to NSXMGR-GeneralInfoNsxEdges.xml file.
        File is used to generate list of NSX edges as well as perform basic checks against NSX Edges.
    '''
    print('Getting Nv Edges General Info...')
    url='https://'+str(nsxmgr)+'/api/4.0/edges'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-GeneralInfoNsxEdges.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_edges_list(nsxmgr,working_dir,edgeType):
    ''' Generates list of edges as Ordered Dict in format edgeId:edgeType-edgeName
    '''
    print('Generating Edge List...')
    data=open_xml(str(working_dir)+'/'+str(nsxmgr)+'-GeneralInfoNsxEdges.xml')
    edgeIdList=[]
    edgeNameList=[]
    if edgeType=='dlr':
        edgeTypeFlag=['distributedRouter']
    if edgeType=='esg':
        edgeTypeFlag=['gatewayServices']
    if edgeType=='all':
        edgeTypeFlag=['distributedRouter','gatewayServices']
    # if list - multiple nsx edges to be captured, if else/dict only one edge deployed:
    if isinstance(data['pagedEdgeList']['edgePage']['edgeSummary'],dict):
        data['pagedEdgeList']['edgePage']['edgeSummary']=[data['pagedEdgeList']['edgePage']['edgeSummary']]
    for edge in data['pagedEdgeList']['edgePage']['edgeSummary']:
         if edge['edgeType'] in edgeTypeFlag:
            edgeIdList +=[( edge['id'])]
            edgeNameList += [(edge['edgeType']+'-'+edge['name'])]
    edgeList=collections.OrderedDict(zip(edgeIdList,edgeNameList))
    return edgeList

def nsx_lookup_edge_name(edge,edgeList):
    ''' Used to convert edgeId to edgeType-edgeName
    '''
    print('Converting Edge IDs to Edge Names...')
    return edgeList[edge]

def nsx_get_esg_config(nsxmgr,working_dir):
    ''' Collects configuration of all NSX ESGs and save it as config.xml file.
        Generated configuration files will be used to perform a configuration checks.
    '''
    print('Getting NSX ESGs configuration...')
    esgList=nsx_get_edges_list(nsxmgr,working_dir,'esg')
    for esg in esgList.keys():
        url='https://'+str(nsxmgr)+'/api/4.0/edges/'+str(esg)
        file_path=str(working_dir)+'/'+str(nsxmgr)+'-'+str(esgList[esg])+'-'+str(esg)+'-config.xml'
        nsx_get(url,file_path)
        xml_pprint(file_path)
        version_control(file_path)

def nsx_get_dlr_config(nsxmgr,working_dir):
    ''' Collects configuration of all NSX DLRs and save it as config.xml file.
        Generated configuration files will be used to perform a configuration checks.
    '''
    print('Getting NSX DLRs configuration...')
    dlrList=nsx_get_edges_list(nsxmgr,working_dir,'dlr')
    for dlr in dlrList.keys():
        url='https://'+str(nsxmgr)+'/api/4.0/edges/'+str(dlr)
        file_path=str(working_dir)+'/'+str(nsxmgr)+'-'+str(dlrList[dlr])+'-'+str(dlr)+'-config.xml'
        nsx_get(url,file_path)
        xml_pprint(file_path)
        version_control(file_path)

def nsx_get_lsw_config(nsxmgr,working_dir):
    print('Getting NSX Logical Switches configuration...')
    url='https://'+str(nsxmgr)+'/api/2.0/vdn/virtualwires'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-logical-switches-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_dfw_config(nsxmgr,working_dir):
    print('Getting NSX DFW Ruleset configuration...')
    url='https://'+str(nsxmgr)+'/api/4.0/firewall/globalroot-0/config'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-dfw-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_dfw_security_groups_config(nsxmgr,working_dir):
    print('Getting NSX DFW Security Groups configuration...')
    url='https://'+str(nsxmgr)+'/api/2.0/services/securitygroup/scope/globalroot-0'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-nsx-security-groups-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_dfw_security_tags_config(nsxmgr,working_dir):
    print('Getting NSX DFW Security Tags configuration...')
    url='https://'+str(nsxmgr)+'/api/2.0/services/securitygroup/scope/globalroot-0'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-nsx-security-tags-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_dfw_security_policies_config(nsxmgr,working_dir):
    print('Getting NSX DFW Security Policies configuration...')
    url='https://'+str(nsxmgr)+'/api/2.0/services/policy/securitypolicy/all'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-nsx-security-policies-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_get_dfw_ipsets_config(nsxmgr,working_dir):
    print('Getting NSX DFW IPsets configuration...')
    url='https://'+str(nsxmgr)+'/api/2.0/services/ipset/scope/globalroot-0'
    file_path=str(working_dir)+'/'+str(nsxmgr)+'-nsx-ipsets-config.xml'
    nsx_get(url,file_path)
    xml_pprint(file_path)
    version_control(file_path)

def nsx_py_check_controllers_config(nsxmgr):
    print('Checking NSX Controllers Configuration...')
    global NVCTRLSOOC
    url='https://'+str(nsxmgr)+'/api/2.0/vdn/controller'
    data=xmltodict.parse(nsx_get(url))
    controllerStatus = config.get('NvControllers','controllerStatus')
    syslogServers = config.get('NvControllers','syslogServers').split(',')
    syslogPort = config.get('NvControllers','syslogPort')
    syslogProtocol = config.get('NvControllers','syslogProtocol')
    syslogLevel = config.get('NvControllers','syslogLevel')
    if isinstance(data['controllers']['controller'],dict):
        data['controllers']['controller'] = [ data['controllers']['controller'] ]
    for controller in data['controllers']['controller']:        
        if controller['status'] != controllerStatus:
            NVCTRLSOOC += [controller['id']+'\t status requires attention. Current:\t'+controller['status']+'\tExpected:\t'+controllerStatus]
        configUrl='https://'+str(nsxmgr)+'/api/2.0/vdn/controller/'+controller['id']+'/syslog'
        try:
            nsxCtrlConfigData=xmltodict.parse(nsx_get(configUrl))
            if nsxCtrlConfigData['controllerSyslogServer']['syslogServer'] not in syslogServers or nsxCtrlConfigData['controllerSyslogServer']['port'] != syslogPort or nsxCtrlConfigData['controllerSyslogServer']['protocol'] != syslogProtocol or nsxCtrlConfigData['controllerSyslogServer']['level'] != syslogLevel:
                NVCTRLSOOC += [controller['id']+'\t'+nsxCtrlConfigData['controllerSyslogServer']['syslogServer']+'\t'+nsxCtrlConfigData['controllerSyslogServer']['port']+'\t'+ nsxCtrlConfigData['controllerSyslogServer']['protocol']+'\t'+nsxCtrlConfigData['controllerSyslogServer']['level']]
        except urllib.request.HTTPError:
             NVCTRLSOOC += [controller['id']+':\t'+'Syslog Server is not configured.']  
    if config.get('General','debugEnabled') == 'true':
        print(NVCTRLSOOC)

def nsx_py_check_nsx_manager_config(nsxmgr):
    print('Checking NSX Manager Configuration...')
    global NSXMGROOC
    syslogServers = config.get('nsxManager','syslogServers').split(',')
    syslogPort = config.get('nsxManager','syslogPort')
    syslogProtocol = config.get('nsxManager','syslogProtocol')
    ntpServers = config.get('nsxManager','ntpServers').split(',')
    vcConfigStatus = config.get('nsxManager','vcConfigStatus')
    configuredNtpServers = str()
    urlNtp='https://'+str(nsxmgr)+'/api/1.0/appliance-management/system/timesettings'
    urlSyslog='https://'+str(nsxmgr)+'/api/1.0/appliance-management/system/syslogserver'
    urlVcConfigStatus='https://'+str(nsxmgr)+'/api/2.0/services/vcconfig/status'
    dataNtp = str()
    dataSyslog = str()
    dataGetNtp=nsx_get(urlNtp)
    dataGetSyslog=nsx_get(urlSyslog)
    dataGetVcConfigStatus=nsx_get(urlVcConfigStatus)
    if dataGetNtp:
        dataNtp=xmltodict.parse(dataGetNtp)
    else:
        NSXMGROOC += [ 'NTP server is not set.' ]
    if dataGetSyslog:
        dataSyslog=xmltodict.parse(dataGetSyslog)
    if dataGetVcConfigStatus:
        datavcConfigStatus=xmltodict.parse(dataGetVcConfigStatus)
    # NTP Check
    if dataNtp:
        for ntpServer in dataNtp['timeSettings']['ntpServer']['string']:
            if ntpServer not in ntpServers:
                configuredNtpServers += ntpServer+'\t'
    if configuredNtpServers or not dataNtp:
        NSXMGROOC += [ 'NTP server is not set or NTP Misconfigured:\t'+configuredNtpServers]
    if dataSyslog:
    # Syslog Check
       if dataSyslog['syslogserver']['syslogServer'] not in syslogServers or dataSyslog['syslogserver']['port'] != syslogPort or dataSyslog['syslogserver']['protocol'] != syslogProtocol:
            NSXMGROOC += [ 'Syslog server is not set or Syslog Misconfigured:\t'+dataSyslog['syslogserver']['syslogServer']+'\t'+dataSyslog['syslogserver']['port']+'\t'+ dataSyslog['syslogserver']['protocol']]
    else:
        NSXMGROOC += [ 'Syslog server is not set.' ]
    # vCenter Connection Status Check
    if datavcConfigStatus['vcConfigStatus']['connected'] != vcConfigStatus:
        NSXMGROOC += [ 'NSX Manager connection to vCenter is down.' ]
    if config.get('General','debugEnabled') == 'true':
        print(NSXMGROOC)

def nsx_py_check_nv_general(nsxmgr,working_dir):
    print('Checking NSX General Edge Appliances Configuration...')
    global NVEDGEGENERALOOC
    dlrApplianceSize=config.get('NvGeneral','dlrApplianceSize')
    dataStoreNameOfActiveVse=config.get('NvGeneral','dataStoreNameOfActiveVse')
    dlrNumberOfDeployedVms=config.get('NvGeneral','dlrNumberOfDeployedVms')
    vmVersion=config.get('NvGeneral','vmVersion')
    edgeStatus=config.get('NvGeneral','edgeStatus')
    esgApplianceSize=config.get('NvGeneral','esgApplianceSize')
    esgNumberOfDeployedVms=config.get('NvGeneral','esgNumberOfDeployedVms')
    data=open_xml(str(working_dir)+'/'+str(nsxmgr)+'-GeneralInfoNsxEdges.xml')
    if isinstance(data['pagedEdgeList']['edgePage']['edgeSummary'],dict):
        data['pagedEdgeList']['edgePage']['edgeSummary'] = [data['pagedEdgeList']['edgePage']['edgeSummary']]
    for edge in data['pagedEdgeList']['edgePage']['edgeSummary']:
        if 'dataStoreNameOfActiveVse' not in edge['appliancesSummary']:
            edge['appliancesSummary']['dataStoreNameOfActiveVse']='NOT DEPLOYED'
        if edge['edgeType'] == 'distributedRouter':
            if edge['appliancesSummary']['applianceSize']!=dlrApplianceSize or dataStoreNameOfActiveVse not in edge['appliancesSummary']['dataStoreNameOfActiveVse'] or edge['appliancesSummary']['numberOfDeployedVms'] is not dlrNumberOfDeployedVms or edge['appliancesSummary']['vmVersion']!=vmVersion or edge['edgeStatus']!=edgeStatus:
                NVEDGEGENERALOOC +=[edge['name']+'\t'+edge['appliancesSummary']['applianceSize']+'\t'+edge['appliancesSummary']['dataStoreNameOfActiveVse']+'\t'+edge['appliancesSummary']['numberOfDeployedVms']+'\t'+edge['appliancesSummary']['vmVersion']+'\t'+edge['edgeStatus']]
        elif edge['edgeType']=='gatewayServices':
            if edge['appliancesSummary']['applianceSize']!=esgApplianceSize or dataStoreNameOfActiveVse not in edge['appliancesSummary']['dataStoreNameOfActiveVse'] or edge['appliancesSummary']['numberOfDeployedVms'] is not esgNumberOfDeployedVms or edge['appliancesSummary']['vmVersion']!=vmVersion or edge['edgeStatus']!=edgeStatus:
                NVEDGEGENERALOOC +=[edge['name']+'\t'+edge['appliancesSummary']['applianceSize']+'\t'+edge['appliancesSummary']['dataStoreNameOfActiveVse']+'\t'+edge['appliancesSummary']['numberOfDeployedVms']+'\t'+edge['appliancesSummary']['vmVersion']+'\t'+edge['edgeStatus']]
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEGENERALOOC)

def nsx_py_check_nv_edge_syslog(data,edgeType):
    print('Checking NSX Edge Syslog Configuration...')
    global NVEDGESYSLOGOOC
    protocol=config.get(edgeType,'syslogProtocol')
    serverAddresses=config.get(edgeType,'syslogServerAddresses').split(',')
    if data['edge']['features']['syslog']['enabled']=='true':
        if data['edge']['features']['syslog']['protocol']!=protocol or data['edge']['features']['syslog']['serverAddresses']['ipAddress'] not in serverAddresses:
            NVEDGESYSLOGOOC+=[data['edge']['name']+'\t'+data['edge']['features']['syslog']['version']+'\t'+ data['edge']['features']['syslog']['enabled']+'\t'+ data['edge']['features']['syslog']['protocol']+'\t'+ data['edge']['features']['syslog']['serverAddresses']['ipAddress']]
    else:
        NVEDGESYSLOGOOC+=[data['edge']['name']+'\tSyslog is not configured.']
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGESYSLOGOOC)

def nsx_py_check_nv_edge_firewall(data,edgeType):
    print('Checking NSX Edge Firewall Configuration...')
    global NVEDGEFWOOC
    if data['edge']['features']['firewall']['enabled']!=config.get(edgeType,'firewallEnabled'):
        NVEDGEFWOOC+=[data['edge']['name']+'\tNSX Edge Appliance Firewall state is misconfigured.\t Firewall State Enabled:\t'+data['edge']['features']['firewall']['enabled']]
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEFWOOC)

def nsx_py_check_nv_edge_routing(data,edgeType):
    print('Checking General NSX Edge Routing Configuration...')
    global NVEDGEROUTINGOOC
    routingEnabled = True
    edgeRoutingEcmp = config.get(edgeType,'ecmpEnabled')
    edgeRoutingLoggingEnabled = config.get(edgeType,'routingLoggingEnabled')
    if data['edge']['features']['routing']['enabled']=='true':
       # ECMP check
       if data['edge']['features']['routing']['routingGlobalConfig']['ecmp']!=edgeRoutingEcmp:
           NVEDGEROUTINGOOC+=[data['edge']['name']+'\tECMP State Enabled:\t'+data['edge']['features']['routing']['routingGlobalConfig']['ecmp']]
       # Routing logging
       if data['edge']['features']['routing']['routingGlobalConfig']['logging']['enable']!=edgeRoutingLoggingEnabled:
           NVEDGEROUTINGOOC+=[data['edge']['name']+'\tRouting Logging State Enabled:\t'+data['edge']['features']['routing']['routingGlobalConfig']['logging']['enable']]
    else:
        NVEDGEROUTINGOOC+=[data['edge']['name']+'\tEdge Routing is not enabled.']
        routingEnabled = False
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEROUTINGOOC)
    return routingEnabled

def nsx_py_check_nv_edge_static_routing(data,edgeType):
    print('Checking NSX Edge Routing Static Routing Configuration...')
    global NVEDGESTATICROUTINGOOC
    staticRoutes=config.get(edgeType,'staticRoutes').split(',')
    staticRouteMtu=config.get(edgeType,'staticRouteMtu')
    staticRouteAdminDistance=config.get(edgeType,'staticRouteAdminDistance')
    staticRouteMissing=True
    staticRouteMissingMsg=''
    if data['edge']['features']['routing']['staticRouting']['staticRoutes']!=None:
        if 'route' in data['edge']['features']['routing']['staticRouting']['staticRoutes']:
            route = data['edge']['features']['routing']['staticRouting']['staticRoutes']['route']
            if isinstance(route, dict):
                route = [route]
            for route in route:
                if route['network'] in staticRoutes and route['adminDistance']!=staticRouteAdminDistance:
                    staticRouteMissingMsg+=route['network']+':\tRoute adminDistance is misconfigured. Expected:\t '+backupStaticRouteAdminDistance+'\t Actual:\t '+route['adminDistance']
                if route['network'] in staticRoutes and route['mtu']!=staticRouteMtu:
                    staticRouteMissingMsg+=route['network']+':\tDefault Route mtu is misconfigured. Expected:\t'+staticRouteMtu+'\t Actual:\t'+route['mtu']
                if route['network'] in staticRoutes and route['adminDistance']==staticRouteAdminDistance and route['mtu']==staticRouteMtu:
                    staticRouteMissing=False
    if staticRouteMissing:
        if staticRouteMissingMsg:
            NVEDGESTATICROUTINGOOC+=[data['edge']['name']+'\t'+staticRouteMissingMsg]
        else:
            NVEDGESTATICROUTINGOOC+=[data['edge']['name']+'\t'+str(staticRoutes)+'\tRoute is missing.']
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGESTATICROUTINGOOC)

def nsx_py_check_nv_edge_ospf(data,edgeType):
    print('Checking NSX Edge OSPF Configuration...')
    global NVEDGEOSPFOOC
    ospfEnabledState=config.get(edgeType,'ospfEnabled')
    if data['edge']['features']['routing']['ospf']['enabled']!=ospfEnabledState:
        NVEDGEOSPFOOC+=[data['edge']['name']+'\tOSPF Enabled State:\t'+data['edge']['features']['routing']['ospf']['enabled']]
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEOSPFOOC)

def nsx_py_check_nv_edge_bgp(data,edgeType):
    print('Checking NSX Edge BGP Configuration...')
    global NVEDGEBGPOOC

    bgpEnabledState=config.get(edgeType,'bgpEnabled')
    bgpHoldDownTimers=config.get(edgeType,'bgpHoldDownTimers').split(',')
    bgpKeepAliveTimers=config.get(edgeType,'bgpKeepAliveTimers').split(',')
    bgpPassword=config.get(edgeType,'bgpPassword')

    if 'bgp' in data['edge']['features']['routing']:
        if data['edge']['features']['routing']['bgp']['enabled']==bgpEnabledState:
            for bgpNeighbor in data['edge']['features']['routing']['bgp']['bgpNeighbours']['bgpNeighbour']:
    #BGP timers
                if isinstance(bgpNeighbor,dict):
                    if 'holdDownTimer' in bgpNeighbor:
                        if bgpNeighbor['holdDownTimer'] not in bgpHoldDownTimers:
                            NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP holdDown timer is misconfigured.']
                    else:
                        NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP holdDown timer is set by default (180s).']
                    if 'keepAliveTimer' in bgpNeighbor:
                        if bgpNeighbor['keepAliveTimer'] not in bgpKeepAliveTimers:
                            NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP keepAliveTimer is misconfigured.']
                    else:
                        NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP keepAliveTimer timer is set by default (60s).']
    #BGP password
                    if 'password' in bgpNeighbor:
                        if bgpNeighbor['password']!=bgpPassword:
                            NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP Password is missing or misconfigured.']
                    else:
                        NVEDGEBGPOOC+=[data['edge']['name']+'\tNeighbor:\t'+bgpNeighbor['ipAddress']+'\tBGP Password is not set.']
    #BGP filters
    #BGP Redistribution
            if data['edge']['features']['routing']['bgp']['redistribution']['enabled'] == config.get(edgeType,'bgpRedistEnabled'):
                if data['edge']['features']['routing']['bgp']['redistribution']['rules']['rule']['from']['connected']!=config.get(edgeType,'redistConnectedToBgp'):
                    NVEDGEBGPOOC+=[data['edge']['name']+'\tBGP Redistribution is misconfigured. BGP to Connected.']
                if data['edge']['features']['routing']['bgp']['redistribution']['rules']['rule']['from']['static']!=config.get(edgeType,'redistStaticToBgp'):
                    NVEDGEBGPOOC+=[data['edge']['name']+'\tBGP Redistribution is misconfigured. BGP to Static.']
                if data['edge']['features']['routing']['bgp']['redistribution']['rules']['rule']['from']['ospf']!=config.get(edgeType,'redistOspfToBgp'):
                    NVEDGEBGPOOC+=[data['edge']['name']+'\tBGP Redistribution is misconfigured. BGP to OSPF.']
    #BGP graceful restart and default originate check
                if data['edge']['features']['routing']['bgp']['gracefulRestart']!=config.get(edgeType,'bgpGracefulRestart'):
                    NVEDGEBGPOOC+=[data['edge']['name']+'\tBGP gracefulRestart is disabled.']
                if data['edge']['features']['routing']['bgp']['defaultOriginate']!=config.get(edgeType,'bgpDefaultOriginate'):
                    NVEDGEBGPOOC+=[data['edge']['name']+'\tBGP defaultOriginate is enabled.']
            else:
                NVEDGEBGPOOC+=['\tBGP Redistribution is misconfigured.']
        else:
            NVEDGEBGPOOC+=['\tBGP is disabled.']
    else:
        NVEDGEBGPOOC+=['\tBGP is disabled.']

    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEBGPOOC)

def nsx_cli_py_check_bgp_session_state(nsxmgr,edge,edgeName,edgeType):
    print('Checking NSX Edge BGP Neighbors state...')
    global NVEDGEBGPOOC
    nsx_cliOutput=nsx_cli(nsxmgr,'show edge '+str(edge)+' ip bgp neighbors')
    for line in nsx_cliOutput.splitlines():
        if 'BGP neighbor' in line:
            bgpNeighbor=line[:-1]
        if 'BGP state' in line:
            bgpState=line.split()[3][:-1]
            if bgpState != config.get(edgeType,'bgpNeighborState'):
                NVEDGEBGPOOC += [ edgeName+'\tBGP Session State Alert for:\t'+bgpNeighbor+'\tExpected:'+config.get(edgeType,'bgpNeighborState')+'\tActual:\t'+bgpState]
    if config.get('General','debugEnabled') == 'true':
        print(NVEDGEBGPOOC)

def nsx_py_check_nv_edge_dhcp_relay(data,edgeType):
    print('Checking NSX DHCP Relay Configuration...')
    global NVDHCPRELAYOOC
    dhcpServers=config.get(edgeType,'dhcpServers').split(',')
    if data['edge']['features']['dhcp']['enabled']=='true' and data['edge']['features']['dhcp']['relay']['relayServer']:
        if isinstance(data['edge']['features']['dhcp']['relay']['relayServer']['ipAddress'],list):
            for dhcpServer in data['edge']['features']['dhcp']['relay']['relayServer']['ipAddress']:
                 if dhcpServer not in dhcpServers:
                     NVDHCPRELAYOOC+=[data['edge']['name']+'\tDHCP Relay is misconfigured.']
        else:
            NVDHCPRELAYOOC+=[data['edge']['name']+'\tDHCP Secondary Relay is missing.']
    else:
        NVDHCPRELAYOOC+=[data['edge']['name']+'\tDHCP Relay is not configured.']

    if config.get('General','debugEnabled') == 'true':
        print(NVDHCPRELAYOOC)

def nsx_py_check_nv_dlr_ifs(data,edgeType):
    print('Checking NSX DLR Interfaces Configuration...')
    global NVDLRIFOOC
    mtu=config.get(edgeType,'IfsMtu')
    interfaceTypeUplink='uplink'
    interfaceTypeUplinkCounter=0
    numberOfUplinks=int(config.get(edgeType,'numberOfUplinks'))
    isConnected=config.get(edgeType,'isConnected')
    if data['edge']['type']=='distributedRouter':
        for interface in data['edge']['interfaces']['interface']:
            if interface['type']==interfaceTypeUplink:
                interfaceTypeUplinkCounter+=1
            if interface['mtu']!=mtu or interface['isConnected']!=isConnected:
                NVDLRIFOOC+=[data['edge']['name']+'\t'+interface['name']+'\tMTU size misconfiguration or Interface is not Connected.']
        if interfaceTypeUplinkCounter!=numberOfUplinks:
            NVDLRIFOOC+=[data['edge']['name']+'\tNumber of uplinks is not matching the DLR standard. Expected:\t'+str(numberOfUplinks)+'\tActual:\t'+str(interfaceTypeUplinkCounter)]
    if config.get('General','debugEnabled') == 'true':
        print(NVDLRIFOOC)

def nsx_py_check_nv_esg_ifs(data,edgeType):
    print('Checking NSX ESG Interfaces Configuration...')
    global NVESGIFOOC
    mtu=config.get(edgeType,'IfsMtu')
    interfaceTypeUplink='uplink'
    interfaceTypeUplinkCounter=0
    numberOfUplinks=int(config.get(edgeType,'numberOfUplinks'))
    isConnected=config.get(edgeType,'isConnected')
    enableProxyArp=config.get(edgeType,'enableProxyArp')
    enableSendRedirects=config.get(edgeType,'enableSendRedirects')
    if data['edge']['type']=='gatewayServices':
        for vnic in data['edge']['vnics']['vnic']:
            if vnic['type']==interfaceTypeUplink:
                interfaceTypeUplinkCounter+=1
            if vnic['isConnected']==isConnected:
                if vnic['mtu']!=mtu:
                    NVESGIFOOC+=[data['edge']['name']+'\t'+vnic['name']+'\tMTU size misconfiguration. Expected:\t'+mtu+'\tActual:\t'+vnic['mtu']]
                if vnic['enableProxyArp']!=enableProxyArp:
                    NVESGIFOOC+=[data['edge']['name']+'\t'+vnic['name']+'\tProxyArp misconfiguration. Expected:\t'+enableProxyArp+'\tActual:\t'+vnic['enableProxyArp']]
                if vnic['enableSendRedirects']!=enableSendRedirects:
                    NVESGIFOOC+=[data['edge']['name']+'\t'+vnic['name']+'\t SendRedirects misconfiguration. Expected:\t'+enableSendRedirects+'\tActual:\t'+vnic['enableSendRedirects']]
        if interfaceTypeUplinkCounter!=numberOfUplinks:
            NVESGIFOOC+=[data['edge']['name']+'\tNumber of uplinks is not matching the ESG standard. Expected:\t'+str(numberOfUplinks)+'\t Actual:\t'+str(interfaceTypeUplinkCounter)]
    if config.get('General','debugEnabled') == 'true':
        print(NVESGIFOOC)

def nsx_cli_get_nsx_hosts_list(nsxmgr):
    print('Generating list of NSX enabled hosts...')
    nsx_cliClusterOutput=nsx_cli(nsxmgr,'show cluster all')
    nsxHostIds = collections.OrderedDict()
    for lineCluster in nsx_cliClusterOutput.splitlines():
       if 'domain' in lineCluster:
           clusterId = lineCluster.split()[2]
           clusterName = lineCluster.split()[1]
           nsx_cliHostOutput=nsx_cli(nsxmgr,'show cluster '+clusterId)
           for lineHost in nsx_cliHostOutput.splitlines():
               if 'host' in lineHost:
                   hostId = lineHost.split()[2]
                   hostName = lineHost.split()[1]
                   nsxHostIds[hostId]=hostName+':'+clusterName
    return nsxHostIds

def nsx_py_check_nsx_hosts_agents(nsxmgr,nsxHostIds):
    print('Checking list of NSX enabled hosts configuration...')
    global NSXHOSTSOOC
    nsxMgrToFirewallAgentConn = config.get('nsxHostsStatus','nsxMgrToFirewallAgentConn')
    nsxMgrToControlPlaneAgentConn =  config.get('nsxHostsStatus','nsxMgrToControlPlaneAgentConn')
    hostToControllerConn = config.get('nsxHostsStatus','hostToControllerConn')
    for hostId in nsxHostIds.keys():
        url='https://'+str(nsxmgr)+'/api/2.0/vdn/inventory/host/'+str(hostId)+'/connection/status'
        data=xmltodict.parse(nsx_get(url))
        if data['hostConnStatus']['nsxMgrToFirewallAgentConn'] != nsxMgrToFirewallAgentConn or data['hostConnStatus']['nsxMgrToControlPlaneAgentConn'] != nsxMgrToControlPlaneAgentConn or data['hostConnStatus']['hostToControllerConn'] != hostToControllerConn:
            NSXHOSTSOOC += [nsxHostIds[hostId]+'\t host communication issue:\tnsxMgrToFirewallAgentConn:'+data['hostConnStatus']['nsxMgrToFirewallAgentConn']+'\tnsxMgrToControlPlaneAgentConn:'+data['hostConnStatus']['nsxMgrToControlPlaneAgentConn']+'\thostToControllerConn:'+data['hostConnStatus']['hostToControllerConn']]
    if config.get('General','debugEnabled') == 'true':
        print(NSXHOSTSOOC)

def nsx_py_check_nv_edges(nsxmgr,working_dir,nsxEdgeList):
    print('Starting checking of NSX Edge components...')
    for edgeId in nsxEdgeList.keys():
        edgeType=nsxEdgeList[edgeId].split('-')[0]
        pattern='*'+edgeId+'-config.xml'
        for file_name in os.listdir(working_dir):
            if fnmatch.fnmatch(file_name,pattern):
                file_path=working_dir+'/'+file_name
        data=open_xml(file_path)
        if data and config.get(edgeType,'CheckEnabled') == 'true':
            if config.get(edgeType,'syslogCheckEnabled') == 'true':
                nsx_py_check_nv_edge_syslog(data,edgeType)
            if config.get(edgeType,'firewallCheckEnabled') == 'true':
                nsx_py_check_nv_edge_firewall(data,edgeType)
            if config.get(edgeType,'routingCheckEnabled') == 'true':
                if nsx_py_check_nv_edge_routing(data,edgeType):
                    if config.get(edgeType,'staticRoutingCheckEnabled') == 'true':
                        nsx_py_check_nv_edge_static_routing(data,edgeType)
                    if config.get(edgeType,'ospfCheckEnabled') == 'true':
                        nsx_py_check_nv_edge_ospf(data,edgeType)
                    if config.get(edgeType,'bgpCheckEnabled') == 'true':
                        nsx_py_check_nv_edge_bgp(data,edgeType)
                        nsx_cli_py_check_bgp_session_state(nsxmgr,edgeId,nsx_lookup_edge_name(edgeId,nsxEdgeList),edgeType)
            if config.get(edgeType,'dhcpRelayCheckEnabled') == 'true':
                nsx_py_check_nv_edge_dhcp_relay(data,edgeType)
            if edgeType == 'distributedRouter':
                if config.get(edgeType,'IfsCheckEnabled') == 'true':
                    nsx_py_check_nv_dlr_ifs(data,edgeType)
            elif edgeType == 'gatewayServices':
                if config.get(edgeType,'IfsCheckEnabled') == 'true':
                    nsx_py_check_nv_esg_ifs(data,edgeType)
    if config.get('nsxHostsStatus','checkEnabled') == 'true':
        nsx_py_check_nsx_hosts_agents(flags.NSXMGR,nsx_cli_get_nsx_hosts_list(flags.NSXMGR))

def nsx_py_check_nv(nsxmgr,working_dir):
    print('Starting checking of NSX components...')
    report = []
    if config.get('NvGeneral','checkEnabled') == 'true':
        nsx_py_check_nv_general(nsxmgr,working_dir)
        nsx_py_check_nv_edges(nsxmgr,working_dir,nsx_get_edges_list(nsxmgr,working_dir,'all'))
    if config.get('nsxManager','checkEnabled') == 'true':
        nsx_py_check_nsx_manager_config(nsxmgr)
    if config.get('NvControllers','checkEnabled') == 'true':
        nsx_py_check_controllers_config(nsxmgr)
    if NSXMGROOC:
        header='NSX Manager: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NSXMGROOC
    if NVCTRLSOOC:
        header='NSX Controllers Syslog: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVCTRLSOOC
    if NSXHOSTSOOC:
        header='NSX Prepared Host CP Communication Status: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NSXHOSTSOOC
    if NVEDGEGENERALOOC:
        header='GENERAL EDGE: Appliance Size, Cluster location, HA configuration, Appliance Version and Edge state: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGEGENERALOOC
    if NVEDGESYSLOGOOC:
        header='NSX Edge Syslog: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGESYSLOGOOC
    if NVEDGEFWOOC:
        header='NSX Edge Appliance Firewall: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGEFWOOC
    if NVEDGEROUTINGOOC:
        header='NSX General Routing: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGEROUTINGOOC
    if NVEDGESTATICROUTINGOOC:
        header='NSX Static Routing: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGESTATICROUTINGOOC
    if NVEDGEOSPFOOC:
        header='NSX OSPF: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGEOSPFOOC
    if NVEDGEBGPOOC:
        header='NSX BGP: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVEDGEBGPOOC
    if NVDHCPRELAYOOC:
        header='NSX DHCP Relay: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVDHCPRELAYOOC
    if NVDLRIFOOC:
        header='NSX DLR Interfaces: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVDLRIFOOC
    if NVESGIFOOC:
        header='NSX ESG Interfaces: all configuration items (CIs) out of compliance with a baseline.'
        report+=[header]+NVESGIFOOC
    return report

if __name__=="__main__":
    nsx_setup(config.get('General','username'),config.get('General','password'))
    if config.get('General','email_report') == 'true':
        email_from=config.get('General','email_from')
        email_to=config.get('General','email_to')
    if flags.collect:
        if config.get('NvGeneral','checkEnabled') == 'true':
            nsx_get_nv_edges_general_info(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDLRconfigs') == 'true':
            nsx_get_dlr_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectESGconfigs') == 'true':
            nsx_get_esg_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectLogicalSWconfigs') == 'true':
            nsx_get_lsw_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDfwRulesetconfigs') == 'true':
            nsx_get_dfw_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDfwSecurityGroupsconfigs') == 'true':
            nsx_get_dfw_security_groups_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDfwSecurityTagsconfigs') == 'true':
            nsx_get_dfw_security_tags_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDfwSecurityPoliciesconfigs') == 'true':
            nsx_get_dfw_security_policies_config(flags.NSXMGR,flags.DIR)
        if config.get('General','collectDfwIpsetconfigs') == 'true':
            nsx_get_dfw_ipsets_config(flags.NSXMGR,flags.DIR)
    if flags.check:
        file_path=str(flags.DIR)+'/'+str(flags.NSXMGR)+'-NSX-PyCheck.report.html'
        report=nsx_py_check_nv(flags.NSXMGR,flags.DIR)
        if report:
            report=render_report(config.get('General','reportJinjaTemplatePath'),report)
        else:
            report=''
        with open(file_path, "w") as file_output:
            print(report, file=file_output)
            version_control(file_path)
        if os.path.isfile(file_path) and os.path.getsize(file_path) > 1:
            subject="Out of Compliance Report for "+str(flags.NSXMGR)+" - "+str(TIMESTAMP)
            if config.get('General','email_report') == 'true':
                send_email(email_from,email_to,subject,file_path)
        file_path=str(flags.DIR)+'/'+str(flags.NSXMGR)+'-NSX-PyCheck.report'
        if report:
            report = get_text(report)
        with open(file_path, "w") as file_output:
            print(report, file=file_output)
            version_control(file_path)
    if flags.CLI:
        print(nsx_cli(flags.NSXMGR,flags.CLI))