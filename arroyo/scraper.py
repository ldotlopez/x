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
import logging


import aiohttp


import arroyo
from arroyo import (
    core,
    schema
)
from arroyo.kit import cache


class Context:
    def __init__(self, provider, uri=None, type=None, language=None):
        self.provider = provider
        self.uri = uri or provider.DEFAULT_URI
        self.type = type
        self.language = language

    @property
    def provider_name(self):
        return self.provider.__class__.__name__.lower()

    def __repr__(self):
        data = [
            ("provider", self.provider_name),
            ("uri", self.uri),
            ("type", self.type),
            ("language", self.language),
        ]
        datastr = ", ".join([
            "%s='%s'" % (x[0], x[1])
            for x in data])

        fmt = "<{clsname} {data} at {hexid}"
        return fmt.format(
            clsname=self.__class__.__name__,
            data=datastr,
            hexid=hex(id(self)))


class Engine:
    # Move to settings
    CLIENT_USER_AGENT = ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) '
                         'Gecko/20100101 Firefox/69.0')
    CLIENT_TIMEOUT = 15
    CLIENT_MAX_PARALEL_REQUESTS = 5

    def __init__(self):
        self.logger = logging.getLogger('arroyo.scraper.engine')

    def process(self, *ctxs):
        ctxs_and_buffers = self.fetch(*ctxs)
        results = self.parse(*ctxs_and_buffers)

        return results

    def fetch(self, *ctxs):
        async def _task(acc, ctx, sess, sem):
            try:
                content = core.cache.get(ctx.uri)
            except cache.CacheKeyError:
                content = None

            if content:
                logmsg = "URI '%s' found in cache, %s bytes"
                logmsg = logmsg % (ctx.uri, len(content))
                self.logger.debug(logmsg)
                acc.append((ctx, content))
                return

            async with sem:
                try:
                    logmsg = "Requesting '%s'..."
                    logmsg = logmsg % ctx.uri
                    self.logger.debug(logmsg)
                    content = await ctx.provider.fetch(sess, ctx.uri)
                except asyncio.TimeoutError:
                    logmsg = "Timeout for '%s'"
                    logmsg = logmsg % ctx.uri
                    self.logger.warning(logmsg)
                    content = ''

                logmsg = "URI '%s' fetched, %s bytes"
                logmsg = logmsg % (ctx.uri, len(content))
                self.logger.debug(logmsg)

                if content:
                    logmsg = "URI '%s' saved to cache, %s bytes"
                    logmsg = logmsg % (ctx.uri, len(content))
                    self.logger.debug(logmsg)

                    core.cache.set(ctx.uri, content)

                acc.append((ctx, content))

        async def _wrapper(ctxs):
            sess_opts = {
                'cookie_jar': aiohttp.CookieJar(),
                'headers': {
                    'User-Agent': self.CLIENT_USER_AGENT
                },
                'timeout': aiohttp.ClientTimeout(total=self.CLIENT_TIMEOUT)
            }

            ret = []
            sem = asyncio.Semaphore(self.CLIENT_MAX_PARALEL_REQUESTS)

            async with aiohttp.ClientSession(**sess_opts) as sess:
                tasks = [_task(ret, ctx, sess, sem) for ctx in ctxs]
                await asyncio.gather(*tasks)

            return ret

        return asyncio.run(_wrapper(ctxs))

    def fetch_one(self, ctx):
        ctx, content = self.fetch(ctx)[0]
        return content

    def parse(self, *ctxs_and_buffers):
        ret = []

        for (ctx, buffer) in ctxs_and_buffers:
            ctxitems = []

            for item in ctx.provider.parse(buffer):
                try:
                    ctxitems.append(self._build_source(ctx, item))
                except schema.ValidationError:
                    logmsg = "Got invalid data from provider '%s', skipping."
                    logmsg = logmsg % ctx.provider_name
                    self.logger.warning(logmsg)
                    break

            if not ctxitems:
                logmsg = "Provider '%s' may be broken. Got 0 items from '%s'."
                logmsg = logmsg % (ctx.provider_name, ctx.uri)
                self.logger.warning(logmsg)

            ret.extend(ctxitems)

        return ret

    def parse_one(self, ctx, buffer):
        yield from self.parse((ctx, buffer))

    def _build_source(self, ctx, item):
        item['provider'] = ctx.provider_name

        item_hints = {
            'type': item.pop('type', None),
            'language': item.pop('language', None)
        }
        ctx_hints = {
            'type': ctx.type,
            'language': ctx.language
        }

        item['hints'] = {k: v for (k, v) in (tuple(item_hints.items()) +
                                             tuple(ctx_hints.items()))
                         if v is not None}

        return schema.Source(**item)


class ProviderMissingError(Exception):
    pass


def build_context(provider=None, uri=None, type=None, language=None):
    if not provider and not uri:
        errmsg = "Either provider or uri must be specified"
        raise ValueError(errmsg)

    if provider is None:
        for name in core.loader.list('providers'):
            cls = core.loader.get_class(name)
            if cls.can_handle(uri):
                provider = cls()
                break
        else:
            raise ProviderMissingError(uri)

    elif isinstance(provider, str):
        provider = core.loader.get('providers.%s' % (provider))

    if not isinstance(provider, arroyo.Provider):
        raise TypeError(provider)

    uri = uri or provider.DEFAULT_URI

    return Context(provider, uri, type=type, language=language)


def build_n_contexts(n, *args, **kwargs):
    def _expand(ctx, n):
        g = ctx.provider.paginate(ctx.uri)
        for _ in range(n):
            try:
                uri = next(g)
            except StopIteration:
                break

            yield Context(provider=ctx.provider, uri=uri,
                          type=ctx.type, language=ctx.language)

    ctx0 = build_context(*args, **kwargs)
    return list(_expand(ctx0, n))


def build_contexts_for_query(q):
    def _get_url(provider):
        try:
            url = provider.get_query_uri(q)
        except Exception as e:
            logmsg = "Invalid query for %s: %s"
            logmsg = logmsg % (provider.__class__.__name__, e)
            _logger.info(logmsg)
            return None

        if url is None:
            logmsg = ("Provider '%s' returns null instead for raise an "
                      "exception. Fix it.")
            logmsg = logmsg % provider.__class__.__name__
            _logger.error(logmsg)

        return url

    providers = [core.loader.get(x)
                 for x in core.loader.list('providers')]
    prov_and_uris = [(x, _get_url(x)) for x in providers]
    prov_and_uris = [(p, u) for (p, u) in prov_and_uris if u]

    ctxs = [build_context(provider=p, uri=u)
            for(p, u) in prov_and_uris]

    return ctxs


_logger = logging.getLogger('arroyo.scraper')
