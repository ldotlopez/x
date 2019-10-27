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


from arroyo import core
from arroyo import scraper


import json


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', required=True)
    parser.add_argument('--input', type=argparse.FileType('r'), required=True)
    parser.add_argument('--type', help='Force type')
    parser.add_argument('--language', help='Force language')

    args = parser.parse_args(sys.argv[1:])

    engine = scraper.Engine()
    ctx = scraper.build_context(core.Loader(), args.provider,
                                type=args.type, language=args.language)
    buffer = args.input.read()

    results = list(engine.parse_one(ctx, buffer))

    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()