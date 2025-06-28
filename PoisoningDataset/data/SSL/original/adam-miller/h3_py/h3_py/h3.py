#!python3
import requests
import yaml
import time
import enum
import sys
import re
import logging
import ssl
from requests.auth import HTTPDigestAuth
from requests.auth import HTTPBasicAuth
from lxml import etree as ET
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager


logger = logging.getLogger(__name__)
with open("config/config.yaml") as f:
	config = yaml.load(f)

# Silence self signed certificate security warning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Specify better cipher. Default causes errors on some systems with outdated ssl libs
requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += 'HIGH:!DH:!aNULL'
try:
    requests.packages.urllib3.contrib.pyopenssl.DEFAULT_SSL_CIPHER_LIST += 'HIGH:!DH:!aNULL'
except AttributeError:
    # no pyopenssl support used / needed / available
    pass

class Ssl3HttpAdapter(HTTPAdapter):
    """"Transport adapter" that allows us to use SSLv3."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_version=ssl.PROTOCOL_SSLv3)

session = requests.Session()
session.mount('https://wbgrp-crawl',Ssl3HttpAdapter())


class Crawl_Status():
	none = "None"
	unbuilt = "Unbuilt"
	ready = "Ready"
	paused = "Active: PAUSED"
	running = "Active: RUNNING"	
	finished = "Finished: ABORTED"

class Crawl_Actions():
	build = "build"
	launch = "launch"
	unpause = "unpause"
	pause = "pause"
	checkpoint = "checkpoint"
	terminate = "terminate"
	teardown = "teardown"

class Crawl_Reports():
	summary = "CrawlSummaryReport"
	seeds = "SeedsReport"
	source = "SourceTagsReport"
	hosts = "HostsReport"
	mime = "MimetypesReport"
	response = "ResponseCodeReport"
	processors = "ProcessorsReport"
	frontier = "FrontierSummaryReport"
	thread = "ToeThreadsReport"


def get_crawl_status(url):
	response = session.get(url,auth=HTTPDigestAuth(config["h3_settings"]["username"],config["h3_settings"]["password"]),verify=False, headers= {'accept':'application/xml'})
	if (response.status_code & 200) == 200:
		root=ET.fromstring(response.text)

		if root.find('statusDescription') is not None:
			return root.find('statusDescription').text
		elif root.find('crawlControllerState') is not None:
			return root.find('crawlControllerState').text

def get_available_actions(url):
	response = session.get(url,auth=HTTPDigestAuth(config["h3_settings"]["username"],config["h3_settings"]["password"]),verify=False, headers= {'accept':'application/xml'})
	actions = []
	if (response.status_code & 200) == 200:
		root=ET.fromstring(response.text)

		for action in root.find('availableActions'):
			actions.append(action.text)
	return actions

def main():
	url = 'https://localhost:6440/engine/job/monthly_test'
	test_full_cycle(url)

def get_crawljob_page(url):
	response = session.get(url,auth=HTTPDigestAuth(config["h3_settings"]["username"],config["h3_settings"]["password"]),verify=False, headers= {'accept':'application/xml'})
	if (response.status_code & 200) == 200:
		return response

def get_crawljob_text_page(url):
	response = requests.get(url,auth=HTTPDigestAuth(config["h3_settings"]["username"],config["h3_settings"]["password"]),verify=False)
	if (response.status_code & 200) == 200:
		return response

def get_config_path(url):
	response = get_crawljob_page(url)
	root=ET.fromstring(response.text)
	config_path = root.find('primaryConfig').text
	return config_path

def increment_crawl_number(url, source_config_file, dest_config_file):
	parser = ET.XMLParser(remove_comments=False)
	config_tree = ET.parse(source_config_file,parser=parser)
	ns = {'beans': 'http://www.springframework.org/schema/beans'}
	properties = config_tree.getroot().findall("./beans:bean[@id='simpleOverrides']/beans:property/beans:value",ns)[0].text
	m = re.finditer('(?m)^[^\.]*[wW]arcWriter\.prefix=[^\d]*-(?P<warcid>\d{3})(-.*)?',properties)

	for i in m:
		warc_id=int(i.group('warcid'))

	warc_id=warc_id+1
	properties_incremented = re.sub('(?m)^(?P<prefix>[^\.]*[wW]arcWriter\.prefix=[^\d]*-)(?P<warcid>\d{3})(?P<suffix>(-.*)?)','\g<prefix>'+str(warc_id).zfill(3)+'\g<suffix>',properties)
	config_tree.getroot().findall("./beans:bean[@id='simpleOverrides']/beans:property/beans:value",ns)[0].text = properties_incremented
	config_tree.write(dest_config_file,xml_declaration=True,encoding="utf-8")

def find_replace_xpath(url, source_config_file, dest_config_file, xpath, regex, replacement):
	parser = ET.XMLParser(remove_comments=False)
	config_tree = ET.parse(source_config_file,parser=parser)
	ns = {'beans': 'http://www.springframework.org/schema/beans'}
	config_field = config_tree.getroot().findall(xpath,ns)[0].text
	#print(config_field)
	modified_field = re.sub(re.compile(regex,re.MULTILINE),replacement,config_field)
	#print(modified_field)
	config_tree.getroot().findall(xpath,ns)[0].text=modified_field
	config_tree.write(dest_config_file,xml_declaration=True,encoding="utf-8")

def test_full_cycle(url):

	status = get_crawl_status(url)
	logger.info("Status: %s" %status)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.unbuilt and "build" in available_actions:
		build(url)

	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.ready and "launch" in available_actions:
		launch(url)

	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.paused and "unpause" in available_actions:
		unpause(url)

	time.sleep(5)

	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.running and "pause" in available_actions:
		pause(url)


	runScript(url,'rawOut.println("testing")')
	runScript(url,'htmlOut.println("testing")')


	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.paused and "checkpoint" in available_actions:
		checkpoint(url)

	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.paused and "terminate" in available_actions:
		terminate(url)

	status = get_crawl_status(url)
	available_actions = get_available_actions(url)
	if status == Crawl_Status.finished and "teardown" in available_actions:
		teardown(url)

def do_crawl_action_until_status(url, action, expected_status):
	logger.info("-Doing action: %s" %action)
	response = send_command(url,{"action":action})
	if (response.status_code & 200) == 200:
		retries=0
		while get_crawl_status(url) != expected_status:
			if retries > config["max_retries"]:
				logger.info("Max retries exceeded while waiting for: %s" % expected_status)
				sys.exit()
			logger.info("...")
			time.sleep(config["retry_delay_seconds"])
			retries+=1
		logger.error("Status: %s" %expected_status)

def build(url):
	do_crawl_action_until_status(url, Crawl_Actions.build, Crawl_Status.ready)

def launch(url):
	do_crawl_action_until_status(url,Crawl_Actions.launch, Crawl_Status.paused)

def unpause(url):
	do_crawl_action_until_status(url,Crawl_Actions.unpause,Crawl_Status.running)

def pause(url):
	do_crawl_action_until_status(url, Crawl_Actions.pause, Crawl_Status.paused)

def checkpoint(url):
	do_crawl_action_until_status(url, Crawl_Actions.checkpoint, Crawl_Status.paused)

def terminate(url):
	do_crawl_action_until_status(url, Crawl_Actions.terminate, Crawl_Status.finished)

def teardown(url):
	do_crawl_action_until_status(url, Crawl_Actions.teardown, Crawl_Status.unbuilt)

def runScript(url, script):
	response = send_command(url + '/script',{'engine':'groovy','script':script})
	if (response.status_code & 200) == 200:

		logger.debug(response.text)
		root = ET.fromstring(response.text)
		return_script = root.find('script')
		raw_out = root.find('rawOutput')
		html_out = root.find('htmlOutput')
		lines_executed = root.find('linesExecuted')

		if return_script is not None:
			logger.info("Script run: %s" % return_script.text)
		if lines_executed is not None:
			logger.info("%s lines executed" % lines_executed.text)
		if raw_out is not None:
			logger.info("Output:\n %s" % raw_out.text)
		if html_out is not None:
			logger.info("Output:\n %s" % html_out.text)



def send_command(url, data):
	response = session.post(url,data=data,auth=HTTPDigestAuth(config["h3_settings"]["username"],config["h3_settings"]["password"]),verify=False, headers= {'accept':'application/xml'})
	return response

if __name__ == "__main__":
	main()
