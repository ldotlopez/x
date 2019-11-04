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


from urllib import parse


import arroyo


import transmissionrpc


# from arroyo import (
#     bittorrentlib,
#     downloads,
#     pluginlib
# )


# from appkit import (
#     loggertools,
#     store
# )
# from sqlalchemy import orm


# Support for monkey patch transmissionrpc

def tranmissionrpc_torrent_files(torrent):
    files = torrent.files().values()
    if not files:
        return []

    return [x['name'] for x in files]


def tranmissionrpc_torrent___str__(torrent):
    files = tranmissionrpc_torrent_files(torrent)
    if not files:
        return repr(torrent)

    root = [x.split('/')[0] for x in files][0]

    return root


transmissionrpc.torrent.Torrent.__str__ = tranmissionrpc_torrent___str__


# models = pluginlib.models


# SETTINGS_NS = 'plugins.downloaders.transmission'
# STATE_MAP = {
#     'checking': models.State.INITIALIZING,
#     'check pending': models.State.INITIALIZING,
#     'download pending': models.State.QUEUED,
#     'downloading': models.State.DOWNLOADING,
#     'seeding': models.State.SHARING,
#     # other states need more logic
# }
# TRANSMISSION_API_ERROR_MSG = (
#     "Error while trying to communicate with transmission: '{message}'"
# )


from arroyo import downloads


STATUS_MAP = {
    'checking': downloads.State.INITIALIZING,
    'check pending': downloads.State.INITIALIZING,
    'download pending': downloads.State.QUEUED,
    'downloading': downloads.State.DOWNLOADING,
    'seeding': downloads.State.SHARING,
    # other states need more logic
}


class Tr(arroyo.Downloader):
    def __init__(self):
        self.client = transmissionrpc.Client(
            address='localhost',
            port=9091,
            user=None,
            password=None)

    def get_identifier(self, source):
        parsed = parse.urlparse(source.uri)
        qs = dict(parse.parse_qsl(parsed.query))
        return qs['xt'].split(':')[2]

    def add(self, uri):
        ret = self.client.add_torrent(uri)
        return ret.hashString

    def list(self):
        return [x.hashString for x in self.client.get_torrents()]

    def get_state(self, id_):
        return NotImplementedError()

    def dump(self):
        return [{'id': x.hashString,
                 'state': STATUS_MAP[x.status]}
                for x in self.client.get_torrents()]


# class _Tr(pluginlib.Downloader):
#     __extension_name__ = 'transmission'

#     def __init__(self, app, *args, **kwargs):
#         super().__init__(app, *args, **kwargs)
#         settings = app.settings

#         self.logger = loggertools.getLogger('transmission')
#         settings.add_validator(self.settings_validator)

#         try:
#             s = settings.get(SETTINGS_NS, default={})
#             self.api = transmissionrpc.Client(
#                 address=s.get('address', 'localhost'),
#                 port=s.get('port', 9091),
#                 user=s.get('user', None),
#                 password=s.get('password', None)
#             )
#             # self.shield = {
#             #     'urn:btih:' + x.hashString: x
#             #     for x in self.api.get_torrents()}

#         except transmissionrpc.error.TransmissionError as e:
#             msg = TRANSMISSION_API_ERROR_MSG.format(message=e.original.message)
#             raise pluginlib.exc.PluginError(msg, e) from e

#     def id_for_source(self, source):
#         return source.urn.split(':')[2]

#     def add(self, source):
#         try:
#             ret = self.api.add_torrent(source.uri)

#         except transmissionrpc.error.TransmissionError as e:
#             msg = TRANSMISSION_API_ERROR_MSG.format(message=e.original.message)
#             raise pluginlib.exc.PluginError(msg, e) from e

#         # self.shield[urn] = ret
#         return ret.hashString

#     def cancel(self, hash_string):
#         return self.remove(hash_string, delete_data=True)

#     def archive(self, hash_string):
#         return self.remove(hash_string, delete_data=False)

#     def _torrent_for_hash_string(self, hash_string):
#         g = (x for x in self.api.get_torrents() if x.hashString == hash_string)
#         try:
#             return next(g)
#         except StopIteration:
#             pass

#         raise downloads.DownloadNotFoundError(hash_string)

#     def remove(self, hash_string, delete_data):
#         # self.shield = {
#         #     urn: i for (urn, i) in
#         #     self.shield.items()
#         #     if i != item
#         # }
#         torrent = self._torrent_for_hash_string(hash_string)

#         try:
#             self.api.remove_torrent(torrent.id, delete_data=delete_data)
#             return True
#         except transmissionrpc.error.TransmissionError as e:
#             msg = TRANSMISSION_API_ERROR_MSG.format(message=e.original.message)
#             raise pluginlib.exc.PluginError(msg, e) from e

#     def list(self):
#         return [x.hashString for x in self.api.get_torrents()]

#     def get_state(self, hash_string):
#         torrent = self._torrent_for_hash_string(hash_string)

#         # stopped status can mean:
#         # - if progress is less that 100, source is paused
#         # - if progress is 100, source can be paused or seeding completed
#         #   isFinished attr can handle this
#         if torrent.status == 'stopped':
#             if torrent.progress < 100:
#                 return models.State.PAUSED
#             else:
#                 return models.State.DONE

#         state = torrent.status

#         if state not in STATE_MAP:
#             msg = "Unknown state «{state}»."
#             msg = msg.format(state=state)
#             raise pluginlib.exc.SelfCheckError(msg)

#         return STATE_MAP[state]

#     def get_info(self, hash_string):
#         torrent = self._torrent_for_hash_string(hash_string)
#         ret = {
#             'files': tranmissionrpc_torrent_files(torrent)
#         }

#         if ret['files']:
#             ret['location'] = torrent.downloadDir + \
#                 ret['files'][0].split('/')[0]

#         for attr in ['eta', 'progress']:
#             try:
#                 value = getattr(torrent, attr)
#             except ValueError:
#                 value = None

#             ret[attr] = value

#         return ret

#     @staticmethod
#     def settings_validator(key, value):
#         if not key.startswith(SETTINGS_NS):
#             return value

#         prop = key[len(TransmissionDownloader._SETTINGS_NS)+1:]

#         if prop == 'enabled':
#             if not isinstance(value, bool):
#                 raise store.ValidationError(key, value, 'Must a bool')
#             else:
#                 return value

#         if prop in ['address', 'user', 'password']:
#             if not isinstance(value, str):
#                 raise store.ValidationError(key, value, 'Must a bool')
#             else:
#                 return value

#         if prop == 'port':
#             if not isinstance(value, int):
#                 raise store.ValidationError(key, value, 'Must be a int')
#             else:
#                 return value

#         else:
#             raise store.ValidationError(key, value, 'Unknow property')


# __arroyo_extensions__ = [
#     TransmissionDownloader
# ]
