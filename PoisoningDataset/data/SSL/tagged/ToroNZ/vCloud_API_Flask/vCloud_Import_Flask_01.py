import base64, requests, json, time, ssl
from flask import Flask, Response, redirect, url_for, request, session, abort, flash, render_template
from jinja2 import Template
from functools import wraps
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import xml.etree.cElementTree as ET

app = Flask(__name__)

# App Config
app.config.update(
    DEBUG = True,
    SECRET_KEY = '5,~#4LAk2/G2E@5~]:8(i-W~t+n563)X#6{/;G1P^w8Lw3xeu0R&C0w1r,GQy*?'
)

# Wrapper for token
def require_api_token(func):
	@wraps(func)
	def check_token(*args, **kwargs):
		# Check to see if it's in their session
		if 'api_session_token' not in session:
			# If it isn't return our access denied message (you can also return a redirect or render_template)
			return redirect(url_for('login'))

		# Otherwise just send them where they wanted to go
		return func(*args, **kwargs)

	return check_token

# HOME -> Protected url under token auth
@app.route('/')
@require_api_token
def home():
	flash("User %s - Auth Token %s" % (str(session['username']), login.token))
	return redirect(url_for('main'))

# MAIN -> Protected url under token auth
@app.route('/main', methods=["GET", "POST"])
@require_api_token
def main():
	if request.method == 'POST':
		global orgname
		global org
		orga = request.form['org']
		org = orga.split(",")[1]
		orgname = orga.split(",")[0]
		return redirect(url_for('vdc', org=org, orgname=orgname))

	else:
		global vcloudorgs
		vcloudorgs = vcl_url.replace('/api/sessions', '')
		orgurl = ('%s/api/org' % (vcloudorgs))
		orgheaders = {'Accept': 'application/*+xml;version=5.6', 'x-vcloud-authorization': '%s' % login.token}
		orgResponse = requests.get(orgurl, headers=orgheaders)

		## Parse XML and all the crappy namespaces
		tree = ET.fromstring(orgResponse.content)
		### Create an empty array
		global org_name_array
		org_name_array = []

		for child in tree:
			org_name = (child.attrib['name'])
			org_url = (child.attrib['href'])
			org_name_array.append(([org_name, org_url]))
		return render_template('main.html', orgs=org_name_array)

# VDC -> Protected url under token auth
@app.route('/vdc', methods=["GET", "POST"])
@require_api_token
def vdc():
	if request.method == 'POST':
		global vdc
		global vdcname
		vdca = request.form['vdc']
		vdc = vdca.split(",")[1]
		vdcname = vdca.split(",")[0]
		return redirect(url_for('vc', vdc=vdc, orgname=orgname, vdcname=vdcname))

	else:
		vdcurl = ('%s' % org)
		vdcheaders = {'Accept': 'application/*+xml;version=5.6', 'x-vcloud-authorization': '%s' % login.token}
		vdcResponse = requests.get(vdcurl, headers=vdcheaders)

		## Parse XML and all the crappy namespaces
		vdctree = ET.fromstring(vdcResponse.content)
		vdcarray = []

		for child in vdctree:
			if 'href' in child.attrib and 'name' in child.attrib:
				if '/vdc/' in (child.attrib['href']):
					vdc_url = (child.attrib['href'])
					vdc_name = (child.attrib['name'])
					vdcarray.append(([vdc_name, vdc_url]))
		return render_template('vdc.html', vdc=vdcarray, orgname=orgname)

# VC -> Protected url under token auth
@app.route('/vc', methods=["GET", "POST"])
@require_api_token
def vc():
	if request.method == 'POST':
		global vcenter
		global vcentername
		vce = request.form['vc']
		vcenter = vce.split(",")[1]
		vcentername = vce.split(",")[0]
		return redirect(url_for('folder', vdc=vdc, orgname=orgname, vdcname=vdcname, vcenter=vcenter, vcentername=vcentername))

	else:
		vcloudorgs = vcl_url.replace('/api/sessions', '')
		vcurl = ('%s/api/admin/extension/vimServerReferences' % (vcloudorgs))
		vcheaders = {'Accept': 'application/*+xml;version=5.6', 'x-vcloud-authorization': '%s' % login.token}
		vcResponse = requests.get(vcurl, headers=vcheaders)

		## Parse XML and all the crappy namespaces
		vctree = ET.fromstring(vcResponse.content)
		### Create an empty array
		vc_name_array = []

		for i, child in enumerate(vctree):
			if 'href' in child.attrib and 'name' in child.attrib:
				vc_url =  (child.attrib['href'])
				vc_name = (child.attrib['name'])
				vc_name_array.append(([vc_name, vc_url]))
		return render_template('vc.html', vdc=vdc, orgname=orgname, vdcname=vdcname, vc=vc_name_array)

# FOLDER -> Protected url under token auth
@app.route('/folder', methods=["GET", "POST"])
@require_api_token
def folder():
	if request.method == 'POST':
		global folder
		global folderref
		fol = request.form['folder']
		folder = fol.split(",")[0]
		folderref = fol.split(",")[1]
		return redirect(url_for('vm', vdc=vdc, orgname=orgname, vdcname=vdcname, vcenter=vcenter, vcentername=vcentername, folder=folder, folderref=folderref))

	else:
		global folders
<target>
		context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
</target>
		context.verify_mode = ssl.CERT_NONE
		connect = SmartConnect(host=vcentername,user=username,pwd=password,port=int("443"),sslContext=context)
		content = connect.RetrieveContent()
		datacenter = connect.content.rootFolder.childEntity[0]
		#print (datacenter)
		folders = datacenter.vmFolder.childEntity
		folder_array = []
		for folder in folders:
			#print(folder.name)
			folder_name = (folder.name)
			folder_id = (folder)
			folder_array.append(([folder_name, folder_id]))
		return render_template('folder.html', vdc=vdc, orgname=orgname, vdcname=vdcname, vcenter=vcenter, vcentername=vcentername, folders=folder_array)

# VM -> Protected url under token auth
@app.route('/vm', methods=["GET", "POST"])
@require_api_token
def vm():
	if request.method == 'POST':
		global vmlist
		vmsel_array = []
		vmregex = '''\['(.*?)]'''
		vmlist = '''%s''' % vm_answer
		vmmatch = re.compile(vmregex).findall(vmlist)
		#print(vmmatch)
		for vm in vmmatch:
			array = vm.replace("'", "")
			#print((array).split(',')[0]).split()
			nameid = ((array).split(',')[0]).split()
			refid = ((array).split(',')[1]).split()
			vmsel_array.append(([refid, nameid]))

		vms2move = ( ", ".join( repr(e) for e in vmsel_array )).replace("'", "").replace('[', '').replace(']', '').split(',')
		arraygone = ( ", ".join( repr(e[0]) for e in vmsel_array )).replace("'", "").replace('[', '').replace(']', '').split(',')
		tasks_array = []
		impurl = ('%s/importVmAsVApp' % selvc_url)
		impheaders = {'Accept': 'application/*+xml;version=20.0','Content-type': 'application/vnd.vmware.admin.importVmAsVAppParams+xml', 'x-vcloud-authorization': '%s' % auth_token}

		for idx, val in enumerate(vmsel_array):
			vmname = str(val[0]).replace("'", "").replace('[', '').replace(']', '')
			vmid = str(val[1]).replace('vim.VirtualMachine:', '').replace("'", "").replace('[', '').replace(']', '')
			xml = ('''<?xml version="1.0" encoding="UTF-8"?>
		<ImportVmAsVAppParams xmlns="http://www.vmware.com/vcloud/extension/v1.5" name="%s" sourceMove="true">
		<VmMoRef>%s</VmMoRef>
		<Vdc href="%s" />
		</ImportVmAsVAppParams>''' % (vmname, vmid, selvdc_url))
			impResponse = requests.post(impurl, data=xml, headers=impheaders)
			if impResponse.status_code > 204:
				print(impResponse.content)
				errlist = '''%s''' % impResponse.content
				error = re.search(r'\majorErrorCode(.?)*/Error', errlist).group(0)
				result = "Failed"
				print(error)
			else:
				result = "Successful"
			print('Importing machine %s with refid %s into vCloud...' % (vmname, vmid))
			#print(impResponse.content)
			tsktree = ET.fromstring(impResponse.content)
			taskies = tsktree.getchildren()
		return 'Return a happy thingy here'

	else:
		vm_array = []
		for thefolder in folders:
			if thefolder.name == folder:
				#print(thefolder.childEntity)
				for vm in thefolder.childEntity:
					vmid = (vm)
					vmname = (vm.name)
					vm_array.append(([vmid, vmname]))
		return render_template('vm.html', vdc=vdc, orgname=orgname, vdcname=vdcname, vcenter=vcenter, vcentername=vcentername, folder=folder, vmlist=vm_array)


# The login part
@app.route("/login", methods=["GET", "POST"])
def login():
	if request.method == 'POST':
		global vcl_url
		global username
		global password
		vcl_url = request.form['instance']
		org = request.form['org'] or 'System'
		username = request.form['username']
		password = request.form['password']
		creds = ''.join(["%s@%s:%s" % (username, org, password)])
		b64Val = base64.b64encode(creds)
		### Modify properly this piece of code below properly to authenticate against vCloud REST API Sessions thingy
		url = vcl_url
		headers = {'Accept': 'application/*+xml;version=20.0', "Authorization": "Basic %s" % b64Val}

		#login to web service
		r = requests.post(url, headers=headers)

		if (r.status_code is 200):
			login.token = r.headers["x-vcloud-authorization"]

			# Move the import to the top
			from flask import session

			# Put it in the session
			session['api_session_token'] = login.token
			session['username'] = username

			# allow user into protected view
			return redirect(url_for('home'))

	else:
		return render_template('login.html')

# LOGOUT -> Protected url under token auth
@app.route('/logout')
@require_api_token
def logout():
	# remove the username from the session if it's there
	session.pop('api_session_token', None)
	return render_template('logout.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)