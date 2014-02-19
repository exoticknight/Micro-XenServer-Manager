#!/usr/bin/env python
# -*- coding: utf-8 -*-


__author__ = 'draco'

import random
from parse_rrd import *
import numpy
import pyqtgraph as pg

class DateAxis(pg.AxisItem):
    def __init__(self):
        super(DateAxis, self).__init__(orientation='bottom')

    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            try:
                strns.append(time.strftime('%H:%M:%S', time.localtime(x)))
            except ValueError:  ## Windows can't handle dates before 1970
                strns.append('')
        return strns

class MemoryAxis(pg.AxisItem):
    def __init__(self):
        super(MemoryAxis, self).__init__(orientation='left')

    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            try:
                strns.append(str(int(x / 1024)))
            except ValueError:
                strns.append('')
        return strns


class DataGraph(pg.GraphicsView):
    def __init__(self, parent, *args, **kwargs):
        super(DataGraph, self).__init__(*args, **kwargs)
        self._parent = parent
        self._sessionRef = None
        self._rrdParser = RRDUpdates()
        self._metricsPlot = {}.fromkeys(('loadavg', 'cpu_avg', 'Used Memory'))
        self._metricsColor = {
            'loadavg': [(0, 80, 238), (229, 20, 0)],
            'cpu_avg': [(0, 80, 238), (229, 20, 0)],
            'Used Memory': [(0, 80, 238), (229, 20, 0)]
        }

        # initial render
        l = pg.GraphicsLayout()
        self.setCentralItem(l)

        # add plots
        # TODO need refactoring
        self._metricsPlot['loadavg'] = pg.PlotItem(title='loadavg', axisItems={'bottom': DateAxis()})
        self._metricsPlot['loadavg'].showGrid(x=True, y=True)
        l.addItem(self._metricsPlot['loadavg'])
        l.nextRow()

        self._metricsPlot['cpu_avg'] = pg.PlotItem(title='cpu_avg', axisItems={'bottom': DateAxis()})
        self._metricsPlot['cpu_avg'].showGrid(x=True, y=True)
        l.addItem(self._metricsPlot['cpu_avg'])
        l.nextRow()

        self._metricsPlot['Used Memory'] = pg.PlotItem(title='Used Memory', axisItems={'bottom': DateAxis(), 'left': MemoryAxis()})
        self._metricsPlot['Used Memory'].showGrid(x=True, y=True)
        self._metricsPlot['Used Memory'].setYRange(0, 2 * 1024 * 1024)   #2G
        l.addItem(self._metricsPlot['Used Memory'])


        #self._metricsPlot['cpu'].clear()

    def bindSession(self, sessionRef):
        self._sessionRef = sessionRef

    def unbindSession(self):
        self._sessionRef = None

    def refresh(self, ips):
        if self._sessionRef is None:
            return

        now = int(time.time()) - 60

        for index, ip in enumerate(ips):
            # data scheme
            data = {
                'time': [],
                'data': {'loadavg': [], 'cpu_avg': [], 'Used Memory': []}
            }

            # get data via network
            self._rrdParser.refresh(self._sessionRef, {'start': now}, server='http://'+ip)
            # parse data
            for row in range(0, self._rrdParser.get_nrows()):
                data['time'].append(self._rrdParser.get_row_time(row))
                for metric in self._metricsPlot:
                    if metric == 'Used Memory':
                        data['data'][metric].append(
                            self._rrdParser.get_host_data('memory_total_kib', row) - self._rrdParser.get_host_data('memory_free_kib', row)
                        )
                    else:
                        data['data'][metric].append(self._rrdParser.get_host_data(metric, row))

            print data
            # update the graph
            for title, plot in self._metricsPlot.items():
                plot.plot(x=data['time'], y=data['data'][title], pen=self._metricsColor[title][index])

