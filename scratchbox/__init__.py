#!/usr/bin/python -tt
# vim: sw=4 ts=4 expandtab ai
#
# python-scratchbox - python API for scratchbox1
#
# Copyright (C) 2006-2009 Ed Bartosh <bartosh@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA
# 02110-1301 USA
#

"""
Scratchbox API. Factory.
"""


def scratchbox_factory(sbver=1):
    """Factory. Create scratchbox objects."""
    sbver = int(sbver)
    if sbver == 1:
        from scratchbox.sb1 import Scratchbox1
        return Scratchbox1()
    elif sbver == 2:
        from scratchbox.sb2 import Scratchbox2
        return Scratchbox2()
    else:
        from scratchbox.common import SBError
        raise SBError("Unknown version of scratchbox: %d" % sbver)
