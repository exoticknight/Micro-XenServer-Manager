# -*- coding: utf-8 -*-

__author__ = 'draco'

import time
from PyQt4 import QtCore

class Task(QtCore.QThread):
    '''the class for async operation

    will check progress and emit updateProgress(int) per specific seconds
    and emit result(QVariant) with a seq as the parameter in the end

    '''
    def __init__(self, manager, function, *args, **kwargs):
        QtCore.QThread.__init__(self)
        self.manager = manager
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def __del__(self):
        self.wait()

    def run(self, delay=0.1):
        self.emit(QtCore.SIGNAL('updateProgress(int)'), 10)  # a trick to clam user
        # check the progress
        task = self.function(*self.args, **self.kwargs)
        record = {}
        # !!! note that task actually can be cancelled, but I don't want to support that right now
        while True:
            try:
                record = self.manager.xenapi.task.get_record(task)
            except Exception, e:
                pass
            else:
                # report progress
                self.emit(QtCore.SIGNAL('updateProgress(int)'), max(record['progress'] * 100, 10))   # a trick again
                if record['status'] != 'pending':
                    break

            time.sleep(delay)   # artificial time delay

        # now that the task ended, just fill up the progress
        self.emit(QtCore.SIGNAL('updateProgress(int)'), 100)
        time.sleep(0.2)
        self.emit(QtCore.SIGNAL('updateProgress(int)'), 0)
        # report result
        self.emit(QtCore.SIGNAL('result(QVariant)'), ({
            'status': record['status'],
            'result': record['result'],
            'error': record.get('error_info')
        },))
        # destroy the task at last
        self.manager.xenapi.task.destroy(task)