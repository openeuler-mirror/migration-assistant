#!/usr/bin/python3

# -*- coding: utf-8 -*-

import argparse
import io
import logging
import os
import re
import shutil
import subprocess
import tarfile
import xml.etree.ElementTree as ET

import distro
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


def detect_os():
    if distro.id != 'uos':
        logging.error('please run in UOS')
        exit()


def parse_args():
    args = []
    parser = argparse.ArgumentParser(
        description='Analyze infomation about bin file.')
    parser.add_argument('-v', '--verbose', action='store_true',
                        default=False, help='Enable verbose output')
    parser.add_argument(
        '--info', metavar='info.tar.gz', help='info tarball file', required=True)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not os.access(f'{args.info}', os.F_OK):
        logging.error(
            f"The info tarball file {args.info} doesn't exist, Please check")
        exit()
    if not os.access(f'{args.info}', os.R_OK):
        logging.error(
            f"The info tarball file {args.info} can't be read, Please check")
        exit()
    return args.info


def extract_tarball(tarball, target_path):
    print(f'Preparing to unpack {tarball} ...')
    with tarfile.open(tarball, 'r:gz') as tar:
        tar.extractall(path=target_path)
    print(f'Unpacking {tarball} ...')


def get_rpmname_without_libs(x):
    # 正则获取rpmname
    return re.sub('-libs$', '', x).strip()


def find_devel_lib_package(target_path):
    print('Checking the dependency ...')
    file = f'{target_path}/pkgs.info'
    if not os.access(f'{file}', os.R_OK):
        logging.error(
            f"The info file {file} can't be read. Please check")
        exit()

    dev_pkgs_set = set()
    libs_pkgs_set = set()
    with open(file, 'r') as f:
        for line in f:
            rpm_name = get_rpmname_without_libs(line)
            dev_pkgs_set.add(f'{rpm_name}-devel')
            # 包名中包含 lib 关键字的包，本身就是 lib 包
            if 'lib' not in rpm_name:
                libs_pkgs_set.add(f'{rpm_name}-libs')
            else:
                libs_pkgs_set.add(f'{rpm_name}')
    return dev_pkgs_set, libs_pkgs_set


def detect_devel_lib_package(dev_pkgs_set, libs_pkgs_set):
    lost_pkg_set = set()
    dev_pkgs_set = dev_pkgs_set | libs_pkgs_set
    for pkg in dev_pkgs_set:
        cmd = f'rpm -q {pkg}'
        returncode, stdout, stderr = run_cmd(cmd)
        if returncode != 0:
            print(f"It seems that the OS doesn't install {pkg}")
            lost_pkg_set.add(pkg)
        else:
            print(f'The packages "{pkg}" have been installed')

    lost_yum_pkg_set = set()
    for pkg in lost_pkg_set:
        cmd = f'yum install -y {pkg}'
        print(f'Trying to install package {pkg} with yum')
        returncode, stdout, stderr = run_cmd(cmd)
        if returncode != 0:
            print(f"Can't install {pkg}, with yum")
            lost_yum_pkg_set.add(pkg)
        else:
            print(f'Successfully installed {pkg} with yum')

    if lost_yum_pkg_set:
        print(f'Please install {lost_yum_pkg_set}, then retry')
        exit()


def gen_abi_cc_xml(tarball, target_path, dev_pkgs_set, libs_pkgs_set):
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

    file = f'{target_path}/dump.xml'
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
    lib_name = str(tarball).split('_')[1]
    dump_file = f'{target_path}/{lib_name}.dump'
    cmd = f'abi-compliance-checker -xml -l {lib_name} -dump {file} -dump-path {dump_file}'
    print(f'Analyzing the symbols of {libs_pkgs_set} ...')
    returncode, stdout, stderr = run_cmd(cmd)

    return dump_file


def compare_syms(target_path, dump_file):
    print('Checking symbol differences ...')
    elf_sym_set = set()
    elf_file = f'{target_path}/elf.info'
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


def output_result(syms_list, target_path):
    df1 = pd.DataFrame(syms_list[0], columns=[u'当前系统缺少符号'])
    df2 = pd.DataFrame(syms_list[1], columns=[u'二进制依赖符号'])

    result = pd.concat([df1, df2], axis=1)
    # 用空替换表格中的 NaN
    result = result.fillna('')

    html = result.to_html()
    csv = result.to_csv()

    file = f'{target_path}/result.html'
    with open(file, 'wt+') as f:
        f.writelines(html)
    html_path = os.path.realpath(file)

    file = f'{target_path}/result.csv'
    with open(file, 'wt+') as f:
        f.writelines(csv)

    print(f'The check result is {html_path}')


def main():

    # 判断系统
    # detect_os()

    # 解析参数
    tarball = parse_args()

    # 用 abc/xxx.tar.gz 的 xxx 作为目录名称
    target_path = tarball.split('/')[-1]
    target_path = target_path.split('.')[-3]

    # 解压 tarball
    extract_tarball(tarball, target_path)

    # 解析 dev 包和 lib 包
    dev_pkgs_set, libs_pkgs_set = find_devel_lib_package(target_path)

    # 判断系统中是否安装 dev 包 和 lib 包
    detect_devel_lib_package(dev_pkgs_set, libs_pkgs_set)

    # 生成 abi-compliance-checker 用到的 xml 文件，并生成 dump 文件
    dump_file = gen_abi_cc_xml(
        tarball, target_path, dev_pkgs_set, libs_pkgs_set)

    # 读取 dump 文件，分析 symbol
    syms_list = compare_syms(target_path, dump_file)

    # 输出结果
    output_result(syms_list, target_path)


if __name__ == "__main__":
    main()
