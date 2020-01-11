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


"""Cache services"""

import abc
import hashlib
import os
import pathlib
import pickle
import shutil
import sys
import tempfile
import time


def _now():
    return time.time()


class CacheKeyError(KeyError):
    """
    Base class for cache errors
    """
    pass


class CacheKeyMissError(CacheKeyError):
    """
    Requested key is missing in cache
    """
    pass


class CacheKeyExpiredError(CacheKeyError):
    """
    Requested key is expired in cache
    """
    pass


class CacheIOError(IOError):
    """
    Cache error related to I/O errors
    """
    pass


class CacheOSError(OSError):
    """
    Cache error related to OS errors
    """
    pass


class BaseCache:
    """
    Abstract base class for all appkit caches
    """
    def __init__(self, delta=0, *args, **kwargs):
        try:
            delta = float(delta)
        except ValueError as e:
            msg = "delta must be an int/float"
            raise TypeError(msg) from e

        if delta < 0:
            delta = sys.maxsize

        self.delta = delta

    def encode_key(self, key):
        return key

    def encode_value(self, value):
        return value

    def decode_value(self, value):
        return value

    @abc.abstractmethod
    def get(self, key):
        raise NotImplementedError()

    @abc.abstractmethod
    def set(self, key, value):
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, key):
        raise NotImplementedError()

    @abc.abstractmethod
    def purge(self):
        raise NotImplementedError()


class NullCache(BaseCache):
    def get(self, key):
        raise CacheKeyMissError(key)

    def set(self, key, data):
        pass


class MemoryCache(BaseCache):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mem = {}

    def get(self, key):
        if key not in self._mem:
            raise CacheKeyMissError(key)

        ts, value = self._mem[key]
        now = _now()

        if now - ts > self.delta:
            del(self._mem[key])
            raise CacheKeyExpiredError(key)

        return value

    def set(self, key, value):
        self._mem[key] = (_now(), value)

    def delete(self, key):
        try:
            del(self._mem[key])
        except KeyError:
            pass

    def purge(self):
        expired = []
        now = _now()

        for (key, (ts, dummy)) in self._mem.items():
            if now - ts > self.delta:
                expired.append(key)

        for key in expired:
            self.delete(key)


class DiskCache(BaseCache):
    def __init__(self, basedir=None, *args, **kwargs):
        """
        Disk-based cache.
        Parameters:
          basedir - Root path for cache. Auxiliar cache files will be stored
                    under this path. If None is suplied then a temporal dir
                    will be used.
        """
        super().__init__(*args, **kwargs)

        self._is_tmp = basedir is None
        if basedir is None:
            self.basedir = tempfile.mkdtemp()
        else:
            self.basedir = basedir

        self.basedir = pathlib.Path(self.basedir)

    def encode_key(self, key):
        hashed = hashlib.sha1(key.encode('utf-8')).hexdigest()
        return self.basedir / hashed[0] / hashed[:2] / hashed

    def encode_value(self, value):
        return pickle.dumps(value)

    def decode_value(self, value):
        return pickle.loads(value)

    def _key_is_expired(self, key):
        p = pathlib.Path(self.encode_key(key))
        return self._path_is_expired(p)

    def _path_is_expired(self, p):
        return _now() - p.stat().st_ctime > self.delta

    def set(self, key, value):
        p = pathlib.Path(self.encode_key(key))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.encode_value(value))

    def get(self, key):
        p = pathlib.Path(self.encode_key(key))

        try:
            expired = self._path_is_expired(p)

        except (OSError, IOError) as e:
            raise CacheKeyMissError(key) from e

        if expired:
            self.delete(key)
            raise CacheKeyExpiredError(key)

        try:
            return self.decode_value(p.read_bytes())

        except EOFError as e:
            self.delete(key)
            raise CacheKeyError(key) from e

        except IOError as e:
            raise CacheIOError() from e

        except OSError as e:
            raise CacheOSError() from e

    def delete(self, key):
        p = pathlib.Path(self.encode_key(key))
        try:
            p.unlink()

        except FileNotFoundError:
            pass

        except IOError as e:
            raise CacheIOError() from e

        except OSError as e:
            raise CacheOSError() from e

    def purge(self):
        expugned = []

        for (dirpath, dirs, files) in os.walk(str(self.basedir)):
            files = [self.basedir / dirpath / f for f in files]
            expugned.extend([f for f in files if self._path_is_expired(f)])

        for f in expugned:
            assert str(f).startswith(str(self.basedir))
            f.unlink()

    def __del__(self):
        if self._is_tmp:
            shutil.rmtree(str(self.basedir))
