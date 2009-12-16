#!/usr/bin/python -tt
# vim: sw=4 ts=4 expandtab ai
#
# python-scratchbox - python API for scratchbox2
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
Scratchbox v.2 python API
"""

import os
import urllib
import time
import re
import shutil
import socket
import stat
import logging
import md5

from urlparse import urlparse
from tarfile import TarFile

from scratchbox.common import Scratchbox, SBError, run_command

class ToolsRootstrap(object):
    """Represents tools rootstraps for Scratchbox2."""

    basedir = "/opt/maemo/tools-rootstraps"

    def __init__(self, tools_url):
        """Constructor."""

        self.tools_url = tools_url
        self.tools_dir = None
        _, self.netloc, path, _, _, _ = urlparse(tools_url)
        if not self.netloc and os.path.isdir(path):
            self.tools_dir = path

        if path.endswith("/"):
            path = path[:-1]
        self.name = os.path.basename(path)
        self.logger = logging.getLogger(__name__)

    def __download(self, tools_dir):
        """Download and extract tools rootstrap unconditionly."""

        tmp_tools_dir = tools_dir + ".tmp"
        os.makedirs(tmp_tools_dir)
        self.create_lock(tmp_tools_dir)
        self.logger.debug("Fetching %s-rootstrap.tgz" % self.name)
        tmpfile_name, _ = urllib.urlretrieve(os.path.join(self.tools_url,
                                               self.name + "-rootstrap.tgz"))
        tarfile = TarFile.open(name=tmpfile_name, mode='r:gz')
        # python2.4 doesn't support extractall method for TarFile
        # tarfile.extractall(path=tools_dir + ".tmp")
        for member in tarfile:
            tarfile.extract(member, path=tmp_tools_dir)
        tarfile.close()
        os.rename(tmp_tools_dir, tools_dir)

    def download(self):
        """Download tools rootstrap."""

        if not self.netloc:
            raise SBError("Tools rootstrap is not remote. "
                                "No need to download")

        self.logger.debug("Fetching %s/%s.full" %
                          (self.tools_url, self.name))
        full = urllib.urlopen(os.path.join(self.tools_url, self.name + ".full"))
        # check if tools rootstrap exists in local cache already
        tools_url_md5 = md5.md5(self.tools_url).hexdigest()
        full_md5 = md5.md5(full.read()).hexdigest()
        full.close()
        tools_dir = os.path.join(self.basedir, tools_url_md5, full_md5)
        if not os.path.exists(tools_dir):
            # tools rootstrap doesn't exist yet

            # check if .tmp directory with rootstrap exists
            tmp_tools_dir = tools_dir + ".tmp"
            if os.path.exists(tmp_tools_dir):
                # check if .tmp directory was created by dead process
                pid_alive = None
                locks = [fname for fname in os.listdir(tmp_tools_dir)
                         if fname.endswith(".lock")]
                self.logger.debug("Found locks: %s" % locks)
                for lock in locks:
                    match = re.match("\w+@([\w\.-]+)\.(\d+)\.lock", lock)
                    if match:
                        pid = int(match.group(2))
                        self.logger.debug("Checking process %d..." % pid)
                        try:
                            os.kill(pid, 0)
                            pid_alive = pid
                            self.logger.debug("Living process found: %d" % pid)
                            break
                        except OSError, exobj:
                            if exobj.errno == 1:
                                pid_alive = pid
                                self.logger.debug("Living process found: %d" \
                                                  % pid)
                                break
                    else:
                        raise SBError("Lock doesn't match regex")
                if pid_alive: # wait for another process finishes downloading
                    timeout = 300
                    delta = 5
                    while timeout > 0:
                        time.sleep(delta)
                        timeout -= delta
                        if os.path.exists(tools_dir):
                            self.create_lock(tools_dir)
                            break
                    if timeout < 1:
                        raise SBError("Stopped to wait for tools"
                                            " rootstrap because of timeout")
                else: # re-download tools rootstrap
                    self.logger.debug("No living processes found: "
                                      "re-downloading tools rootstrap")
                    shutil.rmtree(tmp_tools_dir)
                    self.__download(tools_dir)
            else:
                self.__download(tools_dir)
        else:
            self.create_lock(tools_dir)

        self.tools_dir = tools_dir

    def create_lock(self, tools_dir):
        """Create lock file inside directory with tools rootstrap."""

        # remove locks created by dead processes.
        for lock in os.listdir(tools_dir):
            if not lock.endswith(".lock"):
                continue
            self.logger.debug("Checking the lock file '%s'" % lock)
            match = re.match("\w+@([\w\.-]+)\.(\d+)\.lock", lock)
            if match:
                pid = int(match.group(2))
                self.logger.debug("Checking process %d..." % pid)
                try:
                    os.kill(pid, 0)
                    self.logger.debug("Living process found: %d" % pid)
                    continue
                except OSError, exobj:
                    if exobj.errno == 1:
                        self.logger.debug("Living process found: %d" % pid)
                        continue
                    else:
                        self.logger.debug("OSError: %s" % exobj)
                abslock = os.path.join(tools_dir, lock)

                try:
                    ctime = os.stat(abslock)[stat.ST_CTIME]
                    if (time.time()) - ctime > 7200:
                        self.logger.debug("Removing outdated lock %s" % lock)
                        os.unlink(abslock)
                except OSError:
                    self.logger.error("Can't remove lock file %s "\
                                      "of a dead process" % abslock)
            else:
                raise SBError("Lock doesn't match regex")

        # create symlink <user@host.pid>.lock
        os.symlink("/dev/null", "%s/%s@%s.%d.lock" %
                   (tools_dir, os.environ["USER"], socket.gethostname(),
                    os.getpid()))

    def remove_lock(self):
        """Remove lock file from directory with tools rootstrap."""

        lock_file = "%s/%s@%s.%d.lock" % \
            (self.tools_dir, os.environ["USER"],
             socket.gethostname(), os.getpid())
        self.logger.debug("Removing lock file %s" % lock_file)
        if os.path.exists(lock_file):
            os.unlink(lock_file)

    def get_tools_dir(self):
        """Return path to directory with tools."""

        if not self.tools_dir:
            self.download()
        return self.tools_dir

class Scratchbox2(Scratchbox):
    """Scratchbox2 API."""

    sb1compat_dir = "/opt/maemo/tools/maemo-sdk/scratchbox1-compat"
    sb2init = "/usr/bin/sb2-init"
    dotdir = ".sb2-templates"
    sbdotdir = ".scratchbox2"
    sb2config = "/usr/bin/sb2-config"

    def __init__(self, target_name=""):
        Scratchbox.__init__(self, target_name)
        self.session = None
        self.target_params = {}
        self.target = {}
        self.exe = "/usr/bin/sb2"
        self.tools_rootstrap = None
        self.logger.debug("Scratchbox2 instance created.")

    def init_target(self, target_params, mode=None):
        """Init target."""

        cmdl = "-n "
        if mode:
            cmdl += "-m %s " % mode
        elif "mode" in target_params and target_params["mode"]:
            cmdl += "-m %s " % target_params["mode"]

        if "arch" in target_params and target_params["arch"]:
            cmdl += "-A %s " % target_params["arch"]
        if "tools" in target_params and target_params["tools"]:
            self.tools_rootstrap = ToolsRootstrap(target_params["tools"])
            cmdl += "-t %s " % self.tools_rootstrap.get_tools_dir()

        # there can be 2 parameters with the same meaning
        if "cputransp" in target_params and target_params["cputransp"]:
            cmdl += "-c %s " % target_params["cputransp"]
        elif "cpuemulator" in target_params and \
           target_params["cpuemulator"] != "none":
            cmdl += "-c %s " % target_params["cpuemulator"]

        cmdl += self.target_name + " "
        if "compiler" in target_params and target_params["compiler"]:
            cmdl += target_params["compiler"]

        return self.run(cmdl, self.get_targetdir(), self.sb2init)


    def setup(self, target_params, force=None):
        """Setup target."""

        self.logger.debug("setup target")
        self.target_params = target_params
        self.target_name = target_params["name"]

        targetdir = self.get_targetdir()
        if os.path.exists(targetdir):
            if force:
                shutil.rmtree(targetdir)
            else:
                return

        # create the directory and symlink compat files there
        self.logger.debug("Creating template: %s" % target_params["name"])
        os.makedirs(targetdir)
        os.symlink(self.sb1compat_dir, os.path.join(targetdir,
            os.path.basename(self.sb1compat_dir)))

        # init target
        self.init_target(target_params, mode="devel")

        # create session
        self.session = os.path.join(self.get_basedir(), self.sbdotdir,
                                    "session.%d" % os.getpid())
        cmdl = "-m devel -m emulate -c -t %s -S %s " % (target_params["name"],
                                                        self.session)
        if "mappings" in target_params and target_params["mappings"]:
            cmdl += "-M %s " % target_params["mappings"]
        cmdl += "/bin/true"

        return self.run(cmdl, directory=targetdir)

    def lstargets(self):
        """List targets."""
        try: # sb2 returns non-zero code when there are no targets found
            return self.run("-l 2>/dev/null", exe="sb2-config")[1].split("\n")
        except SBError:
            return ""

    def select(self, tname):
        """Make target default."""
        self.target_name = tname
        return self.run("-d %s" % tname, self.get_targetdir(tname),
                        self.sb2config)

    def tee(self, command, logfn, mode, bufsize=0):
        """Tee."""

        cmdl = "-r -m %s %s " % (mode, command)
        if self.session:
            cmdl = "-J %s %s" % (self.session, cmdl)
        return self._tee(cmdl, logfn, bufsize)

    def remove(self, tname):
        """Remove target."""

        self.logger.debug("Removing target '%s'" % tname)
        # remove session
        if self.session:
            self.run("-D %s" % self.session)

        # remove target itself and target configuration dirs
        for sdir in (self.dotdir, self.sbdotdir):
            tdir = os.path.join(self.get_basedir(), sdir, tname)
            if os.path.exists(tdir):
                shutil.rmtree(tdir)

    def superuser_tee(self, command, logfn, mode, bufsize=0):
        """Run command with root privileges."""

        cmdl = "-R %s " % command
        return self.tee(cmdl, logfn, mode, bufsize)

    def release(self):
        """Release acquired resources."""

        if self.tools_rootstrap:
            self.tools_rootstrap.remove_lock()

    def get_basedir(self):
        """Returns absolute path to scratchbox base directory."""
        return os.environ['HOME']

    def get_targetdir(self, target_name=None):
        """Returns absolute path to scratchbox target."""
        if not target_name:
            target_name = self.target_name
        return os.path.join(self.get_basedir(), self.dotdir, target_name)

    def get_homedir(self):
        """Returns absolute path to directory where build is done."""
        return os.path.join(self.get_basedir(), self.dotdir, self.target_name)

    def get_tmpdir(self):
        """Returns absolute path to scratchbox temporary directory."""
        return os.path.join(self.get_basedir(), self.dotdir,
                            self.target_name, "tmp")

    def get_sb_tmpdir(self):
        """Returns path to temporary directory inside scratchbox."""
        return "tmp"

    def get_sb_homedir(self):
        """Returns path to directory inside scratchbox where build is done."""
        return os.path.join(self.get_basedir(), self.dotdir, self.target_name)

    def get_superuser_cmd(self):
        """Returns superuser command used inside scratchbox."""
        return ""

    def get_mode_options(self, mode=Scratchbox.MODE_DEVEL):
        """Returns scratchbox options for a given mode."""

        if mode == self.MODE_DEVEL:
            return ""
        elif mode == self.MODE_EMUL:
            return "-eR"
        else:
            raise SBError("Unknown mode %s" % mode)

    def extract_rootstrap(self, rootstrap):
        """Extracts given local rootstrap into target."""

        cmd = "tar zxf %s" % rootstrap
        self.logger.debug("Executing the command: %s" % cmd)
        output = run_command(cmd, self.get_targetdir(self.target_name))
        self.logger.debug("Return status tar: \n%s" % output)
        os.symlink(self.sb1compat_dir, os.path.join(self.get_targetdir(\
            self.target_name), os.path.basename(self.sb1compat_dir)))

        self.init_target(self.target_params, mode="accel")

        return self.select(self.target_name)

    def create_target(self, name, params):
        """Creates target."""
        self.target_name = name
        self.target_params = params
        self.logger.debug("No need to create target. In SB2 target is "\
                          "initialised after rootstrap is unpacked.")

