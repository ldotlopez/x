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


import babelfish
import guessit


_SOURCE_TAGS_PREFIX = 'core.'


class Tags:
    AUDIO_CHANNELS = _SOURCE_TAGS_PREFIX + 'audio.channels'
    AUDIO_CODEC = _SOURCE_TAGS_PREFIX + 'audio.codec'
    AUDIO_PROFILE = _SOURCE_TAGS_PREFIX + 'audio.profile'
    BROADCAST_DATE = _SOURCE_TAGS_PREFIX + 'broadcast.date'
    EPISODE_COUNT = _SOURCE_TAGS_PREFIX + 'episode.count'
    EPISODE_DETAILS = _SOURCE_TAGS_PREFIX + 'episode.details'
    EPISODE_TITLE = _SOURCE_TAGS_PREFIX + 'episode.title'
    GUESSIT_OTHER = _SOURCE_TAGS_PREFIX + 'guessit.other'
    GUESSIT_UUID = _SOURCE_TAGS_PREFIX + 'guessit.uuid'
    MEDIA_CONTAINER = _SOURCE_TAGS_PREFIX + 'media.container'
    MEDIA_COUNTRY = _SOURCE_TAGS_PREFIX + 'media.country'
    MEDIA_LANGUAGE = _SOURCE_TAGS_PREFIX + 'media.language'
    MIMETYPE = _SOURCE_TAGS_PREFIX + 'mimetype'
    MOVIE_EDITION = _SOURCE_TAGS_PREFIX + 'edition'
    RELEASE_DISTRIBUTORS = _SOURCE_TAGS_PREFIX + 'release.distributors'
    RELEASE_GROUP = _SOURCE_TAGS_PREFIX + 'release.group'
    RELEASE_PROPER = _SOURCE_TAGS_PREFIX + 'release.proper'
    RELEASE_SOURCE = _SOURCE_TAGS_PREFIX + 'release.source'
    STREAMING_SERVICE = _SOURCE_TAGS_PREFIX + 'streaming.service'
    SUBTITLES_LANGUAGE = _SOURCE_TAGS_PREFIX + 'subtitles.language'
    VIDEO_CODEC = _SOURCE_TAGS_PREFIX + 'video.codec'
    VIDEO_FORMAT = _SOURCE_TAGS_PREFIX + 'video.format'
    VIDEO_SCREEN_SIZE = _SOURCE_TAGS_PREFIX + 'video.screen-size'

    # @classmethod
    # def values(cls):
    #     for x in dir(cls):
    #         if x[0] == '_':
    #             continue

    #         value = getattr(cls, x)
    #         if (not isinstance(value, str) or
    #                 not value.startswith(_SOURCE_TAGS_PREFIX)):
    #             continue

    #         yield value


ENTITIES_DEFS = {
    "movie": {
        'fields': ['title', 'year'],
        'requires': ['title']
    },
    "episode": {
        'fields': ['title', 'year', 'country', 'season', 'episode'],
        'requires': ['title', 'season', 'episode']
    }
}


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
            return pool.map(normalize_one, items)
    else:
        return list(map(normalize_one, items))


def normalize_one(item, type_hint=None):
    type_hint = type_hint or item.get('type')

    try:
        entity, metadata, other = parse(item['name'], type_hint)
    except NormalizationError:
        return None

    return {
        'source': item,
        'entity': entity,
        'metadata': metadata,
        'other': other
    }


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

    entity = extract_entity_data(parsed, type_hint or parsed.get('type'))
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


def extract_entity_data(info, type=None):
    if type is None:
        type = info.get('type')

    if type not in ENTITIES_DEFS:
        raise UnknowEntityTypeError((info, type))

    for f in ENTITIES_DEFS[type]['requires']:
        if info.get(f, None) is None:
            raise MissingEntityDataError(info)

    entity_data = {'type': info.get('type')}
    entity_data.update({
        f: info.pop(f, None)
        for f in ENTITIES_DEFS[type]['fields']
    })
    entity_data = {k: v for (k, v) in entity_data.items() if v is not None}
    return entity_data


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


class MissingEntityDataError(NormalizationError):
    pass


class ParseError(NormalizationError):
    pass
