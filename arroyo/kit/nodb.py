import abc
import contextlib
import copy
import threading
import typing
import pathlib
import json
import os
import unittest
import functools

# import tinydb
# import tinydb.storages

DataContainer = typing.Dict[str, typing.Any]


class Storage:
    def __init__(self, **kwargs: typing.Dict[str, typing.Any]):
        pass

    @abc.abstractmethod
    def read(self) -> typing.Dict[str, typing.Any]:
        raise NotImplementedError()

    @abc.abstractmethod
    def write(self, data: DataContainer) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self) -> None:
        raise NotImplementedError()


class Table:
    DEFAULTS: typing.Dict[typing.Any, typing.Any] = {}

    def __init__(self,
                 data: DataContainer,
                 notify_fn: typing.Callable,
                 lock: typing.Optional[threading.Lock] = None):
        self.data = data
        self.notify = notify_fn
        self.lock = lock

    @contextlib.contextmanager
    def transaction(self):
        self.lock.acquired()
        yield self
        self.lock.release()

    def sync(self):
        self.notify(self.data)


class Database:
    def __init__(self,
                 storage: typing.Type[Storage] = Storage,
                 **kwargs: typing.Dict[str, typing.Any]):
        self.storage = storage(**kwargs)
        self.lock = threading.Lock()
        self.tables: typing.Dict[str, typing.Type[Table]] = {}
        self.data: DataContainer = self.storage.read() or {}

    def __del__(self) -> None:
        self.close()

    def sync(self) -> None:
        self.storage.write(self.data)

    def notify(self, name, data):
        if not (self.data[name] is data):
            self.data[name] = data
        self.sync()

    def create_table(self, name, cls):
        if name not in self.data:
            self.data[name] = copy.copy(cls.DEFAULTS)
        self.sync()

        fn = functools.partial(self.notify, name)
        self.tables[name] = cls(self.data[name], fn, self.lock)
        return self.tables[name]

    def table(self, name):
        return self.tables[name]

    def close(self):
        self.storage.write(self.data)
        self.storage.close()

    # def __getattr__(self, attr):
    #     tables = getattr(self, 'tables')
    #     try:
    #         return tables[attr]
    #     except KeyError as e:
    #         raise TableNotFoundError(attr) from e


#
# Useful exceptions
#
class TableNotFoundError(Exception):
    pass


class QueryError(Exception):
    pass


class NoResultError(QueryError):
    pass


class MultipleResultsError(QueryError):
    pass


#
# Storage implementations
#

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


#
# Table implementations
#

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {int(k): v for (k, v) in self.data.items()}

    def _last_id(self):
        if not self.data:
            return 0

        return max(self.data.keys())

    def insert(self, doc):
        id_ = self._last_id() + 1
        self.data[id_] = doc
        self.sync()

    def _search(self, fn):
        for (id_, doc) in self.data.items():
            if fn(doc):
                yield((id_, doc))

    def search(self, fn):
        return [doc for (_, doc) in self._search(fn)]

    def get(self, fn):
        g = self._search(fn)
        try:
            id_, doc = next(g)
        except StopIteration:
            raise NoResultError()

        try:
            next(g)
        except StopIteration:
            return doc

        raise MultipleResultsError()

    def delete(self, fn):
        res = self._search(fn)
        for (id_, doc) in res:
            del(self.data[id_])

        return [doc for (id_, doc) in res]


class TestingDatabase(Database):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kv = self.create_table('kv', KeyValueTable)
        self.docs = self.create_table('docs', DocumentTable)
        self.d = self.create_table('d', TestingTable)


class TestingTable(Table):
    DEFAULTS = {
        'map': {},
        'list': []
    }

    def map(self, a, b):
        self.data['map'][a] = b

    def append(self, x):
        self.data['list'].append(x)

    def list(self):
        return self.data['list']

    def items(self):
        return dict(self.data['map'].items())


class NoDBTest(unittest.TestCase):

    def test_all(self):
        try:
            os.unlink('/tmp/nodb-test.json')
        except FileNotFoundError:
            pass

        db = TestingDatabase(storage=JSONStorage, path='/tmp/nodb-test.json')
        db.kv.set('foo', 1)
        db.kv.set('bar', 2)
        db.docs.insert({'name': 'foo', 'id': 1})
        db.docs.insert({'name': 'bar', 'id': 2})
        db.d.map('x', 'y')
        db.d.map('foo', 'bar')
        db.d.append(1)
        db.d.append(2)
        self.assertEqual(db.d.items(), {'x': 'y', 'foo': 'bar'})
        self.assertEqual(db.d.list(), [1, 2])

        db2 = TestingDatabase(storage=JSONStorage, path='/tmp/nodb-test.json')
        self.assertEqual(db2.kv.get('foo'), 1)
        self.assertEqual(db2.kv.get('bar'), 2)
        self.assertEqual(db2.docs.get(lambda x: x.get('name') == 'foo'),
                         {'name': 'foo', 'id': 1})


if __name__ == '__main__':
    unittest.main()
