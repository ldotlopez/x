import hashlib
from urllib import parse

from arroyo.analyze import analyze_one
from arroyo.schema import Source


def build_source(name, **kwargs):
    sha1 = hashlib.sha1()
    sha1.update(name.encode('utf-8'))

    uri = 'magnet:?dn=%s&xt=urn:btih:%s' % (
        parse.quote(name), sha1.hexdigest())
    params = {
        'uri': uri,
        'provider': 'mock'
    }
    params.update(kwargs)
    return Source(name=name, **params)


def build_item(name, **kwargs):
    src = build_source(name, **kwargs)
    item = analyze_one(src)
    return item
