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


import argparse
import logging
import os

import appdirs
from arroyo import analyze, defaults, downloads, extensions, query, scraper
from arroyo.services import (
    Services,
    cache,
    database,
    loader,
    settings,
    storage,
)

try:
    import colorama

    _has_colorama = True
except ImportError:
    _has_colorama = False


class App:
    def __init__(
        self,
        settings_path: str,
        database_path: str,
        log_level: int = logging.WARNING,
    ):
        # Setup logging
        handler = logging.StreamHandler()
        handler.setFormatter(LogFormatter(defaults.LOG_FORMAT))

        logger = logging.getLogger(defaults.APP_NAME)
        logger.setLevel(log_level)
        logger.addHandler(handler)

        # Setup filepaths
        touch(database_path)
        touch(settings_path)

        network_cache_path = appdirs.user_cache_dir() + "/arroyo/network"
        os.makedirs(network_cache_path, exist_ok=True)

        # Setup core
        self.srvs = Services(
            logger=logger,
            db=database.Database("sqlite:///" + database_path),
            settings=Settings(
                ConfigFileStorage(settings_path, root=defaults.APP_NAME)
            ),
            loader=loader.ClassLoader(defaults.PLUGINS),
        )

        if self.srvs.settings.get("cache.enabled"):
            self.srvs.cache = cache.DiskCache(
                basedir=network_cache_path,
                delta=self.srvs.settings.get("cache.delta"),
            )

        # Setup engines
        self.scraper = scraper.Engine(self.srvs)
        self.filters = query.Engine(self.srvs)
        self.downloads = downloads.Downloads(self.srvs)

    def query(self, q, provider=None, uri=None):
        filterctx = self.filters.build_filter_context(q)

        # Build scraper contexts
        if provider or uri:
            scrapectxs = [
                self.scraper.build_context(provider=provider, uri=uri)
            ]
        else:
            scrapectxs = self.scraper.build_contexts_for_query(q)

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

    def download(self, source):
        self.downloads.add(source)

    def get_downloads(self):
        g = sorted(
            self.downloads.get_all_states(), key=lambda x: x[0].entity or x[0]
        )

        return list(g)

    def cancel(self, source):
        self.downloads.cancel(source)

    def run_command_line(self, argv, parser=None):
        if not parser:
            parser = build_argparse()

        exes = {}

        commands = parser.add_subparsers(dest="command", required=True)
        subcommands = {}
        for name in self.srvs.loader.list("commands"):
            plugin = self.srvs.loader.get(name, self.srvs)
            exes[plugin.COMMAND_NAME] = plugin

            subcommands[plugin.COMMAND_NAME] = commands.add_parser(
                plugin.COMMAND_NAME
            )
            plugin.configure_command_parser(subcommands[plugin.COMMAND_NAME])

        args = parser.parse_args(argv)
        if args.help:
            parser.print_help()
            return

        try:
            return exes[args.command].run(self, args)
        except extensions.CommandUsageError:
            subcommands[args.command].print_help()


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


class Settings(settings.Settings):
    def get(self, key, default=settings.UNDEF):
        if default == settings.UNDEF:
            default = defaults.SETTINGS.get(key) or settings.UNDEF

        ret = super().get(key, default=default)
        return ret


class ConfigFileStorage(storage.ConfigFileStorage):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self._logger = logging.getLogger('arroyo.config-file-storage')

    # def read(self):
    #     try:
    #         return super().read()
    #     except storage.LocationNotFoundError:
    #         logmsg = "Location '%s' not found" % self.location
    #         self._logger.warning(logmsg)
    #         return {}

    def write(self, data):
        super().write(data)


def build_argparse():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--db", type=str, default=defaults.DB_PATH)
    parser.add_argument("--settings", type=str, default=defaults.SETTINGS_PATH)
    parser.add_argument("-q", "--quiet", default=0, action="count")
    parser.add_argument("-v", "--verbose", default=0, action="count")
    parser.add_argument("-h", "--help", action="store_true")

    return parser


def touch(filepath, contents=None, mode="wb", encoding="utf-8"):
    filepath = os.path.realpath(filepath)
    dirname = os.path.dirname(filepath)
    os.makedirs(dirname, exist_ok=True)
    if contents:
        with open(filepath, mode=mode, encoding=encoding) as fh:
            fh.write(contents)
