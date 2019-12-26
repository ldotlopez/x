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


# App
import arroyo
from arroyo import (
    analyze,
    database,
    downloads,
    loader,
    query,
    services,
    settings,
    scraper
)
from arroyo.kit import (
    cache,
    storage
)


import argparse
import logging
import os.path
import sys


import appdirs
import humanfriendly
import tabulate
try:
    import colorama
    _has_colorama = True
except ImportError:
    _has_colorama = False


APP_NAME = 'arroyo'

DEFAULT_SETTING = "%s/%s/settings.ini" % (appdirs.user_config_dir(), APP_NAME)
DEFAULT_DB = "%s/%s/db.json" % (appdirs.user_data_dir(), APP_NAME)
DEFAULT_LOGLEVEL = 2


LOG_FORMAT = "[%(levelname)s] [%(name)s] %(message)s"
LOG_LEVELS = [
    logging.CRITICAL,
    logging.ERROR,
    logging.WARNING,
    logging.INFO,
    logging.DEBUG
]


class App:
    def __init__(self, settings_path: str, database_path: str):
        touch(database_path)
        touch(settings_path)

        network_cache_path = appdirs.user_cache_dir() + '/arroyo/network'
        os.makedirs(network_cache_path, exist_ok=True)

        arroyo.services.settings = settings.Settings(
            settings.SafeConfigFileStore(settings_path, root=APP_NAME)
        )
        arroyo.services.db = database.Database(
            storage.JSONStorage(database_path)
        )

        arroyo.services.loader = loader.Loader()

        if arroyo.services.settings.get('cache.enabled'):
            arroyo.services.cache = cache.DiskCache(
                basedir=network_cache_path,
                delta=arroyo.services.settings.get('cache.delta')
            )

        self.scraper = scraper.Engine()
        self.filters = query.Engine()
        self.downloads = downloads.Downloads()

    def search(self, q, provider=None, uri=None):
        # Build filters for query
        try:
            filterctx = self.filters.build_filter_context(q)
        except query.MissingFiltersError as e:
            missing = e.args[0]
            msg = "Unknow filters: %s"
            msg = msg % ', '.join(missing)
            print(msg)
            return

        # Build scraper contexts
        if provider or uri:
            scrapectxs = [scraper.build_context(provider=provider, uri=uri)]
        else:
            scrapectxs = scraper.build_contexts_for_query(q)

        results = self.scraper.process(*scrapectxs)
        results = analyze.analyze(*results, mp=False)

        if not results:
            msg = "No results found for %r"
            msg = msg % q
            print(msg)
            return

        msg = "Found %s sources"
        msg = msg % (len(results),)
        print(msg)

        # Filter results
        results = self.filters.apply(filterctx, results)
        msg = "Got %s matching sources for %r"
        msg = msg % (len(results), q)
        print(msg)

        groups = self.filters.sort(results)
        return groups

    def get_downloads(self):
        g = sorted(self.downloads.get_all_states(),
                   key=lambda x: x[0].entity or x[0])

        return list(g)

    def cancel_download(self, src):
        self.downlaods.cancel(src)


class LogFormatter(logging.Formatter):
    if _has_colorama:
        COLOR_MAP = {
            logging.DEBUG: colorama.Fore.CYAN,
            logging.INFO: colorama.Fore.GREEN,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Back.RED,
        }
    else:
        COLOR_MAP = {}

    def format(self, record):
        s = super().format(record)

        color = self.COLOR_MAP.get(record.levelno)
        if color:
            s = color + s + colorama.Style.RESET_ALL

        return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--db',
        type=str,
        default=DEFAULT_DB)
    parser.add_argument(
        '--settings',
        type=str,
        default=DEFAULT_SETTING)
    parser.add_argument(
        '-q', '--quiet',
        default=0,
        action='count')
    parser.add_argument(
        '-v', '--verbose',
        default=0,
        action='count')

    commands = parser.add_subparsers(dest='command', required=True)
    search_cmd = commands.add_parser('search')
    search_cmd.add_argument(
        '--provider',
        help='Force some provider')
    search_cmd.add_argument(
        '--uri',
        help='URI to parse')
    search_cmd.add_argument(
        '-f', '--filter',
        dest='queryparams',
        action='append',
        default=[])
    search_cmd.add_argument(
        '--download',
        action='store_true',
        help='Add selected items to downloads')
    search_cmd.add_argument(
        dest='querystring',
        nargs='?')

    search_cmd = commands.add_parser('downloads')
    search_cmd.add_argument(
        '--list',
        action='store_true',
        help='Show current downloads')
    search_cmd.add_argument(
        '--cancel',
        help='Cancel a download')

    args = parser.parse_args(sys.argv[1:])

    # Setup services
    loglevel = DEFAULT_LOGLEVEL - args.quiet + args.verbose
    loglevel = max(0, min(loglevel, len(LOG_LEVELS) - 1))
    setupLogging(level=LOG_LEVELS[loglevel], format=LOG_FORMAT)

    app = App(settings_path=args.settings, database_path=args.db)

    if args.command == 'search':
        if args.queryparams:
            queryparams = dict([x.split('=', 1) for x in args.queryparams])
            q = query.Query(**queryparams)
        elif args.querystring:
            q = query.Query.fromstring(args.querystring)

        results = app.search(q, provider=args.provider, uri=args.uri)
        states = dict(services.db.downloads.all_states())

        for (entity, sources) in results:
            print(str(entity))
            print(display_group(sources, states))
            print("")

    elif args.command == 'downloads':
        import zlib
        if args.list:
            headers = ['id', 'state', 'name', 'size', 'progress']
            data = [
                (hex(zlib.crc32(src.name.encode('utf-8')))[2:],
                 downloads.STATE_SYMBOLS.get(state) or ' ',
                 src.name,
                 humanfriendly.format_size(src.size),
                 '??')
                for (src, state)
                in app.get_downloads()
            ]
            print(tabulate.tabulate(data, headers=headers))

    else:
        parser.print_help()


def display_group(sources, states=None):


    if states is None:
        states = {}

    headers = ['selected', 'state', 'name', 'size']
    table = [
        ['*' if src == sources[0] else ' ',
         downloads.STATE_SYMBOLS.get(states.get(src) or None) or ' ',
         src.name,
         humanfriendly.format_size(src.size)]
        for src in sources
    ]
    return tabulate.tabulate(table, headers=headers)


def touch(filepath, contents=None, mode='wb', encoding='utf-8'):
    filepath = os.path.realpath(filepath)
    dirname = os.path.dirname(filepath)
    os.makedirs(dirname, exist_ok=True)
    if contents:
        with open(filepath, mode=mode, encoding=encoding) as fh:
            fh.write(contents)


def setupLogging(level, format="%(message)s"):
    handler = logging.StreamHandler()
    handler.setFormatter(LogFormatter(format))
    logger = logging.getLogger(APP_NAME)
    logger.addHandler(handler)
    logger.setLevel(level)
