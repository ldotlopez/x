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


# torrentapi json_extended format:
#
# {'category': 'TV Episodes',
#  'download': 'magnet:?xt=urn:btih:000000000000000000000000000000000000000000000000&dn=Westworld.S01E10.iNTERNAL.HDTV.x264-TURBO%5Brartv%5D&tr=http%3A%2F%2Ftracker.trackerfix.com%3A80%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2710&tr=udp%3A%2F%2F9.rarbg.to%3A2710&tr=udp%3A%2F%2Fopen.demonii.com%3A1337%2Fannounce',  # nopep8
#  'episode_info': {'airdate': '2016-12-04',
#                   'epnum': '10',
#                   'imdb': 'tt0475784',
#                   'seasonnum': '1',
#                   'themoviedb': '63247',
#                   'title': 'The Bicameral Mind',
#                   'tvdb': '296762',
#                   'tvrage': '37537'},
#  'info_page': 'https://torrentapi.org/redirect_to_info.php?token=xxxxxxxxxx&p=x_x_x_x_x_x_x__xxxxxxxxxx',  # nopep8
#  'leechers': 6,
#  'pubdate': '2016-12-06 10:13:24 +0000',
#  'ranked': 1,
#  'seeders': 85,
#  'size': 583676381,
#  'title': 'Westworld.S01E10.iNTERNAL.HDTV.x264-TURBO[rartv]'}


import arroyo

import asyncio
import datetime
import json
import time
from urllib import parse


import aiohttp


class TorrentAPI(arroyo.Provider):
    # URL structure:
    # https://torrentapi.org/apidocs_v2.txt
    # https://torrentapi.org/pubapi_v2.php?get_token=get_token

    APP_ID = 'arroyo'
    BASE_URI = 'http://torrentapi.org/pubapi_v2.php?app_id=' + APP_ID
    DEFAULT_URI = BASE_URI + '&mode=list'
    SEARCH_URI = BASE_URI + '&mode=search'
    TOKEN_URI = BASE_URI + '&get_token=get_token'

    URI_REGEXPS = [
        r'^http(s)?://([^.]+.)?torrentapi\.org/pubapi_v2.php\?'
    ]

    # APP_ID = 'arroyo'
    # DEFAULT_URI = ('http://torrentapi.org/pubapi_v2.php?'
    #                'app_id=arroyo&mode=list')
    # TOKEN_URL = r'http://torrentapi.org/pubapi_v2.php?get_token=get_token&app_id=arroyo'
    # SEARCH_URL = r'http://torrentapi.org/pubapi_v2.php?mode=search&app_id=arroyo'

    CATEGORY_MAP = {
        'episode': 'tv',
        'movie': 'movies'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.logger = self.app.logger.getChild('torrentapi')
        self.token = None
        self.token_ts = 0
        self.token_last_use = 0

    async def fetch(self, fetcher, uri):
        await self.refresh_token()
        await asyncio.sleep(0.5)
        uri = alter_query_params(
            uri,
            dict(
                format='json_extended',
                limit=100,
                sort='last',
                token=self.token)
        )
        return await super().fetch(fetcher, uri)

    async def refresh_token(self):
        # Refresh token if it's older than 15M
        if time.time() - self.token_ts >= 15*60:
            conn = aiohttp.TCPConnector(verify_ssl=False)
            client = aiohttp.ClientSession(connector=conn)
            resp = await client.get(self.TOKEN_URI)
            buff = await resp.content.read()
            await resp.release()
            await client.close()

            self.token = json.loads(buff.decode('utf-8'))['token']
            self.token_ts = time.time()
            self.token_last_use = None
            return

        # No need to throttle
        if self.token_last_use is None:
            return

        # throttle
        now = time.time()
        since_last_use = self.token_last_use - now
        if since_last_use < 2:
            await asyncio.sleep(2 - since_last_use)

    def parse(self, buff):
        def convert_data(e):
            return {
                'name': e.get('title') or e.get('filename'),
                'uri': e['download'],
                'created': self.parse_created(e.get('pubdate', None)),
                'seeds': e.get('seeders', None),
                'leechers': e.get('leechers', None),
                'size': e.get('size', None),
                'type': self.parse_category(e['category'])
            }

        try:
            data = json.loads(buff)
        except json.decoder.JSONDecodeError as e:
            msg = "Error parsing json response: {e}"
            msg = msg.format(e=str(e))
            # self.logger.error(msg)
            return []

        try:
            psrcs = data['torrent_results']

        except KeyError:
            msg = "Invalid response, missing torrent_results key"
            # self.logger.error(msg)
            return []

        ret = [convert_data(x) for x in psrcs]
        return ret

    def get_query_uri(self, query):
        querystr = query.base_string
        if not querystr:
            return None

        q = {
            'search_string': query.base_string
        }

        try:
            q['category'] = self.CATEGORY_MAP[query['type']]
        except KeyError:
            pass

        return self.SEARCH_URI + "&" + parse.urlencode(q)

    @classmethod
    def parse_category(cls, category):
        if not category:
            return None

        if 'movie' in category.lower():
            return 'movie'

        elif 'episodes' in category.lower():
            return 'episode'

        return None

    @classmethod
    def parse_created(cls, created):
        if not created:
            return None

        dt = datetime.datetime.strptime(created[0:19], '%Y-%m-%d %H:%M:%S')
        ts = int(dt.timestamp())
        return ts


def alter_query_params(uri, newparams, **urlencode_kwargs):
    urlencode_kwargs['doseq'] = urlencode_kwargs.get('doseq', True)

    parsed = parse.urlparse(uri)
    params = parse.parse_qs(parsed.query)
    params.update(newparams)
    params = {k: v for (k, v) in params.items() if v is not None}

    return parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path or '/',
                             parsed.params,
                             parse.urlencode(params, **urlencode_kwargs),
                             parsed.fragment))
