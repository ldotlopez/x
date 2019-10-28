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


import typing


import pydantic
import typing_extensions


# Shorcut
ValidationError = pydantic.ValidationError


class Source(pydantic.BaseModel):
    name: str
    provider: str
    uri: str

    created: typing.Optional[int]
    seeds: typing.Optional[int]
    leechers: typing.Optional[int]
    size: typing.Optional[int]
    meta: typing.Optional[typing.Dict[str, typing.Any]]


class Episode(pydantic.BaseModel):
    type: typing_extensions.Literal['episode']
    series: str
    year: typing.Optional[int]
    season: int
    number: int
    country: typing.Optional[str]


class Movie(pydantic.BaseModel):
    type: typing_extensions.Literal['movie']
    title: str
    year: typing.Optional[int]


entity_type_map = {
    'episode': Episode,
    'movie': Movie
}


entity_type_reverse_map = {v: k for (k, v) in entity_type_map.items()}


def Entity(**kwargs):
    cls = entity_type_map.get('type', None)
    if cls is None:
        raise ValueError(kwargs)

    return cls(**kwargs)


def get_entity_name(cls: type):
    return entity_type_reverse_map[cls]


def get_entity_class(name: str):
    return entity_type_map[name]


def validate_entity_name(name: str):
    try:
        get_entity_class(name)
    except KeyError as e:
        raise ValueError(name) from e


def validate_entity_class(cls: type):
    try:
        get_entity_name(cls)
    except KeyError as e:
        raise ValueError(cls)
