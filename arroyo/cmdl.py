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


from arroyo import (
    analyze,
    database,
    downloads,
    schema,
    scraper,
    settings,
    services,
    query
)
from arroyo.kit import storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--db',
        type=str,
        default='/tmp/arroyo-db.json')
    parser.add_argument(
        '--settings',
        type=str,
        default='/tmp/arroyo-settings.json')

    commands = parser.add_subparsers(dest='command', required=True)

    #
    # No OP
    #
    noop_cmd = commands.add_parser('noop')  # noqa

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
    # analyze
    #
    analyze_cmd = commands.add_parser('analyze')
    analyze_cmd.add_argument(
        '--input',
        type=argparse.FileType('r'),
        default=sys.stdin)
    analyze_cmd.add_argument(
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
    # download
    #
    download_cmd = commands.add_parser('download')
    download_cmd.add_argument(
        '--input',
        type=argparse.FileType('r'),
        default=sys.stdin)
    download_cmd.add_argument(
        '--add',
        action='store_true'
    )
    download_cmd.add_argument(
        '--list',
        action='store_true'
    )

    #
    # Do parsing
    #
    args = parser.parse_args(sys.argv[1:])

    #
    # Setup arroyo
    #
    db = database.Database(storage=storage.JSONStorage(location=args.db))
    s = settings.Settings(args.settings)

    services.set_service(services.DATABASE, db)
    services.set_service(services.LOADER, services.Loader())
    services.set_service(services.SETTINGS, s)

    #
    # Run subcommand
    #
    if args.command == 'noop':
        pass

    elif args.command == 'fetch':
        do_fetch(fetch_cmd, args)

    elif args.command == 'parse':
        do_parse(fetch_cmd, args)

    elif args.command == 'scrape':
        do_scrape(scrape_cmd, args)

    elif args.command == 'analyze':
        do_analyze(analyze_cmd, args)

    elif args.command == 'query':
        do_query(query_cmd, args)

    elif args.command == 'download':
        do_download(download_cmd, args)

    else:
        parser.print_help()
        parser.exit(1)


def do_fetch(parser, args):
    if not args.provider and not args.uri:
        parser.print_help()
        parser.exit(1)

    engine = scraper.Engine()
    ctx = scraper.build_context(args.provider, args.uri)
    result = engine.fetch_one(ctx)
    args.output.write(result)


def do_parse(parser, args):
    engine = scraper.Engine()
    ctx = scraper.build_context(args.provider,
                                type=args.type, language=args.language)
    buffer = args.input.read()

    results = list(engine.parse_one(ctx, buffer))
    output = json.dumps([x.dict() for x in results], indent=2)

    args.output.write(output)


def do_scrape(parser, args):
    if not args.provider and not args.uri:
        parser.print_help()
        parser.exit(1)

    ctxs = scraper.build_n_contexts(args.iterations, args.provider, args.uri,
                                    type=args.type, language=args.language)
    engine = scraper.Engine()
    results = engine.process(*ctxs)

    output = json.dumps([x.dict() for x in results], indent=2)
    args.output.write(output)


def do_analyze(parser, args):
    raw = json.loads(args.input.read())
    if isinstance(raw, dict):
        raw = [raw]

    raw = [schema.Source(**x) for x in raw]
    proc = analyze.analyze(*raw, mp=False)

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

    engine = query.Engine()
    try:
        ctx = engine.build_filter(q)
    except query.MissingFiltersError as e:
        errmsg = "Unknow filters: %s"
        errmsg = errmsg % ', '.join(e.args[0])
        print(errmsg, file=sys.stderr)
        parser.exit(1)

    data = json.loads(args.input.read())
    data = [schema.Source(**x) for x in data]
    results = engine.apply(ctx, data)
    results = engine.sort(results)

    results = [[entity.dict(), [src.dict() for src in sources]]
               for (entity, sources) in results]
    output = json.dumps(results, indent=2,
                        default=_json_encode_hook)
    args.output.write(output)


def do_download(parser, args):
    dls = downloads.Downloads()
    if args.list:
        print(repr(dls.get_active()))

    elif args.add:
        data = json.loads(args.input.read())
        data = [
            (schema.Entity(**key), [schema.Source(**src) for src in collection])
            for (key, collection) in data]

        for (key, collection) in data:
            dls.add(collection[0])

    else:
        print("Command needed", file=sys.stderr)


def _json_encode_hook(value):
    return str(value)


if __name__ == '__main__':
    main()
