#!/usr/bin/env python
import re
import os
import sys
import csv
import pycurl
import OpenSSL
import socket
import ssl
import argparse
import logging

from libnmap.parser import NmapParser

from lib.log import logger


# transform list into string
def list_to_str(str_list):
    return re.sub('[\[\]\']', '', str(str_list))


# remove duplicated words
def unique_list(l):
    ulist = []
    [ulist.append(x) for x in l if x not in ulist]
    return ulist


def fingerprint(nmap_host_object, cpematches):
    if nmap_host_object.os.osmatches:
        for match in nmap_host_object.os.osmatches:
            for osclass in match.osclasses:
                for cpe in osclass.cpelist:
                    # store cpe object and os match accuracy
                    cpematches[cpe] = osclass.accuracy

    return cpematches


# TODO: Fingerprint decision, based on OS cpe objects and open services cpe objects
def fingerprint_decision(cpematches, services):
    '''
    Takes a dict with cpe objects with nmap accuracy scores, apply some intel and
    return most probable OS and most probable OS version.
    '''
    most_prob_os = ""
    most_prob_version = ""

    if cpematches:
        #print cpematches
        # get the highest accuracy from SO cpe dict
        cpe = max(cpematches, key=cpematches.get)

        # set the highest probable os and os version
        most_prob_os = "%s %s" % (cpe.get_vendor(), cpe.get_product().replace('_', ' '))
        most_prob_os = ' '.join(unique_list(most_prob_os.split())).title()
        most_prob_version = cpe.get_version()

    # if we can't get from host cpe, let's try with services instead
    # "hardore" fingerprint mode (guess so from services cpe)
    if not most_prob_os:
        # print("\n[*] Host fingerprint cpe failed, trying guess from open port cpe...")
        for service in services:
            if service.open():
                for cpe in service.cpelist:
                    most_prob_os = "%s %s" % (cpe.get_vendor(), cpe.get_product().replace('_', ' '))
                    most_prob_os = ' '.join(unique_list(most_prob_os.split())).title()
                    most_prob_version = cpe.get_version()
                    #most_prob_os = service.service_dict['ostype']
    
    return most_prob_os, most_prob_version


def cert_hostname(ip_address, port):
    try:
        cert = ssl.get_server_certificate((ip_address, port), ssl_version=ssl.PROTOCOL_SSLv23)
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        for compoment in x509.get_subject().get_components():
            compoment_name, hostname = compoment
            if compoment_name.lower() == 'cn':
                if not "*" in hostname:
                    resolved_ip_address = socket.gethostbyname(hostname.lower())
                    if resolved_ip_address == ip_address:
                        return hostname.lower()
    except Exception, e:
        err, err_msg = e
        logger.warn("Unable to extract hostname from certificate for %s on port %s (%s)" % (ip_address, port, err_msg))
        pass

    return

def check_hostname(nmap_host_object, hostnames):
    # add nmap resolved hostname to hostnames list if it exist
    if nmap_host_object.hostnames:
        hostnames += nmap_host_object.hostnames

    # add reversed name lookup
    try:
        hostname, aliaslist, addresslist = socket.gethostbyaddr(nmap_host_object.address)
        if hostname and hostname not in hostnames:
            hostnames.append(hostname.lower())
    except Exception, e:
        pass

    # run through all HTTP SSL enabled ports
    for service in nmap_host_object.services:
        # check hostname inside certificates
        if service.open() and "http" in service.service.lower() and service.tunnel.lower() == "ssl":
            hostname = cert_hostname(nmap_host_object.address, service.port)
            if hostname:
                hostnames.append(hostname)

    return unique_list(hostnames)


def check_ports(services):
    # take service object list and put in the right format
    # 443/tcp, 80/tcp, 22/tcp
    ports = []
    for service in services:
        if service.open():
            # filter add only to udp/tcp ports (avoiding nmap-protocols results)
            if service.protocol == "udp" or service.protocol == "tcp":
                port = "%s/%s" % (service.port, service.protocol.lower())
                ports.append(port)

    ports = unique_list(ports)

    return list_to_str(ports)


def check_services(nmap_host_object, services):
    for service in nmap_host_object.services:
        if service.open():
            services.append(service)

    return unique_list(services)


def nmap_combine(nmap_report, report):
    # receive NmapParser.parse_fromfile object and transcript it to dict
    # including os_name, os_version, open_ports
    for h in nmap_report.hosts:
        # finger only hosts with detected open ports
        if h.get_open_ports():
            # check if report has previously info about the current host
            if not report.has_key(h.address):
                report[h.address] = {'Port/Protocol': [], 'Domains': [], 'Operating System': {}, 'OS Version': "", 'Notes': ""}

            # add cpe objects and os match accuracy to Operating System dict
            report[h.address]['Operating System'] = fingerprint(h, report[h.address]['Operating System'])

            # add open nmap service objects to Port/Protocol list
            report[h.address]['Port/Protocol'] = check_services(h, report[h.address]['Port/Protocol'])

            # add possible hostnames to Domains list
            report[h.address]['Domains'] = check_hostname(h, report[h.address]['Domains'])

            # print report[h.address]

    return report


def search_xml_recursively(directory):
    full_path_files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith('.xml'):
                full_path_files.append("%s/%s" % (root, f))
    
    return unique_list(full_path_files)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='load a nmap XML file')
    group.add_argument('-d', '--dir', help='directory to recursively search for nmap XML files')
    parser.add_argument('--output', default="recon.csv", help='output fingerprinted CSV file (default: recon.csv)')
    parser.add_argument('--debug', action='store_true', help='debug mode')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    options = parser.parse_args()

    if options.dir:
        directory = options.dir
        if directory.endswith('/'):
            directory = directory[:-1]
        # find all xml files recursively
        nmap_xml_reports = search_xml_recursively(directory)
    else:
        # proceed with single file
        nmap_xml_reports = [options.file]        

    if options.output:
        csv_filename = options.output
    
    if options.debug:
        logger.setLevel(logging.DEBUG)

    # results = cumulative dictionary
    results = {}

    # open final report file
    with open(csv_filename, 'w') as csvwrite:
        # set field names
        fieldnames = ['IP Address', 'Port/Protocol', 'Domains', 'Operating System', 'OS Version', 'Notes']
        writer = csv.DictWriter(csvwrite, fieldnames=fieldnames, dialect=csv.excel, quoting=csv.QUOTE_ALL)
        
        # write CSV header
        writer.writeheader()

        # iterate through xml(s)
        for xml_report in nmap_xml_reports:
            try:
                # trying to load xml file
                nmap_report = NmapParser.parse_fromfile(xml_report)
                logger.info("%s host(s) loaded from %s" % (len(nmap_report.hosts), xml_report))
            except Exception, e:
                logger.warn("XML file %s corrupted or format not recognized" % xml_report)
                # keep looking for others xml
                continue

            # start a cumulative dictionary
            results = nmap_combine(nmap_report, results)
            #print "results: %s" % len(results)

        logger.info("Wraping up results")
        for ip_address in results:
            # colecting info for each field
            open_ports = check_ports(results[ip_address]['Port/Protocol'])
            hostnames = list_to_str(results[ip_address]['Domains'])
            notes = results[ip_address]['Notes']
            os, os_version = fingerprint_decision(results[ip_address]['Operating System'], results[ip_address]['Port/Protocol'])
            #print ip_address, results[ip_address]['Operating System']

            # write down to the final report file
            writer.writerow({'IP Address': ip_address, 'Port/Protocol': open_ports, 'Domains': hostnames, 'Operating System': os, 'OS Version': os_version, 'Notes': notes})
            logger.debug("%s,%s,%s,%s,%s,%s" % (ip_address, open_ports, hostnames, os, os_version, notes))

    logger.info("Done: %s" % csv_filename)
    sys.exit(0)
