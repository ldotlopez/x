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

import humanfriendly
import tabulate


import arroyo
from arroyo import (
    core,
    downloads,
    query
)


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
            '--download',
            action='store_true',
            help='Add selected items to downloads')
        cmd.add_argument(
            dest='querystring',
            nargs='?')

    def run(self, app, args):
        if args.queryparams:
            queryparams = dict([x.split('=', 1) for x in args.queryparams])
            q = query.Query(**queryparams)
        elif args.querystring:
            q = query.Query.fromstring(args.querystring)
        else:
            raise NotImplementedError()

        results = app.search(q, provider=args.provider, uri=args.uri)
        states = dict(core.db.downloads.all_states())

        for (entity, sources) in results:
            print(str(entity))
            print(display_group(sources, states))
            print("")


def display_group(sources, states=None):
    if states is None:
        states = {}

    headers = [' ', 'state', 'name', 'size', 's/l']
    table = [
        ['*' if src == sources[0] else ' ',
         downloads.STATE_SYMBOLS.get(states.get(src) or None) or ' ',
         src.name,
         humanfriendly.format_size(src.size),
         '%s/%s' % (src.seeds or '-', src.leechers or '-')]
        for src in sources
    ]
    return tabulate.tabulate(table, headers=headers)
