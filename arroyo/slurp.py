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


class SlurpEngine:
    def __init__(self, loader):
        self.loader = loader

    def get_provider_for(self, url):
        for name in self.loader.list('providers'):
            cls = self.loader.get_class(name)
            if cls.can_handle(url):
                return cls()

        raise ProviderMissingError(url)

    def process(self, urls):
        results = []

        async def _process(url):
            try:
                provider = self.get_provider_for(url)
            except ProviderMissingError:
                return

            buffer = await provider.fetch(url)
            results.append(provider.parse(buffer))

        tasks = [_process(url) for url in urls]
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*tasks))

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


    slurp = SlurpEngine(loader=ClassLoader(plugins))
    results = slurp.process(sys.argv[1:])
    print(repr(results))


if __name__ == '__main__':
    main()
