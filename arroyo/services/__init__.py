from arroyo.kit import cache
import logging


class _Services:
    def __init__(self):
        self._cache = cache.NullCache()
        self._loader = None
        self._settings = None
        self._db = None
        self._logger = logging.getLogger('arroyo.services')

    def _setter(self, attr, value):
        logmsg = "Setting service %s to %s"
        logmsg = logmsg % (attr, value)
        self._logger.debug(logmsg)
        setattr(self, '_' + attr, value)

    @property
    def cache(self):
        return self._cache

    @cache.setter
    def cache(self, x):
        self._setter('cache', x)

    @property
    def loader(self):
        return self._loader

    @loader.setter
    def loader(self, x):
        self._setter('loader', x)

    @property
    def settings(self):
        return self._settings

    @settings.setter
    def settings(self, x):
        self._setter('settings', x)

    @property
    def db(self):
        return self._db

    @db.setter
    def db(self, x):
        self._setter('db', x)


services = _Services()
