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


import multiprocessing
import sys


import babelfish
import guessit
import pydantic


import arroyo
from arroyo import schema


class Tags:
    AUDIO_CHANNELS = 'core.audio.channels'
    AUDIO_CODEC = 'core.audio.codec'
    AUDIO_PROFILE = 'core.audio.profile'
    BROADCAST_DATE = 'core.broadcast.date'
    EPISODE_COUNT = 'core.episode.count'
    EPISODE_DETAILS = 'core.episode.details'
    EPISODE_TITLE = 'core.episode.title'
    GUESSIT_OTHER = 'core.guessit.other'
    GUESSIT_UUID = 'core.guessit.uuid'
    MEDIA_CONTAINER = 'core.media.container'
    MEDIA_COUNTRY = 'core.media.country'
    MEDIA_LANGUAGE = 'core.media.language'
    MIMETYPE = 'core.mimetype'
    MOVIE_EDITION = 'core.edition'
    RELEASE_DISTRIBUTORS = 'core.release.distributors'
    RELEASE_GROUP = 'core.release.group'
    RELEASE_PROPER = 'core.release.proper'
    RELEASE_SOURCE = 'core.release.source'
    STREAMING_SERVICE = 'core.streaming.service'
    SUBTITLES_LANGUAGE = 'core.subtitles.language'
    VIDEO_CODEC = 'core.video.codec'
    VIDEO_FORMAT = 'core.video.format'
    VIDEO_SCREEN_SIZE = 'core.video.screen-size'


METADATA_RULES = [
    ('audio_channels', Tags.AUDIO_CHANNELS),
    ('audio_codec', Tags.AUDIO_CODEC),
    ('audio_profile', Tags.AUDIO_PROFILE),
    ('container', Tags.MEDIA_CONTAINER),
    ('country', Tags.MEDIA_COUNTRY),
    ('date', Tags.BROADCAST_DATE),
    ('edition', Tags.MOVIE_EDITION),
    ('episode_count', Tags.EPISODE_COUNT),
    ('episode_details', Tags.EPISODE_DETAILS),
    ('episode_title', Tags.EPISODE_TITLE),
    ('format', Tags.VIDEO_FORMAT),
    ('language', Tags.MEDIA_LANGUAGE),
    ('mimetype', Tags.MIMETYPE),
    ('proper_count', Tags.RELEASE_PROPER, lambda x: int(x) > 0),
    ('other', Tags.GUESSIT_OTHER),
    ('release_distributors', Tags.RELEASE_DISTRIBUTORS),
    ('release_group', Tags.RELEASE_GROUP),
    ('screen_size', Tags.VIDEO_SCREEN_SIZE),
    ('source', Tags.RELEASE_SOURCE),
    ('streaming_service', Tags.STREAMING_SERVICE),
    ('subtitle_language', Tags.SUBTITLES_LANGUAGE),
    ('uuid', Tags.GUESSIT_UUID),
    ('video_codec', Tags.VIDEO_CODEC),
]

KNOWN_DISTRIBUTORS = [
    'glodls',
    'ethd',
    'ettv',
    'eztv',
    'rartv'
]  # keep lower case!!


def normalize(*items, mp=True):
    if mp:
        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            ret = pool.map(_safe_normalize_one, items)
    else:
        ret = list(map(_safe_normalize_one, items))

    ret = list(filter(lambda x: x is not None, ret))
    return ret


def _safe_normalize_one(item, type_hint=None):
    try:
        return normalize_one(item, type_hint)
    except NormalizationError:
        logmsg = "Error analyzing '%s'"
        logmsg = logmsg % item.name
        _logger.warning(logmsg)


def normalize_one(item, type_hint=None):
    type_hint = type_hint or item.metadata.get('type')

    entity, metadata, other = parse(item.name, type_hint)
    return schema.Item(**{
        'source': item,
        'entity': entity,
        'metadata': metadata,
        'other': other
    })


def parse(name, type_hint=None):
    # We preprocess name to extract distributors
    # (distributors != release-teams)
    release_distributors = set()
    for dist in KNOWN_DISTRIBUTORS:
        tag = '[' + dist + ']'
        idx = name.lower().find(tag)
        if idx == -1:
            continue

        name = (name[:idx] + name[idx+len(tag):]).strip()
        release_distributors.add(dist)

    try:
        parsed = guessit.guessit(name, options={type: type_hint})
    except guessit.api.GuessitException as e:
        raise ParseError() from e

    # Fixes: Insert distributors again
    if release_distributors:
        parsed['release_distributors'] = list(release_distributors)

    # Errors: 'part' is not supported
    if 'part' in parsed:
        msg = ("Unsupported 'part'")
        msg = msg.format(name=name)
        raise NormalizationError(msg)

    try:
        entity = extract_entity(parsed, type_hint or parsed.get('type'))
    except pydantic.ValidationError as e:
        entity = None
        logmsg = "Unable to parse '%s'"
        logmsg = logmsg % name
        _logger.warning(logmsg)

    metadata = extract_items(parsed, METADATA_RULES)

    return (entity, metadata, parsed)

    # Fixes: Reformat date as episode number for episodes if needed
    # if info['type'] == 'episode' and 'date' in info:
    #     if not info.get('season'):
    #         info['season'] = 0

    #     # Reformat episode number
    #     if not info.get('episode'):
    #         info['episode'] = '{year}{month:0>2}{day:0>2}'.format(
    #             year=info['date'].year,
    #             month=info['date'].month,
    #             day=info['date'].day)

    # # Fixes: Rename episode fields
    # if info['type'] == 'episode':
    #     if 'episode' in info:
    #         info['number'] = info.pop('episode')
    #     if 'title' in info:
    #         info['series'] = info.pop('title')

    # # Fixes: Normalize language
    # if isinstance(info.get('language'), list):
    #     # msg = 'Drop multiple instances of {key} in {name}'
    #     # msg = msg.format(name=name, key=k)
    #     # self.logger.warning(msg)
    #     info['language'] = info['language'][0]

    # # Fixes: Normalize language value
    # if 'language' in info:
    #     if info['language'] == 'und':
    #         del info['language']

    #     else:
    #         try:
    #             info['language'] = '{}-{}'.format(
    #                 info['language'].alpha3,
    #                 info['language'].alpha2)
    #         except babelfish.exceptions.LanguageConvertError as e:
    #             # FIXME: Log this error
    #             # msg = "Language error in '{name}': {msg}"
    #             # msg = msg.format(name=name, msg=e)
    #             # self.logger.warning(msg)
    #             del info['language']


def extract_entity(info, type=None):
    if type is None:
        type = info.get('type')

    entity_cls = schema.get_entity_class(type)
    if entity_cls is None:
        raise UnknowEntityTypeError((info, type))

    if entity_cls is schema.Episode:
        info['series'] = info.pop('title', None)
        info['number'] = info.pop('episode', None)
        fields = ('series', 'year', 'season', 'number')

    elif entity_cls is schema.Movie:
        fields = ('title', 'year')

    else:
        raise SystemError('This is a bug')

    fields = fields + ('type',)
    entity_data = {k: info.pop(k, None) for k in fields}

    return entity_cls(**entity_data)


def extract_items(orig, rules):
    ret = {}

    for rule in rules:
        if len(rule) == 3:
            src, dst, fn = rule
        else:
            src, dst = rule
            fn = None

        if src not in orig:
            continue

        value = orig.pop(src)
        if fn:
            value = fn(value)

        ret[dst] = value

    return ret


class NormalizationError(Exception):
    pass


class UnknowEntityTypeError(NormalizationError):
    pass


class ParseError(NormalizationError):
    pass


_logger = arroyo.getLogger('normalize')
