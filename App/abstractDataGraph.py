#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'draco'


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
                strns.append(str(int(x / 1024)))   # KB->MB
            except ValueError:
                strns.append('')
        return strns


class EnergyAsix(pg.AxisItem):
    def __init__(self):
        super(EnergyAsix, self).__init__(orientation='left')

    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            try:
                strns.append(str(x))
            except ValueError:
                strns.append('')
        return strns

class AbstractDataGraph(pg.GraphicsView):
    def __init__(self, parent, *args, **kwargs):
        super(AbstractDataGraph, self).__init__(*args, **kwargs)
        self._parent = parent
        self._sessionRef = None
        self._rrdParser = RRDUpdates()

        #self._metricsPlot['cpu'].clear()

    def bindSession(self, sessionRef):
        self._sessionRef = sessionRef

    def unbindSession(self):
        self._sessionRef = None