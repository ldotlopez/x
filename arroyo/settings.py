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

from arroyo.kit.settings import (
    Settings as KitSettings,
    UNDEF
)
from arroyo.kit.storage import ConfigFileStorate


class Settings(KitSettings):
    DEFAULTS = {
        'downloader': 'transmission',
        'plugin.transmission.host': 'localhost',
        'plugin.transmission.port': '9091',
    }

    def __init__(self, location):
        super().__init__(ConfigFileStorate(location, root='arroyo'))

    def get(self, key, default=UNDEF):
        if default == UNDEF:
            default = self.DEFAULTS.get(key) or UNDEF

        return super().get(key, default=default)
