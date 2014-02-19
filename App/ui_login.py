# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Z:\python\Micro-XenServer-Manager\App\ui_login.ui'
#
# Created: Tue Feb 18 20:01:19 2014
#      by: PyQt4 UI code generator 4.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(171, 171)
        self.lineEdit_ip = QtGui.QLineEdit(Form)
        self.lineEdit_ip.setGeometry(QtCore.QRect(10, 10, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lineEdit_ip.setFont(font)
        self.lineEdit_ip.setObjectName(_fromUtf8("lineEdit_ip"))
        self.lineEdit_username = QtGui.QLineEdit(Form)
        self.lineEdit_username.setGeometry(QtCore.QRect(10, 50, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lineEdit_username.setFont(font)
        self.lineEdit_username.setObjectName(_fromUtf8("lineEdit_username"))
        self.lineEdit_password = QtGui.QLineEdit(Form)
        self.lineEdit_password.setGeometry(QtCore.QRect(10, 90, 151, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.lineEdit_password.setFont(font)
        self.lineEdit_password.setObjectName(_fromUtf8("lineEdit_password"))
        self.pushButton_login = QtGui.QPushButton(Form)
        self.pushButton_login.setGeometry(QtCore.QRect(10, 130, 151, 31))
        self.pushButton_login.setObjectName(_fromUtf8("pushButton_login"))

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "连接", None))
        self.lineEdit_ip.setPlaceholderText(_translate("Form", "IP", None))
        self.lineEdit_username.setPlaceholderText(_translate("Form", "username", None))
        self.lineEdit_password.setPlaceholderText(_translate("Form", "password", None))
        self.pushButton_login.setText(_translate("Form", "Login", None))

