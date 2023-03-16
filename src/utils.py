# -*- coding: utf-8 -*-

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
import os
import re
import stat
import subprocess
import sys

import xml.etree.ElementTree as ET
import pandas as pd

def run_cmd(cmd):
    '''
    run command in subprocess and return exit code, output, error.
    '''
    os.putenv('LANG', 'C')
    os.putenv('LC_ALL', 'C')
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    cmd = cmd.encode('UTF-8')
    proc = subprocess.Popen(cmd, shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            )
    (stdout, stderr) = proc.communicate()
    returncode = proc.returncode
    return (returncode, stdout, stderr)

def find_devel_lib_package(export_dir):
    print('Checking the dependency ...')
    file = f'{export_dir}/OLD-pkgs.info'
    if not os.access(f'{file}', os.R_OK):
        exit_status(
            "Error", f"The info file {file} can't be read. Please check")

    dev_pkgs_set = set()
    libs_pkgs_set = set()
    dbginfo_pkgs_set = set()
    with open(file, 'r') as f:
        for line in f:
            rpm_name = get_rpmname_without_libs(line)
            dev_pkgs_set.add(f'{rpm_name}-devel')
            dbginfo_pkgs_set.add(f'{rpm_name}-debuginfo')
            # 包名中包含 lib 关键字的包，本身就是 lib 包
            if 'lib' not in rpm_name:
                libs_pkgs_set.add(f'{rpm_name}-libs')
            else:
                libs_pkgs_set.add(f'{rpm_name}')
    return dev_pkgs_set, libs_pkgs_set, dbginfo_pkgs_set

def try_install_packages(dev_pkgs, libs_pkgs=set()):
    not_installed_pkgs = set()

    dev_pkgs = set(dev_pkgs) | set(libs_pkgs)
    for pkg in dev_pkgs:
        cmd = f'rpm -q {pkg}'
        returncode, stdout, stderr = run_cmd(cmd)
        if returncode != 0:
            print(f"It seems that the OS doesn't install {pkg}")
            not_installed_pkgs.add(pkg)
        else:
            print(f'The packages "{pkg}" have been installed')

    install_failed_pkgs = set()
    for pkg in not_installed_pkgs:
        cmd = f'yum install -y {pkg}'
        print(f'Trying to install package {pkg} with yum')
        returncode, stdout, stderr = run_cmd(cmd)
        if returncode != 0:
            print(f"Can't install {pkg}, with yum")
            install_failed_pkgs.add(pkg)
        else:
            print(f'Successfully installed {pkg} with yum')

    if install_failed_pkgs:
        exit_status(
            "Error", f'Please install {install_failed_pkgs}, then retry')


def gen_xml_and_dump(abi_name, target_path, dev_pkgs_set, libs_pkgs_set):
    headers_list = list()
    for pkg in dev_pkgs_set:
        cmd = f'rpm -ql {pkg} | grep .*include.*\.h$'
        returncode, stdout, stderr = run_cmd(cmd)
        headers_list.append(stdout.decode())

    libs_list = list()
    for pkg in libs_pkgs_set:
        cmd = f'rpm -ql {pkg} | grep .*lib.*\.so\.*$'
        returncode, stdout, stderr = run_cmd(cmd)
        libs_list.append(stdout.decode())

    file = f'{target_path}/NEW-dump.xml'
    with open(file, 'wt+') as f:
        f.write("<version>\n")
        f.write('1.0\n')
        f.write('</version>\n')

        f.write("<headers>\n")
        f.writelines(headers_list)
        f.write("</headers>\n")

        f.write("<libs>\n")
        f.writelines(libs_list)
        f.write("</libs>\n")
    dump_file = f'{target_path}/NEW-abi.dump'
    cmd = f'abi-compliance-checker -xml -l {abi_name} -dump {file} -dump-path {dump_file}'
    print(f'Analyzing the symbols of {libs_pkgs_set} ...')
    run_cmd(cmd)

    return dump_file

def compare_syms(export_dir, dump_file):
    print('Checking symbol differences ...')
    elf_sym_set = set()
    elf_file = f'{export_dir}/OLD-elf.info'
    with open(f'{elf_file}', 'rt') as f:
        elf_symbol_fmt = ' *(?P<num>[0-9]*): (?P<value>[0-9abcdef]*) (?P<size>[0-9]*).*(FUNC).*@.*'
        for line in f:
            m = re.match(elf_symbol_fmt, line)
            if not m:
                continue
            elf_line_list = re.split(r'\s+', line.strip())
            sym = elf_line_list[7].split('@')[0]

            elf_sym_set.add(sym)

    library_sym_list = set()

    with open(f'{dump_file}', 'r') as file:
        context = file.read().replace('& ', '')

    with open(f'{dump_file}', 'w+') as file:
        file.writelines(context)

    tree = ET.parse(f'{dump_file}')
    for line in tree.iterfind('symbols/library/symbol'):
        sym = line.text.split('@@')[0]
        library_sym_list.add(sym)
        diff_syms_list = list((elf_sym_set - library_sym_list))
        old_syms_list = list(elf_sym_set)

    return [diff_syms_list, old_syms_list]


def check_cmd(prog):
    for path in os.environ['PATH'].split(os.pathsep):
        path = path.strip('"')
        candidate = path+"/"+prog
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def get_abi_name(export_dir):
    file = f'{export_dir}/OLD-name.info'
    if not os.access(f'{file}', os.R_OK):
        exit_status(
            "Error", f"The info file {file} can't be read, Please check")
    with open(file, 'r') as f:
        name = f.read()
    return name


def check_dump_syms(abi_name, export_dir):
    new_dump = f'{export_dir}/NEW-abi.dump'
    old_dump = f'{export_dir}/OLD-abi.dump'
    syms_list = f'{export_dir}/OLD-func-syms.info'
    html = f'{export_dir}/export.html'
    cmd = f'abi-compliance-checker -l {abi_name} -old {old_dump} -new {new_dump} --symbols-list {syms_list} --report-path {html}'
    print(f'Checking the symbols of {abi_name} ...')
    run_cmd(cmd)
    return html


def output_result(syms_list, export_dir):
    df1 = pd.DataFrame(syms_list[0], columns=[u'当前系统缺少符号'])
    df2 = pd.DataFrame(syms_list[1], columns=[u'二进制依赖符号'])

    result = pd.concat([df1, df2], axis=1)
    # 用空替换表格中的 NaN
    result = result.fillna('')

    html = result.to_html()
    csv = result.to_csv()

    file = f'{export_dir}/result.html'
    with open(file, 'wt+') as f:
        f.writelines(html)
    html_path = os.path.realpath(file)

    file = f'{export_dir}/result.csv'
    with open(file, 'wt+') as f:
        f.writelines(csv)

    print(f'The check result is {html_path}')

