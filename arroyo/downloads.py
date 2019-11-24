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


from arroyo import services


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
        self.db = services.get_service(services.DATABASE)

    @property
    def downloader(self):
        loader = services.get_service(services.LOADER)
        return loader.get('downloader')

    def add(self, src):
        id_ = self.downloader.add(src.uri)
        self.db.external_ids.map(src, id_)
        self.db.states.set(src, State.INITIALIZING)

    def cancel(self, src):
        external_id = self.db.external_ids.get_external(src)
        self.downloader.cancel(external_id)
        self.db.states.drop(src)
        # id_ = self.db.to_id(src)
        # self.downloader.cancel(id_)
        # self.db.remove(id_)

    def archive(self, src):
        external_id = self.db.external_ids.get_external(src)
        self.downloader.archive(external_id)
        self.db.states.set(src, State.ARCHIVED)
        # id_ = self.db.to_id(src)
        # self.downloader.archive(id_)
        # self.db.update(id_, src, State.ARCHIVED)

    def get_state(self, src):
        self.sync()
        return self.db.states.get(src)
        # id_ = self.db.to_id(src)
        # states = self.db.get_all_states()
        # return states[id_]

    def list(self):
        self.sync()
        ret = [src
               for (src, state) in self.db.states.all()
               if state < State.ARCHIVED]

        return ret

    def sync(self):
        downloader_data = {}

        for x in self.downloader.dump():
            external_id = x['id']
            try:
                native_id = self.db.external_ids.get_source(external_id)
                downloader_data[native_id] = x
            except KeyError:
                pass

        # Update in-app db data
        for (src, state) in list(self.db.states.all()):
            if src in downloader_data:
                self.db.states.set(src, downloader_data[src]['state'])

            else:
                if state >= State.SHARING:
                    self.db.states.set(src, State.ARCHIVED)
                else:
                    self.db.states.drop(src)
