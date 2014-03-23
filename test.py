#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'draco'

from XenManager import manager

m = manager.Manager()


m.connect('192.168.1.251', 'root', '123456')
print m.get_hosts()
m.disconnect()