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

"""
Scratchbox API. Common classes.
"""

import os
import popen2
import signal
import pwd
import logging

from commands import getstatusoutput

class SBError(Exception):
    """ Error generated in case of problems with Scratchbox """
    pass

def run_command(command, directory = None, fatal = True):
    """ Runs command. Chdir to directory if specified """

    if directory:
        savedir = os.getcwd()
        os.chdir(directory)

    (status, output) = getstatusoutput(command)

    if directory:
        os.chdir(savedir)

    if status and fatal:
        raise SBError("Error running command %s\nExit code: %d\nOutput: %s"
                % (command, status, output))

    if fatal:
        return output
    else:
        return (status, output)

class Scratchbox(object):
    """Base class."""

    MODE_DEVEL = "devel"
    MODE_EMUL = "emulation"

    def __init__(self, target_name=None):
        self.user = pwd.getpwuid(os.geteuid())[0]
        self.exe = None
        self.target_name = target_name
        self.logger = logging.getLogger(__name__)
        if target_name:
            self.select(target_name)

    def killall(self, sig=signal.SIGHUP):
        """Send signal to all sb processes."""
        pass

    def run(self, command, directory=None, exe=None, fatal=True):
        """Run command inside scratchbox."""
        if not exe:
            exe = self.exe
        self.logger.debug("running command: %s %s" % (exe, command))
        return run_command("%s %s" % (exe, command), directory, fatal=fatal)

    def extract_rootstrap(self, rootstrap):
        """Extracts given rootstrap into target."""
        raise NotImplementedError

    def _tee(self, command, logfn, bufsize=0):
        """Run command on pipe. redirect stdout and stderr to log file.
            Return: exit code of the command.
        """

        self.logger.debug("_tee: running %s %s log: %s" % \
                (self.exe, command, logfn))
        pipe = popen2.Popen4("%s %s </dev/null" % (self.exe, command))
        logfd = open(logfn, "w", bufsize)

        pipe.tochild.close()

        while True:
            line = pipe.fromchild.readline()
            if not line:
                break
            logfd.write(line)

        pipe.fromchild.close()
        logfd.close()

        status = pipe.wait()
        if os.WIFEXITED(status):
            return os.WEXITSTATUS(status)

        return -1

    def select(self, tname):
        """Select target."""
        raise NotImplemented

    def release(self):
        """Release acquired resources."""
        pass

    def reset(self, tname):
        """Reset target and put required libraries in place."""
        pass

    def get_basedir(self):
        """Returns absolute path to scratchbox base directory."""
        raise NotImplementedError

    def get_targetdir(self, tname=None):
        """Returns absolute path to scratchbox target."""
        raise NotImplementedError

    def get_homedir(self):
        """Returns absolute path to directory where build is done."""
        raise NotImplementedError

    def get_sb_homedir(self):
        """Returns path to directory inside scratchbox where build is done."""
        raise NotImplementedError

    def get_superuser_cmd(self):
        """Returns superuser command used inside scratchbox."""
        raise NotImplementedError

    def get_sb_tmpdir(self):
        """Returns path to temporary directory inside scratchbox."""
        raise NotImplementedError

    def get_mode_options(self, mode=None):
        """Returns scratchbox options for a given mode."""
        return ""

    def install_files(self, files=None):
        """Installs into target Scratchbox extra file."""
        pass

    def pull_dir(self, sb_dir, host_dir):
        """Move directory from scratchbox env to specified host folder."""
        pass
