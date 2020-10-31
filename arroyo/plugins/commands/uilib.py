import sys
import zlib

import tabulate


import humanfriendly
from arroyo import downloads


def display_data(data, labels):
    print(tabulate.tabulate(data, headers=labels))


def build_dataset(db, fields, srcollection):
    if "state" in fields:
        # FIXME: query app, not db
        states = dict(db.downloads.all_states())
    if "count" in fields:
        count_g = (x for x in range(sys.maxsize))

    def _count_fn(src):
        nonlocal count_g
        return str(next(count_g) + 1)

    def _crc32_fn(src):
        return hex(zlib.crc32(src.name.encode("utf-8")))[2:]

    def _selected_fn(src):
        return "*" if src == srcollection[0] else " "

    def _state_fn(src):
        nonlocal states
        return downloads.STATE_SYMBOLS.get(states.get(src) or None) or " "

    def _name_fn(src):
        return src.name

    def _size_fn(src):
        return humanfriendly.format_size(src.size)

    def _share_fn(src):
        return "%s/%s" % (src.seeds or "-", src.leechers or "-")

    def _progress_fn(src):
        return "..."

    def _raw_source_fn(src):
        return src

    m = {
        "count": _count_fn,
        "crc32": _crc32_fn,
        "selected": _selected_fn,
        "state": _state_fn,
        "name": _name_fn,
        "size": _size_fn,
        "share": _share_fn,
        "progress": _progress_fn,
        "raw_source": _raw_source_fn,
    }

    fns = [m[f] for f in fields]
    datum = [[fn(src) for fn in fns] for src in srcollection]
    return datum
