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


from arroyo import (
    database,
    services
)


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
    def __init__(self, logger=None):
        self.logger = logger or services.getLogger('downloads')
        self.db = services.get_service(services.DATABASE)
        self.settings = services.get_service(services.SETTINGS)

    @property
    def downloader(self):
        loader = services.get_service(services.LOADER)
        name = self.settings.get('downloader')
        return loader.get('downloaders.' + name)

    def add(self, src):
        try:
            state = self.db.downloads.get_state(src)
        except database.NotFoundError:
            state = None

        if state is not None and state != State.ARCHIVED:
            # Download in progress, ignore
            return

        id_ = self.downloader.add(src.uri)
        if state is None:
            self.db.downloads.add(src, id_, State.INITIALIZING, src.entity)
        else:
            self.db.downloads.set_state(src, State.INITIALIZING)

    def cancel(self, src):
        external_id = self.db.downloads.external_for_source(src)
        self.downloader.cancel(external_id)
        self.db.downloads.delete(src)

    def archive(self, src):
        external_id = self.db.downloads.external_for_source(src)
        self.downloader.archive(external_id)
        self.db.downloads.set_state(src, State.ARCHIVED)

    def get_state(self, src):
        self.sync()
        return self.db.downloads.get_state(src)

    def get_active(self):
        self.sync()
        ret = [src
               for (src, state) in self.db.downloads.all_states()
               if state < State.ARCHIVED]

        return ret

    def sync(self):
        downloader_data = {}

        for x in self.downloader.dump():
            external_id = x['id']
            try:
                src = self.db.downloads.source_for_external(external_id)
                downloader_data[src] = x
            except database.NotFoundError:
                pass

        # Update in-app db data
        for (src, state) in self.db.downloads.all_states():
            if src in downloader_data:
                self.db.downloads.set_state(src, downloader_data[src]['state'])

            else:
                if state >= State.SHARING:
                    self.db.downloads.set_state(src, State.ARCHIVED)
                else:
                    self.db.downloads.delete(src)
