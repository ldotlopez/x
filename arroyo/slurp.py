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


from kit import ClassLoader


class SlurpContext:
    def __init__(self, provider, uri, iterations=1):
        self.provider = provider
        self.uri = uri
        self.iterations = iterations


class SlurpEngine:
    def __init__(self, loader):
        self.loader = loader

    def build_context(self, provider=None, uri=None, iterations=1):
        if not provider and not uri:
            errmsg = "Either provider or uri must be specified"
            raise ValueError(errmsg)

        provider = provider or self.get_provider_for_uri(uri)
        uri = uri or provider.DEFAULT_URI

        return SlurpContext(provider, uri, iterations)

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
                print("processed %s: found %d items" % (uri, len(items)))
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

        return results


class ProviderMissingError(Exception):
    pass


def main():
    import argparse
    import sys

    plugins = {
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
    args = parser.parse_args(sys.argv[1:])
    if not args.provider and not args.uri:
        parser.print_help()
        sys.exit(1)

    slurp = SlurpEngine(loader=ClassLoader(plugins))
    ctx = slurp.build_context(args.provider, args.uri, args.iterations)
    results = slurp.process(ctx)

    print(repr(results))


if __name__ == '__main__':
    main()
