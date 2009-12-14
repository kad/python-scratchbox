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
Scratchbox v.1 python API
"""

import os
import types
import re
import signal

from scratchbox.common import Scratchbox, SBError

class Scratchbox1(Scratchbox):
    """Scratchbox 1 API,"""

    def __init__(self, target_name=None):
        Scratchbox.__init__(self, target_name)
        self.exe = "/scratchbox/login"
        self.logger.debug("Scratchbox1 instance created.")

    def lstargets(self):
        """List targets."""
        return self.run("list --targets 2>/dev/null",
                        exe="sb-conf")[1].split("\n")

    def setup(self, target, force=None):
        """Setup target."""

        cmdl = ""
        for param in "compiler", "devkits", "cputransp":
            if param in target and target[param]:
                cmdl = "%s --%s %s" % (cmdl, param, target[param])

        if force:
            cmdl += " --force"
        cmdl = "sb-conf setup %s %s" % (target["name"], cmdl)
        self.logger.debug("setting up the target: %s" % cmdl)
        return self.run(cmdl)

    def reset(self, tname):
        """Reset target and put required libraries in place."""
        self.killall(signal.SIGTERM)
        self.run("sb-conf select %s" % tname)

        # check if we really selected target
        output = self.run('cat /targets/links/scratchbox.config')
        match = re.search("\n*SBOX_TARGET_NAME=(.+)\n*", output, re.M)
        if not match:
            self.logger.error("Can't find target in output: %s" % output)
            raise SBError("Failed to select target %s, exiting" % tname)
        if match.group(1) != tname:
            self.logger.error("Wrong target selected: %s instead of %s" % \
                              (match.group(1), tname))
            raise SBError("Failed to select target %s, exiting" % tname)
        return self.run("sb-conf reset %s --force" % tname)

    def select(self, tname):
        """Select target."""
        return self.run("sb-conf select %s" % tname)

    def remove(self, tname):
        """Remove target."""

        self.logger.debug("Removing target '%s'" % tname)
        # select another target
        for target in self.lstargets():
            if target != tname:
                self.select(target)
                break

        return self.run("sb-conf remove %s -f" % tname)

    def killall(self, sig=signal.SIGHUP):
        """Send signals to all processes inside scratchbox."""
        return self.run("sb-conf killall --signal=%d" % sig)

    def tee(self, command, logfn, mode, bufsize=0):
        """Tee."""
        return self._tee(command, logfn, bufsize)

    def superuser_tee(self, command, logfn, mode, bufsize=0):
        """Tee with root privileges."""

        return self.tee("fakeroot %s" % command, logfn, mode, bufsize)

    def get_basedir(self):
        """Returns absolute path to scratchbox base directory."""
        return os.path.join('/scratchbox/users', os.environ['USER'])

    def get_targetdir(self, target_name=None):
        """Returns absolute path to scratchbox target."""
        if target_name:
            self.select(target_name)
        return os.path.join(self.get_basedir(), 'targets', target_name)

    def get_homedir(self):
        """Returns absolute path to directory where build is done."""
        return os.path.join(self.get_basedir(), self.get_sb_homedir()[1:])

    def get_tmpdir(self):
        """Returns absolute path to scratchbox temporary directory."""
        return os.path.join(self.get_basedir(), "tmp")

    def get_sb_tmpdir(self):
        """Returns path to temporary directory inside scratchbox."""
        return "/tmp"

    def get_sb_homedir(self):
        """Returns path to directory inside scratchbox where build is done."""
        return os.path.join('/home', os.environ['USER'])

    def get_superuser_cmd(self):
        """Returns superuser command used inside scratchbox."""
        return "fakeroot"

    def extract_rootstrap(self, rootstrap):
        """Extracts given rootstrap into target."""

        (status, output) = self.run("sb-conf rs %s" % rootstrap, fatal=False)
        if output.find("_SBOX_RESTART_FILE") >= 0:
            # Workarround
            status = 0
        if status != 0:
            self.logger.debug("Error output: "+output)
            raise SBError, "Failed to extract rootstrap, exiting"

        return output

    def create_target(self, name, params):
        """Wrapper around self.setup() method adapting sbdmock parameters."""

        if 'compiler-name' not in params or not params['compiler-name']:
            raise SBError, "No compilers specified for target %s, exiting" \
                  % name
        if 'devkits' not in params or not params['devkits']:
            raise SBError, "No devkits specified for target %s, exiting" % name

        target = {'compiler': params['compiler-name'],
                  'devkits': params['devkits'],
                  'name': name}
        if 'cputransparency-method' in params and \
               params['cputransparency-method']:
            target['cputransp'] = params['cputransparency-method']
        self.setup(target, force = True)

    def install_files(self, files=("etc", "devkits")):
        """Installs into target Scratchbox files
           (etc, devkits, fakeroot, clibrary).
        """

        if files and isinstance(files, (types.TupleType, types.ListType) ):
            cmd_args = "sb-conf in --" + " --".join(files)
            self.run(cmd_args)
