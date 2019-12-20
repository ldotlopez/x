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
import time
from unittest import mock

from arroyo.kit.storage import MemoryStorage
from arroyo.database import (
    Database,
    NotFoundError
)
from arroyo.settings import Settings
from arroyo.downloads import (
    Downloads,
    State,
)
from arroyo.services import (
    DATABASE,
    LOADER,
    SETTINGS,
    ClassLoader,
)


from testlib import (
    build_source,
    build_item,
    patch_service,
    unpatch_service
)


class DownloaderTestMixin:
    SLOWDOWN = 0.0

    def setUp(self):
        patch_service(SETTINGS, Settings(storage=MemoryStorage()))

        name, clsspec = self.DOWNLOADER_SPEC
        patch_service(LOADER, ClassLoader({
            name: clsspec
        }))
        patch_service(DATABASE, Database(storage=MemoryStorage()))

        self.downloads = Downloads()

    def tearDown(self):
        unpatch_service(LOADER)
        unpatch_service(DATABASE)

    def wait(self):
        if self.SLOWDOWN:
            time.sleep(self.SLOWDOWN)

    def test_add(self):
        s1 = build_source('foo')

        self.downloads.add(s1)
        self.wait()

        self.assertEqual(self.downloads.get_active(),
                         [s1])

    def test_add_duplicated(self):
        src1 = build_source('foo')

        self.downloads.add(src1)
        self.wait()

        self.downloads.add(src1)
        self.wait()

        self.assertNotEqual(self.downloads.get_state(src1),
                            None)

        self.assertEqual(self.downloads.get_active(),
                         [src1])

    def test_archive(self):
        src1 = build_source('foo')

        self.downloads.add(src1)
        self.wait()

        self.downloads.archive(src1)
        self.wait()

        self.assertEqual(self.downloads.get_state(src1),
                         State.ARCHIVED)

        self.assertEqual(self.downloads.get_active(),
                         [])

    def test_cancel(self):
        src1 = build_source('foo')

        self.downloads.add(src1)
        self.wait()

        self.downloads.cancel(src1)
        self.wait()

        with self.assertRaises(NotFoundError):
            self.downloads.get_state(src1)

        self.assertEqual(self.downloads.get_active(),
                         [])

    def test_add_duplicated_archived(self):
        src1 = build_source('foo')

        self.downloads.add(src1)
        self.wait()

        self.downloads.archive(src1)
        self.wait()

        self.downloads.add(src1)
        self.wait()

        self.assertNotEqual(self.downloads.get_state(src1),
                            None)

        self.assertEqual(self.downloads.get_active(),
                         [src1])

    def test_remove_unknown_source(self):
        src1 = build_source('foo')

        with self.assertRaises(NotFoundError):
            self.downloads.cancel(src1)

    def test_archive_unknown_source(self):
        # This test fails if the name is foo. ¿?
        src1 = build_source('foo')

        with self.assertRaises(NotFoundError):
            self.downloads.archive(src1)

    def test_unexpected_download_from_plugin(self):
        src1 = build_source('foo')
        src2 = build_source('bar')

        self.downloads.add(src1)
        self.wait()

        fake_dump = [
            {'id': self.downloads.db.downloads.external_for_source(src1),
             'state': State.DOWNLOADING},
            {'id': 'external-added-id',
             'state': State.DOWNLOADING}
        ]
        with mock.patch.object(self.downloads.downloader.__class__, 'dump',
                               return_value=fake_dump):
            self.assertEqual(
                self.downloads.get_active(),
                [src1])

    def test_handle_unexpected_remove_from_plugin_as_cancel(self):
        src1 = build_source('foo')
        src2 = build_source('bar')

        self.downloads.add(src1)
        self.downloads.add(src2)
        self.wait()

        fake_dump = [
            {'id': self.downloads.db.downloads.external_for_source(src1),
             'state': State.DOWNLOADING},
        ]
        with mock.patch.object(self.downloads.downloader.__class__, 'dump',
                               return_value=fake_dump):

            self.assertEqual(
                self.downloads.get_active(),
                [src1])

            with self.assertRaises(NotFoundError):
                self.downloads.get_state(src2)

    def test_handle_unexpected_remove_from_plugin_as_archive(self):
        src1 = build_source('foo')
        src2 = build_source('bar')

        self.downloads.add(src1)
        self.downloads.add(src2)
        self.wait()

        # Manually update state of src2
        self.downloads.db.downloads.set_state(src2, State.SHARING)

        # Mock plugin list to not list src2
        fake_dump = [
            {'id': self.downloads.db.downloads.external_for_source(src1),
             'state': State.DOWNLOADING}
        ]

        with mock.patch.object(self.downloads.downloader.__class__, 'dump',
                               return_value=fake_dump):
            self.assertEqual(
                self.downloads.get_state(src2),
                State.ARCHIVED
            )

    def test_ignore_duplicated_entity(self):
        s1 = build_item('foo.2019.S01E01.720p.mkv')
        s2 = build_item('foo.2019.S01E01.1080p.mkv')

        self.downloads.add(s1)
        self.downloads.add(s2)

        self.assertEqual(
            self.downloads.get_active(),
            [s1, s2]
        )

        self.assertEqual(
            self.downloads.db.downloads.sources_for_entity(s1.entity),
            [s1, s2])


class TransmissionTest(DownloaderTestMixin, unittest.TestCase):
    DOWNLOADER_SPEC = ('downloaders.transmission',
                       'arroyo.plugins.downloaders.transmission.Tr')
    SLOWDOWN = 0.2

    def tearDown(self):
        transmission = self.downloads.downloader.client

        for x in transmission.get_torrents():
            if 'foo' in x.name or 'bar' in x.name:
                transmission.remove_torrent(x.id, delete_data=True)

        self.wait()
        super().tearDown()

# class DirectoryTest(DownloaderTestMixin, unittest.TestCase):
#     # TODO:
#     # - Set storage path to tmpdir

#     PLUGINS = ['downloaders.directory']
#     DOWNLOADER = 'directory'
#     SLOWDOWN = 0.2

#     def setUp(self):
#         super().setUp()
#         cls = self.plugin_class()
#         cls._fetch_torrent = mock.Mock(return_value=b'')


if __name__ == '__main__':
    unittest.main()
