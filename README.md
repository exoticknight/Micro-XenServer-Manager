Micro XenServer Manager
=======================

Micro XenServer Manager（简称MXM）是一个基于Python2.7和pyqt库的、利用citrix公司提供的XenAPI作为底层管理手段的、对以XenServer系统组成的系统集群进行虚拟机的监控和操纵为主要功能的开源工具。

##系统要求
python2.7+
pyqt4.8+
numpy1.8.0
scipy0.13.3
pyqtgraph0.9.8

##开发历史
V0.9
加入双物理机运行数据实时对比功能
V0.8
代码全面重构，实现了图形界面，使操作和状态监测变得动态和直观
V0.1
实现了CLI下对集群中虚拟机的基本控制，包括启动/关闭/重启/停止/恢复/迁移

##reference
depends on [parse_rrd.py](https://github.com/wawrzek/XenRRD) to parse XML-format data.
[XenAPI](http://www.xenserver.org/partners/developing-products-for-xenserver.html)