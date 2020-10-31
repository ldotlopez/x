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


from arroyo import extensions
from arroyo.plugins.commands import uilib


class Downloads(extensions.Command):
    COMMAND_NAME = "downloads"

    def configure_command_parser(self, cmd):
        cmd.add_argument("--list", action="store_true", help="Show current downloads")
        cmd.add_argument("--cancel", help="Cancel a download")

    def run(self, app, args):
        if args.list:
            labels = ["id", "state", "name", "size", "progress"]
            columns = ["crc32", "state", "name", "size", "progress"]

            data = uilib.build_dataset(
                self.srvs.db, columns, [src for (src, state) in app.get_downloads()]
            )

            uilib.display_data(data, labels=labels)

        elif args.cancel:
            data = uilib.build_dataset(
                self.srvs.db,
                ["crc32", "raw_source"],
                [src for (src, state) in app.get_downloads()],
            )
            data = {x[0]: x[1] for x in data}

            if args.cancel not in data:
                print("Error: Invalid ID")
                return

            app.cancel(data[args.cancel])

        else:
            raise extensions.CommandUsageError()
