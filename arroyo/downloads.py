# -*- coding: utf-8 -*-

# Copyright (C) 2015 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


import pickle
import typing


import pydantic


from arroyo import (
    schema,
    services
)
import functools


# Don't make state an Enum
# If state are defined as ints we can compare as __gt__ and __lt__
class State:
    INITIALIZING = 1
    QUEUED = 2
    PAUSED = 3
    DOWNLOADING = 4
    SHARING = 5
    DONE = 6
    ARCHIVED = 7


# STATE_SYMBOLS = {
#     # State.NONE: ' ',
#     State.INITIALIZING: '⋯',
#     State.QUEUED: '⋯',
#     State.PAUSED: '‖',
#     State.DOWNLOADING: '↓',
#     State.SHARING: '⇅',
#     State.DONE: '✓',
#     State.ARCHIVED: '▣'
# }


class Downloads:
    def __init__(self):
        self.db = services.get_service(services.DOWNLOADS_DB)

    @property
    def downloader(self):
        loader = services.get_service(services.LOADER)
        return loader.get('downloader')

    def add(self, src):
        id_ = self.downloader.add(src.uri)
        self.db.update(id_, src, State.INITIALIZING)

    def cancel(self, src):
        id_ = self.db.to_id(src)
        self.downloader.cancel(id_)
        self.db.remove(id_)

    def archive(self, src):
        id_ = self.db.to_id(src)
        self.downloader.archive(id_)
        self.db.update(id_, src, State.ARCHIVED)

    def get_state(self, src):
        self.sync()
        id_ = self.db.to_id(src)
        states = self.db.get_all_states()
        return states[id_]

    def list(self):
        self.sync()
        ret = [self.db.to_source(id)
               for (id, state) in self.db.get_all_states().items()
               if state < State.ARCHIVED]
        return ret

    def sync(self):
        # Load known data from downloader, indexed by source
        downloader_data = {}
        for x in self.downloader.dump():
            try:
                downloader_data[self.db.to_source(x['id'])] = x
            except UnknowObjectError:
                pass

        # Update in-app db data
        for (id_, state) in self.db.get_all_states().items():
            src = self.db.to_source(id_)

            if src in downloader_data:
                self.db.update(id_, src, downloader_data[src]['state'])

            else:
                if state >= State.SHARING:
                    self.db.update(id_, src, State.ARCHIVED)
                else:
                    self.db.remove(id_)


def catch_keyerror(meth):
    @functools.wraps(meth)
    def _wrap(*args, **kwargs):
        try:
            return meth(*args, **kwargs)
        except KeyError as e:
            raise UnknowObjectError() from e

    return _wrap


class RawDatabase:
    def __init__(self,
                 by_id:
                 typing.Dict[str, typing.Tuple[schema.Source, int]] = None,
                 source_map:
                 typing.Dict[schema.Source, str] = None):
        if by_id is None:
            by_id = {}

        if source_map is None:
            source_map = {}

        self.by_id = by_id
        self.source_map = source_map

    @classmethod
    def frombuffer(cls, buffer):
        data = pickle.loads(buffer)
        return cls(by_id=data['by_id'], source_map=data['source_map'])

    def dump(self):
        return pickle.dumps({
            'version': 1,
            'by_id': self.by_id,
            'source_map': self.source_map
        })

    @catch_keyerror
    def to_id(self, src):
        return self.source_map[src]

    @catch_keyerror
    def to_source(self, id):
        return self.by_id[id][0]

    def list(self):
        return list(self.by_id.keys())

    @catch_keyerror
    def update(self, id, src, state):
        self.by_id[id] = (src, state)
        self.source_map[src] = id

    @catch_keyerror
    def remove(self, id):
        src = self.to_source(id)
        del(self.by_id[id])
        del(self.source_map[src])

    def get_all_states(self):
        ret = {id_: state
               for (id_, (_, state)) in self.by_id.items()}
        return ret


class Database(RawDatabase):
    dbpath: str

    def __init__(self, dbpath):
        self.dbpath = dbpath

        try:
            with open(self.dbpath, 'rb') as fh:
                data = pickle.loads(fh.read())

        except FileNotFoundError:
            data = {
                'by_id': {},
                'source_map': {}
            }

        super().__init__(by_id=data['by_id'], source_map=data['source_map'])

    def update(self, *args, **kwargs):
        ret = super().update(*args, **kwargs)

        with open(self.dbpath, 'wb') as fh:
            fh.write(self.dump())

        return ret


class UnknowObjectError(Exception):
    pass
