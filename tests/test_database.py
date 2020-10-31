import unittest

import sqlalchemy as sa
from arroyo.services.database import Base, Download, Episode, Movie, Source
from sqlalchemy import orm


class RawDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.engine = sa.create_engine("sqlite:///:memory:")
        # self.engine = sa.create_engine(
        #     "sqlite:////home/luis/src/x/tests/a.db", echo=True
        # )
        Base.metadata.create_all(self.engine)
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
    #     s1 = Source(id="x", data={"name": "foo"})
    #     s2 = Source(id="y", data={"name": "bar"})
    #     self.sess.add_all([s1, s2])
    #     self.sess.commit()

    #     self.assertEqual(
    #         self.sess.query(Source).filter(
    #             Source.data["name"] == "foo"
    #         ).one(),
    #         s1
    #     )

    def test_source_uniqueness(self):
        self._test_uniqueness(Source, id="x")

    def test_episode_uniqueness(self):
        self._test_uniqueness(Episode, series="x", season=1, number=1)

    def test_movie_uniqueness(self):
        self._test_uniqueness(Movie, title="x")

    def test_source_download_relationship(self):
        # Check one-to-one relationship
        src = Source(id="x")
        dl = Download(source=src, foreign_id="mock:1", state="none")
        self.sess.add_all([src, dl])
        self.sess.commit()
        self.assertEqual(src.download, dl)
        self.assertEqual(dl.source, src)

        # Delete download DOESN'T delete source
        self.sess.delete(dl)
        self.sess.commit()
        self.assertEqual(
            self.sess.query(Source).filter(Source.id == "x").one(), src
        )

        # Delete source DOES delete download
        src.dl = Download(source=src, foreign_id="mock:1", state="none")
        self.sess.commit()
        self.sess.delete(src)
        self.assertEqual(
            self.sess.query(Download)
            .filter(Download.foreign_id == "mock:1")
            .count(),
            0,
        )

    def test_source_episode_relationship(self):
        e = Episode(series="foo", season=1, number=2)
        s1 = Source(id="x", entity=e)
        s2 = Source(id="y", entity=e)
        self.sess.add_all([e, s1, s2])
        self.sess.commit()

        self.assertEqual(set(e.sources), set([s1, s2]))
        self.assertEqual(s1.entity, e)
        self.assertEqual(s1.episode, e)
        self.assertTrue(s1.movie is None)

        self.sess.delete(s1)
        self.sess.delete(s2)
        self.assertEqual(self.sess.query(Episode).one(), e)

    def test_source_movie_relationship(self):
        e = Movie(title="foo")
        s1 = Source(id="x", entity=e)
        s2 = Source(id="y", entity=e)
        self.sess.add_all([e, s1, s2])
        self.sess.commit()

        self.assertEqual(set(e.sources), set([s1, s2]))
        self.assertEqual(s1.entity, e)
        self.assertEqual(s1.movie, e)
        self.assertTrue(s1.episode is None)

        self.sess.delete(s1)
        self.sess.delete(s2)
        self.assertEqual(self.sess.query(Movie).one(), e)


if __name__ == "__main__":
    unittest.main()
