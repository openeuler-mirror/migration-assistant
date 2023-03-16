#!/usr/bin/python3

# -*- coding: utf-8 -*-

import argparse
import logging
import os
import re
import subprocess
import sys
import tarfile

import distro

from utils import *

TOOL_VERSION = "1.0"
ABI_CC = "abi-compliance-checker"
ABI_DUMPER = "abi-dumper"

CMD_NAME = os.path.basename(__file__)
ERROR_CODE = {"Ok": 0, "Error": 1, "Empty": 10, "NoDebug": 11, "NoABI": 12}

ARGS = {}

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
        tar.extractall(path=export_dir)
    print(f'The file {tarball} has been decompressed.')


def get_rpmname_without_libs(x):
    # 正则获取rpmname
    return re.sub('-libs$', '', x).strip()
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
