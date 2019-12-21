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
from arroyo.kit.settings import (
    Settings as KitSettings,
    UNDEF
)
from arroyo.kit.storage import (
    ConfigFileStorage,
    LocationNotFoundError
)


class SafeConfigFileStore(ConfigFileStorage):
    def __init__(self, *args, logger, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger

    def read(self):
        try:
            return super().read()
        except LocationNotFoundError:
            logmsg = "Location '%s' not found" % self.location
            self.logger.warning(logmsg)
            return {}


class Settings(KitSettings):
    DEFAULTS = {
        'downloader': 'transmission',
        'plugin.transmission.host': 'localhost',
        'plugin.transmission.port': '9091',
    }

    def __init__(self, location):
        self.logger = services.getLogger('services')
        store = SafeConfigFileStore(location, root='arroyo', logger=self.logger)
        super().__init__(store)

    def get(self, key, default=UNDEF):
        if default == UNDEF:
            default = self.DEFAULTS.get(key) or UNDEF

        return super().get(key, default=default)