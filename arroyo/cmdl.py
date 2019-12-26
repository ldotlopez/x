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
from arroyo import application


def main():
    parser = application.build_argparse()
    args, remain = parser.parse_known_args()

    loglevel = application.DEFAULT_LOGLEVEL - args.quiet + args.verbose
    loglevel = max(0, min(loglevel, len(application.LOG_LEVELS) - 1))
    loglevel = application.LOG_LEVELS[loglevel]

    app = application.App(log_level=loglevel, settings_path=args.settings,
                          database_path=args.db)
    app.run_command_line(sys.argv[1:], parser=parser)
