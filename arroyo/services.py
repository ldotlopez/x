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


import importlib
import logging


DATABASE = 'database'
SETTINGS = 'setting'
LOADER = 'loader'


_services_reg = {
    DATABASE: None,
    LOADER: None,
    SETTINGS: None
}


_loggers = {}


_plugins = {
    'filters.state':
        'arroyo.plugins.filters.generic.StateFilter',
    'filters.source':
        'arroyo.plugins.filters.generic.SourceAttributeFilter',
    'filters.episode':
        'arroyo.plugins.filters.generic.EpisodeAttributeFilter',
    'filters.movie':
        'arroyo.plugins.filters.generic.MovieAttributeFilter',

    'providers.eztv':
        'arroyo.plugins.providers.eztv.EzTV',
    'providers.epublibre':
        'arroyo.plugins.providers.epublibre.EPubLibre',
    'providers.torrentapi':
        'arroyo.plugins.providers.torrentapi.TorrentAPI',
    'providers.thepiratebay':
        'arroyo.plugins.providers.thepiratebay.ThePirateBay',

    'sorters.basic':
        'arroyo.plugins.sorters.basic.Basic',

    'downloaders.transmission':
        'arroyo.plugins.downloaders.transmission.Tr'
}


def set_service(name, obj):
    if _services_reg[name] is not None:
        errmsg = "service '%s' already set"
        errmsg = errmsg % name
        raise ValueError(errmsg)

    _services_reg[name] = obj


class Services:
    LOADER = 'loader'
    SETTINGS = 'settings'


def get_service(name):
    if name not in _services_reg or _services_reg[name] is None:
        errmsg = "service '%s' is not configured"
        errmsg = errmsg % name
        raise ServiceNotFoundError(errmsg)

    return _services_reg[name]


def getLogger(name):
    global _loggers

    if not _loggers:
        logging.basicConfig()

    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)

    return _loggers[name]


class ClassLoader:
    def __init__(self, defs=None):
        self._reg = {}
        if defs:
            for (name, cls) in defs.items():
                self.register(name, cls)

    def resolve(self, clsstr):
        parts = clsstr.split('.')
        mod, cls = '.'.join(parts[0:-1]), parts[-1]

        if not mod:
            raise ValueError(clsstr)

        mod = importlib.import_module(mod)
        return getattr(mod, cls)

    def register(self, name, target):
        self._reg[name] = target

    def get(self, name, *args, **kwargs):
        return self.get_class(name)(*args, **kwargs)

    def get_class(self, name):
        try:
            cls = self._reg[name]
        except KeyError as e:
            raise ClassNotFoundError(name) from e

        if isinstance(cls, str):
            cls = self.resolve(cls)
            self._reg[name] = cls

        if not isinstance(cls, type):
            raise TypeError(type)

        return cls

    def list(self, ns=''):
        if ns:
            prefix = ns + '.'

        ret = [name for (name, cls) in self._reg.items()
               if name.startswith(prefix)]

        return ret


class Loader(ClassLoader):
    def __init__(self):
        super().__init__(_plugins)


class ClassNotFoundError(Exception):
    pass


class ServiceNotFoundError(Exception):
    pass
