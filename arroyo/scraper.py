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


from arroyo import (
    core,
    extensions
)


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
    def process(self, *ctxs):
        ctxs_and_buffers = self.fetch(*ctxs)
        results = self.parse(*ctxs_and_buffers)

        return results

    # async def _process(url):
    #     try:
    #         url_provider = provider or self.get_provider_for(url)
    #     except ProviderMissingError:
    #         return

    #     buffer = await provider.fetch(url)
    #     results.append(provider.parse(buffer))

    # uris = [self.get_uris(o) for origin in origins]
    # print(repr(uris))

    # tasks = [_process(uri) for uri in uris]
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(asyncio.gather(*tasks))

    def fetch(self, *ctxs):
        ua = core.AsyncFetcher()
        ret = []

        async def _fetch(ctx):
            nonlocal ret
            buffer = await ctx.provider.fetch(ua, ctx.uri)
            ret.append((ctx, buffer))

        tasks = [_fetch(ctx) for ctx in ctxs]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

        return ret

    def fetch_one(self, ctx):
        ua = core.AsyncFetcher()
        ret = asyncio.run(ctx.provider.fetch(ua, ctx.uri))
        return ret

    def parse(self, *ctxs_and_buffers):
        ret = []

        for (ctx, buffer) in ctxs_and_buffers:
            try:
                ret.extend([self._fix_item(ctx, x)
                            for x in ctx.provider.parse(buffer)])
            except Exception as e:
                print(repr(e))

        return ret

    def parse_one(self, ctx, buffer):
        yield from self.parse((ctx, buffer))

    def _fix_item(self, ctx, item):
        item['provider'] = ctx.provider_name

        if ctx.type:
            item['type'] = ctx.type
        if ctx.language:
            item['language'] = ctx.language

        return item


class ProviderMissingError(Exception):
    pass


def build_context(loader, provider=None, uri=None, type=None, language=None):
    if not isinstance(loader, core.Loader):
        raise TypeError(loader)

    if not provider and not uri:
        errmsg = "Either provider or uri must be specified"
        raise ValueError(errmsg)

    if provider is None:
        for name in loader.list('providers'):
            cls = loader.get_class(name)
            if cls.can_handle(uri):
                provider = cls()
                break
        else:
            raise ProviderMissingError(uri)

    elif isinstance(provider, str):
        provider = loader.get('providers.%s' % (provider))

    if not isinstance(provider, extensions.Provider):
        raise TypeError(provider)

    uri = uri or provider.DEFAULT_URI

    return Context(provider, uri, type=type, language=language)


def build_n_contexts(loader, n, *args, **kwargs):
    def _expand(ctx, n):
        g = ctx.provider.paginate(ctx.uri)
        for _ in range(n):
            try:
                uri = next(g)
            except StopIteration:
                break

            yield Context(provider=ctx.provider, uri=uri,
                          type=ctx.type, language=ctx.language)

    ctx0 = build_context(loader, *args, **kwargs)
    return list(_expand(ctx0, n))
