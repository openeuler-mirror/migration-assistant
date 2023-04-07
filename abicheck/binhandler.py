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

    def get_old_os_main_pkgs(self):
        for soname in self.required_sonames:
            pkgs = utils.dnf_provides(
                self.old_dnf_conf, f"*{str(soname)}*", arch=self.arch
            )
            if pkgs:
                pkg = pkgs[0]
            else:
                continue
            if pkg not in self.old_required_rpm_pkgs:
                self.old_required_rpm_pkgs.append(pkg)
        self.logger.debug(
            f"The list of packages that the {self.binfile}"
            f" binary requires is {self.old_required_rpm_pkgs}."
        )

    def get_new_os_main_pkgs(self):
        for soname in self.required_sonames:

            pkgs = utils.dnf_provides(
                "/etc/dnf/dnf.conf", f"*{str(soname)}*", arch=self.arch
            )
            if pkgs:
                pkg = pkgs[0]
            else:
                self.so_dep_rpm_dict[f"{str(soname)}"] = [f"{self.NOTFOUND}"]
                continue
            self.so_dep_rpm_dict[f"{str(soname)}"] = pkgs
            if pkg and pkg not in self.new_required_rpm_pkgs:
                self.new_required_rpm_pkgs.append(pkg)
        self.logger.debug(
            f"The list of packages that the {self.binfile}"
            f" binary requires is {self.new_required_rpm_pkgs}."
        )

    @staticmethod
    def _get_rpmname_without_libs(x):
        x = re.sub("-libs$", "", x).strip()
        x = re.sub("-lib$", "", x).strip()
        return x

    def get_old_devel_pkgs(self):
        for line in self.old_required_rpm_pkgs:
            name = self._get_rpmname_without_libs(line)
            devel_name = f"{name}-devel"
            if devel_name in list(self.old_all_pkgs_list):
                self.old_required_rpm_devel_pkgs.append(devel_name)
            devel_name = f"{name}-headers"
            if devel_name in self.old_all_pkgs_list:
                self.old_required_rpm_devel_pkgs.append(devel_name)
        self.logger.debug(
            f"The list of devel packages that the {self.binfile}"
            f" binary requires is {self.old_required_rpm_devel_pkgs}."
        )

    def get_new_devel_pkgs(self):
        for line in self.new_required_rpm_pkgs:
            name = self._get_rpmname_without_libs(line)
            devel_name = f"{name}-devel"
            if devel_name in self.new_all_pkgs_list:
                self.new_required_rpm_devel_pkgs.append(devel_name)
            devel_name = f"{name}-headers"
            if devel_name in self.new_all_pkgs_list:
                self.new_required_rpm_devel_pkgs.append(devel_name)

        for line in self.old_required_rpm_devel_pkgs:
            if (
                line in self.new_all_pkgs_list
                and line not in self.new_required_rpm_devel_pkgs
            ):
                self.new_required_rpm_devel_pkgs.append(line)

        self.logger.debug(
            f"The list of devel packages that the {self.binfile}"
            f" binary requires is {self.new_required_rpm_devel_pkgs}."
        )

    def get_old_libs_pkgs(self):
        for line in self.old_required_rpm_pkgs:
            name = self._get_rpmname_without_libs(line)
            lib_name = f"{name}-lib"
            if lib_name in self.old_all_pkgs_list:
                self.old_required_rpm_libs_pkgs.append(lib_name)
            lib_name = f"{name}-libs"
            if lib_name in self.old_all_pkgs_list:
                self.old_required_rpm_libs_pkgs.append(lib_name)
        self.logger.debug(
            f"The list of libs packages that the {self.binfile}"
            f" binary requires is {self.old_required_rpm_libs_pkgs}."
        )

    def get_new_libs_pkgs(self):
        for line in self.new_required_rpm_pkgs:
            name = self._get_rpmname_without_libs(line)
            lib_name = f"{name}-lib"
            if lib_name in self.new_all_pkgs_list:
                self.new_required_rpm_libs_pkgs.append(lib_name)
            lib_name = f"{name}-libs"
            if lib_name in self.new_all_pkgs_list:
                self.new_required_rpm_libs_pkgs.append(lib_name)

        for line in self.old_required_rpm_libs_pkgs:
            if (
                line in self.new_all_pkgs_list
                and line not in self.new_required_rpm_libs_pkgs
            ):
                self.new_required_rpm_libs_pkgs.append(line)

        self.logger.debug(
            f"The list of libs packages that the {self.binfile}"
            f" binary requires is {self.new_required_rpm_libs_pkgs}."
        )

    def download_old_packages(self):
        """Download rpm packages with dnf download command"""
        if not os.path.exists(self.old_dnf_conf):
            self.logger.critical(f"No such file {self.old_dnf_conf}, please check.")
        if not os.path.exists(self.old_rpm_downloaddir):
            utils.mkdir_p(self.old_rpm_downloaddir)
        cmd = f"dnf -c {self.old_dnf_conf} download"
        cmd += " --resolve --alldeps"
        cmd += f" --arch {self.arch}"
        cmd += f" --downloaddir {self.old_rpm_downloaddir}"
        all_pkgs = self.old_required_rpm_pkgs + self.old_required_rpm_devel_pkgs
        pkgs = ""
        for pkg in all_pkgs:
            pkgs += f" {pkg}"
        cmd = cmd + pkgs
        self.logger.info(
            "The program will automatically download"
            f" packages {pkgs} to directory {self.old_rpm_downloaddir}."
        )

        utils.run_subprocess(cmd, print_cmd=True, print_output=True)

    def download_new_packages(self):
        """Download rpm packages with dnf download command"""
        if not os.path.exists(self.new_dnf_conf):
            self.logger.critical(f"No such file {self.new_dnf_conf}, please check.")
        if not os.path.exists(self.new_rpm_downloaddir):
            utils.mkdir_p(self.new_rpm_downloaddir)
        cmd = f"dnf -c {self.new_dnf_conf} download"
        cmd += " --resolve --alldeps"
        cmd += f" --arch {self.arch}"
        cmd += f" --downloaddir {self.new_rpm_downloaddir}"
        all_pkgs = self.new_required_rpm_pkgs + self.new_required_rpm_devel_pkgs
        all_pkgs += self.new_required_rpm_libs_pkgs
        pkgs = ""
        for pkg in all_pkgs:
            pkgs += f" {pkg}"
        cmd = cmd + pkgs
        self.logger.info(
            "The program will automatically download"
            f"packages {pkgs} to directory {self.new_rpm_downloaddir}"
        )
        utils.run_subprocess(cmd, print_cmd=True, print_output=True)

    def decompress_old_packages(self):
        src = self.old_rpm_downloaddir
        dst = self.old_rpm_cpiodir
        if not os.listdir(src):
            self.logger.critical(f"Can not find rpm packages in" f" {src}.")
        if not os.path.exists(dst):
            utils.mkdir_p(dst)

        # pushd dest dir
        cwd = os.getcwd()
        os.chdir(dst)

        for parent, _, filenames in os.walk(src):
            filenames[:] = (f for f in filenames if f.endswith(".rpm"))

        self.logger.info(f"Decompressing packages to {dst} ...")
        for filename in filenames:
            filename = os.path.join(parent, filename)
            cmd = f"rpm2cpio {filename} | cpio -dim"
            utils.run_cmd(cmd, print_cmd=False)
        self.logger.info(f"Decompression completed.")
        # popd dest dir
        os.chdir(cwd)

    def decompress_new_packages(self):
        src = self.new_rpm_downloaddir
        dst = self.new_rpm_cpiodir
        if not os.listdir(src):
            self.logger.critical(f"Can not find rpm packages in" f" {src}.")
        if not os.path.exists(dst):
            utils.mkdir_p(dst)

        # pushd dest dir
        cwd = os.getcwd()
        os.chdir(dst)

        for parent, _, filenames in os.walk(src):
            filenames[:] = (f for f in filenames if f.endswith(".rpm"))

        self.logger.info(f"Decompressing packages to {dst} ...")
        for filename in filenames:
            filename = os.path.join(parent, filename)
            cmd = f"rpm2cpio {filename} | cpio -dim"
            utils.run_cmd(cmd, print_cmd=False)
        self.logger.info(f"Decompression completed.")
        # popd dest dir
        os.chdir(cwd)

    @staticmethod
    def _gen_xml(
        file,
        os_version,
        dev_pkgs,
        libs_pkgs,
        required_soname,
        rpm_dir,
        sysroot="",
        installed=True,
    ):

        loggerinst = logging.getLogger(__name__)
        loggerinst.info(f"Generating xml file {file}")

        header_file_list = list()
        libs_file_list = list()
        for pkg in dev_pkgs:
            cmd = f"rpm -ql"
            if installed:
                cmd += f" {pkg}"
            else:
                cmd += f" -p {rpm_dir}/{pkg}*"
            cmd += " |grep .*include.*\.h$"
            returncode, stdout, _ = utils.run_cmd(cmd, print_cmd=False)
            if returncode == 0 and stdout:
                for line in stdout.decode().strip("\n").split("\n"):
                    header_file_list.append(sysroot + line + "\n")

        for soname in required_soname:
            for pkg in libs_pkgs:
                cmd = f"rpm -ql"
                if installed:
                    cmd += f" {pkg}"
                else:
                    cmd += f" -p {rpm_dir}/{pkg}*"
                cmd += f"| grep {soname}$"
                returncode, stdout, _ = utils.run_cmd(cmd, print_cmd=False)

                if returncode == 0 and stdout:
                    for line in stdout.decode().rstrip("\n").split("\n"):
                        libs_file_list.append(sysroot + line + "\n")

        loggerinst.info(f"Finish generating the xml {file}")

        with open(file, "w") as f:
            f.write("<version>\n")
            f.write(f"{os_version}\n")
            f.write("</version>\n")

            f.write("<headers>\n")
            f.writelines(header_file_list)
            f.write("</headers>\n")

            f.write("<libs>\n")
            f.writelines(libs_file_list)
            f.write("</libs>\n")

    def gen_old_xml(self):
        file = os.path.join(self.output_dir, self.OLD_XML_FILE)
        os_version = self.old_os_full_name
        dev_pkgs = self.old_required_rpm_devel_pkgs
        libs_pkgs = self.old_required_rpm_pkgs
        required_soname = self.required_sonames
        rpm_dir = self.old_rpm_downloaddir
        sysroot = self.old_rpm_cpiodir

        self._gen_xml(
            file,
            os_version,
            dev_pkgs,
            libs_pkgs,
            required_soname,
            rpm_dir,
            sysroot=sysroot,
            installed=False,
        )

    def gen_new_xml(self):
        file = os.path.join(self.output_dir, self.NEW_XML_FILE)
        os_version = self.new_os_full_name
        dev_pkgs = self.new_required_rpm_devel_pkgs
        libs_pkgs = self.new_required_rpm_pkgs + self.new_required_rpm_libs_pkgs
        required_soname = self.required_sonames
        rpm_dir = self.new_rpm_downloaddir
        sysroot = self.new_rpm_cpiodir

        self._gen_xml(
            file,
            os_version,
            dev_pkgs,
            libs_pkgs,
            required_soname,
            rpm_dir,
            sysroot=sysroot,
            installed=False,
        )

    @staticmethod
    def _gen_dump(name, num, xml, dump, log):
        loggerinst = logging.getLogger(__name__)
        loggerinst.info(f"Generating dump file {dump}")
        cmd = f"{ABI_CC} -l {name}"
        cmd += f" -vnum {num}"
        cmd += f" -dump {xml}"
        cmd += f" -dump-path {dump}"
        cmd += f" -log-path {log}"
        utils.run_cmd(cmd, print_cmd=True)
        loggerinst.info(f"Finish generating dump file {dump}")

    def gen_old_dump(self):

        name = self.basename
        num = self.old_os_full_name
        xml_file = os.path.join(self.output_dir, self.OLD_XML_FILE)
        dump_file = os.path.join(self.output_dir, self.OLD_DUMP_FILE)
        log_file = os.path.join(self.output_dir, self.OLD_ABICC_LOG)

        self._gen_dump(name, num, xml_file, dump_file, log_file)

    def gen_new_dump(self):

        name = self.basename
        num = self.new_os_full_name
        xml_file = os.path.join(self.output_dir, self.NEW_XML_FILE)
        dump_file = os.path.join(self.output_dir, self.NEW_DUMP_FILE)
        log_file = os.path.join(self.output_dir, self.NEW_ABICC_LOG)

        self._gen_dump(name, num, xml_file, dump_file, log_file)

    def diff_dump(self):
        name = self.basename
        new_dump = os.path.join(self.output_dir, self.NEW_DUMP_FILE)

        old_dump = os.path.join(self.output_dir, self.OLD_DUMP_FILE)
        log_file = os.path.join(self.output_dir, self.DIFF_ABICC_LOG)
        sym_list = os.path.join(self.output_dir, self.FUNC_DYNSYM_NAME_FILE)
        html = os.path.join(self.output_dir, self.EXPORT_HTML_FILE)

        self.logger.info(f"Comparing dump file {old_dump} and {new_dump} ...")
        cmd = f"{ABI_CC} -l {name}"
        cmd += f" -old {old_dump}"
        cmd += f" -new {new_dump}"
        cmd += f" --symbols-list {sym_list}"
        cmd += f" --report-path {html}"
        cmd += f" -log-path {log_file}"

        utils.run_cmd(cmd)
        self.logger.info(f"Finished Comparison.")

    def gen_soname_deppng(self):

        png_file = os.path.join(self.output_dir, self.OLD_SO_PNG_FILE)
        dot_file = os.path.join(self.output_dir, self.OLD_SO_DOT_FILE)
        file = self.binfile
        self.logger.info(
            f"The so running dependency graph for {file} is being generated..."
        )
        with open(dot_file, "w", encoding="utf-8") as f:
            f.write("digraph graphname {\n")
            graphs_attrs = """
            ranksep = "1 equally"
            nodesep=0.15
            smoothing=triangle
            splines=curved
            size="15,8";
            dpi="100";
            """
            f.write(f"{graphs_attrs}")
            # node [shape=record fontsize=28]
            # ranksep = 1
            # nodesep=0.1
            node_attrs = "node "
            node_attrs += "["
            node_attrs += "shape=record,"
            node_attrs += "fontsize=22,"
            node_attrs += "fixedsize=true,"
            node_attrs += "width=2.8,"
            node_attrs += "height=0.35,"
            node_attrs += "style=filled,"
            node_attrs += "]"

            f.write(f"{node_attrs}\n")

            _dep(f, file)
            f.write("}\n")

        cmd = f"{DOT} -Tpng -o {png_file} {dot_file}"
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)
        cmd = f"{CONVERT} {png_file} -gravity center -background white -extent 1500x800 {png_file}"
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)
        self.logger.info(f"The so run dependency graph {png_file} has been generated")

    def gen_rpm_deppng(self):

        png_file = os.path.join(self.output_dir, self.OLD_RPM_PNG_FILE)
        dot_file = os.path.join(self.output_dir, self.OLD_RPM_DOT_FILE)
        file = self.binfile
        self.logger.info(
            f"The rpm running dependency graph for {file} is being generated..."
        )
        with open(dot_file, "w", encoding="utf-8") as f:
            f.write("digraph graphname {\n")
            nodesep = 0.05
            graphs_attrs = f"""
            concentrate = true;
            ranksep = 2;
            nodesep = {nodesep};
            rankdir = LR;
            splines = ortho;
            size="15,8!";
            dpi=100;
            """
            node_w = 2.8
            node_h = 0.35
            node_attrs = "node "
            node_attrs += "["
            node_attrs += "shape=record,"
            node_attrs += "fontsize=22,"
            node_attrs += "fixedsize=true,"
            node_attrs += f"width={node_w},"
            node_attrs += f"height={node_h},"
            node_attrs += "style=filled,"
            node_attrs += "]"
            f.write(f"{graphs_attrs}\n")
            f.write(f"{node_attrs}\n")
            if len(self.required_sonames) > 0:
                ibox_h = (len(self.required_sonames) - 1) * (node_h + nodesep) - (
                    nodesep * 2
                )
                f.write(f'i [shape=box, label="", width=0, height={ibox_h}];\n')
                f.write(f'"{self.basename}":e -> i [arrowhead="none"];\n')
            for so in self.required_sonames:
                f.write(f'i -> "{so}":w;\n')
            for soname in self.so_dep_rpm_dict.keys():
                for pkg in self.so_dep_rpm_dict[soname]:
                    if pkg == self.NOTFOUND:
                        f.write(f'"{self.NOTFOUND}"[fillcolor="red"];\n')
                        f.write(f'"{soname}" -> "{self.NOTFOUND}";\n')
                    else:
                        f.write(f'"{soname}" -> "{pkg}.rpm";\n')
            f.write("}\n")

        cmd = f"{DOT} -Tpng -o {png_file} {dot_file}"
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)
        cmd = f"{CONVERT} {png_file} -gravity center -background white -extent 1500x800 {png_file}"
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)
        self.logger.info(f"The rpm run dependency graph {png_file} has been generated")

    def add_deptab(self):

        html_file = os.path.join(self.output_dir, self.EXPORT_HTML_FILE)
        self.logger.info(f"Generating html file {html_file}")

        substr = r"\n<a id='LibGraphID' href='#LibGraphTab' style='margin-left:3px' class='tab disabled'>"
        substr += "Library<br/>Dependency</a>"
        substr += r"\n<a id='PkgGraphID' href='#PkgGraphTab' style='margin-left:3px' class='tab disabled'>"
        substr += "Package<br/>Dependency</a>"

        str = "Source<br/>Compatibility</a>"
        cmd = f"""sed -i "s@{str}@{str}{substr}@g" {html_file}"""
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)

        substr = r"<div id='LibGraphTab' class='tab'>\n"
        substr += f"<div style='text-align:center;vertical-align:middle;'>"
        substr += f"<img style='margin: auto; max-width:90%; max-height: 90%; background-color: hsl(0, 0%, 100%)' src='{self.OLD_SO_PNG_FILE}'>"
        substr += r"</div></div>\n"

        substr += r"</div><div id='PkgGraphTab' class='tab'>\n"
        substr += f"<div style='text-align:center;vertical-align:middle;'>"
        substr += f"<img style='margin: auto; max-width:90%; max-height: 90%; background-color: hsl(0, 0%, 100%)' src='{self.OLD_RPM_PNG_FILE}'>"
        substr += r"</div></div>\n"

        str = "<div class='footer'"
        cmd = f"""sed -i "s@{str}@{substr}{str}@g" {html_file}"""
        utils.run_subprocess(cmd, print_cmd=False, print_output=False)

        self.logger.info(f"Complete generation.")

    def show_html(self):
        html_file = os.path.join(self.output_dir, self.EXPORT_HTML_FILE)
        self.logger.info(f"The check result is {os.path.abspath(html_file)}")

    def clean_cache(self):
        cache_dir = '/tmp/abi-info-check-cache'
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

# get the libs prog depends on and write the results into opened file f
analyzedlist = []


def _dep(f, prog):
    # one lib may be used by several users
    if prog in analyzedlist:
        return
    else:
        analyzedlist.append(prog)

    pname = prog.split("/")[-1]
    needed = os.popen("ldd " + prog)
    neededso = re.findall(r"[>](.*?)[(]", needed.read())
    for so in neededso:
        if len(so.strip()) > 0:
            f.write('"' + pname + '" -> "' + so.split("/")[-1] + '";\n')
            _dep(f, so)
