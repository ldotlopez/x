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


import base64
import binascii
import hashlib
import re
import typing
from urllib import parse

import pydantic


# Shorcut
ValidationError = pydantic.ValidationError


#
# Entity definitions
#


class Episode(pydantic.BaseModel):
    type = "episode"
    series: str
    year: typing.Optional[int]
    season: int
    # FIXME: guessit returns episodeList attribute if more than one episode is
    # detected, take care of this
    number: int
    country: typing.Optional[str]

    @property
    def id(self):
        dig = hashlib.sha1()
        s = "\0".join(
            [
                self.type,
                self.series,
                str(self.year or ""),
                str(self.season),
                str(self.number),
                self.country or "",
            ]
        )
        dig.update(s.encode("utf-8"))
        return dig.hexdigest()

    def __eq__(self, x):
        return (
            isinstance(x, self.__class__)
            and self.series.lower() == x.series.lower()
            and self.year == x.year
            and self.season == x.season
            and self.number == x.number
            and (self.country or "").lower() == (x.country or "").lower()
        )

    def __lt__(self, x):
        if not isinstance(x, self.__class__):
            return super().__lt__(x)

        for attr in ["series", "year", "season", "number"]:
            this = getattr(self, attr)
            other = getattr(x, attr)
            if this != other:
                return this < other

        return False

    def __hash__(self):
        return hash(
            (
                self.series.lower(),
                self.year,
                self.season,
                self.number,
                (self.country or "").lower(),
            )
        )

    def __repr__(self):
        return f"<Episode id={self.id}>"


class Movie(pydantic.BaseModel):
    type = "movie"
    title: str
    year: typing.Optional[int]

    @property
    def id(self):
        dig = hashlib.sha1()
        s = "\0".join([self.type, self.title, str(self.year or "")])
        dig.update(s.encode("utf-8"))
        return dig.hexdigest()

    def __eq__(self, x):
        return (
            isinstance(x, self.__class__)
            and self.title.lower() == x.title.lower()
            and self.year == x.year
        )

    def __lt__(self, x):
        if not isinstance(x, self.__class__):
            return super().__lt__(x)

        for attr in ["title", "year"]:
            this = getattr(self, attr)
            other = getattr(x, attr)
            if this != other:
                return this < other

        return False

    def __hash__(self):
        return hash((self.title.lower(), self.year))

    def __repr__(self):
        return f"<Movie id={self.id}>"


EntityType = typing.Union[Episode, Movie]
MetadataType = typing.Dict[str, typing.Any]


class Source(pydantic.BaseModel):
    id: str
    name: str
    provider: str
    uri: str

    created: typing.Optional[int]
    seeds: typing.Optional[int]
    leechers: typing.Optional[int]
    size: typing.Optional[int]
    hints: typing.Dict[str, typing.Any] = {}

    entity: typing.Optional[EntityType] = None
    metadata: MetadataType = {}

    def __init__(self, *args, **kwargs):
        parsed = parse.urlparse(kwargs["uri"])
        qs = dict(parse.parse_qsl(parsed.query))
        kwargs["id"] = qs["xt"]
        super().__init__(*args, **kwargs)

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        return f"<Source id={self.id}>"

    def __str__(self):
        return self.name

    @pydantic.validator("id")
    def id_validator(cls, value):
        # Check sha1 bittorrent urn
        if re.match(r"^urn:btih:[0-9a-f]{40}", value, re.IGNORECASE):
            return value.lower()

        # check base32 bittorrent urn
        elif re.match("^urn:btih:[A-Z2-7]{32}$", value, re.IGNORECASE):
            p1, p2, hash = value.split(":", 2)
            hash = hash.upper()
            hash = base64.b32decode(hash)
            hash = binascii.hexlify(hash)
            hash = hash.decode("ascii")
            hash = hash.lower()

            return f"{p1}:{p2}:{hash}"

        else:
            raise ValueError("Invalid id")


entity_type_map = {"episode": Episode, "movie": Movie}


entity_type_reverse_map = {v: k for (k, v) in entity_type_map.items()}


def Entity(**kwargs):
    cls = entity_type_map.get(kwargs.get("type"), None)
    if cls is None:
        raise ValueError(kwargs)

    return cls(**kwargs)


def get_entity_name(cls: typing.Type):
    return entity_type_reverse_map[cls]


def get_entity_class(name: str):
    return entity_type_map[name]


def validate_entity_name(name: str):
    try:
        get_entity_class(name)
    except KeyError as e:
        raise ValueError(name) from e


def validate_entity_class(cls: typing.Type):
    try:
        get_entity_name(cls)
    except KeyError as e:
        raise ValueError(cls) from e
