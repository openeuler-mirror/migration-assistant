#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pylspci
import json
import platform


def get_pci_list()->list:
    return pylspci.parsers.SimpleParser().run()


def int_id_to_hex(int_id: int)->str:
    hex_id = hex(int_id)[2:]
    if len(hex_id)==3 :
        hex_id = hex_id + '0'
    return hex_id


def get_hex_id(name_with_id: pylspci.fields.NameWithID)->str:
    int_id = name_with_id.as_dict().get('id')
    if int_id==None :           # 若为空，直接返回
        return ''
    hex_id = hex(int_id)[2:]
    if len(hex_id)==3 :         # 否则判断补全一下
        hex_id = hex_id + '0'
    return hex_id


def get_pci_info() -> list:
    pci_dev_list = pylspci.parsers.SimpleParser().run()
    
    parsed_list = []
    for pci_dev_item in pci_dev_list:
        item_dict = {}
        item_dict['vendorID'] = get_hex_id(pci_dev_item.vendor)
        item_dict['deviceID'] = get_hex_id(pci_dev_item.device)
        item_dict['svID'] = get_hex_id(pci_dev_item.subsystem_vendor)
        item_dict['ssID'] = get_hex_id(pci_dev_item.subsystem_device)
        item_dict['type'] = pci_dev_item.cls.name
        item_dict['chipVendor'] = pci_dev_item.vendor.name
        parsed_list.append(item_dict)
    
    return parsed_list


def main():
    jsonstr = json.dumps(get_pci_info())
    jsonfile = open("hardware_list_"+platform.machine()+".json", 'w')
    with jsonfile:
        jsonfile.write(jsonstr)
        
    print("complete. save hardware info file in current direcory")


if __name__ == "__main__":
    main()