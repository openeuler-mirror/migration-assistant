import os
import sys
import argparse

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



