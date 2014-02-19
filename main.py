# -*- coding: utf-8 -*-

__author__ = 'draco'

import sys
from PyQt4.QtGui import QApplication
from App import window_main

# run the application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = window_main.MainWindow()
    window.show()
    sys.exit(app.exec_())