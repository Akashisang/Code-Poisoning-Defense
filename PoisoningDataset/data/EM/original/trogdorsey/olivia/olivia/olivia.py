'''
Fork of pdf.py from jsunpack
'''
import binascii
import cStringIO
import Crypto.Cipher.ARC4 as ARC4
import Crypto.Cipher.AES as AES
import hashlib
import lzw
import re
import string
import struct
import xml.dom.minidom
import zlib


class pdfobj(object):
    #this class parses single "1 0 obj" up till "endobj" elements
    def __init__(self, keynum, data):
        self.tags = [] #tuples of [key,value]
        self.keynum = keynum
        self.indata = data
        self.tagstream = ''
        self.tagstreamError = False
        self.tagstreamChanged = False
        self.hiddenTags = 0 #tags containing non-normalized data
        self.children = [] #if this has a script tag, parse children of it
        self.staticScript = '' #for those things not within objects append to this structure

        #special children types
        self.isJS = False #could be a reference (or self contains JS)
        self.isDelayJS = False #for OpenAction
        self.isEmbedded = False #for /EmbeddedFile
        self.isAnnot = False
        self.isObjStm = []
        self.is_xfa = False
        self.is_xfaData = False
        self.isEncrypt = False
        self.isFromObjStream = False
        self.contains_comment = False
        self.knownName = '' #related to annots
        self.subj = '' #related to annots
        self.doc_properties = []
        #self.isTitle = False
        #self.isKeywords = False
        self.xfaChildren = []

        if self.indata:
            self.parseObject()

    def __repr__(self):
        out = 'pdfobj %s\n' % (self.keynum)
        if self.children:
            out += '\tchildren %s\n' % (str(self.children))
        if self.isJS:
            out += '\tisJS'
        if self.isAnnot:
            out += '\tisAnnot'
        for doc_prop in self.doc_properties:
            out += '\tis%s' % doc_prop
        if self.isDelayJS:
            out += '\tisDelayJS'
        return out

    def parseTag(self, tag, stream):
        '''
            Input:  tag is the contents of /Tag1 value1 /Tag2 value2
                    stream is (optional) contents between stream and endstream
            Output: self.tags and self.tagstream
            If stream is not set, then we should set it before it gets assigned to tagstream
        '''
        state = 'INIT'
        precomment_state = 'INIT'
        curtag = ''
        curval = ''
        multiline = 0 # for tracking multiline in TAGVALCLOSED state
        uncleaned_tags = [] #output of statemachine
        num_paren_open = 0
        is_bracket_closed = True
        for index in range(0, len(tag)):
            #if self.keynum == '23 0':
            #    print state, index, hex(index), hex(ord(tag[index])), tag[index], curtag, len(curval), num_paren_open, is_bracket_closed
            if state == 'INIT':
                is_bracket_closed = True
                if tag[index] == '/':
                    state = 'TAG'
            elif state == 'TAG':
                is_bracket_closed = True
                if re.match('[a-zA-Z0-9#]', tag[index]):
                    curtag += tag[index]
                elif tag[index] == '/':
                    if curtag:
                        uncleaned_tags.append([state, curtag, '']) # no tag value
                        curtag = ''
                    state = 'TAG'
                elif tag[index] == '(':
                    state = 'TAGVALCLOSED'
                    num_paren_open = 0
                    multiline = 0
                    curval = '' # ignore the (, for the most part
                elif tag[index] == '[': # start of an array... probably
                    state = 'TAGVAL'
                    is_bracket_closed = False
                    curval = '['
                elif tag[index] == '\n':
                    state = 'TAG'
                elif tag[index] == '%':
                    precomment_state = state
                    state = 'COMMENT'
                else:
                    state = 'TAGVAL'
                    curval = ''
            elif state == 'COMMENT':
                self.contains_comment = True
                if tag[index] in ['\x0d', '\x0a']:
                    state = precomment_state
            elif state == 'TAGVAL':
                # Weird cases with arrays
                if tag[index] == '/' and (not tag[index - 1] == '\\\\') and \
                    ((curval and curval[0] == '[' and is_bracket_closed) or  \
                    (not curval) or (curval and curval[0] != '[')):
                    # a new open bracket and we are not in the middle of a bracket
                     # or there is bracket here, but we ignore this one
                    if curtag or curval:
                        uncleaned_tags.append([state, curtag, curval])
                    state = 'TAG'
                    curtag = curval = ''
                elif curval and curval[0] == '[' and tag[index] == ']':  # finished array
                    curval += tag[index]
                    is_bracket_closed = True
                elif tag[index] == '(':
                    #what do we do with curval? toss it
                    if re.match(r'^[\s\[\]\(\)<>]*$', curval): # look for any characters that indicate this isn't a TAGVALCLOSED
                        state = 'TAGVALCLOSED'
                        multiline = 0
                        if curtag in ['JS', 'O', 'U']:
                            num_paren_open += 1

                        if len(curval) > 0:
                            #print '\ttossed out %d characters (%s) because we entered TAGVALCLOSED state' % (len(curval),curval)
                            curval = ''
                    else: #keep processing?
                        curval += tag[index]
                elif tag[index] == '[' and curtag == 'XFA': # coming up on an array listing the XFA objects
                    is_bracket_closed = False
                    state = 'TAGVALCLOSED'
                # Normally ignore these, but they are useful when parsing the ID in the trailer
                elif (tag[index] == '<' or tag[index] == '>') and self.keynum != 'trailer':
                    pass
                elif tag[index] == ' ' and curval == '':
                    pass #already empty
                elif tag[index] == '%':
                    precomment_state = state
                    state = 'COMMENT'
                else:
                    curval += tag[index]
            elif state == 'TAGVALCLOSED':
                #in this state we know that the code started with (... therefore we can't end until we see )
                #the code could also have enclosed ( chars; therefore, this algorithm is greedy
                grab_more = 0 # if grab_more is set to 1, it means the tag isn't closing yet
                if tag[index] == ')': #possible closing tag
                    if (tag[index - 1] == '\\' and tag[index-2] != '\\') or \
                        (tag[index-1] == '\\' and tag[index-2] == '\\' and tag[index-3] == '\\') or \
                        ((curtag == 'JS' or curtag == 'JavaScript') and num_paren_open > 0 and tag[index-1] == '\\') or \
                        (curtag == 'XFA' and not is_bracket_closed): # we are in the middle of a JS string or an XFA array
                        grab_more = 1

                        if num_paren_open > 0:
                            num_paren_open -= 1

                    elif multiline: #tricky cases
                        #either a newline or "(" character leads us here.

                        #IGNORE THESE
                        #if re.match('^\)\s*($|\n\s*([^\)\s])',tag[index:]):
                        #    #yep its closing time
                        #    #this regex ensures there isn't another following close tag
                        #res = re.match('^(.*)\)  $',tag[index:])

                        if index + 1 < len(tag):
                            indexParen = tag[index + 1:].find(')')
                            #indexNewL = tag[index+1:].find('\n')
                            if indexParen > -1: # and (indexNewL == -1 or indexNewL > indexParen):
                                if not re.match('^\s*\/[A-Za-z0-9]+\s*\(', tag[index + 1:]):
                                    grab_more = 1
                    if grab_more:
                        curval += tag[index]
                    else: #ok ok, its simply closing
                        uncleaned_tags.append([state, curtag, curval])
                        state = 'INIT'
                        #print '%s (TAGVALCLOSED), length=%d bytes with %d/%d completed (around %s)' % (curtag, len(curval),index,len(tag), tag[index-20:index+20])
                        curtag = curval = ''
                elif tag[index] == '(': #tag[index] == '\n'
                    num_paren_open += 1
                    curval += tag[index]
                elif tag[index] == ']' and curtag != 'JS' and not is_bracket_closed: # can have ]s inside JS strings...
                    is_bracket_closed = True
                elif tag[index] == '%' and num_paren_open == 0 and curtag not in ['JS', 'O', 'U']: #can have % inside JS strings... And in O and U strings in Encrypt Objects
                    precomment_state = state
                    state = 'COMMENT'
                else:
                    curval += tag[index]
            else:
                print 'invalid state in parseTag: %s' % state
        if curtag: #an ending tag with NO final separator
            uncleaned_tags.append(['ENDTAG', curtag, curval])

        #clean uncleaned_tags and put in self.tags instead
        for source, tagtype, tagdata in uncleaned_tags:
            newtagtype = pdfobj.fixPound(tagtype)
            if newtagtype != tagtype:
                self.hiddenTags += 1
                tagtype = newtagtype

            #newlines in tagtype? ONLY for state != TAGVALCLOSED
            if source != 'TAGVALCLOSED':
                #its okay to replace newlines, spaces, tabs here
                tagdata = re.sub('[\s\r\n]+', ' ', tagdata)

            # You can have octal further in the string, but that can sometimes cause problems
            # so if there is a problem, just back out and use the original
            if re.search('([^\\\\]\\\\[0-9]{3}\s*)+', tagdata): #ie. need to convert \040 == 0x20
                original = tagdata
                try:
                    tagdata = re.sub('\\\\([0-9]{3})', lambda mo: chr(int(mo.group(1), 8)), tagdata)
                except:
                    tagdata = original

            # to my dismay, there are lot of tags to unescape
            unescaped_tagdata = ''
            backslash = False
            for d in tagdata:
                if backslash:
                    backslash = False
                    if d == 'b':
                        unescaped_tagdata += '\b'
                    elif d == 'f':
                        unescaped_tagdata += '\f'
                    elif d == 'n':
                        unescaped_tagdata += '\n'
                    elif d == 'r':
                        unescaped_tagdata += '\r'
                    elif d == 's':
                        unescaped_tagdata += 's' # this one is weird, I know
                    elif d == 't':
                        unescaped_tagdata += '\t'
                    elif d in ('(', ')', '\\'):
                        unescaped_tagdata += d
                    elif d == '\'' and tagtype == 'JS':
                        unescaped_tagdata += '\\\''

                elif d == '\\':
                    backslash = True
                else:
                    unescaped_tagdata += d

            tagdata = unescaped_tagdata
                #print 'set stream to %s; %s; %d bytes' % (source, tagtype, len(tagdata))

            #sometimes it's a short snippet without a ; at the end.  So add a ;
            if len(tagdata) < 50 and tagdata.find('AFDate') != -1 and tagdata[-1] != ';':
                tagdata += ';'

            # Only really want the JavaScript, and then only when it's not in a unicode format
            if not stream and \
                (source == 'TAGVALCLOSED' or source == 'ENDTAG') and \
                (tagtype == 'JS' or tagtype == 'JavaScript') and \
                len(tagdata) > 2 and tagdata[0:2] != '\xfe\xff':
                stream = tagdata
            self.tags.append([source, tagtype, tagdata])
        self.tagstream = stream

        if olivia.DEBUG:
            print 'obj %s: ' % (self.keynum)
            for source, tagtype, tagdata in self.tags:

                tagtxt = '\ttag %s' % re.sub('\n', '', tagtype)
                if len(tagdata) > 30:
                    tagtxt += ' = [data %d bytes]' % len(tagdata)
                elif tagdata:
                    tagtxt += ' = '
                    for c in tagdata:
                        if c in string.printable and c != '\n':
                            tagtxt += c
                        else:
                            tagtxt += '\\x%02x' % (ord(c))
                print '%-50s (%s)' % (tagtxt, source)
                #end

    def parseChildren(self):
        '''
            Input: self.tags (must be populated)
            Output: self.children
        '''
        for state, k, kval in self.tags:
            hasRef = re.search('\+?(\d+)\s+\+?(\d+)\s+R', kval)
            if hasRef:
                objkey = hasRef.group(1) + ' ' + hasRef.group(2)
                self.children.append([k, objkey])
            if k == 'XFA':
                kids = re.findall('(\d+\s+\d+)\s+R', kval)
                for kid in kids:
                    self.xfaChildren.append([k, kid])

    def parseObject(self):
        #previously this was non-greedy, but js with '>>' does mess things up in that case
        #to solve the problem, do both

        #if olivia.DEBUG:
        #    print '\tstarting object len %d' % len(self.indata)
        tags = re.findall('<<(.*)>>[\s\r\n%]*(?:stream[\s\r\n]*(.*?)[\r\n]*endstream)?', self.indata, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if tags:
            for tag, stream in tags:
                gttag = tag.find('>>')
                streamtag = tag.find('stream')
                endstream_tag_end = self.indata.rfind('endstream')
                endstream_tag_begin = self.indata.find('endstream')
                #
                # This means that there was an improper parsing because the tag shouldn't contain a stream object
                if endstream_tag_end != -1 and 0 < gttag < streamtag:
                    # do this in case the word stream is in the tag data somewhere...
                    stream_location_match = re.search('>>[\s\r\n%]*stream?', self.indata, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    if stream_location_match:
                        stream_location = stream_location_match.start()
                    else:
                        stream_location = self.indata.find('stream')

                    stream_start = self.indata.find('stream', stream_location)
                    stream_match = re.search('stream[\s\r\n]*(.*?)[\r\n]*endstream', self.indata, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    stream_data = ''
                    # Only search to start of stream, a compressed stream can have >> in it, and that will through off the regex
                    tag_match = re.search('<<(.*)>>', self.indata[0:stream_start], re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    if tag_match and stream_match:
                        stream_data = stream_match.group(1)
                        tag = tag_match.group(1)
                        tags = [(tag, stream_data)]
                #
                # This checks if the word endstream happens inside the stream
                if endstream_tag_begin != -1 and endstream_tag_begin != endstream_tag_end:
                    stream_location_match = re.search('>>[\s\r\n%]*stream?', self.indata, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    if stream_location_match:
                        stream_location = stream_location_match.start()
                    else:
                        stream_location = self.indata.find('stream')

                    stream_start = self.indata.find('stream', stream_location)
                    stream_match = re.search('stream[\s\r\n]*(.*?)[\r\n]*endstream$', self.indata, re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    tag_match = re.search('<<(.*)>>', self.indata[0:stream_start], re.MULTILINE | re.DOTALL | re.IGNORECASE)
                    stream_data = ''
                    if stream_match and tag_match:
                        stream_data = stream_match.group(1)
                        tag = tag_match.group(1)
                        tags = [(tag, stream_data)]

        if not tags: #Error parsing object!
            return

        for tag, stream in tags:
            self.parseTag(tag, stream)
            self.parseChildren()

    @staticmethod
    def fixPound(i):
        #returns '#3a' substituted with ':', etc
        #strips newlines, '[', and ']' characters
        #this allows indexing in arrays

        i = re.sub('[\[\]\n]', '', i)
        i = re.sub('<<$', '', i)
        return re.sub('#([a-fA-F0-9]{2})', lambda mo: chr(int('0x' + mo.group(1), 0)), i)

    @staticmethod
    def lzwdecode(data):
        try:
            return ''.join(lzw.LZWDecoder(cStringIO.StringIO(data)).run())
        except:
            return data

    @staticmethod
    def rldecode(input):
        output = ''
        index = 0
        try:
            key_len = ord(input[index])

            while key_len != 0x80:
                index += 1
                if key_len & 0x80:
                    output += input[index] * (256 - key_len + 1)
                    index += 1
                else:
                    output += input[index:index + key_len + 1]
                    index += key_len + 1
                key_len = ord(input[index])
        except:
            return input
        return output

    @staticmethod
    def ascii85(input):
        outdata = ''
        input = re.sub('\s', '', input)
        input = re.sub('^<~', '', input)
        input = re.sub('~>$', '', input)

        for i in range(0, len(input), 5):
            bytes = input[i:i + 5]
            fraglen = len(bytes)
            if bytes[0] == 'z':
                pass #ignore
            if bytes[0] == 'y':
                pass #ignore
            if i + 5 >= len(input):
                #data not divisible by 5
                bytes = input[i:]
                fraglen = len(bytes)
                if fraglen > 1:
                    bytes += 'vvv'

            total = 0
            shift = 85 * 85 * 85 * 85
            for c in bytes:
                total += shift * (ord(c) - 33)
                shift /= 85

            if fraglen > 1:
                outdata += chr((total >> 24) % 256)
                if fraglen > 2:
                    outdata += chr((total >> 16) % 256)
                    if fraglen > 3:
                        outdata += chr((total >> 8) % 256)
                        if fraglen > 4:
                            outdata += chr((total) % 256)
        return outdata

class olivia(object):

    DEBUG = 0

    def __init__(self, indata, infile, password=''):
        self.indata = indata
        self.size = len(self.indata)
        self.infile = infile
        self.objects = {}
        self.pages = []
        self.numPages = 0
        self.list_obj = []
        self.jsObjects = []
        self.encrypt_key = ''
        self.encrypt_key_valid = False
        self.encrypt_object = {}
        self.encrypt_password = password
        self.xfaObjects = []

    def parse(self):

        '''
        #parsing xref tables
        xrefs = re.findall('xref\s*\n\d+\s+(\d+)\s*\n((\d+\s+\d+\s+[fn]\s*\n)+)\s*trailer\s*\n',self.indata)#.*?startxref\s*\n(\d+)\s*\n\s*%%EOF\s*',self.indata)
        for entries, table,junk in xrefs:
            entries = int(entries)
            print 'entries=',entries
            lines = table.split('\n')
            for line in lines:
                valid = re.match('\s*(\d+)\s+(\d+)\s+[fn]\s*',line)
                if valid:
                    offset,zero = int(valid.group(1)), int(valid.group(2))
                    print 'line = ', offset, zero
            #offset = int(offset)
        '''

        objs = re.findall('\n?(\d+)\s+(\d+)[\x00\s]+obj[\s]*(.*?)\s*\n?(?<!%)(endobj|.ndobj|e.dobj|en.obj|end.bj|endo.j|endob.|objend)', self.indata, re.MULTILINE | re.DOTALL)
        if objs:
            for obj in objs:
                #fill all objects
                key = obj[0] + ' ' + obj[1]
                if not key in self.list_obj:
                    self.list_obj.append(key)
                else: # There are cases with the two objects have the same number, because PDFs are awesome that way
                    key = key + ' dup'
                    self.list_obj.append(key)

                self.objects[key] = pdfobj(key, obj[2])

            trailers = re.findall('(trailer[\s\r\n]*<<(.*?)>>)', self.indata, re.MULTILINE | re.DOTALL)
            for trailertags in trailers:
                trailerData = trailertags[1]
                #
                # Check for a dictionary inside the trailer
                #
                isDict = trailerData.find("<<")
                if isDict != -1:
                    offset = self.indata.find(trailertags[0])
                    trailerData = self.extractTrailerData(offset)

                trailerstream = '' #no stream in trailer
                trailerobj = pdfobj('trailer', '') #empty second parameter indicates not to do an object parse
                trailerobj.parseTag(trailerData, trailerstream)
                trailerobj.parseChildren()
                key = 'trailer'
                if not key in self.list_obj:
                    self.list_obj.append(key)
                else: # There are cases with the two objects have the same number, because PDFs are awesome that way
                    key = key + ' dup'
                    self.list_obj.append(key)
                self.objects[key] = trailerobj
                for tag, value in trailerobj.children:
                    # If there is an encrypt object, it should be specified in the trailer
                    # (in practice, that's not always the case... *sigh*)
                    if tag == 'Encrypt' and not self.encrypt_key_valid:
                        # Make sure the encrypt object is actually there
                        if value in self.objects:
                            self.objects[value].isEncrypt = True
                            self.encrypt_object = self.populate_encrypt_object(self.objects[value])

                        fileId = ''
                        for state, tag, val in trailerobj.tags:
                            if tag == 'ID':
                                ids = re.findall('<([\d\w]*)>', val)
                                # Just in case the ID has something I'm not expecting
                                if ids:
                                    try:
                                        fileId = binascii.unhexlify(ids[0])
                                    except:
                                        pass
                                else:
                                    fileId = val
                        # yay for default passwords
                        padding = binascii.unhexlify('28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A')
                        # limit of 16 characters
                        passwd = (self.encrypt_password + padding)[0:32]
                        self.encrypt_key = self.compute_encrypt_key(self.encrypt_object, passwd, fileId)
                        self.encrypt_key_valid = self.validate_encrypt_key(self.encrypt_key, padding, fileId, self.encrypt_object)
                        break

            # but wait, sometimes the encrypt object is not specified in the trailer, yet sometimes another
            # object has it in it, so search for it now
            if not self.encrypt_key_valid:
                encrypt_object_key = ''
                fileId = '\x00' * 16
                for key in self.list_obj:
                    if key == 'trailer':
                        continue
                    for kstate, k, kval in self.objects[key].tags:
                        if k == 'Encrypt':
                            for child_type, child_key in self.objects[key].children:
                                if child_type == 'Encrypt':
                                    self.objects[child_key].isEncrypt = True
                                    encrypt_object_key = child_key
                                    break
                        if k == 'ID':
                            ids = re.findall('\[([\d\w]*)\]', kval)
                            if ids:
                                firstId = ids[0]
                                # for some reason it's there twice...
                                firstId = firstId[0:len(firstId)/2]
                                try:
                                    fileId = binascii.unhexlify(firstId)
                                except:
                                    pass

                    if encrypt_object_key and fileId:
                        break

                if encrypt_object_key and fileId: # we found it
                    self.encrypt_object = self.populate_encrypt_object(self.objects[encrypt_object_key])
                    padding = binascii.unhexlify('28BF4E5E4E758A4164004E56FFFA01082E2E00B6D0683E802F0CA9FE6453697A')
                    # limit of 32 characters here
                    passwd = (self.encrypt_password + padding)[0:32]
                    self.encrypt_key = self.compute_encrypt_key(self.encrypt_object, passwd, fileId)
                    if self.encrypt_object['V'] == 5 and self.encrypt_key != '\xca\x1e\xb0' and 'Perms' in self.encrypt_object:
                        aes = AES.new(self.encrypt_key, AES.MODE_ECB)
                        decryptedPerms = aes.decrypt(self.encrypt_object['Perms'])
                        if decryptedPerms[0:4] == self.encrypt_object['P'][0:4] and decryptedPerms[9:12] == 'adb':
                            self.encrypt_key_valid = True
                    else:
                        self.encrypt_key_valid = self.validate_encrypt_key(self.encrypt_key, padding, fileId, self.encrypt_object)

            for key in self.list_obj: #sorted(self.objects.keys()):
                #set object options
                if self.encrypt_key and self.encrypt_key_valid:
                    if self.objects[key].tagstream and not self.objects[key].isEncrypt and not self.objects[key].isFromObjStream:
                        if self.encrypt_object['algorithm'] == 'RC4':
                            self.objects[key].tagstream = self.decryptRC4(self.objects[key].tagstream, key)
                        elif self.encrypt_object['algorithm'] == 'AES':
                            self.objects[key].tagstream = self.decryptAES(self.objects[key].tagstream, key)

                        self.objects[key].tagstreamModified = True

                for kstate, k, kval in self.objects[key].tags:
                    if k == 'OpenAction':
                        # sometimes OpenAction is an array, so check for that
                        if not kval or kval[0] != '[':
                            self.objects[key].isDelayJS = True
                            for child_type, child_key in self.objects[key].children:
                                if child_type == 'OpenAction' and child_key in self.objects:
                                    self.objects[child_key].isDelayJS = False # This isn't the JS, the children have it
                                    for cState, cType, cValue in self.objects[child_key].tags:
                                        if cType in ['JavaScript', 'JS']:
                                            self.objects[child_key].isDelayJS = True
                                elif olivia.DEBUG:
                                    print 'error: not a valid object for child (%s)' % (child_key)


                    if k  in ['JavaScript', 'JS']:
                        self.objects[key].isJS = True
                        foundChildJs = False
                        for child_type, child_key in self.objects[key].children: # Is the JS with the children?
                            if child_key in self.objects and child_type in ['JS', 'JavaScript']:
                                self.objects[child_key].isJS = True
                                self.objects[key].isJS = False
                                if child_key not in self.jsObjects:
                                    self.jsObjects.append(child_key)
                                foundChildJs = True

                        if not foundChildJs: # JS is here
                            if key not in self.jsObjects:
                                self.jsObjects.append(key)

                    if k == 'XFA':
                        self.objects[key].is_xfa = True
                        for xfaType, xfaKey in self.objects[key].xfaChildren:
                            if xfaKey in self.objects:
                                self.objects[xfaKey].is_xfaData = True

                    if k == 'NM':
                        self.objects[key].knownName = kval

                    if k == 'Subj':
                        self.objects[key].subj = kval

                    if k == 'EmbeddedFile':
                        self.objects[key].isEmbedded = True

                    if k == 'Annot':
                        #since JavaScript can call getAnnots() we must populate these entries now
                        #don't handle /Annots (precursory tag), children will contain Subj element

                        self.objects[key].isAnnot = True
                        for type, childkey in self.objects[key].children:
                            if childkey in self.objects and (type == 'Subj'):
                                self.objects[childkey].isAnnot = True
                                self.jsObjects.append(childkey)

                    if k == 'Page':
                        hasContents = False
                        for childtype, childkey in self.objects[key].children:
                            if childtype == 'Contents':
                                self.pages.append(childkey)
                                hasContents = True
                        if not hasContents:
                            self.pages.append(key)

                    if k == 'Pages':
                        for pagestate, pagetag, pagevalue in self.objects[key].tags:
                            if pagetag == 'Count':
                                try:
                                    self.numPages += int(pagevalue)
                                except ValueError:
                                    # Check children
                                    for childtype, childkey in self.objects[key].children:
                                        if childtype == 'Count':
                                            pagevalue = self.objects[childkey].indata
                                            try:
                                                self.numPages += int(pagevalue)
                                            except ValueError:
                                                pass

                    #populate pdfobj's doc_properties with those that exist
                    enum_properties = ['Title', 'Author', 'Subject', 'Keywords', 'Creator', 'Producer', 'CreationDate', 'ModDate', 'plot']

                    if k in enum_properties:
                        value = kval
                        value = re.sub('[\xff\xfe\x00]', '', value)
                        isReference = re.match('^\s*\d+\s+\d+\s+R\s*$', value)
                        if isReference:
                            validReference = False
                            for child_type, child_key in self.objects[key].children:
                                if child_key in self.objects and (child_type == k):
                                    validReference = True
                                    self.objects[child_key].doc_properties.append(k.lower())
                                    self.jsObjects.append(child_key)
                            if not validReference:
                                if olivia.DEBUG:
                                    print '[warning] possible invalid reference in %s' % (k)
                                self.objects[key].doc_properties.append(k.lower())
                        else:
                            #not a reference, use the direct value
                            value = re.sub('\'', '\\x27', value)
                            self.objects[key].staticScript += 'info.%s = String(\'%s\');\n' % (k.lower(), olivia.do_hexAscii(value))
                            self.objects[key].staticScript += 'this.%s = info.%s;\n' % (k.lower(), k.lower())
                            self.objects[key].staticScript += 'info.%s = info.%s;\n' % (k, k.lower())
                            self.objects[key].staticScript += 'app.doc.%s = info.%s;\n' % (k.lower(), k.lower())
                            self.objects[key].staticScript += 'app.doc.%s = info.%s;\n' % (k, k.lower())

                            if k == 'CreationDate':
                                self.objects[key].staticScript += 'app.doc.creationDate = info.creationdate;\n'
                                self.objects[key].staticScript += 'info.creationDate = info.creationdate;\n'

                            if key not in self.jsObjects:
                                self.jsObjects.append(key)

                for kstate, k, kval in self.objects[key].tags:
                    # Multiple filters, sometimes pound issues, throws off the decode, so handle it here
                    if k == 'Filter':
                        kval = pdfobj.fixPound(kval)
                        filters = re.findall('/(\w+)', kval)
                        if filters:
                            for filter in filters:
                                if filter == 'FlateDecode' or filter == 'Fl':
                                    try:
                                        self.objects[key].tagstream = zlib.decompress(self.objects[key].tagstream)
                                    except zlib.error, msg:
                                        if olivia.DEBUG:
                                            print 'failed to decompress object %s (inlen %d)' % (key, len(self.objects[key].tagstream))
                                            print self.objects[key].tagstream
                                        self.objects[key].tagstream = '' #failed to decompress

                                if filter == 'ASCIIHexDecode' or filter == 'AHx':
                                    result = ''
                                    counter = 0
                                    self.objects[key].tagstream = re.sub('[^a-fA-F0-9]+', '', self.objects[key].tagstream)
                                    for i in range(0, len(self.objects[key].tagstream), 2):
                                        result += chr(int('0x' + self.objects[key].tagstream[i:i + 2], 0))
                                    self.objects[key].tagstream = result
                                if filter == 'ASCII85Decode' or filter == 'A85':
                                    self.objects[key].tagstream = pdfobj.ascii85(self.objects[key].tagstream)
                                if filter == 'LZWDecode' or filter == 'LZW':
                                    self.objects[key].tagstream = pdfobj.lzwdecode(self.objects[key].tagstream)
                                if filter == 'RunLengthDecode' or filter == 'RL':
                                    self.objects[key].tagstream = pdfobj.rldecode(self.objects[key].tagstream)
                    if k == 'FlateDecode' or k == 'Fl':
                        try:
                            self.objects[key].tagstream = zlib.decompress(self.objects[key].tagstream)
                        except zlib.error, msg:
                            # There is a chance our regex removed too many \r or \n when pulling out the stream.  We probably
                            # should fix this there, but in the mean time, if it fails, try adding them back.
                            lame_fixes = ["\n", "\r"]
                            lame_fix_worked = True
                            for lame_fix in lame_fixes:
                                try:
                                    self.objects[key].tagstream = zlib.decompress(self.objects[key].tagstream+lame_fix)
                                    lame_fix_worked = True
                                    break
                                except zlib.error, msg:
                                    pass

                            if not lame_fix_worked:
                                if olivia.DEBUG:
                                    print 'failed to decompress object %s (inlen %d)' % (key, len(self.objects[key].tagstream))
                                    print self.objects[key].tagstream
                                self.objects[key].tagstream = '' #failed to decompress

                    if k == 'ASCIIHexDecode' or k == 'AHx':
                        result = ''
                        counter = 0
                        self.objects[key].tagstream = re.sub('[^a-fA-F0-9]+', '', self.objects[key].tagstream)
                        for i in range(0, len(self.objects[key].tagstream), 2):
                            result += chr(int('0x' + self.objects[key].tagstream[i:i + 2], 0))
                        self.objects[key].tagstream = result

                    if k == 'ASCII85Decode' or k == 'A85':
                        self.objects[key].tagstream = pdfobj.ascii85(self.objects[key].tagstream)
                    if k == 'LZWDecode' or k == 'LZW':
                        self.objects[key].tagstream = pdfobj.lzwdecode(self.objects[key].tagstream)
                    if k == 'RunLengthDecode' or k == 'RL':
                        self.objects[key].tagstream = pdfobj.rldecode(self.objects[key].tagstream)

                # Check for Object Streams, but only if we don't have an error with tagstream
                if not self.objects[key].tagstreamError:
                    object_stream_data = ''
                    object_stream_n = 0
                    object_stream_first = 0
                    for kstate, k, kval in self.objects[key].tags:
                        if k == 'ObjStm':
                            object_stream_data = self.objects[key].tagstream
                        if k == 'N':
                            # just in case
                            try:
                                object_stream_n = int(kval)
                            except:
                                pass
                        if k == 'First':
                            # ...
                            try:
                                object_stream_first = int(kval)
                            except:
                                pass

                    if object_stream_data != '' and object_stream_n != 0 and object_stream_first != 0:
                        self.parse_object_stream(object_stream_data, object_stream_n, object_stream_first)

                self.objects[key].tagstream = olivia.applyFilter(self.objects[key].tagstream)
                if olivia.DEBUG and self.objects[key].tagstream.startswith('MZ'):
                    print 'PDF file has embedded MZ file'
        else:
            print 'Fatal error: pdf has no objects in ' + self.infile

    def populate_encrypt_object(self, encrypt_object):
        e = {}

        e['V'] = 0
        e['R'] = 0
        e['O'] = ''
        e['U'] = ''

        for state, tag, value in encrypt_object.tags:
            # Multiple lengths, referring to different things, take the bigger one, that *should* be right
            if tag == 'Length' and 'Length' in e:
                if int(value) > int(e[tag]):
                    e[tag] = value
                continue
            e[tag] = value

        e['KeyLength'] = 5

        if 'AESV2' in e or 'AESV3' in e:
            e['algorithm'] = 'AES'
        else:
            e['algorithm'] = 'RC4'

        if 'EncryptMetadata' in e:
            if e['EncryptMetadata'].lower() == 'false':
                e['EncryptMetadata'] = False
        else:
            e['EncryptMetadata'] = True

        if 'V' in e:
            e['V'] = int(e['V'])

        if e['V'] >= 2 and 'Length' in e:
            e['KeyLength'] = int(e['Length'])/8

        if 'R' in e:
            e['R'] = int(e['R'])

        if e['R'] <= 4 and len(e['O']) > 32:
            e['O'] = binascii.unhexlify(e['O'].strip())

        if e['R'] <= 4 and len(e['U']) > 32:
            e['U'] = binascii.unhexlify(e['U'].strip())

        if 'P' in e:
            e['P'] = struct.pack('L', int(e['P']) & 0xffffffff)

        return e

    def compute_encrypt_key(self, encrypt_object, password, fileId):
        '''Computes the encrypt key based on values in encrypt object'''
        if encrypt_object['R'] <= 4:
            h = hashlib.md5()
            h.update(password)
            h.update(encrypt_object['O'])
            h.update(encrypt_object['P'][0:4])
            h.update(fileId)
            if encrypt_object['R'] == 4 and not encrypt_object['EncryptMetadata']:
                h.update("\xff\xff\xff\xff")
            key = h.digest()[0:encrypt_object['KeyLength']]
            if encrypt_object['R'] >= 3:
                for i in range(50):
                    key = hashlib.md5(key[0:encrypt_object['KeyLength']]).digest()
                key = key[0:encrypt_object['KeyLength']]
            return key

        elif encrypt_object['R'] == 5:
            user_key = hashlib.sha256(encrypt_object['U'][32:40]).digest()
            if user_key == encrypt_object['U'][0:32]: # success!
                almost_key = hashlib.sha256(encrypt_object['U'][40:48]).digest()
                aes = AES.new(almost_key, AES.MODE_CBC, '\x00'*16)
                the_key = aes.decrypt(encrypt_object['UE'])
                return the_key

            #
            # Ok, then check the owner password
            #
            owner_sha = hashlib.sha256()
            owner_sha.update(encrypt_object['O'][32:40])
            owner_sha.update(encrypt_object['U'][0:48])
            owner_hash = owner_sha.digest()
            if owner_hash == encrypt_object['O'][0:32]:
                almost_hash = hashlib.sha256()
                almost_hash.update(encrypt_object['O'][40:48])
                almost_hash.update(encrypt_object['U'][0:48])
                almost_key = almost_hash.digest()
                aes = AES.new(almost_key, AES.MODE_CBC, '\x00'*16)
                the_key = aes.decrypt(encrypt_object['OE'])
                return the_key
        else:
            print "No good", encrypt_object['R']

        return '\xca\x1e\xb0'

    def validate_encrypt_key(self, key, password, fileId, encrypt_object):
        '''Verifies that the encryption key is correct'''
        if encrypt_object['R'] == 2:
            rc4 = ARC4.new(key)
            password_encrypted = rc4.encrypt(password)
            if encrypt_object['U'] == password_encrypted:
                return True
        elif encrypt_object['R'] >= 3:
            m = hashlib.md5()
            m.update(password)
            m.update(fileId)
            cHash = m.digest()
            rc4 = ARC4.new(key)
            dHash = rc4.encrypt(cHash)
            for i in range(1, 20):
                newKey = ''
                for k in key:
                    newKey += chr(ord(k) ^ i)
                stepE = ARC4.new(newKey)
                dHash = stepE.encrypt(dHash)

            if dHash == encrypt_object['U'][0:16]:
                return True
        else:
            print "No good", encrypt_object['R']

        return False

    def parse_object_stream(self, data, n, first):
        integer_pairs = re.findall('(\d+) +(\d+)', data[0:first])

        for i, pairs in enumerate(integer_pairs):
            key = str(pairs[0]) + " 0"

            start_offset = first + int(pairs[1])
            if i+1 == n:
                end_offset = None
            else:
                end_offset = first + int(integer_pairs[i+1][1])

            obj_data = data[start_offset:end_offset]

            if not key in self.list_obj:
                self.list_obj.append(key)
            else:
                key = key + ' dup'
                self.list_obj.append(key)

            self.objects[key] = pdfobj(key, obj_data)
            self.objects[key].isFromObjStream = True

        return

    def extractTrailerData(self, trailer_start):
        dictionaries = 0
        trailer_end = trailer_start
        first_dictionary = False
        while dictionaries != 0 or not first_dictionary:
            d = self.indata[trailer_end:trailer_end+2]
            if d == '<<':
                first_dictionary = True
                dictionaries += 1
                trailer_end += 2
                continue
            elif d == '>>':
                dictionaries -= 1
                trailer_end += 2
                continue
            elif d == '':
                break

            trailer_end += 1

        trailer = self.indata[trailer_start:trailer_end]
        return trailer

    def decryptRC4(self, data, key):
        '''
            Input: data is the data to decrypt, key is the obj information of the form '5 0'
            Assumptions: self.encrypt_key is set
            Output: returns string of decrypted data
        '''
        try:
            obj, rev = key.split(' ')

            keyLength = self.encrypt_object['KeyLength'] + 5
            if keyLength > 16:
                keyLength = 16

            decrypt_key = hashlib.md5(self.encrypt_key + struct.pack('L', int(obj))[0:3] + struct.pack('L', int(rev))[0:2]).digest()[0:keyLength]
            cipher = ARC4.new(decrypt_key)
            return cipher.decrypt(data)
        except:
            return ''

    def decryptAES(self, aes_data, objectKey):
        '''Function that will take AES encrypted data and decrypt it'''
        if self.encrypt_object['V'] <= 4:
            try:
                obj, rev = objectKey.split(' ')
                keyLength = self.encrypt_object['KeyLength'] + 5
                if keyLength > 16:
                    keyLength = 16
                m = hashlib.md5()
                m.update(self.encrypt_key)
                m.update(struct.pack('L', int(obj))[0:3])
                m.update(struct.pack('L', int(rev))[0:2])
                m.update('\x73\x41\x6c\x54')
                aes_key = m.digest()[0:keyLength]
                iv = aes_data[0:16]
                aes = AES.new(aes_key, AES.MODE_CBC, iv)
                pad_size = 16 - (len(aes_data)%16)
                pad = "C" * pad_size
                data = aes.decrypt(aes_data[16:] + pad)[0:(pad_size*-1)]
                return data
            except Exception:
                return ''
        else:
            try:
                iv = aes_data[0:16]
                aes = AES.new(self.encrypt_key, AES.MODE_CBC, iv)
                pad_size = 16 - (len(aes_data)%16)
                pad = "C" * pad_size
                data = aes.decrypt(aes_data[16:] + pad)[0:(pad_size*-1)]
                return data
            except Exception:
                return ''


    def is_valid(self):
        '''Determines if this is a valid PDF file or not'''
        if 0 <= self.indata[0:1024].find('%PDF-') <= 1024:
            return True
        return False

    def __repr__(self):
        if not self.is_valid():
            return 'Invalid PDF file "%s"' % (self.infile)
        out = 'PDF file %s has %d obj items\n' % (self.infile, len(self.objects))
        for obj in sorted(self.objects.keys()):
            out += str(self.objects[obj]) + '\n'

        return out

    def get_javascript(self):
        '''Extracts all JavaScript from the PDF'''
        out = ''
        sloppy_flag = False
        for jskey in self.jsObjects:
            if self.objects[jskey].tagstreamError:
                continue

            if self.objects[jskey].staticScript:
                out += self.objects[jskey].staticScript

            if self.objects[jskey].tagstream:
                value = self.objects[jskey].tagstream
                value = re.sub('\'', '\\x27', value)
                # Sometimes there is just weird data there (or unicode), maybe getting rid of it helps
                # (like below)
                value = re.sub('[\x00-\x1f\x7f-\xff]', '', value)

                if self.objects[jskey].isAnnot:
                    out += 'var zzza = []; if(zzzannot.length > 0){ zzza=zzzannot.pop(); } zzza.push({subject:\'%s\'}); zzzannot.push(zzza);\n' % (value) #getAnnots
                    if self.objects[jskey].knownName:
                        if self.objects[jskey].subj:
                            subj = self.objects[jskey].subj
                        else:
                            subj = value
                        subj = re.sub('[\x00-\x1f\x7f-\xff]', '', subj) # <- below
                        out += 'zzzannot2["%s"] = {subject:\'%s\'};\n' % (self.objects[jskey].knownName, subj) #getAnnot

                for doc_prop in self.objects[jskey].doc_properties:
                    out += 'info.%s = String(\'%s\'); this.%s = info.%s;\n' % (doc_prop, olivia.do_hexAscii(value), doc_prop, doc_prop)

        if self.pages:
            for page in self.pages:
                if page in self.objects:
                    lines = self.objects[page].tagstream.split('\n')
                    out += 'c = []; '
                    for line in lines:
                        text_be = re.findall('BT[^(]*\(([^)]+)\)[^)]*?ET', line)
                        for hexdata in text_be:
                            words = hexdata.strip().split(' ')
                            for word in words:
                                out += 'c.push("%s"); ' % (olivia.do_hexAscii(word))
                    out += 'zzzpages.push(c); this.numPages = zzzpages.length; xfa.host.numPages = zzzpages.length;\n'
                else:
                    out += 'this.numPages = ' + str(self.numPages) + ';\n'
                    out += 'xfa.host.numPages = ' + str(self.numPages) + ';\n'
        else:
            out += 'c = []; '
            out += 'zzzpages.push(c); this.numPages = zzzpages.length; xfa.host.numPages = zzzpages.length;\n'

        out += '\nfilesize = ' + str(self.size) + ';\n'
        if out:
            out += '\n//jsunpack End PDF headers\n'

        headersjs = out #split value into 2 return values [js, header_js]
        out = ''

        delayout = ''
        for jskey in self.jsObjects:
            if self.objects[jskey].tagstreamError:
                continue

            # only do it if no encryption or it was decrypted
            if self.encrypt_key == '' or self.encrypt_key_valid == True:
                if self.objects[jskey].isDelayJS: #do this first incase the tag has /OpenAction /JS (funct())
                    if olivia.DEBUG:
                        print 'Found JavaScript (delayed) in %s (%d bytes)' % (jskey, len(self.objects[jskey].tagstream))
                    delayout += self.objects[jskey].tagstream
                elif self.objects[jskey].isJS:
                    if olivia.DEBUG:
                        print 'Found JavaScript in %s (%d bytes)' % (jskey, len(self.objects[jskey].tagstream))
                    #if jskey == '84 0':
                    #    print self.objects[jskey].tagstream
                    if len(self.objects[jskey].tagstream) > 4 and self.objects[jskey].tagstream[3] != '\x00':
                        out += self.objects[jskey].tagstream
                        if out[-1] not in[';', '}']:
                            out += ';'
                    else:
                        temp_js = re.sub(r'([^\x00])\x0a', r'\1', self.objects[jskey].tagstream)
                        temp_js = re.sub(r'([^\x00])\x0d', r'\1', temp_js)
                        temp_js = re.sub('^([\x80-\xff])', '', temp_js)
                        temp_js = re.sub('([\x00-\x08\x0b\x0c\x0e-\x1f])', '', temp_js)
                        temp_js = re.sub('([\x80-\xff])', 'C', temp_js)
                        out += temp_js

                if olivia.DEBUG:
                    if self.objects[jskey].isJS or self.objects[jskey].isDelayJS:
                        print '\tchildren ' + str(self.objects[jskey].children)
                        print '\ttags ' + str(self.objects[jskey].tags)
                        print '\tindata = ' + re.sub('[\n\x00-\x19\x7f-\xff]', '', self.objects[jskey].indata)[:100]

        for key in self.list_obj:
            if self.objects[key].is_xfa and (self.encrypt_key == '' or self.encrypt_key_valid):
                xfa_data = ''
                for xfa_type, xfa_key in self.objects[key].xfaChildren:
                    if xfa_key in self.list_obj:
                        xfa_data += self.objects[xfa_key].tagstream

                # gets rid of some crap.  But unicode will probably cause problems down the road
                xfa_data = re.sub('^([\x80-\xff])', '', xfa_data)
                xfa_data = re.sub('([\x00-\x08\x0b\x0c\x0e-\x1f])', '', xfa_data)
                xfa_data = re.sub('([\x80-\xff])', 'C', xfa_data)

                try:
                    doc = xml.dom.minidom.parseString(xfa_data)
                except Exception as e:
                    print "drat", str(e)
                    continue

                scriptElements = doc.getElementsByTagNameNS("*", "script")
                if not scriptElements:
                    continue

                for script in scriptElements:
                    if script.getAttribute('contentType') != 'application/x-javascript' or not script.childNodes:
                        continue

                    js = script.childNodes[0].data
                    # maybe?
                    if type(js) == unicode:
                        js = unicode(js).encode('utf-8')

                    dataForJs = ''
                    jsNode = script.parentNode.parentNode
                    jsName = jsNode.getAttribute('name')
                    if type(jsName) == unicode:
                        jsName = unicode(jsName).encode('utf-8')

                    dataElements = doc.getElementsByTagName(jsName)
                    if dataElements and dataElements[0].childNodes and dataElements[0].childNodes[0].nodeType == xml.dom.minidom.Node.TEXT_NODE:
                        dataForJs = dataElements[0].childNodes[0].data.replace('\n', '').replace('\r', '')

                    xfa_javascript = ''
                    if jsName:
                        xfa_javascript += jsName + "=this;\n"
                        xfa_javascript += 'var rawValue = "' + dataForJs.strip() + '";\n'
                        for k in jsNode.attributes.keys():
                            xfa_javascript += jsName + '.' + k + ' = "' + jsNode.getAttribute(k) + '";\n'

                    xfa_javascript += js + '\n'
                    if jsName:
                        xfa_javascript += 'print("<rawValue>" + ' + jsName + '.rawValue + "</rawValue>");\n'

                    out += xfa_javascript

        if len(out + delayout) <= 0:
            #Basically if we don't find ANY JavaScript, then we can parse the other elements
            for jskey in self.objects.keys():
                sloppy = re.search('function |var ', self.objects[jskey].tagstream)
                if sloppy:
                    sloppy_flag = True
                    out += self.objects[jskey].tagstream
                    if olivia.DEBUG:
                        print 'Sloppy PDF parsing found %d bytes of JavaScript' % (len(out))

        return re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f\x80-\xff]', '', out + delayout), headersjs, sloppy_flag

    @staticmethod
    def do_hexAscii(input):
        return re.sub('([^a-zA-Z0-9])', lambda m: '\\x%02x' % ord(m.group(1)), input)

    @staticmethod
    def applyFilter(data):
        if len(data) > 10000000:
            return data

        for i in range(0, len(data)):
            c = ord(data[i])
            if 0 < c < 0x19 or 0x7f < c < 0xff or data[i] in ' \n\r':
                pass #cut beginning non-ascii characters
            else:
                data = data[i:]
                break

        data = data[::-1] #reversed
        for i in range(0, len(data)):
            c = ord(data[i])

            if 0 < c < 0x19 or 0x7f < c < 0xff or data[i] in ' \n\r':
                pass  #cut trailing non-ascii characters
            else:
                data = data[i:]
                break
        output = data[::-1]

        #output = re.sub('^[\x00-\x19\x7f-\xff\n\s]*[\x00-\x19\x7f-\xff]','',input) #look for starting non-ascii characters
        #output = re.sub('[\x00-\x19\x7f-\xff\s]+$','',output) #look for trailing non-ascii characters
        return output

