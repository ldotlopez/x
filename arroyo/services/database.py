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

import functools
import re
import sys

import sqlalchemy as sa
from arroyo import schema
from sqlalchemy import orm
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext import declarative, hybrid
from sqlalchemy.orm import exc

Base = declarative.declarative_base()
Base.metadata.naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


@functools.lru_cache(maxsize=8)
def _ensure_model_class(x):

    try:
        if issubclass(x, Base):
            return x
    except TypeError:
        pass

    if "." in x:
        mod = sys.modules[x]
        x = x.split(".")[-1]

    else:
        mod = sys.modules[__name__]

    cls = getattr(mod, x)
    issubclass(cls, Base)

    return cls


class EntityPropertyMixin:
    ENTITY_MAP = {}

    @hybrid.hybrid_property
    def entity(self):
        entity_attrs = self.ENTITY_MAP.values()

        for attr in entity_attrs:
            value = getattr(self, attr, None)
            if value:
                return value

        return None

    @entity.setter
    def entity(self, entity):
        entity_map_by_cls = {
            _ensure_model_class(k): v for (k, v) in self.ENTITY_MAP.items()
        }

        # Check for unknown entity type
        if entity is not None and entity.__class__ not in entity_map_by_cls:
            raise TypeError(entity)

        # Set all entity-attributes correctly
        for (model, attr) in entity_map_by_cls.items():
            value = entity if isinstance(entity, model) else None
            setattr(self, attr, value)


class Source(EntityPropertyMixin, Base):
    ENTITY_MAP = {  # EntityPropertyMixin
        "Episode": "episode",
        "Movie": "movie",
    }

    __tablename__ = "source"
    id = sa.Column(sa.String, primary_key=True)
    data = sa.Column(JSON, nullable=True)

    episode_id = sa.Column(sa.Integer, sa.ForeignKey("episode.id"))
    movie_id = sa.Column(sa.Integer, sa.ForeignKey("movie.id"))

    # No cascade here, keep entities in database.
    # This will allow us to filter entities in searches without needing to have
    # a matching source
    episode = orm.relationship("Episode", backref="sources")
    movie = orm.relationship("Movie", backref="sources")


class Entity(Base):
    __tablename__ = "entity"
    id = sa.Column(sa.Integer, primary_key=True)
    type = sa.Column(sa.String)
    state = sa.Column(sa.String, nullable=False, default="")

    # No need to declare a polymorphic_identity, raw entities doesn't
    # exists
    __mapper_args__ = {
        "polymorphic_on": "type",
    }


class Episode(Entity):
    __tablename__ = "episode"
    __table_args__ = (
        # Warning: UniqueConstraint CAN'T handle nullable columns on sqlite.
        sa.UniqueConstraint("series", "year", "season", "number"),
    )
    __mapper_args__ = {"polymorphic_identity": "episode"}

    id = sa.Column(sa.Integer, sa.ForeignKey("entity.id"), primary_key=True)
    series = sa.Column(sa.String, nullable=False, index=True)
    year = sa.Column(sa.Integer, nullable=False, default="")
    season = sa.Column(sa.Integer, nullable=False)
    number = sa.Column(sa.Integer, nullable=False)

    @orm.validates("series")
    def validate(self, key, value):
        if key == "series":
            return re.sub(r"\s+", " ", value.lower())
        else:
            raise ValueError(key)


class Movie(Entity):
    __tablename__ = "movie"
    __table_args__ = (
        # Warning: UniqueConstraint CAN'T handle nullable columns on sqlite.
        sa.UniqueConstraint("title", "year"),
    )
    __mapper_args__ = {"polymorphic_identity": "movie"}

    id = sa.Column(sa.Integer, sa.ForeignKey("entity.id"), primary_key=True)
    title = sa.Column(sa.String, nullable=False, index=True)
    year = sa.Column(sa.Integer, nullable=False, default="")

    @orm.validates("title")
    def validate(self, key, value):
        if key == "title":
            return re.sub(r"\s+", " ", value.lower())
        else:
            raise ValueError(key)


class Download(Base):
    __tablename__ = "download"
    id = sa.Column(sa.Integer, primary_key=True)
    foreign_id = sa.Column(sa.String, nullable=False)
    source_id = sa.Column(
        sa.String, sa.ForeignKey("source.id"), nullable=False
    )
    state = sa.Column(sa.String, nullable=False, default="none")

    source = orm.relationship(
        "Source",
        uselist=False,
        backref=orm.backref("download", uselist=False, cascade="all, delete"),
    )


class Database:
    MAPPING = {
        schema.Episode: (Episode, ["series", "year", "season", "number"]),
        schema.Movie: (Movie, ["title", "year"]),
    }

    def __init__(self, uri):
        self.engine = sa.create_engine(uri)
        Base.metadata.create_all(self.engine)
        self.sess = orm.sessionmaker()(bind=self.engine)

    def _model_for_entity(self, entity):
        return self.MAPPING[entity.__class__][0]

    def _qdict_for_entity(self, entity):
        (model, fields) = self.MAPPING[entity.__class__]
        qdict = {f: getattr(entity, f) for f in fields}

        # Empty year is represented as '' in database because it is used as
        # part of a unique constraint and sqlite doesn't support empty columns
        # as part of unique constraints.
        # Here we transform year key to handle this tweak
        if 'year' in qdict and qdict['year'] is None:
            qdict['year'] = ''

        return qdict

    def get_source_state(self, src):
        return (
            self.sess.query(schema.Source)
            .filter(schema.Source.id == src.id)
            .one()
            .state
        )

    def update_entity(self, entity, state=None):
        # py3.9: https://www.python.org/dev/peps/pep-0584/
        data = self._qdict_for_entity(entity)
        data.update(dict(state=state))

        Model = self._model_for_entity(entity)
        m = Model(**data)

        self.sess.merge(m)
        self.sess.commit()

    def query_entity(self, entity):
        qdict = self._qdict_for_entity(entity)

        try:
            obj = self.sess.query(Episode).filter_by(**qdict).one()
        except exc.NoResultFound:
            return None

        return dict(state=obj.state)

    def set_entity_state(self, entity, state):
        data = self._qdict_for_entity(entity)
        data['state'] = state

        Model = self._model_for_entity(entity)
        m = Model(**data)

        self.sess.merge(m)
        self.sess.commit()

    def get_entity_state(self, entity):
        qdict = self._qdict_for_entity(entity)

        try:
            return self.sess.query(Episode).filter_by(**qdict).one().state
        except exc.NoResultFound:
            return None

    # def update_entity(self, entity, state=_UNDEF):
    #     # py3.9: https://www.python.org/dev/peps/pep-0584/
    #     data = self._qdict_for_entity(entity)
    #     data.update(dict(state=state))

    #     Model = self._model_for_entity(entity)
    #     m = Model(**data)

    #     self.sess.merge(m)
    #     self.sess.commit()

    # def query_entity(self, entity):
    #     qdict = self._qdict_for_entity(entity)

    #     try:
    #         obj = self.sess.query(Episode).filter_by(**qdict).one()
    #     except exc.NoResultFound:
    #         return None

    #     return dict(state=obj.state)