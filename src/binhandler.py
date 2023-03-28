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

    def gen_soname_file(self):
        self.logger.info("Checking package dependencies ...")
        # list like  [ "EVP_DigestUpdate@OPENSSL_1_1_0" ]
        func_dynsym_list = list()
        # list like [ "EVP_DigestUpdate" ]
        func_dynsym_name_list = list()
        # list lke [ "OPENSSL_1_1_0" ]
        func_dynsym_ver_list = list()
        elf_file = os.path.join(self.output_dir, self.READELF_FILE)
        elf_text = utils.get_file_content(elf_file, as_list=True)
        elf_symbol_fmt = (
            " *(?P<num>[0-9]*): (?P<value>[0-9abcdef]*) (?P<size>[0-9]*).*(FUNC).*@.*"
        )

        for line in elf_text:
            m = re.match(elf_symbol_fmt, line)
            if not m:
                continue
            elf_line_list = re.split(r"\s+", line)
            if elf_line_list[7] not in func_dynsym_list:
                func_dynsym_list.append(elf_line_list[7])

            sym = elf_line_list[7].split("@")
            if sym[0] not in func_dynsym_name_list:
                func_dynsym_name_list.append(sym[0])

            if sym[1] not in func_dynsym_ver_list:
                func_dynsym_ver_list.append(sym[1])

        output_file = os.path.join(self.output_dir, self.FUNC_DYNSYM_FILE)
        self.logger.info(f"Writing file {output_file} ...")
        utils.store_content_to_file(output_file, func_dynsym_list)

        output_file = os.path.join(self.output_dir, self.FUNC_DYNSYM_NAME_FILE)
        self.logger.info(f"Writing file {output_file} ...")
        utils.store_content_to_file(output_file, func_dynsym_name_list)

        output_file = os.path.join(self.output_dir, self.FUNC_DYNSYM_VER_FILE)
        self.logger.info(f"Writing file {output_file} ...")
        utils.store_content_to_file(output_file, func_dynsym_ver_list)

        ldd_file = os.path.join(self.output_dir, self.LDD_FILE)
        ldd_text = utils.get_file_content(ldd_file, as_list=True)

        soname_file_list = list()
        for line in ldd_text:
            if not re.match(".*=>.*", line):
                continue
            soname = line.strip().split(" ")[0]
            if soname not in soname_file_list:
                soname_file_list.append(soname)
        self.required_sonames = soname_file_list
        self.logger.debug(
            f"The list of dynamic libraries that the {self.binfile}"
            f" binary requires is {self.required_sonames}."
        )

