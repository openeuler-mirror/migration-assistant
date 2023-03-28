import logging
import os
import platform
import re
import shutil

import distro

from abicheck import utils
from abicheck.toolopts import tool_opts

ABI_CC = "abi-compliance-checker"
ABI_DUMPER = "abi-dumper"
READELF = "eu-readelf"
LDD = "ldd"
RPM2CPIO = "rpm2cpio"
DOT = "dot"
CONVERT = "convert"


class ABI:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.output_dir = tool_opts.output_dir

        self.binfile = os.path.abspath(tool_opts.binfile)
        self.basename = os.path.basename(self.binfile)
        self.arch = platform.machine()

        self.READELF_FILE = f"OLD_{self.basename}_readelf.info"
        self.LDD_FILE = f"OLD_{self.basename}_ldd.info"
        self.required_sonames = []

        self.old_os_full_name = tool_opts.old_os_full_name
        self.OLD_XML_FILE = f"OLD_{self.basename}.xml"
        self.OLD_DUMP_FILE = f"OLD_{self.basename}.dump"
        self.OLD_ABICC_LOG = f"{self.basename}_{self.old_os_full_name}.log"

        self.FUNC_DYNSYM_FILE = f"OLD_{self.basename}_func_dynsym.info"
        self.FUNC_DYNSYM_NAME_FILE = f"OLD_{self.basename}_func_dynsym_name.info"
        self.FUNC_DYNSYM_VER_FILE = f"OLD_{self.basename}_func_dynsym_version.info"
        self.old_required_rpm_pkgs = []
        self.old_required_rpm_devel_pkgs = []
        self.old_required_rpm_libs_pkgs = []
        self.old_dnf_conf = tool_opts.old_dnf_conf
        self.old_all_pkgs_list = utils.dnf_list(self.old_dnf_conf, self.arch)
        self.old_rpm_downloaddir = (
            f"{utils.TMP_DIR}/{self.old_os_full_name}/{self.arch}/Packages"
        )
        self.old_rpm_cpiodir = (
            f"{utils.TMP_DIR}/{self.old_os_full_name}/{self.arch}/chroot"
        )

        self.new_os_full_name = f"{distro.id()}_{distro.major_version()}"
        self.NEW_XML_FILE = f"NEW_{self.basename}.xml"
        self.NEW_DUMP_FILE = f"NEW_{self.basename}.dump"
        self.NEW_ABICC_LOG = f"{self.basename}_{self.new_os_full_name}.log"
        self.new_required_rpm_pkgs = []
        self.new_required_rpm_devel_pkgs = []
        self.new_required_rpm_libs_pkgs = []
        self.new_dnf_conf = "/etc/dnf/dnf.conf"
        self.new_all_pkgs_list = utils.dnf_list(self.new_dnf_conf, self.arch)
        self.new_rpm_downloaddir = (
            f"{utils.TMP_DIR}/{self.new_os_full_name}/{self.arch}/Packages"
        )
        self.new_rpm_cpiodir = (
            f"{utils.TMP_DIR}/{self.new_os_full_name}/{self.arch}/chroot"
        )
        self.DIFF_ABICC_LOG = (
            f"{self.basename}_{self.old_os_full_name}_{self.new_os_full_name}.log"
        )
        self.EXPORT_HTML_FILE = "export.html"

        self.OLD_SO_DOT_FILE = f"{self.basename}_{self.old_os_full_name}_so.dot"
        self.OLD_SO_PNG_FILE = f"{self.basename}_{self.old_os_full_name}_so.png"
        self.OLD_RPM_DOT_FILE = f"{self.basename}_{self.old_os_full_name}_rpm.dot"
        self.OLD_RPM_PNG_FILE = f"{self.basename}_{self.old_os_full_name}_rpm.png"
        self.so_dep_rpm_dict = dict()
        self.NOTFOUND = "Not Found"

    def gen_elf_info(self):
        self.logger.info(f"Checking ELF information of file {self.binfile} ...")
        output, _ = utils.run_subprocess(
            f"{READELF} -s {self.binfile}", print_output=False
        )

        output_file = os.path.join(self.output_dir, self.READELF_FILE)
        utils.store_content_to_file(output_file, output)

    def gen_ldd_info(self):
        self.logger.info(f"Checking ldd information of file {self.binfile} ...")
        output, _ = utils.run_subprocess(f"{LDD} {self.binfile}", print_output=False)

        output_file = os.path.join(self.output_dir, self.LDD_FILE)
        utils.store_content_to_file(output_file, output)

