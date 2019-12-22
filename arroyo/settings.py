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


import logging


from arroyo.kit.settings import (
    Settings as KitSettings,
    UNDEF
)
from arroyo.kit.storage import (
    ConfigFileStorage,
    LocationNotFoundError
)


class SafeConfigFileStore(ConfigFileStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger('arroyo.safe-config-file-store')

    def read(self):
        try:
            return super().read()
        except LocationNotFoundError:
            logmsg = "Location '%s' not found" % self.location
            self._logger.warning(logmsg)
            return {}


class Settings(KitSettings):
    DEFAULTS = {
        'downloader': 'transmission',
        'sorter': 'basic',
        'plugin.transmission.host': 'localhost',
        'plugin.transmission.port': '9091',
    }

    def get(self, key, default=UNDEF):
        if default == UNDEF:
            default = self.DEFAULTS.get(key) or UNDEF

        return super().get(key, default=default)
