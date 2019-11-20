import abc
import collections
import contextlib
import threading
import typing
import pathlib
import json
import os

# import tinydb
# import tinydb.storages


class Storage:
    def __init__(self, **kwargs: typing.Dict[str, typing.Any]):
        pass

    @abc.abstractmethod
    def read(self) -> typing.Dict[str, typing.Any]:
        raise NotImplementedError()

    @abc.abstractmethod
    def write(self, data: collections.Mapping) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()


class MemoryStorage(Storage):
    def __init__(self):
        self.memory = {}

    def read(self):
        return self.memory

    def write(self, data):
        self.memory = data

    def close(self):
        pass


class JSONStorage(Storage):
    def __init__(self, path: pathlib.Path):
        super().__init__()
        self.touch(path, create_dirs=True)  # Create file if not exists
        self._fh = open(path, 'r+', encoding='utf-8')

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
    def touch(fname: pathlib.Path, create_dirs: bool) -> None:
        if create_dirs:
            base_dir = os.path.dirname(fname)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)

        if not os.path.exists(fname):
            with open(fname, 'a'):
                os.utime(fname, None)


class Database:
    def __init__(self,
                 storage: typing.Type[Storage] = MemoryStorage,
                 **kwargs: typing.Dict[str, typing.Any]):
        self.storage = storage(**kwargs)
        self.lock = threading.Lock()
        self.tables: typing.Dict[str, typing.Type[Table]] = {}
        self.data: DataContainer = self.storage.read() or {}

    def __del__(self) -> None:
        self.storage.close()

    def sync(self) -> None:
        self.storage.write(self.data)

    def create_table(self, name, cls):
        if name not in self.data:
            self.data[name] = {}
        self.sync()

        self.tables[name] = cls(self, self.data[name])
        return self.tables[name]

    def table(self, name):
        return self.tables[name]

    def __getattr__(self, attr):
        tables = getattr(self, 'tables')
        try:
            return tables[attr]
        except KeyError as e:
            raise TableError(attr) from e


class TableError(Exception):
    pass


DataContainer = typing.Dict[str, typing.Any]


class Table:
    def __init__(self, db: Storage, data: DataContainer):
        self.db = db
        self.data = data

    @contextlib.contextmanager
    def lock(self):
        self.db.acquired()
        yield self
        self.db.release()

    def sync(self):
        self.db.sync()


class KeyValueTable(Table):
    def set(self, k, v):
        self.data[k] = v
        self.sync()

    def get(self, k):
        return self.data[k]

    def get_all(self):
        return list(self.data.keys())

    def remove(self, k):
        del(self.data[k])


class DocumentTable(Table):
    def _last_id(self):
        if not self.data:
            return 0

        return max(self.data.keys())

    def insert(self, doc):
        id_ = self._last_id() + 1
        self.data[id_] = doc

    def _search(self, fn):
        for (id_, doc) in self.data.items():
            if fn(doc):
                yield((id_, doc))

    def search(self, fn):
        return [doc for (_, doc) in self._search(fn)]

    def get(self, fn):
        g = self._search(fn)
        ret = next(g)
        try:
            next(g)
        except StopIteration:
            return ret

        raise MultipleResultsError()

    def delete(self, fn):
        res = self._search(fn)
        for (id_, doc) in res:
            del(self.data[id_])

        return [doc for (id_, doc) in res]


class QueryError(Exception):
    pass


class MultipleResultsError(QueryError):
    pass
