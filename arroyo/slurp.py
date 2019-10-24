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
import kit


class Context:
    def __init__(self, provider, uri, iterations=1, type=None, language=None):
        self.provider = provider
        self.provider_name = provider.__class__.__name__.lower() if provider else ''
        self.uri = uri
        self.iterations = iterations
        self.type = type
        self.language = language


class Engine:
    def __init__(self, loader):
        self.loader = loader

    def build_context(self, provider=None, uri=None, iterations=1, type=None, language=None):
        if not provider and not uri:
            errmsg = "Either provider or uri must be specified"
            raise ValueError(errmsg)

        if provider is None:
            provider = self.get_provider_for_uri(uri)
        elif isinstance(provider, str):
            provider = self.loader.get('providers.%s' % (provider))

        if not isinstance(provider, extensions.Provider):
            raise TypeError(provider)

        provider = provider or self.get_provider_for_uri(uri)
        uri = uri or provider.DEFAULT_URI

        return Context(provider, uri, iterations=iterations, type=type, language=language)

    def get_provider_for_uri(self, uri):
        for name in self.loader.list('providers'):
            cls = self.loader.get_class(name)
            if cls.can_handle(uri):
                return cls()

        raise ProviderMissingError(uri)

    def get_uris(self, origin):
        ret = []

        g = origin.provider.paginate(origin.uri)
        for _ in range(origin.iterations):
            try:
                ret.append(next(g))
            except StopIteration:
                break

        return ret

    def process(self, *ctxs):
        results = []

        for ctx in ctxs:
            for uri in self.get_uris(ctx):
                buffer = asyncio.run(ctx.provider.fetch(uri))
                items = ctx.provider.parse(buffer)
                results.extend(items)

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

    async def _fetch_uri(self, ctx, uri):
        try:
            return await ctx.provider.fetch(uri)
        except asyncio.TimeoutError:
            raise

    def _parse_buffer(self, ctx, buffer):
        def _fix_item(item):
            item['provider'] = ctx.provider_name

            if ctx.type:
                item['type'] = ctx.type
            if ctx.language:
                item['language'] = ctx.language

            return item

        return (_fix_item(i) for i in ctx.provider.parse(buffer))


class ProviderMissingError(Exception):
    pass


def main():
    import argparse
    import sys

    plugins = {
        'providers.eztv': 'arroyo.plugins.providers.dummy.EzTV',
        'providers.rarbg': 'arroyo.plugins.providers.dummy.RarBG',
        'providers.thepiratebay': 'arroyo.plugins.providers.dummy.ThePirateBay'
    }

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--provider', help='Force some provider'
    )
    parser.add_argument(
        '--uri', help='URI to parse'
    )
    parser.add_argument(
        '--iterations', default=1, type=int, help='Iterations to do'
    )
    parser.add_argument(
        '--dump', action='store_true'
    )

    args = parser.parse_args(sys.argv[1:])

    if not args.provider and not args.uri:
        parser.print_help()
        sys.exit(1)

    if args.dump and args.iterations > 1:
        print("dump only works with iterations=1")
        sys.exit(1)

    slurp = Engine(loader=core.Loader())
    ctx = slurp.build_context(args.provider, args.uri, args.iterations)

    if args.dump:
        ctx = slurp.build_context(args.provider)
        print(asyncio.run(slurp._fetch_uri(ctx, uri)))
        sys.exit(0)

    else:
        ctx = slurp.build_context(args.provider, args.uri, args.iterations)
        results = slurp.process(ctx)
        print(repr(results))


if __name__ == '__main__':
    main()
