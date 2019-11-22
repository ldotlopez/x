from arroyo.kit import nodb


class Database(nodb.Database):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.states = self.create_table('states', States)
        self.links = self.create_table('links', Links)
        self.external_ids = self.create_table('external_ids', IdMapping)


class IdMapping(nodb.Table):
    DEFAULTS = {
        'native': {},
        'reverse': {}
    }

    def map(self, source, external_id):
        self.data['native'][source] = external_id
        self.data['reverse'][external_id] = source

    def get_native(self, external_id):
        return self.data['reverse'][external_id]

    def get_external(self, native_id):
        return self.data['native'][native_id]


class States(nodb.Table):
    def set(self, src, state):
        self.data[src] = state

    def get(self, src):
        return self.data[src]

    def drop(self, src):
        del(self.data[src])

    def all(self):
        return self.data.items()


class Links(nodb.Table):
    def link(self, src, entity):
        self.data[src.id] = entity

    def unlink(self, src, entity):
        del(self.data[src.id])

    def get_source(self, entity):
        return {v: k for (k, v) in self.items()}[entity]
