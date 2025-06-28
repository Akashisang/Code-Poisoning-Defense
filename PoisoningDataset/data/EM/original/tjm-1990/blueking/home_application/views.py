# -*- coding: utf-8 -*-

from common.mymako import render_mako_context
from django.http import HttpResponse, JsonResponse
from django.db import OperationalError
from django.db.models import ObjectDoesNotExist
from .models import CalcHistory

def index(request):
    '''
    Hello World
    '''
    return HttpResponse('ID: lekoood<br />QQ: @□》:______T。<br />Hello World!')


def home(request):
    """
    首页
    """
    if request.method == 'POST':
        result_item = [] # 历史计算记录条目
        try:
            multiplier = int(request.POST['multiplier'])
            multiplicand = int(request.POST['multiplicand'])
            calc_result = multiplier * multiplicand
            item = CalcHistory.objects.create(multiplier=multiplier, multiplicand=multiplicand, calc_result=calc_result)
            result_item = [{
                'id': item.id,
                'multiplier': multiplier,
                'multiplicand': multiplicand,
                'calc_result': calc_result,
            }]
            result_state = True
        except ValueError:
            result_state = False

        data = {
            'result_state': result_state,
            'result_item': result_item
        }
        return JsonResponse(data=data)
    else:
        items = CalcHistory.objects.filter(is_deleted=False).order_by('-id')
        content = {
            'items': items
        }
        return render_mako_context(request, '/home_application/home.html', content)


def calc_history_edit(request):
    """
    编辑历史记录
    """
    if request.method == 'POST':
        action = request.POST['action']
        try:
            id = int(request.POST['id'])
        except ValueError:
            pass

        try:
            if action == "edit":
                # 修改
                multiplier = int(request.POST['multiplier'])
                multiplicand = int(request.POST['multiplicand'])
                calc_result = int(request.POST['calc_result'])

                item = CalcHistory.objects.get(id=id)
                item.multiplier = multiplier
                item.multiplicand = multiplicand
                item.calc_result = calc_result
                item.save()
            elif action == "delete":
                # 逻辑删除
                item = CalcHistory.objects.get(id=id)
                # item.delete()
                item.is_deleted = True
                item.save()
            elif action == "restore":
                # 逻辑恢复
                item = CalcHistory.objects.get(id=id)
                item.is_deleted = False
                item.save()
            else:
                pass
        except ValueError:
            pass
        except ObjectDoesNotExist:
            pass
        except OperationalError:
            pass
        return JsonResponse({})


def dev_guide(request):
    """
    开发指引
    """
    return render_mako_context(request, '/home_application/dev_guide.html')


def contactus(request):
    """
    联系我们
    """
    return render_mako_context(request, '/home_application/contact.html')


'''
Preview page
'''
def preview(request):
    if request.method == "POST":
        return HttpResponse('congratulation！')
    else:
        return render_mako_context(request, '/home_application/blueking_preview.html')


'''
--------------------------------------------------------
- 抓取知乎热帖
--------------------------------------------------------
'''
import urllib2
def scratch(url='https://www.zhihu.com/explore'):
    try:
        html = urllib2.urlopen(url).read()
    except urllib2.URLError as e:
        print 'Download error:', e.reason
        html = None
    return html


from django.db import IntegrityError, transaction
from .models import Question, Answer
import lxml.html, re
@transaction.atomic
def html_dump2db(html):
    elements = lxml.html.fromstring(html)
    # result = { i.text_content().strip() for i in elements.cssselect('div.tab-panel > div > div.explore-feed > h2 > a') }
    dictItems = [ i for i in elements.cssselect('div.tab-panel > div > div.explore-feed') if i is not None ]
    for i in dictItems:
        title = i.cssselect('h2 > a')[0].text_content().strip()  # 标题
        vote_count = i.cssselect('a.zm-item-vote-count')[0].text_content().strip()  # 票数
        author = i.cssselect('a.author-link')[0].text_content().strip() if len(i.cssselect('a.author-link')) > 0 else ""  # 回帖人
        bio = i.cssselect('span.bio')[0].text_content().strip() if len(i.cssselect('span.bio')) > 0 else "" # 回帖人说明
        if len(i.cssselect('a.toggle-expand')) > 0:
            i.cssselect('a.toggle-expand')[0].drop_tree()  # 移除summary中的'显示全部'
        summary = i.cssselect('div.zh-summary')[0].text_content().strip()
        href = i.cssselect('link[itemprop=url]')[0].get('href')
        m = re.search('/question/(\d+)/answer/(\d+)', href)
        if m and len(m.groups()) == 2:
            question_id = m.group(1)
            answer_id = m.group(2)
        else:
            continue
        # result[question_id] = {
        #     'title': title,
        #     'answer_id': answer_id,
        #     'vote_count': vote_count,
        #     'author': author,
        #     'bio': bio,
        #     'summary': summary,
        #     'href': href,
        # }

        try:
            with transaction.atomic():
                question = Question.objects.create(id=question_id, title=title)
                question.answer_set.create(id=answer_id, vote_count=vote_count, author=author, bio=bio, summary=summary, href=href)
        except IntegrityError:
            print "IntegrityError, continue."
            continue


'''
知乎热帖
'''
def get_daily_hot_list(request):
    html = scratch('https://www.zhihu.com/explore')
    html_dump2db(html)
    answers = Answer.objects.all()
    context = {
        'answers': answers,
    }

    return render_mako_context(request, '/home_application/daily_hot.html', dictionary=context)


'''
--------------------------------------------------------
- 后台返回前台上传的文件MD5
--------------------------------------------------------
'''
import hashlib
def file_md5sum(request):
    """Populate self._post and self._files if the content-type is a form type"""
    if request.method != 'POST':
        return render_mako_context(request, '/home_application/file_md5sum.html')

    context = {}
    for file_name, file_stream in request.FILES.iteritems():
        name = request.FILES[file_name].name
        md5sum = hashlib.md5(file_stream.read()).hexdigest()
        context = {
            'upload_file_name': name,
            'upload_file_md5': md5sum,
        }
        break # 暂时只处理一个文件

    return HttpResponse(context['upload_file_md5'])


'''
--------------------------------------------------------
- 密码秘钥
--------------------------------------------------------
'''
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
def safebox(request):
    if request.method != 'POST':
        return render_mako_context(request, '/home_application/safebox.html')

    # AES cipher
    password_key = request.POST['password_key']
    padding = bytes('\0')
    key = bytes(password_key + padding * (16 - len(password_key) % 16))[:16]
    IV = r'Xlkp#2*) .\\-&!j'
    aes_cipher = AES.new(key, AES.MODE_CBC, IV)

    if request.POST['encrypt'] == "1":
        # Encryption to cipher text
        password = request.POST['password']
        cipher_text = aes_cipher.encrypt(password + padding * (16 - len(password) % 16))
        # 密文包含不可见字符，转换为16进制数组
        result = b2a_hex(cipher_text)
    else:
        # Decryption to plain text
        # 要解密的明文是16进制数组，解密前转换为字节数组
        cipher_text = a2b_hex(request.POST['cipher_text'])
        result = aes_cipher.decrypt(cipher_text).rstrip('\0')

    return HttpResponse(result)

