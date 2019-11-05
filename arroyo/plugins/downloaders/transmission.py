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


# Documentation for transmissionrpc:
# https://pythonhosted.org/transmissionrpc/reference/transmissionrpc.html


import functools
from urllib import parse


import transmissionrpc


import arroyo
from arroyo import downloads


STATUS_MAP = {
    'checking': downloads.State.INITIALIZING,
    'check pending': downloads.State.INITIALIZING,
    'download pending': downloads.State.QUEUED,
    'downloading': downloads.State.DOWNLOADING,
    'seeding': downloads.State.SHARING,
    # other states need more logic
}


def trap_transmission_error(fn):
    @functools.wraps(fn)
    def _wrap(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except transmissionrpc.error.TransmissionError as e:
            raise ClientError(e.message, e.original) from e

    return _wrap


class Tr(arroyo.Downloader):
    @trap_transmission_error
    def __init__(self):
        self.client = transmissionrpc.Client(
            address='localhost',
            port=9091,
            user=None,
            password=None)

    @trap_transmission_error
    def add(self, uri):
        ret = self.client.add_torrent(uri)
        return ret.hashString

    @trap_transmission_error
    def archive(self, id):
        self.client.remove_torrent(id, delete_data=False)

    @trap_transmission_error
    def cancel(self, id):
        self.client.remove_torrent(id, delete_data=True)

    @trap_transmission_error
    def dump(self):
        return [{'id': x.hashString,
                 'state': STATUS_MAP[x.status]}
                for x in self.client.get_torrents()]


class ClientError(arroyo.ExtensionError):
    pass
