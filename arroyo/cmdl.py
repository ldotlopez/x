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


import argparse
import json
import sys


import arroyo
from arroyo import (
    normalize,
    schema,
    scraper,
    query
)


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)

    #
    # Fetch command
    #
    fetch_cmd = commands.add_parser('fetch')
    fetch_cmd.add_argument(
        '--provider',
        help='Force some provider')
    fetch_cmd.add_argument(
        '--uri',
        help='URI to parse')
    fetch_cmd.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout)

    #
    # Parse command
    #
    parse_cmd = commands.add_parser('parse')
    parse_cmd.add_argument(
        '--provider',
        required=True)
    parse_cmd.add_argument(
        '--input',
        type=argparse.FileType('r'),
        default=sys.stdin)
    parse_cmd.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout)
    parse_cmd.add_argument(
        '--type',
        help='Force type')
    parse_cmd.add_argument(
        '--language',
        help='Force language')

    #
    # Scrape command (fetch+parse)
    #
    scrape_cmd = commands.add_parser('scrape')
    scrape_cmd.add_argument(
        '--provider',
        required=True)
    scrape_cmd.add_argument(
        '--uri',
        help='URI to parse'),
    scrape_cmd.add_argument(
        '--iterations',
        default=1,
        type=int)
    scrape_cmd.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout)
    scrape_cmd.add_argument(
        '--type',
        help='Force type')
    scrape_cmd.add_argument(
        '--language',
        help='Force language')

    #
    # normalize
    #
    normalize_cmd = commands.add_parser('normalize')
    normalize_cmd.add_argument(
        '--input',
        type=argparse.FileType('r'),
        default=sys.stdin)
    normalize_cmd.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout)

    #
    # query
    #
    query_cmd = commands.add_parser('query')
    query_cmd.add_argument(
        '--input',
        type=argparse.FileType('r'),
        default=sys.stdin)
    query_cmd.add_argument(
        '--output',
        type=argparse.FileType('w'),
        default=sys.stdout)
    query_cmd.add_argument(
        '--filter',
        dest='queryparams',
        action='append',
        default=[])
    query_cmd.add_argument(
        dest='querystring',
        nargs='?')

    #
    # Do parsing
    #

    args = parser.parse_args(sys.argv[1:])

    if args.command == 'fetch':
        do_fetch(fetch_cmd, args)

    elif args.command == 'parse':
        do_parse(fetch_cmd, args)

    elif args.command == 'scrape':
        do_scrape(scrape_cmd, args)

    elif args.command == 'normalize':
        do_normalize(normalize_cmd, args)

    elif args.command == 'query':
        do_query(query_cmd, args)

    else:
        parser.print_help()
        parser.exit(1)


def do_fetch(parser, args):
    if not args.provider and not args.uri:
        parser.print_help()
        parser.exit(1)

    loader = arroyo.Loader()
    engine = scraper.Engine()
    ctx = scraper.build_context(loader, args.provider, args.uri)
    result = engine.fetch_one(ctx)
    args.output.write(result)


def do_parse(parser, args):
    engine = scraper.Engine()
    ctx = scraper.build_context(arroyo.Loader(), args.provider,
                                type=args.type, language=args.language)
    buffer = args.input.read()

    results = list(engine.parse_one(ctx, buffer))
    output = json.dumps([x.dict() for x in results], indent=2)

    args.output.write(output)


def do_scrape(parser, args):
    if not args.provider and not args.uri:
        parser.print_help()
        parser.exit(1)

    ctxs = scraper.build_n_contexts(arroyo.Loader(), args.iterations,
                                    args.provider, args.uri,
                                    type=args.type, language=args.language)
    engine = scraper.Engine()
    results = engine.process(*ctxs)

    output = json.dumps([x.dict() for x in results], indent=2)
    args.output.write(output)


def do_normalize(parser, args):
    raw = json.loads(args.input.read())
    if isinstance(raw, dict):
        raw = [raw]

    raw = [schema.Source(**x) for x in raw]
    proc = normalize.normalize(*raw, mp=False)

    output = json.dumps([x.dict() for x in proc], indent=2,
                        default=_json_encode_hook)
    args.output.write(output)


def do_query(parser, args):
    def _parse_queryparams(pairs):
        for pair in pairs:
            key, value = pair.split('=', 1)
            if not key or not value:
                raise ValueError(pair)

            yield (key, value)

    if not args.queryparams and not args.querystring:
        parser.print_help()
        errmsg = "filter or querystring are requierd"
        print(errmsg, file=sys.stderr)
        parser.exit(1)

    q = {}
    if args.querystring:
        q.update(query.Query.fromstring(args.querystring))

    if args.queryparams:
        params = dict(_parse_queryparams(args.queryparams))
        q = query.Query(**params)

    engine = query.Engine(arroyo.Loader())
    ctx = engine.build_filter(q)

    data = json.loads(args.input.read())
    data = [schema.Item(**x) for x in data]
    results = engine.apply(ctx, data)

    output = json.dumps([x.dict() for x in results], indent=2,
                        default=_json_encode_hook)
    args.output.write(output)


def _json_encode_hook(value):
    return str(value)


if __name__ == '__main__':
    main()
