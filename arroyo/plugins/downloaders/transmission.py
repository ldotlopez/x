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


import transmissionrpc


import arroyo
from arroyo import (
    downloads,
    services
)


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
    SETTINGS_PREFIX = "plugin.downloader.transmission"

    @property
    def client(self):
        return transmissionrpc.Client(
            services.settings.get(self.SETTINGS_PREFIX + '.host', 'localhost'),
            services.settings.get(self.SETTINGS_PREFIX + '.port', 9091),
            services.settings.get(self.SETTINGS_PREFIX + '.username', None),
            services.settings.get(self.SETTINGS_PREFIX + '.password', None),
        )

    @trap_transmission_error
    def add(self, uri):
        """
        raises transmissionrpc.TransmissionError on error
        """
        ret = self.client.add_torrent(uri)
        return ret.hashString

    @trap_transmission_error
    def archive(self, id):
        """
        On invalid or non existent torrents it just ignores them
        """
        self.client.remove_torrent(id, delete_data=False)

    @trap_transmission_error
    def cancel(self, id):
        """
        On invalid or non existent torrents it just ignores them
        """
        self.client.remove_torrent(id, delete_data=True)

    @trap_transmission_error
    def dump(self):
        return [{'id': x.hashString,
                 'state': self.state_for_torrent(x),
                 'progress': x.progress / 100}
                for x in self.client.get_torrents()]

    def state_for_torrent(self, torrent):
        if torrent.status in STATUS_MAP:
            return STATUS_MAP[torrent.status]

        elif torrent.status == 'stopped':
            if torrent.progress < 100:
                return downloads.State.PAUSED
            else:
                return downloads.State.DONE

        else:
            logmsg = "Unknow transmission status '%s"
            logmsg = logmsg % (torrent.status)
            self.logger.error(logmsg)
            return downloads.State.UNKNOWN


class ClientError(arroyo.ExtensionError):
    pass
