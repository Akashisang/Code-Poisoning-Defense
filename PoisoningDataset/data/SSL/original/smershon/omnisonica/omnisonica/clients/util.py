import requests

import ssl
from functools import wraps

def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)
    return bar

ssl.wrap_socket = sslwrap(ssl.wrap_socket)

def retry(uri, retries=5):
    while retries:
        try:
            resp = requests.get(uri)
        except:
            retries -= 1
        else:
            return resp
    raise Exception('Uh, not working dude')

def batch_as_stream(input_stream, process_func, batch_size=100):
    buffer = []
    for item in input_stream:
        buffer.append(item)
        if len(buffer) >= batch_size:
            for processed_item in process_func(buffer):
                yield processed_item
            buffer = []
    if buffer:
        for processed_item in process_func(buffer):
            yield processed_item
            
def clean_title(title):
    cleaned_title = []
    for i,token in enumerate(title.split(' ')):
        if (token.startswith('-') 
                or (token.startswith('(') and i >= 1)
                or (token.startswith('[') and i >= 1)):
            break
        cleaned_title.append(token)
    return ' '.join(cleaned_title)
    
def batch_retrieve(data, src_field, lookup_fn, tgt_field=None, default=None):
    tgt_field = tgt_field or src_field
    lookup = lookup_fn(set([x[src_field] for x in data]))
    for d in data:
        d[tgt_field] = lookup.get(d[src_field], default)
     
    