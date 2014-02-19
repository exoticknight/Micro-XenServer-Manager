#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'draco'

import time
from collections import defaultdict
from App import parse_rrd
from XenManager import manager

m = manager.Manager()
p = parse_rrd.RRDUpdates()

m.connect('192.168.1.251', 'root', '123456')
p.refresh(
    m.get_session_ref(),
    server='http://192.168.1.251'
)

print p.get_host_param_list()

data = {
        'time': [],
        'data': {'cpu0': [], 'cpu1': [], 'memory_free_kib': [], 'memory_total_kib': []}
}

for x in range(0, p.get_nrows()):
    data['time'].append(p.get_row_time(x))
    for me in data['data'].keys():
        print me
        data['data'].get(me).append(p.get_host_data(me, x))

print data
m.disconnect()