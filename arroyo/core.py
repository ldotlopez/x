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

import asyncio


import aiohttp


from kit import ClassLoader


_plugins = {
    'providers.eztv': 'arroyo.plugins.providers.eztv.EzTV',
    'providers.epublibre': 'arroyo.plugins.providers.epublibre.EPubLibre',
    'providers.torrentapi': 'arroyo.plugins.providers.torrentapi.TorrentAPI',
    'providers.thepiratebay': 'arroyo.plugins.providers.thepiratebay.ThePirateBay'
}


class Loader(ClassLoader):
    def __init__(self):
        super().__init__(_plugins)


class AsyncFetcher:
    def __init__(self, logger=None, cache=None, max_requests=1,
                 **session_options):
        self._logger = logger
        self._cache = cache
        self._semaphore = asyncio.Semaphore(max_requests)
        self._session_options = session_options
        self._session_options['cookie_jar'] = aiohttp.CookieJar()
        self._session_options['timeout'] = aiohttp.ClientTimeout(total=10)
        self._session_options['headers'] = {
            'User-Agent': ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) '
                           'Gecko/20100101 Firefox/69.0')
        }

    async def fetch(self, url, **request_options):
        resp, content = await self.fetch_full(url, **request_options)
        return content

    async def fetch_full(self, uri, skip_cache=False, **request_options):
        # FIXME: Try getting from cache
        # try:
        #     buff = self._cache.get(url)
        #     return None, buff
        # except cache.CacheKeyError:
        #     pass

        # Do actual request
        async with self._semaphore:
            async with aiohttp.ClientSession(**self._session_options) as sess:
                async with sess.get(uri, **request_options) as resp:
                    content = await resp.text()

        # FIXME: Save to cache?
        # self._cache.set(uri, content)

        return resp, content
