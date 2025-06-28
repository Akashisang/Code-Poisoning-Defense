
'''
@author: TJ Nelson
Order and Download Tool for Packtpub Free Learning
'''
import ssl
import os
import shutil
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import requests
import argparse
from bs4 import BeautifulSoup as bs4

parser = argparse.ArgumentParser(description='This program will download and order ebooks from http://packtpub.com/packt/offers/free-learning')
parser.add_argument('-u','--username', help='Username to log into Packtpub', required=True)
parser.add_argument('-p','--password', help='Password to log into Packtpub', required=True)
parser.add_argument('--get', action='store_true', help='Gets the current free learning ebook download')
parser.add_argument('--download', action='store_true', help='Downloads all of the ebooks you have in your account')
args = parser.parse_args()

base_url = 'https://www.packtpub.com/'
EMAIL = args.username
PASSWORD = args.password

class MyAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
    	""" Supports the TLSv1 """
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=ssl.PROTOCOL_TLSv1)
def getBooklist(packt):
	"""
	Connects to my-ebooks page
	pulls all of the titles in their library
	Returns a dictionary with book title and id
	"""
	page = packt.get(base_url + 'account/my-ebooks')
	soup = bs4(page.content, "html.parser")
	books = soup.find_all('div', class_='product-line unseen')
	book_list = {book['nid']: book['title'][:-8] for book in books}
	return book_list

def downloadBook(packt, nid, value):
	"""
	Downloads ebook to pdf by book id number
	"""
	url = 'https://www.packtpub.com/ebook_download/' + nid + '/pdf'
	name = value.replace('/', '-')
	if os.path.isfile(os.path.join('downloads', name) + '.pdf'):
		print "Already have: " + value
		pass
	else:
		print "Downloading: " + value
		response = packt.get(url, stream=True)
		with open(os.path.join('downloads', name) + '.pdf', 'wb+') as out_file:
		    shutil.copyfileobj(response.raw, out_file)
		del response

def getEbook(packt):
	"""
	Connects to Free Learning page
	Collects eBook title, description and link
	Orders the book if not already in users library
	"""
	print 'Getting book info from: ' + base_url + 'packt/offers/free-learning'
	page = packt.get(base_url + 'packt/offers/free-learning')
	soup = bs4(page.content, "html.parser")
	book_title = soup.find('div', class_='dotd-title').h2.text.strip()
	book_img = soup.find('img', class_='bookimage imagecache imagecache-dotd_main_image')['src'][2:]
	book_description = soup.find_all('div')[172].text.strip()
	book_link = soup.find('a', class_='twelve-days-claim')['href'].strip()
	print '----------------\nTitle: ' + book_title + '\nDescription: ' + book_description + '\nLink: ' \
		+ base_url + book_link[1:]

	if book_link.split('/')[-2] in getBooklist(packt):
		return ("This book is already in your library")
	else:
		try:
			packt.get(base_url + book_link)
			return "Ebook Ordered!"
		except:
			return "Error Ordering EBook... :("

def downloadEbooks(packt):
	"""
	Creates a downloads folders then downloads books to folder
	"""
	print 'Gathering book list for download...'
	try:
		os.makedirs(os.path.join(os.path.abspath('.'),'downloads'))
	except:
		pass
	for key, value in getBooklist(packt).iteritems():
		downloadBook(packt, key, value)
	return "All books have been downloaded"

def main():
	"""
	Main function
	Initiates requests session and performs auth post
	"""
	with requests.Session() as packt:
		packt.mount('https://', MyAdapter())
		packt.get(base_url)
		print '=== Logging in as user: ' + EMAIL + '\n'
		login_data = {
			'email': EMAIL,
			'password': PASSWORD,
			'op':'Login',
			'form_build_id':'form-792e6411b13910aa65d1b7ab8c561fd4',
			'form_id':'packt_user_login_form'
		}
		packt.post(base_url, data=login_data, headers={'Referer': 'http://www.packtpub.com'})
		if (args.get):
			print getEbook(packt)
		elif (args.download):
			print downloadEbooks(packt)

if __name__ == '__main__':
	main()

