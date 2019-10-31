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


from arroyo import Sorter


import functools
import itertools
import sys


class Basic(Sorter):
    def cmp_source_health(self, a, b):
        def is_proper(item):
            return item.metadata.get('core.release.proper', False)

        def has_release_group(item):
            return item.metadata.get('core.release.group', None) is not None

        def seeds_are_relevant(item):
            return (item.source.seeds or 0) > 10

        def share_ratio(item):
            seeds = item.source.seeds or 0
            leechers = item.source.leechers or 0

            if not item.source.seeds and not item.source.leechers:
                return None

            if seeds and (leechers == 0):
                return float(sys.maxsize)

            if (seeds == 0) and leechers:
                return 0.0

            return seeds / leechers

        # proper over non-proper
        a_is_proper = is_proper(a)
        b_is_proper = is_proper(b)

        if a_is_proper and not b_is_proper:
            return -1

        if b_is_proper and not a_is_proper:
            return 1

        #
        # Priorize s/l info over others
        #
        if seeds_are_relevant(a) and not seeds_are_relevant(b):
            return -1

        if seeds_are_relevant(b) and not seeds_are_relevant(a):
            return 1

        #
        # Order by seed ratio
        #
        sr_a = share_ratio(a)
        sr_b = share_ratio(b)
        sr_diff = abs(sr_a - sr_b)
        percent20 = (sr_a + sr_b) / 2 * 0.2

        if sr_diff > percent20:
            if sr_a > sr_b:
                return -1
            else:
                return 1

        # if (a.source.leechers and b.source.leechers):
        #     try:
        #         balance = (max(a.share_ratio, b.share_ratio) /
        #                    min(a.share_ratio, b.share_ratio))
        #         if balance > 1.2:
        #             return -1 if a.share_ratio > b.share_ratio else 1

        #     except ZeroDivisionError:
        #         return -1 if int(a.share_ratio) else 1

        #     return -1 if a.seeds > b.seeds else 1

        #
        # Put releases from a team over others
        #
        a_has_release_team = has_release_group(a)
        b_has_release_team = has_release_group(b)

        if a_has_release_team and not b_has_release_team:
            return -1
        if b_has_release_team and a_has_release_team:
            return 1

        # Retry with pure seeds
        if b.source.seeds > a.source.seeds:
            return 1

        return -1

    def sort(self, items):
        m = {}

        for item in items:
            if item.entity not in m:
                m[item.entity] = []

            m[item.entity].append(item)

        for entity in m:
            if entity is None:
                continue

            m[entity] = sorted(
                m[entity],
                key=functools.cmp_to_key(self.cmp_source_health))

        return list(itertools.chain.from_iterable((m[k] for k in m)))
