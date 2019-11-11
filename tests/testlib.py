import hashlib
from typing import *
from urllib import parse

from arroyo.analyze import analyze_one
from arroyo.schema import Source
from arroyo.services import _services_reg


_services_patches: Dict[str, object] = {}


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


def patch_service(service, obj):
    global _services_patches

    if service not in _services_patches:
        _services_patches[service] = []

    _services_patches[service].append(_services_reg[service])
    _services_reg[service] = obj


def unpatch_service(service):
    global _services_patches

    obj = _services_patches[service].pop(-1)
    _services_reg[service] = obj
