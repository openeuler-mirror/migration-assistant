# migration-assistant

#### 介绍
Migration assistant helps users migrate business applications from other Linux hairstyles to openEuler OS.

#### 安装教程

1.  使用以下命令安转依赖：  
`yum install python3-pandas  python3-pexpect zlib-devel gcc gcc-c++ make graphviz ImageMagick`
2.  使用make命令安装abi-compliance-checker-2.4和abi-dumper-2.1  
`cd abi-compliance-checker-2.4`  
`make install`
`cd abi-dumper-2.1`  
`make install`

3.  新建文件夹  
`cd abicheck`
`mkdir -p /usr/share/abicheck/`
`cp -r conf /usr/share/abicheck/`

#### 使用说明

1.  查看帮助  
`cd abicheck`
`python3 main.py --help`
2.  查看本机ssh与centos7.6 ssh版本的对比  
`python3 main.py --input /usr/bin/ssh --release centos_7.6`
3.  在执行结果可以查看`./abi-info-export`目录下的export.html文件
