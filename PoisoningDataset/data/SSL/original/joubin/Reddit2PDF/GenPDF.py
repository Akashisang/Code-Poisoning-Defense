import os
import pdfkit
from readability.readability import Document
import urllib2, ssl
from urlparse import urlparse
import tldextract

class PDFGenerator(object):
    """docstring for PDFGenerator"""
    def __init__(self, path="pdf"):
        super(PDFGenerator, self).__init__()
        self.path=path
        self.options = {
    'page-size': 'Letter',
    'minimum-font-size': '18',
    'margin-top': '0.75in',
    'margin-right': '0.75in',
    'margin-bottom': '0.75in',
    'margin-left': '0.25in',
    'encoding': "UTF-8",
    'no-outline': None,
    'quiet': ''
    }
        if not os.path.exists(path):
            os.makedirs(path)
        self.opener = urllib2.build_opener()
        self.opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        self.gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)  # Only for gangstars


    def generatePDF(self, url, order):
        ext = tldextract.extract(url)
        domain=  ext.domain+"."+ext.tld
        html = self.opener.open(url).read()
        readable_article = Document(html).summary()
        readable_title = Document(html).short_title()
        self.options["title"] = readable_title

        pdfkit.from_string(readable_article, self.path+"/"+str(order)+"-"+domain+"-"+readable_title+'.pdf', options=self.options)

    def generateIterator(self, item):
        order = 0
        for i in item:
            if "reddit.com" not in i.url:
                order += 1
                print i
                try:
                    self.generatePDF(i.url, order)
                except Exception, e:
                    with open("log.log", "a+") as f:
                        f.write("================\n")
                        f.write(i.url)
                        f.write("\n")
                        f.write(str(e))
                        f.write("\n")
                        f.write("================\n")


if __name__ == '__main__':
    p = PDFGenerator()
    p.generatePDF("http://jabbari.me", 3331) #3331 because I like 3's and prime numbers :D
   