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


import enum
import pickle
import typing


import pydantic


from arroyo import schema
import functools


class State(enum.Enum):
    INITIALIZING = 1
    QUEUED = 2
    PAUSED = 3
    DOWNLOADING = 4
    SHARING = 5
    DONE = 6
    ARCHIVED = 7


STATE_SYMBOLS = {
    # State.NONE: ' ',
    State.INITIALIZING: '⋯',
    State.QUEUED: '⋯',
    State.PAUSED: '‖',
    State.DOWNLOADING: '↓',
    State.SHARING: '⇅',
    State.DONE: '✓',
    State.ARCHIVED: '▣'
}


class SchemaV1(pydantic.BaseModel):
    # version: typing_extensions.Literal(1)
    states: typing.Dict[schema.Source, State] = {}
    by_id: typing.Dict[str, schema.Item] = {}
    # by_entity: typing.Dict[
    #     typing.Union[schema.Episode, schema.Movie], str
    # ] = {}


class Downloads:
    def __init__(self, loader):
        self.loader = loader
        self.downloader = loader.get('downloader')
        self.db = Database()

    def add(self, src):
        id_ = self.downloader.add(src.uri)
        self.db.update(id_, src, State.INITIALIZING)

    def cancel(self, src):
        self.sync()
        id_ = self.db.get_id(src)
        self.db.remove(id_)

    def archive(self, src):
        self.sync()
        id_ = self.db.to_id(src)
        self.db.update(id_, src, State.ARCHIVED)

    def get_state(self, src):
        self.sync()
        id_ = self.db.to_id(src)
        states = self.db.get_all_states()
        return states[id_]

    def list(self):
        self.sync()
        return [self.db.to_source(x) for x in self.db.list()]

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
                if state == State.DONE:
                    self.db.update(src, State.ARCHIVED)
                else:
                    self.db.remove(src)


def catch_keyerror(meth):
    @functools.wraps(meth)
    def _wrap(*args, **kwargs):
        try:
            return meth(*args, **kwargs)
        except KeyError as e:
            raise UnknowObjectError() from e

    return _wrap


class Database:
    def __init__(self, initial_data: SchemaV1 = None):
        super().__init__()
        # self.data = initial_data or SchemaV1()
        self.by_id: typing.Dict[str, typing.Tuple[schema.Source, State]] = {}
        self.source_map: typing.Dict[schema.Source, str] = {}

    def load(self, buffer):
        self.data = pickle.load(buffer)

    def dump(self):
        return pickle.dump(self.data)

    def to_id(self, src):
        return self.source_map[src]

    def to_source(self, id):
        return self.by_id[id][0]

    def list(self):
        return list(self.by_id.keys())

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

    # def _get_key(self, d, key):
    #     try:
    #         return d[key]
    #     except KeyError as e:
    #         raise UnknowObjectError() from e

    # def add(self, id_, src, state=State.INITIALIZING):
    #     self.data.states[src] = state
    #     self.data.by_id[id_] = src

    # def list(self):
    #     return list(self.data.states.keys())

    # @catch_keyerror
    # def get_state(self, src):
    #     return self._get_key(self.data.states, src)

    # def get_source_by_id(self, id_):
    #     return self._get_key(self.data.by_id, id_)

    # def get_state_by_id(self, id_):
    #     src = self.get_source_by_id(id_)
    #     return self.get_state(src)

    # def set_state(self, item, state):
    #     # O(1)
    #     self.data.states[item.source] = state
    #     self.data.by_id[item.source.id] = item.source
    #     self.data.by_entity[item.entity] = item.source.id

    # def get_state(self, item):
    #     # O(1)
    #     return self._get_key(self.data.states, item.source)

    # def get_by_id(self, id_):
    #     return self._get_key(self.data.by_id, id_)

    # def get_sources_in_state(self, states):
    #     # O(n)
    #     if not isinstance(states, (list, tuple)):
    #         states = list(states)

    #     return [source
    #             for (source, state) in self.data.states.items()
    #             if state in states]

    # def get_entity_source(self, entity):
    #     # O(1)
    #     id_ = self._get_key(self.data.by_entity, entity)
    #     src = self._get_key(self.data.by_id, id_)
    #     return src


class UnknowObjectError(Exception):
    pass
