# -*- coding: utf-8 -*-

# Resource object code
#
# Created: Wed Sep 4 08:34:31 2013
#      by: The Resource Compiler for PyQt (Qt v5.1.1)
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore

qt_resource_data = b"\
\x00\x00\x00\xf9\
\x69\
\x6d\x70\x6f\x72\x74\x20\x51\x74\x51\x75\x69\x63\x6b\x20\x32\x2e\
\x30\x0a\x0a\x52\x65\x63\x74\x61\x6e\x67\x6c\x65\x20\x7b\x0a\x20\
\x20\x20\x20\x77\x69\x64\x74\x68\x3a\x20\x33\x36\x30\x0a\x20\x20\
\x20\x20\x68\x65\x69\x67\x68\x74\x3a\x20\x33\x36\x30\x0a\x20\x20\
\x20\x20\x54\x65\x78\x74\x20\x7b\x0a\x20\x20\x20\x20\x20\x20\x20\
\x20\x61\x6e\x63\x68\x6f\x72\x73\x2e\x63\x65\x6e\x74\x65\x72\x49\
\x6e\x3a\x20\x70\x61\x72\x65\x6e\x74\x0a\x20\x20\x20\x20\x20\x20\
\x20\x20\x74\x65\x78\x74\x3a\x20\x22\x48\x65\x6c\x6c\x6f\x20\x57\
\x6f\x72\x6c\x64\x22\x0a\x20\x20\x20\x20\x7d\x0a\x20\x20\x20\x20\
\x4d\x6f\x75\x73\x65\x41\x72\x65\x61\x20\x7b\x0a\x20\x20\x20\x20\
\x20\x20\x20\x20\x61\x6e\x63\x68\x6f\x72\x73\x2e\x66\x69\x6c\x6c\
\x3a\x20\x70\x61\x72\x65\x6e\x74\x0a\x20\x20\x20\x20\x20\x20\x20\
\x20\x6f\x6e\x43\x6c\x69\x63\x6b\x65\x64\x3a\x20\x7b\x0a\x20\x20\
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x51\x74\x2e\x71\x75\x69\
\x74\x28\x29\x3b\x0a\x20\x20\x20\x20\x20\x20\x20\x20\x7d\x0a\x20\
\x20\x20\x20\x7d\x0a\x7d\x0a\x0a\
"

qt_resource_name = b"\
\x00\x09\
\x03\x32\x8d\xbc\
\x00\x68\
\x00\x65\x00\x6c\x00\x6c\x00\x6f\x00\x2e\x00\x71\x00\x6d\x00\x6c\
"

qt_resource_struct = b"\
\x00\x00\x00\x00\x00\x02\x00\x00\x00\x01\x00\x00\x00\x01\
\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\
"

def qInitResources():
    QtCore.qRegisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

def qCleanupResources():
    QtCore.qUnregisterResourceData(0x01, qt_resource_struct, qt_resource_name, qt_resource_data)

qInitResources()
