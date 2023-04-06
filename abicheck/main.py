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
import sys
import os

sys.path.append(os.path.dirname(os.getcwd()))
from abicheck import binhandler, toolopts, utils

loggerinst = logging.getLogger("abicheck")


def main():
    """Perform all steps for the entire conversion process."""

    utils.require_root()

    # handle command line arguments
    cli = toolopts.CLI()
    cli.process_cli_options()

    # check cmd
    utils.check_cmd(binhandler.ABI_CC)
    utils.check_cmd(binhandler.ABI_DUMPER)
    utils.check_cmd(binhandler.READELF)
    utils.check_cmd(binhandler.RPM2CPIO)
    utils.check_cmd(binhandler.DOT)
    utils.check_cmd(binhandler.CONVERT)

    checker = binhandler.ABI()

    checker.gen_elf_info()
    checker.gen_ldd_info()
    checker.gen_soname_file()

    # old
    checker.get_old_os_main_pkgs()
    checker.get_old_devel_pkgs()
    checker.get_old_libs_pkgs()
    checker.download_old_packages()
    checker.decompress_old_packages()
    checker.gen_old_xml()
    checker.gen_old_dump()

    # new
    checker.get_new_os_main_pkgs()
    checker.get_new_devel_pkgs()
    checker.get_new_libs_pkgs()
    checker.download_new_packages()
    checker.decompress_new_packages()
    checker.gen_new_xml()
    checker.gen_new_dump()

    # diff
    checker.diff_dump()

    # library depdency
    checker.gen_soname_deppng()
    checker.gen_rpm_deppng()

    checker.add_deptab()

    # show result
    checker.show_html()


if __name__ == "__main__":

    sys.exit(main())
