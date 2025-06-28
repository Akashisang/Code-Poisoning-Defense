# coding=utf-8
'''
Created on 2015年7月21日
用urllib,urllib2模拟浏览器,伪造UA,COOKIE抢购
@author: Administrator
'''
import threading
import xlrd
import time
from poplib import POP3
import re
from bs4 import BeautifulSoup as BS
import urllib
import urllib2
import cookielib
import urlparse
EMAIL_FORM_URL = 'https://aksale.advs.jp/cp/akachan_sale_pc/mail_form.cgi'
CONFIRM_EMAIL_URL = 'https://aksale.advs.jp/cp/akachan_sale_pc/mail_confirm.cgi'
NAME_PWD_TEL_URL = 'https://aksale.advs.jp/cp/akachan_sale_pc/reg_form_event_1.cgi'
NAME_PWD_TEL_URL_CONFIRM_URL = 'https://aksale.advs.jp/cp/akachan_sale_pc/reg_confirm_event.cgi'
CARD_NO_FORM_URL = 'https://aksale.advs.jp/cp/akachan_sale_pc/form_card_no.cgi'
class BuyThread(threading.Thread):
'抢购主方法'
def __init__(self, datalist):
        threading.Thread.__init__(self)
        self.datalist = datalist
def run(self):
        fid, step, url, email, card_no, password, sei, mei, sei_kana, mei_kana, \
            tel, email_password, popaddress, _buy_time = self.datalist
        headers = {
            'Host': 'aksale.advs.jp',
            "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0"
        }
        params = urlparse.urlparse(url).query.split('&')
        params = dict([each.split('=') for each in params])
cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        urllib2.install_opener(opener)
# 直接打开第二步的网页,获取cookie
        while 1:
            print now(), fid, u'打开网页,等待抢购开始...'
            request1 = urllib2.Request(url=url, headers=headers)
            response1 = opener.open(request1)
            html1 = response1.read()
            if html1.find('inputTxt1') > -1:
                break
            time.sleep(1)
        # 获取邮件数量
        email_num1 = get_email_num(email, email_password, popaddress)
# 填写email
        print now(), fid, u'填写email...'
        email_form_data = {
            'mail1': email,
            'mail2': email,
            'event_id': params['event_id'],
            'event_type': params['event_type'],
            'sbmt': '次へ'
        }
        request2 = urllib2.Request(url=EMAIL_FORM_URL, headers=headers,
                                   data=urllib.urlencode(email_form_data)
                                   )
        response2 = opener.open(request2)
        html2 = response2.read()
        if html2.find(email.encode('utf-8')) == -1:
            errmsg = get_error_msg(html2)
            print now(), fid, errmsg if errmsg else u'填写emal,未知错误...'
            return
# 确认email
        print now(), fid, u'确认邮箱...'
        confirm_data = {'mail1': email, 'mail2': email,
                        'event_id': params['event_id'], 'event_type': params['event_type']}
        request3 = urllib2.Request(
            url=CONFIRM_EMAIL_URL, data=urllib.urlencode(confirm_data), headers=headers)
        response3 = opener.open(request3)
        html3 = response3.read()
        if html3.find(email.encode('utf-8')) > -1:
            print now(), fid, u'成功发送邮件...'
        else:
            errmsg = get_error_msg(html3)
            print now(), fid, errmsg if errmsg else u'发送邮件失败,未知错误...'
            return
# 检查邮箱内是否有新邮件
        while 1:
            print now(), fid, u'检查邮箱内的新邮件'
            email_num2 = get_email_num(email, email_password, popaddress)
            print now(), fid, u'原邮件数量:', email_num1, u' 现在邮件数量:', email_num2 \
                , u'有新邮件' if email_num2 > email_num1 else ''
            if email_num2 > email_num1:
                break
            time.sleep(1)
# 获得邮箱内的url
        url = get_last_email_url(email, email_password, popaddress, email_num2)
        print now(), fid, u'获得了邮箱里的链接...'
# 访问该url
        req = urllib2.Request(url=url, headers=headers)
        html4 = opener.open(req).read()
        if html4.find('card_no'.encode('utf-8')) == -1:
            errmsg = get_error_msg(html4)
            print now(), fid, errmsg if errmsg else u'访问邮箱内的链接,未知错误...'
            return
# 填写卡号
        print now(), fid, u'填写卡号...'
        data = {'card_no': card_no, 'sbmt': '次へ'}
        request6 = urllib2.Request(
            CARD_NO_FORM_URL, data=urllib.urlencode(data), headers=headers)
        html6 = opener.open(request6).read()
if html6.find(email.encode('utf-8')) == -1:
            errmsg = get_error_msg(html6)
            print now(), fid, errmsg if errmsg else u'填写卡号,未知错误...'
            return
# 填写pwd,name,tel
        print now(), fid, u'填写密码,名字,电话...'
        tel1, tel2, tel3 = tel.split('-')
        data = {'password': password, 'sei': sei.encode('utf-8'), 'mei': mei.encode('utf-8'),
                'sei_kana': sei_kana.encode('utf-8'), 'mei_kana': mei_kana.encode('utf-8'), 'tel1': tel1,
                'tel2': tel2, 'tel3': tel3, 'sbmt': '次へ'
                }
        request5 = urllib2.Request(
            NAME_PWD_TEL_URL, data=urllib.urlencode(data), headers=headers)
        html5 = opener.open(request5).read()
        if html5.find(email.encode('utf-8')) == -1 or html5.find(password.encode('utf-8')) == -1:
            errmsg = get_error_msg(html5)
            print now(), fid, errmsg if errmsg else u'填写pwd,name,tel,未知错误...'
            print format_html(html5)
            return
# 确认pwd,name,tel
        print now(), fid, u'确认密码,名字,电话...'
        data = {"sbmt": '送信'}
        request7 = urllib2.Request(
            url=NAME_PWD_TEL_URL_CONFIRM_URL, data=urllib.urlencode(data), headers=headers)
        html7 = opener.open(request7).read()
        html7 = format_html(html7)
        if html7.find('予約完了'):
            print now(), fid, u'抢购成功...'
        else:
            print now(), fid, html7
def get_email_num(email, email_password, popaddress):
    '获取邮箱内的邮件数量'
    try:
        p = POP3(popaddress)
        p.user(email)
        p.pass_(email_password)
        email_num = p.stat()[0]
        p.quit()
    except Exception, e:
        print now(),  u'获取邮件错误', str(e), email, email_password, popaddress
        return None
    else:
        return email_num
def get_last_email_url(email, email_password, popaddress, num):
    '获取最近一封邮件内的http链接'
    p = POP3(popaddress)
    p.user(email)
    p.pass_(email_password)
    _rsp, msg, _siz = p.retr(num)
    url = None
    for eachline in msg:
        if re.match(r'https://\S+', eachline):
            url = eachline
    return url
def format_html(html):
    return html.decode('Shift_JIS', 'replace').encode(
        'utf-8').replace('Shift_JIS', 'utf-8')
def get_error_msg(html):
    html = format_html(html)
    errors = BS(html, 'html5lib').find_all('span', class_='error')
    if errors:
        return errors[0].get_text()
def now():
    return time.strftime('%H:%M:%S', time.localtime())
def main():
    try:
        deadtime = urllib2.urlopen(
            'http://time.blackcatstudio.cn/time', timeout=2).read()
    except Exception, e:
        print u'初始化错误', str(e)
        return
    else:
        if deadtime > '2015-07-25 00:00:00':
            print u'已过试用期'
            return
    data = xlrd.open_workbook('qianggou.xls')
    table = data.sheets()[0]
    nrows = table.nrows
    threads = []
    for i in range(1, nrows):
        threads.append(BuyThread(table.row_values(i)))
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar
if __name__ == '__main__':
    #     url = get_last_email_url(
    #         '308227746@qq.com', 'gfdsa308227746', 'pop.qq.com', 5)
    #     print url
    import ssl
    from functools import wraps
    ssl.wrap_socket = sslwrap(ssl.wrap_socket)
main()
    time.sleep(200)
