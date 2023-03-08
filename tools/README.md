# 工具说明

本文件夹内存放开发过程中使用的程序代码。每一类工具的代码会被放在同一个文件夹中，文件夹的名称是用到工具的模块



## 硬件扫描 & 硬件兼容性数据集制作工具

用于 utmtc-scanhardware

- `scan_local_hardware.py` ： 使用 lspci 扫描设备已连接的 pci 设备，并将这些设备的信息在执行目录下输出为一个 `json` 文件。

  - 用法示例：`$ python3 ./scan_local_hardware.py`

    输出文件命名规则为 `hardware_list_<当前设备架构>.json` 示例：

    ```json
    [{"vendorID": "8086", "deviceID": "9b43", "svID": "1849", "ssID": "9b43", "type": "Host bridge", "chipVendor": "Intel Corporation"}........]
    ```

- `merge_hardware_lists.py` ： 用于合并多个由上面的工具生成的 json 列表，去除所有重复项，输出一个名为 `ut_compat_hardware.json` 的文件

  - 用法示例： `$ python3 ./ut_compat_hardware.json` 

    运行完成后会在执行目录下输出一个合并了所有其他 json 文件内容的 `ut_compat_hardware.json` 文件。

  - 注意，本工具只进行同目录下多个 json 文件的去重合并，不会检查内容准确性

