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


import sys


from arroyo.kit import settings


import arroyo
from arroyo import (
    core,
    query
)
from arroyo.plugins.commands import uilib


class Search(arroyo.Command):
    COMMAND_NAME = 'search'

    def configure_command_parser(self, cmd):
        cmd.add_argument(
            '--provider',
            help='Force some provider')
        cmd.add_argument(
            '--uri',
            help='URI to parse')
        cmd.add_argument(
            '-f', '--filter',
            dest='queryparams',
            action='append',
            default=[])
        cmd.add_argument(
            '--from-config',
            action='store_true')
        cmd.add_argument(
            '--download',
            action='store_true',
            help='Add selected items to downloads')
        cmd.add_argument(
            '--auto',
            action='store_true',
            help='Automatic selection of downloads')
        cmd.add_argument(
            dest='querystring',
            nargs='?')

    def run(self, app, args):
        if args.queryparams:
            queryparams = dict([x.split('=', 1) for x in args.queryparams])
            qs = [query.Query(**queryparams)]

        elif args.querystring:
            qs = [query.Query.fromstring(args.querystring)]

        elif args.from_config:
            qs = queries_from_config(core.settings)

        else:
            raise NotImplementedError()

        for q in qs:
            try:
                results = app.query(q, provider=args.provider, uri=args.uri)
            except query.MissingFiltersError as e:
                msg = "Unknow filters: %s"
                msg = msg % ', '.join(e.args[0])
                print(msg, file=sys.stderr)
                continue

            labels = [' ', ' ', 'state', 'name', 'size', 's/l']
            columns = ['selected', 'count', 'state', 'name', 'size', 'share']

            for (entity, sources) in results:
                data = uilib.build_data(columns, sources)
                uilib.display_data(data, labels)
                if not args.download:
                    continue

                if not args.auto:
                    userchoice = select_data(len(data))
                    selected = sources[userchoice]
                    print("Ok, selected: %s" % selected.name)
                else:
                    selected = sources[0]

                try:
                    app.download(selected)
                except arroyo.ExtensionError as e:
                    print("Error: %s" % e)


def queries_from_config(s):
    DEFAULTS = 'arroyo.query.defaults.global'
    TYPE_DEFAULTS = 'arroyo.query.defaults.%s'
    QUERY = 'query.%s'

    defaults = s.get(DEFAULTS, {})
    type_defaults = {}

    try:
        children = s.children('query')
    except (settings.NotNamespaceError,):
        # Convert to log
        print("No queries")
        return []

    for name in children:
        params = s.get(QUERY % name)
        query_type = params.get('type', 'source')
        if query_type not in type_defaults:
            type_defaults[query_type] = s.get(TYPE_DEFAULTS % query_type, {})

        q = {}
        q.update(defaults)
        q.update(type_defaults[query_type])
        q.update(params)

        yield query.Query(**q)


def select_data(n_items):
    while True:
        sel = input("Selection? (1-%d) " % n_items)
        try:
            sel = int(sel)
        except ValueError:
            print("error: type a number plese")
            continue

        if sel < 1 or sel > n_items:
            print("error: type a number between 1 and %d please" % n_items)
            continue

        return sel - 1
