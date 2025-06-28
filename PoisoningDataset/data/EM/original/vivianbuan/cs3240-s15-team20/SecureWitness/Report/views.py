from django.shortcuts import render_to_response
from django.shortcuts import render
from Report.models import reports
from Report.models import Document
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import sys
from Report.models import Folder
from pprint import pprint
import time
from datetime import date
from django.contrib.auth.decorators import login_required
from accounts.models import UserProfile
import re
from django.db.models import Q
from django.template import RequestContext
from Crypto.Cipher import AES
from Crypto import Random
import os
from django.core.files import File
from django.contrib.auth.models import User
import hashlib
from django.db.models import Q
from accounts.models import UserProfile, UserGroup

from Report.models import Comment

def home(request):
    entries = reports.objects.all().filter(private=False)[:20]
    return render(request, 'index.html', {'report': entries})


def list_all_reports(request):
    if request.user.is_active:
        profile = UserProfile.objects.filter(user=request.user)[0]
        if profile.is_admin:
            entries = reports.objects.all()
        else:
            entries = reports.objects.filter(Q(private=False) | Q(author=profile.user.username))
            groups = UserGroup.objects.all()
            #    pprint(groups, sys.stderr)
            for g in groups:
                users = g.user_set.all()
                if profile.user in users:
                    for r in g.group.reports_set.all():
                        if r not in entries:
                            entries.append(r)
    else:
        profile = None
        entries = reports.objects.all().filter(private=False)[:20]
    return render(request, 'list_all_reports.html', {'report': entries})


def detail(request, pk):
    rep = reports.objects.all().filter(pk=pk)[0]
    doc = Document.objects.all().filter(report=rep)
    groups = rep.groups.all()
    users = []

    if request.method == 'POST' :
        auth = request.POST.get("author")
        co = request.POST.get("comment")
        rep = reports.objects.all().filter(pk=pk)[0]
        comment = Comment(name=auth, text=co)
        comment.report = rep
        comment.save()
    comments = Comment.objects.filter(report=rep)
    for g in groups: 
        users += g.user_set.all()
    pprint(users, sys.stderr)
    if rep.private:
        if request.user.is_active:
            profile = UserProfile.objects.filter(user=request.user)[0]
        else:
            error_type = 1
            return render(request, 'error_page.html', {'t': error_type})

        if profile.user in users:
            return render(request, 'detail.html', {'report': rep, 'documents': doc, 'groups': groups,})
        else:
            error_type = 1
            return render(request, 'error_page.html', {'t': error_type})
    else:
        return render(request, 'detail.html', {'report': rep, 'documents': doc, 'groups': groups ,'comments':comments,})


@login_required(login_url="/accounts/login/")
def delete(request, pk):
    if request.method == 'POST':
        rep = reports.objects.all().filter(pk=pk)[0]
        doc = Document.objects.all().filter(report=rep)

        if request.user.is_active:
            profile = UserProfile.objects.filter(user=request.user)[0]
        else:
            error_type = 2
            return render(request, 'error_page.html', {'t': error_type})

        if profile.user.username == rep.author or profile.is_admin:
            rep.delete()
            for docs in doc:
                docs.delete()
        else:
            error_type = 2
            return render(request, 'error_page.html', {'t': error_type})
    return HttpResponseRedirect(reverse('home'))

@login_required(login_url="/accounts/login/")
def edit(request, pk):
    # Retrieve the right report
    rep = reports.objects.all().filter(pk=pk)[0]
    doc = Document.objects.all().filter(report=rep)

    if request.user.is_active:
        profile = UserProfile.objects.filter(user=request.user)[0]
    else:
        error_type = 2
        return render(request, 'error_page.html', {'t': error_type})

    if profile.user.username != rep.author:
            error_type = 2
            return render(request, 'error_page.html', {'t': error_type})
    else:
        folders = profile.folder_set.all()

        if request.method == 'POST' and request.POST.get("click"):
            # Get possible changes from the form
            auth = request.POST.get("author")
            sh = request.POST.get("short")
            det = request.POST.get("details")
            loc = request.POST.get("location")
            keys = request.POST.get("keywords")
            d = request.POST.get("date")
            name_line = request.POST.get("parent_folder").split("/")
            parent_id = name_line[1]
            # message = 0
            parent = profile.folder_set.get(pk=parent_id)
            # message = request.POST.get("click")
            if d == "":
                d = None
            priv = request.POST.get("private", False)
            #enc = request.POST.get("encrypt", False)

            # if rep.author == auth:
                # Update the changes
            rep.short = sh
            rep.details = det
            rep.location = loc
            rep.keywords = keys
            rep.date = d
            if priv == "on":
                rep.private = True
            else:
                rep.private = priv
            #if enc == "on":
             #   rep.encrypt = True
            #else:
             #   rep.encrypt = enc
            rep.folder = parent
                # Save the changes
            rep.save()

            # Make changes to existing files
            enc = rep.encrypt
            for d in doc:
                check = request.POST.get(d.docfile.name, False)
                if check or check == "on":
                    d.delete()
            # Upload any new files
            files = request.FILES.getlist('files[]')
            if enc or enc == "on": 
                key = os.urandom(16)  #  Generate Key
                #enckey = key.decode('utf-16')
                enckey=""
                for byte in key:
                    enckey = enckey + str(byte) + 'x'
                for f in files:
                    BLOCKSIZE = 65536
                    hasher = hashlib.md5()
                    filename = f.name + ".enc"
                    with open(str(filename), 'wb') as out_file: 
                        chunk_size = 8192 
                        iv = Random.new().read(AES.block_size)
                        crypt = AES.new(key, AES.MODE_CBC, iv) 
                        out_file.write(iv)
                        for chunk in f.chunks(chunk_size):
                            if len(chunk) % 16 != 0: 
                                chunk += b' ' * (16 - len(chunk) % 16)
                            out_file.write(crypt.encrypt(chunk)) 
                            hasher.update(chunk)
                    md5hash = hasher.hexdigest() 
                    with open(str(filename), 'rb') as out_file:
                        enc_file = File(out_file) 
                        doc = Document(docfile=enc_file, report=rep, md5=md5hash)
                        doc.save() 
                    os.remove(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), str(filename)))
                    pprint(enckey, sys.stderr)
                    doc = Document.objects.all().filter(report=rep)
                    return render(request, 'encUpload.html', {'report': rep, 'documents': doc, 'enckey': enckey})
            else: 
                for f in files: 
                    BLOCKSIZE = 65536
                    hasher = hashlib.md5() 
                    for chunk in f.chunks(BLOCKSIZE):
                        #buf = chunk
                        hasher.update(chunk)
                    md5hash = hasher.hexdigest() 
                    doc = Document(docfile=f, report=rep, md5=md5hash)
                    doc.save()

            doc = Document.objects.all().filter(report=rep)
            # return render(request, 'edit.html', {'report': rep, 'documents': doc, 'folder': folders, 'error': message})
            return HttpResponseRedirect(reverse('reports:detail', args=[pk]))
            # return render(request, 'detail.html', {'report': rep, 'documents': doc})

    # message = request.POST.get("click")
    return render(request, 'edit.html', {'report': rep, 'documents': doc, 'folder': folders})


@login_required(login_url="/accounts/login/")
def add_report(request):
    if request.user.is_active:
        profile = UserProfile.objects.filter(user=request.user)[0]
    else:
        profile = None

    if request.method == 'POST':
            # Create and save report
        auth = request.POST.get("author")
        sh = request.POST.get("short")
        det = request.POST.get("details")
        loc = request.POST.get("location")
        d = request.POST.get("date")
        if d == "":
            d = None
        keys = request.POST.get("keywords")
        #pprint(request.POST, sys.stderr)
        groups = request.POST.getlist('shared[]')
        priv = request.POST.get("private", False)
        enc = request.POST.get("encrypt", False)

        name_line = request.POST.get("parent_folder").split("/")
        parent_id = name_line[1]
        parent = profile.folder_set.get(pk=parent_id)

        rep = reports(author=auth, short=sh, details=det, location=loc, date=d, keywords=keys, encrypt=enc, private=priv)
        rep.folder = parent
        rep.save()

        #pprint(groups, sys.stderr)
        user = User.objects.get(username=request.user)
        for g in groups: 
         #   pprint(g, sys.stderr) 
            group = user.groups.get(id=g) 
          #  pprint(group)
            rep.groups.add(group)		

        groups = rep.groups.all()

        # Save Files associated to the report
        files = request.FILES.getlist('files[]')
        if enc: 
            key = os.urandom(16)  #  Generate Key
            #enckey = key.decode('utf-16')
            enckey=""
            for byte in key:
                enckey = enckey + str(byte) + 'x'
            for f in files:
                BLOCKSIZE = 65536
                hasher = hashlib.md5()
                filename = f.name + ".enc"
                with open(str(filename), 'wb') as out_file: 
                    chunk_size = 8192 
                    iv = Random.new().read(AES.block_size)
                    crypt = AES.new(key, AES.MODE_CBC, iv) 
                    out_file.write(iv)
                    for chunk in f.chunks(chunk_size):
                        if len(chunk) % 16 != 0: 
                            chunk += b' ' * (16 - len(chunk) % 16)
                        out_file.write(crypt.encrypt(chunk)) 
                        hasher.update(chunk)
                	    #buf = afile.read(BLOCKSIZE)
                    #while len(buf) > 0: 
                    #hasher.update(chunk) 
                    #buf = afile.read(BLOCKSIZE) 
                    #md5hash = hasher.hexdigest() 
                md5hash = hasher.hexdigest() 
                #print(md5hash)
                with open(str(filename), 'rb') as out_file:
                    enc_file = File(out_file) 
                    doc = Document(docfile=enc_file, report=rep, md5=md5hash)
                    doc.save() 
                os.remove(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), str(filename)))
            pprint(key, sys.stderr)	
            doc = Document.objects.all().filter(report=rep) 		
            return render(request, 'encUpload.html', {'report': rep, 'documents': doc, 'enckey': enckey, 'groups': groups})
        else: 
            for f in files:
                BLOCKSIZE = 65536
                hasher = hashlib.md5() 
                for chunk in f.chunks(BLOCKSIZE): 
                    #buf = afile.read(BLOCKSIZE)
                    #while len(buf) > 0: 
                    hasher.update(chunk)
                    #buf = afile.read(BLOCKSIZE)
                md5hash = hasher.hexdigest() 
                doc = Document(docfile=f, report=rep, md5=md5hash)
                doc.save()

            # entries = reports.objects.all().filter(private=False)
            return HttpResponseRedirect(reverse('home'))
            # return render(request, 'index.html', {'report': entries})
        
    entries = reports.objects.all()
    folders = profile.folder_set.all()
    user = User.objects.get(username=request.user)
    groups = user.groups.all() 

    return render(request, 'add_report.html', {'report': entries, 'folder': folders, 'groups': groups})




def search(request):

    if ('a' in request.GET) and request.GET['a'].strip():
            query_string = request.GET['a']
            found_entries = reports.objects.filter(Q(keywords__icontains=query_string)|Q(short__icontains=query_string)
            |Q(author__icontains=query_string)|Q(details__icontains=query_string))

            return render(request,'search.html',
                          {  'found_entries': found_entries, 'query': query_string },
                        )
    if ('q' in request.GET) and request.GET['q'].strip():
            query_string = request.GET['q']
            query = None

            for pairs in query_string.split('&&'):
                or_query = None
                pairs = pairs.split(':')
                if len(pairs) < 2 :
                    error_type = 6
                    return render(request, 'error_page.html', {'t': error_type})
                x = pairs[0].strip()
                y = pairs[1].strip()

                entries = Q(**{"%s__icontains" % x: y})

                if or_query is None:
                    or_query = entries
                else:
                    or_query = or_query & entries
            if query is None:
                query = or_query
            else:
                query = query & or_query

            found_entries = reports.objects.filter(query)

            return render(request,'search.html',
                      {  'found_entries': found_entries, 'query': query_string },
                    )

    return render_to_response('search.html')


@login_required(login_url="/accounts/login/")
def delete_comment(request, pk):
    if request.method == 'POST':
        rep = reports.objects.all().filter(pk=pk)[0]
        com = Comment.objects.all().filter(report=rep)

        if request.user.is_active:
            profile = UserProfile.objects.filter(user=request.user)[0]
        else:
            error_type = 2
            return render(request, 'error_page.html', {'t': error_type})

        if profile.user.username == com.name:
            com.delete()

        else:
            error_type = 2
            return render(request, 'error_page.html', {'t': error_type})
    return HttpResponseRedirect(reverse('detail'))




