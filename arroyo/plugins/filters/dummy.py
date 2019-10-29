from arroyo import Filter


import fnmatch
import re



class Generic(Filter):
    HANDLES = [
        'name', 'name-like', 'name-glob',
        'uri', 'uri-like', 'uri-glob',
        'size', 'size-min', 'size-max',
        'seeds''seeds-min', 'seeds-max',
        'leechers', 'leechers-min', 'leechers-max',
        'created', 'created-min', 'created-max',
        'age', 'age-min', 'age-max',
        'provider', 'provider-in'
    ]

    def filter(self, key, value, item):
        key, fn = eval_key(key)
        return False


def eval_key(key):
    if key.endswith('-like'):
        key = key[:-5]
        fn = cmp_like

    elif key.endswith('-glob'):
        key = key[:-5]
        fn = cmp_glob

    elif key.endswith('-min'):
        key = key[:-4]
        fn = cmp_min

    elif key.endswith('-max'):
        key = key[:-4]
        fn = cmp_max

    else:
        fn = cmp_eq

    return key, fn


def cmp_eq(a, b):
    return a == b


def cmp_min(n, limit):
    return n >= limit


def cmp_max(n, limit):
    return n <= limit


def cmp_glob(s, pattern):
    return fnmatch.fnmatch(s, pattern)


def cmp_like(s, pattern):
    re.match(pattern, s)
