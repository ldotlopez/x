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


import appdirs


APP_NAME = 'arroyo'

SETTINGS_PATH = "%s/%s/settings.ini" % (appdirs.user_config_dir(), APP_NAME)
DB_PATH = "%s/%s/db.json" % (appdirs.user_data_dir(), APP_NAME)
DEFAULT_LOGLEVEL = 2


LOG_FORMAT = "[%(levelname)s] [%(name)s] %(message)s"


KEY_SCRAPER_MAX_PARALEL_REQUESTS = 'fetch.max-paralel-requests'
KEY_SCRAPER_TIMEOUT = 'fetch.timeout'
KEY_SCRAPER_UA = 'fetch.user-agent'


SETTINGS = {
    'downloader': 'transmission',
    'sorter': 'basic',

    'cache.enabled': True,
    'cache.delta': 60*60,

    KEY_SCRAPER_UA: ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) '
                     'Gecko/20100101 Firefox/69.0'),
    KEY_SCRAPER_TIMEOUT: 15,
    KEY_SCRAPER_MAX_PARALEL_REQUESTS: 5,

    'plugin.transmission.host': 'localhost',
    'plugin.transmission.port': '9091',
}

PLUGINS = {
    'commands.dev':
        'arroyo.plugins.commands.dev.Command',
    'commands.downloads':
        'arroyo.plugins.commands.downloads.Downloads',
    'commands.search':
        'arroyo.plugins.commands.search.Search',

    'filters.state':
        'arroyo.plugins.filters.generic.StateFilter',
    'filters.source':
        'arroyo.plugins.filters.generic.SourceAttributeFilter',
    'filters.episode':
        'arroyo.plugins.filters.generic.EpisodeAttributeFilter',
    'filters.movie':
        'arroyo.plugins.filters.generic.MovieAttributeFilter',
    'filters.metadata':
        'arroyo.plugins.filters.generic.MetadataAttributeFilter',

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
