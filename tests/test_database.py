import unittest

import sqlalchemy as sa
from arroyo import schema as sch
from arroyo.services import database as db
from sqlalchemy import orm


class RawDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        # self.engine = sa.create_engine(
        #     "sqlite:////home/luis/src/x/tests/a.db", echo=True
        # )
        db.Base.metadata.create_all(self.engine)
        self.sess = orm.sessionmaker()(bind=self.engine)

    def tearDown(self):
        del self.sess
        del self.engine

    def _test_uniqueness(self, Model, **kwargs):
        self.sess.add(Model(**kwargs))
        self.sess.commit()

        with self.assertRaises(sa.exc.IntegrityError):
            self.sess.add(Model(**kwargs))
            self.sess.commit()

    # def test_source_data_field(self):
    #     s1 = db.Source(id="x", data={"name": "foo"})
    #     s2 = db.Source(id="y", data={"name": "bar"})
    #     self.sess.add_all([s1, s2])
    #     self.sess.commit()

    #     self.assertEqual(
    #         self.sess.query(db.Source).filter(
    #             db.Source.data["name"] == "foo"
    #         ).one(),
    #         s1
    #     )

    def test_source_uniqueness(self):
        self._test_uniqueness(db.Source, id="x")

    def test_episode_uniqueness(self):
        self._test_uniqueness(db.Episode, series="x", season=1, number=1)

    def test_movie_uniqueness(self):
        self._test_uniqueness(db.Movie, title="x")

    def test_source_download_relationship(self):
        # Check one-to-one relationship
        src = db.Source(id="x")
        dl = db.Download(source=src, foreign_id="mock:1", state="none")
        self.sess.add_all([src, dl])
        self.sess.commit()
        self.assertEqual(src.download, dl)
        self.assertEqual(dl.source, src)

        # Delete download DOESN'T delete source
        self.sess.delete(dl)
        self.sess.commit()
        self.assertEqual(
            self.sess.query(db.Source).filter(db.Source.id == "x").one(), src
        )

        # Delete source DOES delete download
        src.dl = db.Download(source=src, foreign_id="mock:1", state="none")
        self.sess.commit()
        self.sess.delete(src)
        self.assertEqual(
            self.sess.query(db.Download)
            .filter(db.Download.foreign_id == "mock:1")
            .count(),
            0,
        )

    def test_source_episode_relationship(self):
        e = db.Episode(series="foo", season=1, number=2)
        s1 = db.Source(id="x", entity=e)
        s2 = db.Source(id="y", entity=e)
        self.sess.add_all([e, s1, s2])
        self.sess.commit()

        self.assertEqual(set(e.sources), set([s1, s2]))
        self.assertEqual(s1.entity, e)
        self.assertEqual(s1.episode, e)
        self.assertTrue(s1.movie is None)

        self.sess.delete(s1)
        self.sess.delete(s2)
        self.assertEqual(self.sess.query(db.Episode).one(), e)

    def test_source_movie_relationship(self):
        e = db.Movie(title="foo")
        s1 = db.Source(id="x", entity=e)
        s2 = db.Source(id="y", entity=e)
        self.sess.add_all([e, s1, s2])
        self.sess.commit()

        self.assertEqual(set(e.sources), set([s1, s2]))
        self.assertEqual(s1.entity, e)
        self.assertEqual(s1.movie, e)
        self.assertTrue(s1.episode is None)

        self.sess.delete(s1)
        self.sess.delete(s2)
        self.assertEqual(self.sess.query(db.Movie).one(), e)


class DatabaseAPITest(unittest.TestCase):
    def setUp(self):
        self.db = db.Database("sqlite:///:memory:")

    def tearDown(self):
        del self.db

    # def test_query_update_entity(self):
    #     e = sch.Episode(series="x", season=1, number=1)
    #     self.assertEqual(self.db.query_entity(e), None)

    #     self.db.update_entity(e, state="skipped")
    #     self.assertEqual(self.db.query_entity(e), {"state": "skipped"})
    def test_get_set_entity(self):
        e = sch.Episode(series='x', season=1, number=1)
        self.assertEqual(self.db.get_entity_state(e), None)

        self.db.set_entity_state(e, 'skipped')
        self.assertEqual(self.db.get_entity_state(e), 'skipped')


if __name__ == "__main__":
    unittest.main()
