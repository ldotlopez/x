from arroyo.kit import nodb
from arroyo import schema


class Database(nodb.Database):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.states = self.create_table('states', States)
        self.links = self.create_table('links', Links)
        self.external_ids = self.create_table('external_ids', IdMapping)


class IdMapping(nodb.Table):
    SCHEMA = {
        'native': {},
        'reverse': {}
    }

    @nodb.writes
    def map(self, source: schema.Source, external_id: str) -> None:
        self.data['native'][source] = external_id
        self.data['reverse'][external_id] = source

    def get_source(self, external_id: str) -> schema.Source:
        return self.data['reverse'][external_id]

    def get_external(self, source: schema.Source) -> str:
        return self.data['native'][source]


class States(nodb.Table):
    SCHEMA = {}

    @nodb.writes
    def set(self, src, state):
        self.data[src] = state

    def get(self, src):
        return self.data[src]

    @nodb.writes
    def drop(self, src):
        del(self.data[src])

    def all(self):
        return self.data.items()


class Links(nodb.Table):
    SCHEMA = {}

    @nodb.writes
    def link(self, src, entity):
        self.data[src.id] = entity

    @nodb.writes
    def unlink(self, src, entity):
        del(self.data[src.id])

    def get_source(self, entity):
        return {v: k for (k, v) in self.items()}[entity]
