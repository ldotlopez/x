import abc
import contextlib
import copy
import functools
import threading
import typing
import pathlib
import json
import os
import unittest
import functools


DataContainer = typing.Dict[str, typing.Any]


def writes(fn):
    @functools.wraps(fn)
    def _wrap(self, *args, **kwargs):
        ret = fn(self, *args, **kwargs)
        self.notify()
        return ret

    return _wrap


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
    DEFAULTS: typing.Any = None

    def __init__(self,
                 data: DataContainer,
                 notify_fn: typing.Callable,
                 lock: typing.Optional[threading.Lock] = None):
        self.data = data
        self._notify = notify_fn

    @classmethod
    def init_data(self, data):
        return data

    def notify(self):
        self._notify(self.data)


class Database:
    def __init__(self,
                 storage: typing.Type[Storage] = Storage,
                 **kwargs: typing.Dict[str, typing.Any]):
        self._storage = storage(**kwargs)
        self._tables: typing.Dict[str, typing.Type[Table]] = {}
        self._lock = threading.Lock()

        self.data: DataContainer = self._storage.read() or {}
        self.in_transaction = threading.Lock()

    def __del__(self) -> None:
        self.close()

    @contextlib.contextmanager
    def transaction(self):
        with self.in_transaction:
            yield self
        self.commit()

    def commit(self) -> None:
        if self.in_transaction.acquire(blocking=False):
            with self._lock:
                self._storage.write(self.data)
            self.in_transaction.release()
        else:
            pass

    def rollback(self) -> None:
        self.data = self._storage.read()
        for (name, table) in self._tables.items():
            self.data[name] = table.init_data(self.data[name])
            self._tables[name].data = self.data[name]

    def notify(self, name, data):   
        if not (self.data[name] is data):
            raise ValueError("Tables should not modify data attribute")

        self.commit()

    def create_table(self, name, cls):
        if name not in self.data:
            table_data = copy.deepcopy(cls.DEFAULTS)
            table_data = cls.init_data(table_data)
            self.data[name] = table_data

        self.commit()

        fn = functools.partial(self.notify, name)

        self._tables[name] = cls(self.data[name], fn, self._lock)
        return self._tables[name]

    def table(self, name):
        return self._tables[name]

    def close(self):
        self._storage.write(self.data)
        self._storage.close()

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
        return copy.deepcopy(self.memory)

    def write(self, data):
        self.memory = copy.deepcopy(data)

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
    DEFAULTS: typing.Dict[typing.Any, typing.Any] = {}

    def set(self, k, v):
        self.data[k] = v
        self.notify()

    def get(self, k):
        return self.data[k]

    def get_all(self):
        return list(self.data.keys())

    @writes
    def remove(self, k):
        del(self.data[k])


class DocumentTable(Table):
    DEFAULTS: typing.Dict[int, typing.Any] = {}

    @classmethod
    def init_data(cls, data):
        return {int(k): v for (k, v) in data.items()}

    def _last_id(self):
        if not self.data:
            return 0

        return max(self.data.keys())

    @writes
    def insert(self, doc):
        id_ = self._last_id() + 1
        self.data[id_] = doc
        self.notify()

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

    @writes
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

    @writes
    def map(self, a, b):
        self.data['map'][a] = b

    @writes
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


        db3 = TestingDatabase(storage=MemoryStorage)
        db3.kv.set('foo', 'bar')
        with db3.transaction():
            db3.kv.remove('foo')
            with self.assertRaises(KeyError):
                db3.kv.get('foo')
            db3.rollback()

        self.assertEqual(db3.kv.get('foo'), 'bar')


if __name__ == '__main__':
    unittest.main()
