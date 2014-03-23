# -*- coding: utf-8 -*-

__author__ = 'draco'

from PyQt4 import QtCore, QtGui


class GenericNode(object):
    def __init__(self, data, parent=None):
        self._data = data
        self._children = []
        self._parent = parent

        if parent is not None:
            parent.addChild(self)

    def data(self, data=None):
        if data is not None:
            self._data = data
            return
        return self._data

    def children(self):
        return self._children

    def addChild(self, child):
        self._children.append(child)
        child._parent = self

    def deleteChild(self, child):
        self._children.remove(child)
        child._parent = None

    def insertChild(self, position, child):
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        return True

    def removeChild(self, position):
        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None
        return True

    def child(self, row):
        return self._children[row]

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)

    def name(self):
        return self._data['name_label']

    def ref(self):
        return self._data['OpaqueRef']

    # virtual method
    def type(self):
        pass


class VMNode(GenericNode):
    def __init__(self, data, parent=None):
        super(VMNode, self).__init__(data, parent)

    # implement method
    def type(self):
        return 'VM'

    def state(self):
        '''
        according to the reference, this will return a string which is Halted/Paused/Running/Suspended
        '''
        return self._data['power_state']


class HostNode(GenericNode):
    def __init__(self, data, parent=None):
        super(HostNode, self).__init__(data, parent)

    # implement method
    def type(self):
        return 'HOST'

    def enable(self):
        return self._data['enabled']

    def ip(self):
        return self._data['address']


class PoolTreeModel(QtCore.QAbstractItemModel):
    def __init__(self, root, parent=None):
        super(PoolTreeModel, self).__init__(parent)
        self._rootNode = root

        def createPixmap(color):
            pixmap = QtGui.QPixmap(12, 12)
            pixmap.fill(QtCore.Qt.transparent)  # transparent background

            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            painter.setPen(color)
            painter.setBrush(QtGui.QBrush(color))

            painter.drawEllipse(0, 0, 12, 12)

            return pixmap

        self._vm_icon = {}.fromkeys(('Halted', 'Paused'), QtGui.QIcon(createPixmap(QtCore.Qt.gray)))  # gray
        self._vm_icon['Running'] = QtGui.QIcon(createPixmap(QtCore.Qt.green))  # green
        self._vm_icon['Suspended'] = QtGui.QIcon(createPixmap(QtCore.Qt.red))  # red

    def getNode(self, QModelIndex):
        if QModelIndex.isValid():
            node = QModelIndex.internalPointer()
            if node:
                return node

        return self._rootNode

    def index(self, row, column, QModelIndex_parent):
        if not QModelIndex_parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = QModelIndex_parent.internalPointer()

        childNode = parentNode.child(row)

        if childNode:
            return self.createIndex(row, column, childNode)
        else:
            return QtCore.QModelIndex()

    def data(self, QModelIndex, role):
        if not QModelIndex.isValid():
            return None

        node = QModelIndex.internalPointer()

        if role == QtCore.Qt.DisplayRole:
            return node.name()

        elif role == QtCore.Qt.DecorationRole:
            if node.type() == 'VM':
                return self._vm_icon.get(node.state(), None)
            return None

        elif role == QtCore.Qt.UserRole:
            return node.ref()

        elif role == QtCore.Qt.UserRole + 1:
            return node.type()

        elif role == QtCore.Qt.UserRole + 2:
            return node.data()

    def parent(self, QModelIndex):
        if not QModelIndex.isValid():
            return QtCore.QModelIndex()

        node = QModelIndex.internalPointer()
        parentNode = node.parent()

        if parentNode == self._rootNode:
            return QtCore.QModelIndex()

        return self.createIndex(parentNode.row(), 0, parentNode)

    def headerData(self, section, Qt_Orientation, int_role=None):
        return self.tr('vms')

    def insertRow(self, position, child, QModelIndex_parent=QtCore.QModelIndex()):
        self.beginInsertRows(QModelIndex_parent, position, position + 1)

        # insert
        node = self.getNode(QModelIndex_parent)
        result = node.insertChild(position, child)

        self.endInsertRows()
        return result

    def removeRow(self, position, QModelIndex_parent=QtCore.QModelIndex()):
        self.beginRemoveRows(QModelIndex_parent, position, position + 1)

        # remove
        node = self.getNode(QModelIndex_parent)
        result = node.removeChild(position)

        self.endRemoveRows()
        return result

    def rowCount(self, QModelIndex_parent):
        if not QModelIndex_parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = QModelIndex_parent.internalPointer()

        return parentNode.childCount()

    def columnCount(self, QModelIndex_parent):
        return 1

    def flags(self, QModelIndex):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled

    def clear(self):
        self._rootNode = None
        self.reset()
