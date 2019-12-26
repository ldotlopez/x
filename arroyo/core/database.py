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


from arroyo import schema


class Database:
    def __init__(self, storage):
        self._storage = storage
        self.data = self._storage.read() or {
            'version': 1,
            'downloads': {}
        }
        self.downloads = _Downloads(self)

    def commit(self):
        self._storage.write(self.data)


class _Downloads:
    SOURCE = 0
    EXTERNAL = 1
    STATE = 2
    ENTITY = 3

    def __init__(self, db):
        self.db = db
        self.data = db.data

    def add(self, src, external, state=0, entity=None):
        if src.id in self.data['downloads']:
            raise IntegrityError()

        row = [src.dict(), external, state, entity.dict() if entity else {}]
        self.data['downloads'][src.id] = row
        self.db.commit()

    def delete(self, src):
        try:
            del(self.data['downloads'][src.id])
        except KeyError as e:
            raise NotFoundError() from e
        self.db.commit()

    def set_state(self, src, state):
        try:
            self.data['downloads'][src.id][self.STATE] = state
        except KeyError as e:
            raise NotFoundError() from e
        self.db.commit()

    def get_state(self, src):
        try:
            return self.data['downloads'][src.id][self.STATE]
        except KeyError as e:
            raise NotFoundError() from e

    def all_states(self):
        yield from ((schema.Source(**row[self.SOURCE]), row[self.STATE])
                    for row in self.data['downloads'].values())

    def external_for_source(self, src):
        try:
            return self.data['downloads'][src.id][self.EXTERNAL]
        except KeyError as e:
            raise NotFoundError() from e

    def source_for_external(self, external):
        row = self._find_one(self.EXTERNAL, external)
        srcdata = row[self.SOURCE]
        return schema.Source(**srcdata)

    def sources_for_entity(self, entity):
        entity = entity.dict()
        return [
            schema.Source(**row[self.SOURCE])
            for row in self._find(self.ENTITY, entity)]

    def _find(self, column, value):
        def _fn():
            for row in self.data['downloads'].values():
                if row[column] == value:
                    yield row

        return list(_fn())

    def _find_one(self, column, value):
        res = self._find(column, value)
        if not res:
            raise NotFoundError()

        if len(res) > 1:
            raise MultipleResultsError()

        return res[0]


class IntegrityError(Exception):
    pass


class NotFoundError(Exception):
    pass


class MultipleResultsError(Exception):
    pass
