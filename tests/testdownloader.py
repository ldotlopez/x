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


import unittest
from unittest import mock


import time


from arroyo import ClassLoader
from arroyo.plugins.downloaders.transmission import (
    Tr as TransmissionDownloader
)
from arroyo.downloads import (
    Downloads,
    Database as DownloadsDatabase,
    State as DownloadState
)
from testlib import build_item, build_source


class BaseTest:
    SLOWDOWN = None

    def wait(self):
        if self.SLOWDOWN:
            time.sleep(self.SLOWDOWN)

    def setUp(self):
        loader = ClassLoader({
            'downloader': self.DOWNLOADER_CLS
        })
        self.downloads = Downloads(loader)

    def test_identifier(self):
        src1 = build_source('foo')
        downloader = self.DOWNLOADER_CLS()
        self.assertEqual(
            downloader.get_identifier(src1),
            '0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33'
        )

    def test_add(self):
        s1 = build_source('foo')
        self.downloads.add(s1)
        self.wait()
        self.assertTrue(
            self.downloads.list() ==
            [s1]
        )

    def test_add_duplicated(self):
        src1 = build_source('foo')
        self.downloads.add(src1)
        self.wait()
        self.downloads.add(src1)
        self.wait()

        self.downloads.get_state(src1)
        self.assertEqual(
            set(self.downloads.list()),
            set([src1])
        )

    def test_add_duplicated_archived(self):
        src1 = build_source('foo')

        self.downloads.add(src1)
        self.wait()

        self.downloads.archive(src1)
        self.wait()

        self.downloads.add(src1)
        self.wait()

        self.assertEqual(
            self.downloads.list(),
            [])


class TransmissionTest(BaseTest, unittest.TestCase):
    PLUGINS = ['downloaders.transmission']
    DOWNLOADER_CLS = TransmissionDownloader
    SLOWDOWN = 0.2

    def setUp(self):
        super().setUp()

    def tearDown(self):
        transmission = self.downloads.downloader.client

        for x in transmission.get_torrents():
            if x.name in ['foo', 'bar']:
                transmission.remove_torrent(x.id, delete_data=True)

        self.wait()


#     def test_add_duplicated(self):
#         src1 = build_item('foo')
#         self.app.insert_sources(src1)
#         self.app.downloads.add(src1)
#         self.wait()

#         with self.assertRaises(downloads.DuplicatedDownloadError):
#             self.app.downloads.add(src1)

#         self.assertEqual(
#             set(self.app.downloads.list()),
#             set([src1]))

#     def test_add_duplicated_archived(self):
#         src1 = build_item('foo')
#         self.app.insert_sources(src1)
#         self.app.downloads.add(src1)
#         self.app.downloads.archive(src1)
#         self.wait()

#         with self.assertRaises(downloads.DuplicatedDownloadError):
#             self.app.downloads.add(src1)

#         self.assertEqual(
#             self.app.downloads.list(),
#             [])

#     def test_cancel(self):
#         src1 = build_item('foo')
#         self.app.insert_sources(src1)
#         self.app.downloads.add(src1)
#         self.app.downloads.cancel(src1)
#         self.wait()

#         self.assertEqual(
#             src1.download,
#             None)
#         self.assertEqual(
#             self.app.downloads.list(),
#             [])

#     def test_archive(self):
#         src1 = build_item('foo')
#         self.app.insert_sources(src1)
#         self.app.downloads.add(src1)
#         self.app.downloads.archive(src1)
#         self.wait()

#         self.assertEqual(
#             src1.download.state,
#             models.State.ARCHIVED)
#         self.assertEqual(
#             self.app.downloads.list(),
#             [])

#     def test_remove_unknown_source(self):
#         src1 = build_item('foo')
#         src2 = build_item('bar')
#         self.app.insert_sources(src1, src2)
#         self.wait()

#         with self.assertRaises(downloads.DownloadNotFoundError):
#             self.app.downloads.cancel(src1)
#         with self.assertRaises(downloads.DownloadNotFoundError):
#             self.app.downloads.archive(src2)

#     def plugin_class(self):
#         return self.app._get_extension_class(downloads.Downloader,
#                                              self.DOWNLOADER)

#     def foreign_ids(self, srcs):
#         return [self.app.downloads.plugin.id_for_source(src)
#                 for src in srcs]

#     def test_unexpected_download_from_plugin(self):
#         src1 = build_item('foo')
#         src2 = build_item('bar')
#         self.app.insert_sources(src1)
#         self.app.downloads.add(src1)
#         self.wait()

#         fake_list = self.foreign_ids([src1, src2])
#         with mock.patch.object(self.plugin_class(), 'list',
#                                return_value=fake_list):
#             self.assertEqual(
#                 set(self.app.downloads.list()),
#                 set([src1]))

#     def test_handle_unexpected_remove_from_plugin_as_cancel(self):
#         src1 = build_item('foo')
#         src2 = build_item('bar')
#         self.app.insert_sources(src1, src2)
#         self.app.downloads.add(src1)
#         self.app.downloads.add(src2)
#         self.wait()

#         fake_list = self.foreign_ids([src1])
#         with mock.patch.object(self.plugin_class(), 'list',
#                                return_value=fake_list):

#             self.app.downloads.sync()

#         self.assertEqual(
#             src2.download,
#             None)

#     def test_handle_unexpected_remove_from_plugin_as_archive(self):
#         src1 = build_item('foo')
#         src2 = build_item('bar')
#         self.app.insert_sources(src1, src2)
#         self.app.downloads.add(src1)
#         self.app.downloads.add(src2)
#         self.wait()

#         # Manually update state of src2
#         src2.download.state = models.State.SHARING

#         # Mock plugin list to not list src2
#         fake_list = self.foreign_ids([src1])
#         with mock.patch.object(self.plugin_class(), 'list',
#                                return_value=fake_list):
#             self.app.downloads.sync()

#         self.assertEqual(
#             src2.download.state,
#             models.State.ARCHIVED
#         )

#     def test_info(self):
#         src = build_item('foo')
#         self.app.insert_sources(src)
#         self.app.downloads.add(src)
#         self.app.downloads.get_info(src)


# class MockTest(BaseTest, unittest.TestCase):
#     DOWNLOADER_CLS = MockDownloader


# class TransmissionTest(BaseTest, unittest.TestCase):
#     PLUGINS = ['downloaders.transmission']
#     DOWNLOADER = 'transmission'
#     SLOWDOWN = 0.2

#     def setUp(self):
#         super().setUp()
#         for t in self.app.downloads.plugin.api.get_torrents():
#             if t.name in ['foo', 'bar']:
#                 self.app.downloads.plugin.api.remove_torrent(
#                     t.id, delete_data=True)
#         self.wait()


# class DirectoryTest(BaseTest, unittest.TestCase):
#     # TODO:
#     # - Set storage path to tmpdir

#     PLUGINS = ['downloaders.directory']
#     DOWNLOADER = 'directory'
#     SLOWDOWN = 0.2

#     def setUp(self):
#         super().setUp()
#         cls = self.plugin_class()
#         cls._fetch_torrent = mock.Mock(return_value=b'')


class StorageTest(unittest.TestCase):
    def setUp(self):
        pass

    def _build_db(self):
        db = DownloadsDatabase()

        src = build_source('Foo s01e02')
        db.set_state(src, DownloadState.DOWNLOADING)

        return db

    def test_get_and_set(self):
        db = DownloadsDatabase()

        src = build_source('Foo s01e02')
        db.set_state(src, DownloadState.DOWNLOADING)
        state = db.get_state(src)
        self.assertTrue(state == DownloadState.DOWNLOADING)

    def test_dump(self):
        db = self._build_db()
        b = db.dump()


if __name__ == '__main__':
    unittest.main()
