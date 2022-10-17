#!/usr/bin/python3

# -*- coding: utf-8 -*-

import argparse
import logging
import os
import re
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

import distro
import pandas as pd


TOOL_VERSION = "1.0"

ABI_CC = "abi-compliance-checker"
ABI_DUMPER = "abi-dumper"

CMD_NAME = os.path.basename(__file__)
ERROR_CODE = {"Ok": 0, "Error": 1, "Empty": 10, "NoDebug": 11, "NoABI": 12}

ARGS = {}


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


def detect_os():
    if distro.id != 'uos':
        logging.error('please run in UOS')
        exit()


def parse_args():
    desc = "Analyze abi infomation about bin file."
    parser = argparse.ArgumentParser(
        description=desc, epilog=f"example: {CMD_NAME} -tar /path/OLD-abi-info.tar.gz")
    parser.add_argument('-v', action='version',
                        version='Package ABI Info Collector '+TOOL_VERSION)
    parser.add_argument(
        '-debug', help='enable debug messages', action='store_true')
    parser.add_argument('-tar', metavar='OLD-abi-info.tar.gz',
                        help='abi info tarball file',)
    parser.add_argument(
        '-debuginfo', help=argparse.SUPPRESS, action='store_true')
    parser.add_argument(
        '-export-dir', help='specify a directory to save and reuse ABI info export (default: ./abi-info-export)', metavar='DIR')
    #parser.add_argument('-src', help='collect source abi info', action='store_true')
    return parser.parse_args()


def extract_tarball(tarball, export_dir):
    print(f'Decompressing file {tarball} ...')
    with tarfile.open(tarball, 'r:gz') as tar:
        def is_within_directory(directory, target):
            
            abs_directory = os.path.abspath(directory)
            abs_target = os.path.abspath(target)
        
            prefix = os.path.commonprefix([abs_directory, abs_target])
            
            return prefix == abs_directory
        
        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
        
            for member in tar.getmembers():
                member_path = os.path.join(path, member.name)
                if not is_within_directory(path, member_path):
                    raise Exception("Attempted Path Traversal in Tar File")
        
            tar.extractall(path, members, numeric_owner=numeric_owner) 
            
        
        safe_extract(tar, path=export_dir)
    print(f'The file {tarball} has been decompressed.')


def get_rpmname_without_libs(x):
    # 正则获取rpmname
    return re.sub('-libs$', '', x).strip()


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


def s_exit(code):
    sys.exit(ERROR_CODE[code])


def print_err(msg):
    sys.stderr.write(msg+"\n")


def exit_status(code, msg):
    if code != "Ok":
        print_err("ERROR: "+msg)
    else:
        print(msg)

    s_exit(code)


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


def gen_dump_with_debuginfo(basename, export_dir, debuginfo_pkgs):
    # TODO:当前实现有困难
    pass


def check_dump_syms(abi_name, export_dir):
    new_dump = f'{export_dir}/NEW-abi.dump'
    old_dump = f'{export_dir}/OLD-abi.dump'
    syms_list = f'{export_dir}/OLD-func-syms.info'
    html = f'{export_dir}/export.html'
    cmd = f'abi-compliance-checker -l {abi_name} -old {old_dump} -new {new_dump} --symbols-list {syms_list} --report-path {html}'
    print(f'Checking the symbols of {abi_name} ...')
    run_cmd(cmd)
    return html


def main():
    global ARGS
    ARGS = parse_args()

    # 检查参数
    if not ARGS.tar:
        exit_status('Error', 'tarball file are not specified (-tar option)')

    tarball = ARGS.tar
    if not os.path.isfile(tarball):
        exit_status('Error', f'''file "{tarball}" does not exist.''')
    if not os.access(tarball, os.R_OK):
        exit_status('Error', f'''file "{tarball}" can't be read.''')
    if not tarfile.is_tarfile(tarball):
        exit_status(
            'Error', f'''file "{tarball}" isn't a standard tarball file.''')

    if ARGS.export_dir:
        export_dir = ARGS.export_dir
    else:
        export_dir = "abi-info-export"

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    # 检查 abi-compliance-checker 是否安装
    global ABI_CC, ABI_DUMPER
    if not check_cmd(ABI_CC):
        exit_status('Error', 'ABI Compliance Checker is not installed')

    # 检查 abi-dumper 是否安装
    if not check_cmd(ABI_DUMPER):
        exit_status('Error', 'ABI Dumper is not installed')

    # 判断系统
    # detect_os()

    # 解压 tarball
    extract_tarball(tarball, export_dir)

    # 获取OLD-name 值
    abi_name = get_abi_name(export_dir)

    # 解析  dev 包 和 lib 包
    dev_pkgs, libs_pkgs, debuginfo_pkgs = find_devel_lib_package(export_dir)

    if not ARGS.debuginfo:

        # 判断系统中是否安装 dev 包 和 lib 包
        try_install_packages(dev_pkgs, libs_pkgs)
        # 生成 abi-compliance-checker 用到的 xml 文件，并生成 dump 文件
        dump_file = gen_xml_and_dump(
            abi_name, export_dir, dev_pkgs, libs_pkgs)
    else:
        # 判断系统中是否安装 debuginfo_pkgs 包
        try_install_packages(debuginfo_pkgs)
        # 通过 debuginfo 信息生成 dump 文件
        dump_file = gen_dump_with_debuginfo(abi_name, export_dir,
                                            debuginfo_pkgs)

    # 读取 dump 文件，分析 symbol
    #syms_list = compare_syms(export_dir, dump_file)
    # 比较前后两个dump 文件
    html = check_dump_syms(abi_name, export_dir)

    if os.path.isfile(html):
        print(f'The check result is {html}')
    else:
        exit_status("Error", "Checking error")
    # 输出结果
    # output_result(export_dir)


if __name__ == "__main__":
    main()
