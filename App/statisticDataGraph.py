#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'draco'

import pyqtgraph as pg
from abstractDataGraph import *

class StatisticDataGraph(AbstractDataGraph):
    def __init__(self, parent, *args, **kwargs):
        super(StatisticDataGraph, self).__init__(parent, *args, **kwargs)
        # self._parent = parent
        # self._sessionRef = None
        # self._rrdParser = RRDUpdates()

        # initial render
        l = pg.GraphicsLayout()
        self.setCentralItem(l)

        self._plot = pg.PlotItem(title=self.tr('总能耗'), axisItems={'bottom': DateAxis(), 'left': EnergyAsix()})
        self._plot.showGrid(x=True, y=True)
        l.addItem(self._plot)

    def renderGraph(self, *args, **kwargs):
        try:
            self._plot.plot(*args, **kwargs)
        except Exception, e:
            print e