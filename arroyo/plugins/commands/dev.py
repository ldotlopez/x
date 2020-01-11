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
    extensions,
    downloads,
    query,
    schema,
    scraper,
)


class Command(extensions.Command):
    COMMAND_NAME = 'dev'

    def configure_command_parser(self, cmd):
        subcmds = cmd.add_subparsers(dest='devcmd')

        #
        # Fetch command (fetch+parse)
        #
        fetch_cmd = subcmds.add_parser('fetch')
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
        parse_cmd = subcmds.add_parser('parse')
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
        scrape_cmd = subcmds.add_parser('scrape')
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
        analyze_cmd = subcmds.add_parser('analyze')
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
        query_cmd = subcmds.add_parser('query')
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
        # query2
        #
        query_cmd = subcmds.add_parser('query2')
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
        download_cmd = subcmds.add_parser('download')
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

    def run(self, app, args):
        if args.devcmd == 'fetch':
            self.run_fetch(app, args)

        elif args.devcmd == 'parse':
            self.run_parse(app, args)

        elif args.devcmd == 'scrape':
            self.run_scrape(app, args)

        elif args.devcmd == 'analyze':
            self.run_analyze(app, args)

        elif args.devcmd == 'query':
            self.run_query(app, args)

        elif args.devcmd == 'query2':
            self.run_query2(app, args)

        elif args.devcmd == 'download':
            self.run_download(app, args)

        elif not args.devcmd:
            raise extensions.CommandUsageError()

        else:
            raise NotImplementedError()

    def run_fetch(self, app, args):
        if not args.provider and not args.uri:
            raise extensions.CommandUsageError()

        engine = scraper.Engine(app.srvs)
        ctx = engine.build_context(args.provider, args.uri)
        result = engine.fetch_one(ctx)
        args.output.write(result)

    def run_parse(self, app, args):
        engine = scraper.Engine()
        ctx = engine.build_context(provider=args.provider,
                                   type=args.type,
                                   language=args.language)
        buffer = args.input.read()

        results = list(engine.parse_one(ctx, buffer))
        output = json.dumps([x.dict() for x in results], indent=2)

        args.output.write(output)

    def run_scrape(self, app, args):
        if not args.provider and not args.uri:
            raise extensions.CommandUsageError()

        engine = scraper.Engine(app.srvs)
        ctxs = engine.build_n_contexts(args.iterations,
                                       args.provider,
                                       args.uri,
                                       type=args.type,
                                       language=args.language)
        results = engine.process(*ctxs)

        output = json.dumps([x.dict() for x in results], indent=2)
        args.output.write(output)

    def run_analyze(self, app, args):
        raw = json.loads(args.input.read())
        if isinstance(raw, dict):
            raw = [raw]

        raw = [schema.Source(**x) for x in raw]
        proc = analyze.analyze(*raw, mp=False)

        output = json.dumps([x.dict() for x in proc],
                            indent=2,
                            default=_json_encode_hook)
        args.output.write(output)

    def do_query(self, app, args):
        def _parse_queryparams(pairs):
            for pair in pairs:
                key, value = pair.split('=', 1)
                if not key or not value:
                    raise ValueError(pair)

                yield (key, value)

        if not args.queryparams and not args.querystring:
            errmsg = "filter or querystring are requierd"
            print(errmsg, file=sys.stderr)
            raise extensions.CommandUsageError()

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
            raise extensions.CommandUsageError()

        data = json.loads(args.input.read())
        data = [schema.Source(**x) for x in data]
        results = engine.apply(ctx, data)
        results = engine.sort(results)

        results = [[entity.dict(), [src.dict() for src in sources]]
                   for (entity, sources) in results]
        output = json.dumps(results, indent=2,
                            default=_json_encode_hook)
        args.output.write(output)

    def do_query2(self, app, args):
        def _parse_queryparams(pairs):
            for pair in pairs:
                key, value = pair.split('=', 1)
                if not key or not value:
                    raise ValueError(pair)

                yield (key, value)

        if not args.queryparams and not args.querystring:
            errmsg = "filter or querystring are requierd"
            print(errmsg, file=sys.stderr)
            raise extensions.CommandUsageError()

        q = {}
        if args.querystring:
            q = query.Query.fromstring(args.querystring)

        if args.queryparams:
            params = dict(_parse_queryparams(args.queryparams))
            q = query.Query(**params)

        # Setup filters before scrape anything
        query_engine = query.Engine()
        try:
            filters = query_engine.build_filter(q)
        except query.MissingFiltersError as e:
            errmsg = "Unknow filters: %s"
            errmsg = errmsg % ', '.join(e.args[0])
            print(errmsg, file=sys.stderr)
            raise extensions.CommandUsageError()

        # Build scrape ctxs and process them
        scrape_engine = scraper.Engine()
        ctxs = scrape_engine.build_contexts_for_query(q)
        sources = scrape_engine.process(*ctxs)
        sources = analyze.analyze(*sources)

        # Pass sources thru filters
        results = query_engine.apply(filters, sources)
        results = query_engine.sort(results)

        # Output
        results = [[entity.dict(), [src.dict() for src in sources]]
                   for (entity, sources) in results]
        output = json.dumps(results, indent=2,
                            default=_json_encode_hook)
        args.output.write(output)

    def run_download(self, app, args):
        dls = downloads.Downloads()
        if args.list:
            print(repr(dls.get_active()))

        elif args.add:
            data = json.loads(args.input.read())
            data = [
                (schema.Entity(**key),
                 [schema.Source(**src) for src in collection])
                for (key, collection) in data]

            for (key, collection) in data:
                try:
                    dls.add(collection[0])
                except extensions.ExtensionError as e:
                    print("Add '%s' failed. Extension error: %r" %
                          (collection[0], e))

        else:
            raise extensions.CommandUsageError()


def _json_encode_hook(value):
    return str(value)
