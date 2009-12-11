#!/usr/bin/python -tt
# vim: sw=4 ts=4 expandtab ai
#
# python-scratchbox - python API for scratchbox
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

from setuptools import setup

def debpkgver(changelog = "debian/changelog"):
    return open(changelog).readline().split()[1][1:-1]

setup (name = "python-scratchbox",
    description="Python Scratchbox API.",
    version=debpkgver(),
    author="Ed Bartosh",
    author_email="bartosh@gmail.com",
    packages=['scratchbox'],
    license = "GPL",
)
