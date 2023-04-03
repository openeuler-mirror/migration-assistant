# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import optparse
import os
import platform
import sys

import distro

from abicheck import __version__, utils
from abicheck.utils import mkdir_p

PROG = "abi-info-check"

SUPPORT_OS = (
    "centos_7.1",
    "centos_7.2",
    "centos_7.3",
    "centos_7.4",
    "centos_7.5",
    "centos_7.6",
    "centos_7.7",
    "centos_7.8",
    "centos_7.9",
)


class ToolOpts(object):
    def __init__(self):
        self.prog = PROG
        self.support_os = SUPPORT_OS

        self.debug = False
        self.disable_colors = False
        self.output_dir = "./abi-info-export"
        self.binfile = ""

        self.old_os_full_name = None
        # Old OS name (e.g. CentOS, UnionTech OS Server 20)
        self.old_os_name = None
        # Major verion of OS,(e.g. 7.1)
        self.old_os_version = None

        self.old_dnf_conf = ""

        self.new_os_id = distro.id()
        self.new_os_name = distro.name()
        self.new_os_version = distro.major_version()


class CLI(object):
    def __init__(self):
        self._parser = self._get_argparser()
        self._register_options()

    @staticmethod
    def _get_argparser():
        usage = (
            "\n"
            f"  {PROG} --help\n"
            f"  {PROG} --version\n"
            f"  {PROG} --input BINFILE --release OS_RELEASE"
            " [--output-dir DIR] [--debug] \n"
            "\n\n"
            "WARNING: The pre-migration operating system supported by the tool is"
            f" {SUPPORT_OS}"
            "\n"
            "WARNING: The tool needs to be run under the root user")
        return optparse.OptionParser(
            conflict_handler="resolve",
            usage=usage,
            add_help_option=False,
            version=__version__,
        )

    def _register_options(self):
        """Prescribe what command line options the tool accepts."""
        self._parser.add_option(
            "-h",
            "--help",
            action="help",
            help="Show help message and exit.",
        )
        self._parser.add_option(
            "-v",
            "--version",
            action="version",
            help=f"Show {PROG} version and exit.",
        )

        self._parser.add_option(
            "-i",
            "--input",
            metavar="BINFILE",
            help="Input binary file to be migrated.",
        )
        self._parser.add_option(
            "-r",
            "--release"
            metavar="OS_RELEASE",
            choices=SUPPORT_OS,
            help="Operating systems that support migration."
            f" supported OS.RELEASE is {SUPPORT_OS}",
        )
        self._parser.add_option(
            "-o",
            "--output-dir",
            metavar="DIR",
            help="Directory to save output file (default: ./abi-info-export)",
        )

        self._parser.add_option(
            "-d",
            "--debug",
            action="store_true",
            help=
            "Print traceback in case of an abnormal exit and messages that could help find an issue.",
        )
        self._parser.add_option(
            "--disable-colors",
            action="store_true",
            help=optparse.SUPPRESS_HELP,
        )

    def process_cli_options(self):
        """Process command line options used with the tool."""
        warn_on_unsupported_options()

        parsed_opts, _ = self._parser.parse_args()

        global tool_opts  # pylint: disable=C0103

        if parsed_opts.output_dir:
            tool_opts.output_dir = parsed_opts.output_dir
        if not os.path.exists(tool_opts.output_dir):
            mkdir_p(tool_opts.output_dir)
        from abicheck import logger
        logger.initialize_logger("abicheck.log", tool_opts.output_dir)
        loggerinst = logging.getLogger(__name__)
        loggerinst.info(f"The output-dir is {tool_opts.output_dir}.")

        if parsed_opts.debug:
            tool_opts.debug = True

        if parsed_opts.disable_colors:
            tool_opts.disable_colors = True

        if parsed_opts.release:
            tool_opts.old_os_full_name = parsed_opts.release
            tool_opts.old_os_name = tool_opts.old_os_full_name.split('_')[0]
            tool_opts.old_os_version = tool_opts.old_os_full_name.split('_')[1]
            arch = platform.machine()
            tool_opts.old_dnf_conf = f'{utils.DATA_DIR}/conf/{arch}/{tool_opts.old_os_full_name}.conf'
        else:
            loggerinst.critical(
            "Error: --release is required.")

        if parsed_opts.input:
            tool_opts.binfile = parsed_opts.input
            if not utils.isbinary(tool_opts.binfile):
                loggerinst.critical(
                    f"Error: {tool_opts.binfile} isn't a binary file.")

        else:
            loggerinst.critical(
            "Error: --input is required.")
            pass


def warn_on_unsupported_options():
    loggerinst = logging.getLogger(__name__)
    if any(x in sys.argv[1:] for x in ["--debuginfo"]):
        loggerinst.critical("The --debuginfo option is not supported.\n"
                            f"See {PROG} -h for more information.")


# Code to be executed upon module import
tool_opts = ToolOpts()  # pylint: disable=C0103
