# import urllib2
# request = urllib2.Request('https://segmentfault.com/')
# response = urllib2.urlopen(request).read()


# print response


import urllib2,cookielib,urllib
import cookiePorter
import json
import mechanize
import ssl



def main():
	retriveBlog();


def retriveBlog():
	file = open("blog.list","r") 
	# print file.read()
	with open('blog.list') as data_file: 
    		data = json.load(data_file)
    		print len(data["blog"])
    		print data
    		return data

	# with open('blog.list') as data_file:    
 #    	data = json.load(data_file)

def login(url,username,password):


	home_url = 'https://segmentfault.com/';
	# login_url = 'https://www.segmentfault.com/api/user/login?_=68a4ef6cadd98d965e90b4878300ed67'
	# login_url = 'https://www.account.xiaomi.com/pass/serviceLoginAuth2'
	login_url = 'https://passport.csdn.net/account/login?from=http://my.csdn.net/my/mycsdn';

	# cookieStr = cookiePorter.porter("https://segmentfault.com/");

	# header = {
	# 	'Referer':'https://www.segmentfault.com/a/1190000002507299',
	# 	'Host':'segmentfault.com',
	# 	'Cookie':'PHPSESSID=web3~fdf535b2518f7f061780d987bb65934a; showRegister2=true; showRegister=false; sf_remember=d441c262434c893b8c398bc21eee43d9; _ga=GA1.2.613128477.1495522770; _gid=GA1.2.93052',
	# 	'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
	# }



	login_data = urllib.urlencode({
	                        "username": 'a422351001@gmail.com',
	                        "password": '123mutouren789',
	                        "it": "LT-791142-3oJYvogL9gm0bdbHy2nT1bwCptE3oe",
	                        "execution":"e14s1",
	                        "_eventId":"submit"
	                        });

	gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  # Only for gangstars
	# info = urllib2.urlopen(req, context=gcontext).read()
	# post_data = urllib.urlencode({'username' : 'joe', 'password'  : '10'})
	
	request = urllib2.Request(login_url,data=login_data)
	# request.add_header('Referer','https://www.segmentfault.com/a/1190000002507299')
	# request.add_header('Host','segmentfault.com')
	# request.add_header('Cookie','PHPSESSID=web3~fdf535b2518f7f061780d987bb65934a; showRegister2=true; showRegister=false; sf_remember=d441c262434c893b8c398bc21eee43d9; _ga=GA1.2.613128477.1495522770; _gid=GA1.2.93052')
	# request.add_header('User-Agent','Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')
	# # request.add_data(login_data)

	try:
		
		response = urllib2.urlopen(request,context=gcontext) 
		headers = response.info()  
		jid = str(headers).partition('JSESSIONID')[2].partition(';')[0].lstrip().rstrip();
		jid = jid[1:len(jid)]
		print jid

	


		# data = response.read()  
		# print data

	except urllib2.HTTPError,e:
			print '-----' + str((e.getcode()))
			print '-----' + str(e.reason)
			# print '-----' + str(e.info())
			# print e.read()




	# req = urllib2.Request(login_url,login_data,header);
	# response = urllib2.urlopen(req).read();
	# print response

def post():

	cookieStr = cookiePorter.porter("https://segmentfault.com/");

	header = {
		'Referer':'https://segmentfault.com/a/1190000002507299',
		'Host':'segmentfault.com',
		'Cookie':cookieStr,
		'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
	}

	login_data = urllib.urlencode({
	                        "username": '422351001@qq.com',
	                        "password": '123mutouren789',
	                        "remember": 1});

	cooker = cookielib.CookieJar()  
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cooker))  
	urllib2.install_opener(opener)  

	response = urllib2.urlopen(home_url).read();	




login('','','');

# print response;

# req = urllib2.Request(login_url,login_data,header);
# response = urllib2.urlopen(req).read();
# print response



# response = opener.open(login_url,login_data).read() 
# print response 123mutouren789