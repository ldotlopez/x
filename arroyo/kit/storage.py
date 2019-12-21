import abc
import configparser
import copy
import json
import os
import pathlib
import typing


class Storage:
    def __init__(self, location, **kwargs: typing.Dict[str, typing.Any]):
        self.location = location

    @abc.abstractmethod
    def read(self) -> typing.Any:
        raise NotImplementedError()

    @abc.abstractmethod
    def write(self, data: typing.Any):
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()


#
# Storage implementations
#


class MemoryStorage(Storage):
    def __init__(self):
        super().__init__(None)
        self.memory = {}

    def read(self):
        return copy.deepcopy(self.memory)

    def write(self, data):
        self.memory = copy.deepcopy(data)

    def close(self):
        pass


class JSONStorage(Storage):
    def __init__(self, location: str):
        super().__init__(location)
        self.touch(pathlib.Path(location))  # Create file if not exists
        self._fh = open(location, 'r+', encoding='utf-8')

    def read(self):
        self._fh.seek(0, os.SEEK_END)
        size = self._fh.tell()
        if size == 0:
            return {}

        self._fh.seek(0)
        return json.load(self._fh)

    def write(self, data):
        self._fh.seek(0)
        self._fh.write(json.dumps(data))
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.truncate()

    def close(self):
        self._fh.close()

    @staticmethod
    def touch(fname: pathlib.Path) -> None:
        base_dir = os.path.dirname(os.path.realpath(fname))
        os.makedirs(base_dir, exist_ok=True)

        if not os.path.exists(fname):
            with open(fname, 'a'):
                os.utime(fname, None)


class ConfigFileStorage(Storage):
    def __init__(self, location, root):
        super().__init__(location)
        self.root = root

    def readflat(self):
        def f():
            cp = configparser.ConfigParser()
            try:
                fh = open(self.location, encoding='utf-8')
            except FileNotFoundError as e:
                raise LocationNotFoundError() from e

            cp.read_file(fh)
            for sect in cp.sections():
                for (k, v) in cp[sect].items():
                    if self.root == sect:
                        k2 = k
                    else:
                        k2 = sect + '.' + k
                    yield (k2, v)
            fh.close()

        return dict(f())

    def read(self):
        def update(dest, k, v):
            if '.' not in k:
                dest[k] = v
            else:
                k1, kn = k.split('.', 1)
                if k1 not in dest:
                    dest[k1] = {}
                update(dest[k1], kn, v)

        ret = {}
        for (k, v) in self.readflat().items():
            update(ret, k, v)

        return ret


class LocationNotFoundError(Exception):
    pass
