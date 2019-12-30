import argparse
import logging
import os


import appdirs
try:
    import colorama
    _has_colorama = True
except ImportError:
    _has_colorama = False


from arroyo import (
    core,
    analyze,
    downloads,
    scraper,
    query
)
from arroyo.kit import (
    cache,
    loader,
    settings,
    storage
)
from arroyo.services import (
    database,
)


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

SETTINGS = {
    'cache.enabled': True,
    'cache.delta': 60*60,
    'downloader': 'transmission',
    'sorter': 'basic',
    'plugin.transmission.host': 'localhost',
    'plugin.transmission.port': '9091',
}

PLUGINS = {
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


class App:

    def __init__(self, settings_path: str, database_path: str,
                 log_level: int = logging.WARNING):
        setupLogging(level=log_level, format=LOG_FORMAT)

        touch(database_path)
        touch(settings_path)

        network_cache_path = appdirs.user_cache_dir() + '/arroyo/network'
        os.makedirs(network_cache_path, exist_ok=True)

        core.settings = Settings(ConfigFileStorage(settings_path, root=APP_NAME))
        core.db = database.Database(storage.JSONStorage(database_path))
        core.loader = loader.ClassLoader(PLUGINS)

        if core.settings.get('cache.enabled'):
            core.cache = cache.DiskCache(
                basedir=network_cache_path,
                delta=core.settings.get('cache.delta')
            )

        self.scraper = scraper.Engine()
        self.filters = query.Engine()
        self.downloads = downloads.Downloads()

    def query(self, q, provider=None, uri=None):
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

    def download(self, source):
        self.downloads.add(source)

    def get_downloads(self):
        g = sorted(self.downloads.get_all_states(),
                   key=lambda x: x[0].entity or x[0])

        return list(g)

    def cancel(self, source):
        self.downloads.cancel(source)

    def run_command_line(self, argv, parser=None):
        if not parser:
            parser = build_argparse()

        exes = {}

        commands = parser.add_subparsers(dest='command', required=True)
        for name in core.loader.list('commands'):
            plugin = core.loader.get(name)
            exes[plugin.COMMAND_NAME] = plugin

            cmd = commands.add_parser(plugin.COMMAND_NAME)
            plugin.configure_command_parser(cmd)

        args = parser.parse_args(argv)
        if args.help:
            parser.print_help()
            return

        return exes[args.command].run(self, args)


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
            default = SETTINGS.get(key) or settings.UNDEF

        return super().get(key, default=default)


class ConfigFileStorage(storage.ConfigFileStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = logging.getLogger('arroyo.config-file-storage')

    def read(self):
        try:
            return super().read()
        except storage.LocationNotFoundError:
            logmsg = "Location '%s' not found" % self.location
            self._logger.warning(logmsg)
            return {}

    def write(self, data):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()


def build_argparse():
    parser = argparse.ArgumentParser(add_help=False)
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
    parser.add_argument(
        '-h', '--help',
        action='store_true')

    return parser


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
