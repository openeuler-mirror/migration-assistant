import json
import os

def main():
    file_list = []
    
    raw_device_str_list = []
    device_list = []
    
    for root, dirs, files in os.walk("./"):
        file_list = files
    
    for item in file_list:
        if item.endswith('.json'):
            with open('./'+item, 'r') as f:
                item_json_array = json.loads(f.read())
                for json_item in item_json_array:
                    raw_device_str_list.append(json.dumps(json_item))
    
    for dev in set(raw_device_str_list):
        device_list.append(dev)
    
    print(device_list)
    
    jsonlist = []
    
    for dev in device_list:
        jsonlist.append(json.loads(dev))
        
    print(jsonlist)
    
    with open('./ut_compat_hardwares.json', 'w') as f:
        f.write(json.dumps(jsonlist))
    

if __name__ == "__main__":
    main()