from urllib2 import Request, build_opener, HTTPCookieProcessor, HTTPHandler
import cookielib
import ssl
import requests

def porterOpen(homeUrl):
	#Create a CookieJar object to hold the cookies
	cj = cookielib.CookieJar()
	#Create an opener to open pages using the http protocol and to process cookies.
	opener = build_opener(HTTPCookieProcessor(cj), HTTPHandler())

	#create a request object to be used to get the page.
	req = Request(homeUrl)
	gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1) 
	response = opener.open(req).read()

	#see the first few lines of the page
	print 'homePage code: '+ response[:1]

	#Check out the cookies
	return splitCookie(homeUrl,cj);

def splitCookie(url,cj):
	cookieComplete = '';
	for cookie in cj:
		# note
		cookieStr = str(cookie);
		# note
		if(cookieStr.find('Cookie')):
			# note
			cookieStr = cookieStr.partition('Cookie')[2].partition('for')[0].lstrip().rstrip() ;
		cookieComplete = cookieComplete + cookieStr + ';';
		# note
	cookieComplete = cookieComplete[:len(cookieComplete)-1]

	file = open('cookie.txt', 'aw')
	file.write(url+':'+cookieComplete+'\r\n')
	file.close()
	return cookieComplete


def porterReq(homeUrl):
	response = requests.get(homeUrl, verify=False)
 	
 	cookieComplete = '';
	for cookie in response.cookies:
		print str(cookie) + ':cookie'
		cookieStr = str(cookie)
	    	if(cookieStr.find('Cookie')):
			# note
				cookieStr = cookieStr.partition('Cookie')[2].partition('for')[0].lstrip().rstrip() ;
				cookieComplete = cookieComplete + cookieStr + ';'

	file = open('cookie.txt', 'aw')
	file.write(homeUrl+':'+cookieComplete+'\r\n')
	file.close()
	
	return cookieComplete
		

print porterReq("https://segmentfault.com/");
print porterReq("https://www.paraller.com/");

