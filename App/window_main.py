# -*- coding: utf-8 -*-

_Author__ = 'draco'

import json
import types
import time

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_main import Ui_MainWindow
from ui_login import Ui_Form

from parse_rrd import *
from Model import treeModel
from liveDataGraph import LiveDataGraph
from statisticDataGraph import StatisticDataGraph
import XenManager.manager
import task


class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, types.StringTypes):
            return json.JSONEncoder.default(self, obj)
        else:
            return repr(obj)

# set translator's coding to utf8
QTextCodec.setCodecForTr(QTextCodec.codecForName("utf8"))


class LoginWindow(QDialog, Ui_Form):
    def __init__(self, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # bind data
        self.poolMasterInfo = {}.fromkeys(('ip', 'username', 'password'))
        self.ui.lineEdit_ip.setText('192.168.1.251')
        self.ui.lineEdit_username.setText('root')
        self.ui.lineEdit_password.setText('123456')

        # make connection
        self.connect(self.ui.pushButton_login, SIGNAL('clicked()'), self.check)

    def check(self):
        class EmptyIP(Exception): pass
        class EmptyUsername(Exception): pass
        class EmptyPassword(Exception): pass
        # check whether the ip/username/password is valid
        self.poolMasterInfo['ip'], self.poolMasterInfo['username'], self.poolMasterInfo['password'] = \
            str(self.ui.lineEdit_ip.text()), str(self.ui.lineEdit_username.text()), str(self.ui.lineEdit_password.text())
        try:
            if len(self.poolMasterInfo['ip']) == 0:
                raise EmptyIP, self.tr('IP不能为空')
            if len(self.poolMasterInfo['username']) == 0:
                raise EmptyUsername, self.tr('用户名不能为空')
            if len(self.poolMasterInfo['password']) == 0:
                raise EmptyPassword, self.tr('密码不能为空')
        except EmptyIP, e:
            QMessageBox.warning(self, self.tr('IP地址错误'), unicode(e))
            self.ui.lineEdit_ip.selectAll()
            self.ui.lineEdit_ip.setFocus()
            return
        except EmptyUsername, e:
            QMessageBox.warning(self, self.tr('用户名为空'), unicode(e))
            self.ui.lineEdit_username.selectAll()
            self.ui.lineEdit_username.setFocus()
            return
        except EmptyPassword, e:
            QMessageBox.warning(self, self.tr('密码为空'), unicode(e))
            self.ui.lineEdit_password.selectAll()
            self.ui.lineEdit_password.setFocus()
            return
        QDialog.accept(self)

    def getPoolMasterInfo(self):
        return self.poolMasterInfo


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent = None):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # global variables
        self.poolMasterInfo = None
        self.poolDataIndex = {}.fromkeys(('hostIndex', 'vmIndex'))
        self.operationLock = False

        # initial xen manager
        self.xenManager = XenManager.manager.Manager()

        # initial pool monitor timer
        self.stateMonitorTimer = QTimer(self)
        self.stateMonitorTimer.timeout.connect(self.monitoringVMs)

        # initial data monitor timer
        self.dataMonitorTimer = QTimer(self)
        self.dataMonitorTimer.timeout.connect(self.monitoringData)

        # model for QTreeView
        self.poolTreeModel = None

        # action mapper
        self.actionMapper = QSignalMapper(self)
        # with the suffix of QAction's name as key and the operation as value
        self.supportOperations = {
            'VMStart': self.xenManager.start_vm,
            'VMShutdown': self.xenManager.shutdown_vm,
            'VMReboot': self.xenManager.reboot_vm,
            'VMSuspend': self.xenManager.suspend_vm,
            'VMResume': self.xenManager.resume_vm
        }
        self.mapActionToOperation()

        # claim host QAction signalMapper
        self.migrateMapper = QSignalMapper(self)

        # make ui connection
        self.makeConnection()

        # customize ui
        #self.setWindowFlags(Qt.FramelessWindowHint)
        #self.ui.statusBar.setSizeGripEnabled(True)
        self.ui.dateTimeEditTo.setDateTime(QDateTime.currentDateTime())
        self.ui.dateTimeEditFrom.setDateTime(QDateTime.currentDateTime().addSecs(-60))

        # initial data graph
        self.liveDataGraph = None
        self.statisticDataGraph = None
        self.buildDataGraph()

        # everything is ok, notify the user
        self.ui.statusBar.showMessage(self.tr('准备就绪。'))

        # test

    def mousePressEvent(self, event):
        '''
        Note:
            override mouse press event
        '''
        self._postion = event.globalPos() - self.pos()

    def mouseMoveEvent(self, event):
        '''
        Note:
            override mouse move event
        '''
        self.move(event.globalPos() - self._postion)

    def closeEvent(self, event):
        '''
        Note:
            override close event
        '''
        # close connection before close
        self.onActionQuit()
        event.accept()

    def mapActionToOperation(self):

        for name in self.supportOperations:
            actionWidget = self.findChild(QAction, 'action' + name)
            self.actionMapper.setMapping(actionWidget, name)
            actionWidget.triggered.connect(self.actionMapper.map)

        self.actionMapper.mapped['QString'].connect(self.asyncOperation)

    def asyncOperation(self, operation):
        '''a slot for the QAction which controls VM and host'''
        if self.operationLock:
            self.ui.statusBar.showMessage(self.tr('请等待上一个操作完成。'), 2000)
            # for now, I don't want to support multi-operation
            return

        self.operationLock = True

        index = self.ui.treeView.selectedIndexes()[0]

        self.t = task.Task(
            self.xenManager,
            self.supportOperations[str(operation)],
            self.poolTreeModel.data(index, Qt.UserRole)
        )
        self.updateLog('name:{0}\noperation:{1}'.format(self.poolTreeModel.data(index, Qt.DisplayRole), operation))
        self.connect(self.t, SIGNAL('updateProgress(int)'), self.updateProgress)
        self.connect(self.t, SIGNAL('result(QVariant)'), self.takeResult)
        self.t.start()

    def asyncMigrate(self, host):
        '''a slot for the migrate QAction '''
        if self.operationLock:
            self.ui.statusBar.showMessage(self.tr('请等待上一个操作完成。'), 2000)
            # for now, I don't want to support multi-operation
            return

        self.operationLock = True

        index = self.ui.treeView.selectedIndexes()[0]

        self.t = task.Task(
            self.xenManager,
            self.xenManager.migrate_vm,
            self.poolTreeModel.data(index, Qt.UserRole),
            str(host)
        )
        self.updateLog('name:{0}\noperation:{1}\nhost:{2}'.format(self.poolTreeModel.data(index, Qt.DisplayRole), 'VMMigrate', host))
        self.connect(self.t, SIGNAL('updateProgress(int)'), self.updateProgress)
        self.connect(self.t, SIGNAL('result(QVariant)'), self.takeResult)
        self.t.start()

    def makeConnection(self):
        # context menu
        self.ui.treeView.customContextMenuRequested.connect(self.showTreeViewMenu)

        # menu trigger
        self.ui.actionConnect.triggered.connect(self.onActionConnect)
        self.ui.actionDisconnect.triggered.connect(self.onActionDisconnect)
        self.ui.actionQuit.triggered.connect(self.onActionQuit)
        self.ui.menuVMMigrate.aboutToShow.connect(self.menuMigrateToShow)

        # ui event
        self.ui.treeView.clicked.connect(self.onTreeItemClicked)

        # button event
        self.ui.pushButtonSaveLog.clicked.connect(self.saveLogToFile)
        self.ui.pushButtonAnalyze.clicked.connect(self.generateStatistic)

    def monitoringVMs(self):
        if self.poolDataIndex.get('vmIndex') is None:
            return

        changed = False
        # qDebug('-------------------------')
        for OpaqueRef, vmNode in self.poolDataIndex['vmIndex'].items():
            oldRecord = vmNode.data()
            try:
                newRecord = self.xenManager.xenapi.VM.get_record(OpaqueRef)
                # qDebug('old ' + oldRecord['name_label'] + ' ' + oldRecord['power_state'])
                # qDebug('new ' + oldRecord['name_label'] + ' ' + newRecord['power_state'])
            except Exception, e:
                # qDebug('miss ' + oldRecord['name_label'])
                pass
            else:
                # check whether 'power_state' is changed
                if oldRecord['power_state'] != newRecord['power_state']:
                    # update data with the new record
                    newRecord['OpaqueRef'] = oldRecord['OpaqueRef']
                    vmNode.data(newRecord)
                    # update flag
                    changed = True

                # check whether 'resident_on' is changed
                if oldRecord['resident_on'] != newRecord['resident_on']:

                    # remove it from old host and add it to new host
                    self.poolDataIndex['hostIndex'][oldRecord['resident_on']].deleteChild(vmNode)
                    if newRecord['resident_on'] == 'OpaqueRef:NULL':
                        self.poolDataIndex['hostIndex'][newRecord['affinity']].addChild(vmNode)
                    else:
                        self.poolDataIndex['hostIndex'][newRecord['resident_on']].addChild(vmNode)

                    # update data with the new record
                    newRecord['OpaqueRef'] = oldRecord['OpaqueRef']
                    vmNode.data(newRecord)
                    # update flag
                    changed = True

        if changed:
            self.poolTreeModel.reset()
            self.ui.treeView.expandAll()

    def monitoringData(self):
        # TODO replace the tuple with dynamic data
        self.liveDataGraph.refresh(['192.168.1.251', '192.168.1.252'])

    '''
    ui stuff start
    '''
    def showTreeViewMenu(self, point):
        '''handle for the right-click of treeview node

        show operations for host or vm, depending on which type of node is right-clicked
        '''
        # get the QModelIndex and check whether node is clicked first
        QModelIndex_node = self.ui.treeView.indexAt(point)
        if not QModelIndex_node.isValid():
            return

        node = self.poolTreeModel.getNode(QModelIndex_node)
        nodeType = node.type()

        if nodeType == 'HOST':
            # host node, show the host context menu
            # not support yet
            #self.ui.menuHost.exec_(QCursor.pos())
            pass
        elif nodeType == 'VM':
            # vm node, show the vm context menu
            state = node.state()

            if state == 'Running':
                self.ui.menuRunningVM.exec_(QCursor.pos())
            elif state == 'Halted':
                self.ui.menuHaltedVM.exec_(QCursor.pos())
            elif state == 'Suspended':
                self.ui.menuSuspendedVM.exec_(QCursor.pos())

    def buildTreeView(self, hosts, vms):
        '''render the tree view with hosts' data and vms' data

        should be used after a session was made
        '''
        rootNode = treeModel.GenericNode(None)
        self.poolDataIndex['hostIndex'] = {}
        self.poolDataIndex['vmIndex'] = {}

        # special host node
        self.poolDataIndex['hostIndex']['OpaqueRef:NULL'] = rootNode

        for h in hosts:
            hostNode = treeModel.HostNode(h, rootNode)
            self.poolDataIndex['hostIndex'][h['OpaqueRef']] = hostNode   # set up host dict

        for v in vms:
            if v['power_state'] == 'Running':
                parentRef = v['resident_on']
            else:
                parentRef = v['affinity']

            if self.poolDataIndex['hostIndex'].get(parentRef) is None:
                # extreme case, no host 'owns' this vm, then put it under the root node
                vmNode = treeModel.VMNode(v, parent=rootNode)
            else:
                vmNode = treeModel.VMNode(v, parent=self.poolDataIndex['hostIndex'][parentRef])

            self.poolDataIndex['vmIndex'][v['OpaqueRef']] = vmNode   # set up vm dict

            # log file
            with open(v['name_label'] + '.txt', 'w') as f:
                    f.write(json.dumps(v, indent=4, cls=ComplexEncoder))

        self.poolTreeModel = treeModel.PoolTreeModel(rootNode)

        self.ui.treeView.setModel(self.poolTreeModel)
        self.ui.treeView.expandAll()

    def onTreeItemClicked(self):
        '''handler of click on treeViewItem'''

        QModelIndex = self.ui.treeView.selectedIndexes()[0]

        if not QModelIndex.isValid():
            return

        node = QModelIndex.internalPointer()

        if node.type() == 'VM':
            tabIndex = self.ui.tabWidget.currentIndex()
            if tabIndex == 0:  # information tab
                self.refreshVMInformation(node.data())
            elif tabIndex == 1:  # statistic tab
                pass
            elif tabIndex == 2:  # log tab
                pass

    def refreshVMInformation(self, data):
        '''refresh the data when click on a vm in the treeView

        Note:
            currently, show the following information:
                描述 -> name_description
                uuid -> uuid
                名称 -> name_label
                内部引用 -> OpaqueRef
                CPU数量 -> VCPUs_at_startup
                状态 -> power_state
                分配内存 -> memory_target

            for each field name, for example, xxx,
            there should be a widget with the object name 'lineEdit_xxx' to hold the data

        '''
        fields = [
            'name_label',
            'name_description',
            'uuid',
            'is_control_domain',
            'power_state',
            'tags',
            'OpaqueRef',
            'VCPUs_at_startup',
            'memory_target'
        ]

        for i in fields:
            obj = data[i]
            if isinstance(obj, str):
                self.ui.tabInformation.findChild(QLineEdit, 'lineEdit_' + i).setText(data[i])
            elif isinstance(obj, bool):
                self.ui.tabInformation.findChild(QLineEdit, 'lineEdit_' + i).setText(str(obj))
            elif isinstance(obj, list):
                self.ui.tabInformation.findChild(QLineEdit, 'lineEdit_' + i).setText('/'.join(obj))

    def buildDataGraph(self):
        '''initialize all data graphics
        this will initialize two main data graphic, including data monitoring and data statistics
        '''
        #
        self.liveDataGraph = LiveDataGraph(self, background='#FFFFFF')
        self.ui.verticalLayout_6.addWidget(self.liveDataGraph)

        self.statisticDataGraph = StatisticDataGraph(self, background='#FFFFFF')
        self.ui.verticalLayout_8.addWidget(self.statisticDataGraph)

    def generateStatistic(self):
        paramFromTime = int(time.mktime(self.ui.dateTimeEditFrom.dateTime().toPyDateTime().timetuple()))
        paramToTime = int(time.mktime(self.ui.dateTimeEditTo.dateTime().toPyDateTime().timetuple()))
        if paramFromTime >= paramToTime:
            return

        # data structure
        data = [[], []]

        # get parameters
        paramK = self.ui.doubleSpinBoxK.value()
        paramT = 5   # T
        formula = lambda t, c, m, k: t * (c + k * m)

        totalEnergy = 0
        urlParam = {'start': paramFromTime, 'end': paramToTime}
        parser = RRDUpdates()
        for ip in [x.ip() for x in self.poolDataIndex['hostIndex'].values() if x.type() == 'HOST']:
            totalEnergyPerIp = 0
            dataPerIp = [[], []]

            # query the data from host
            parser.refresh(self.xenManager.get_session_ref(), urlParam, server='http://' + ip)

            # parse data
            for row in range(0, parser.get_nrows()):
                paramM = (parser.get_host_data('memory_total_kib', row) - parser.get_host_data('memory_free_kib', row)) / 1024   # KB->MB
                paramC = parser.get_host_data('cpu_avg', row) * 100
                totalEnergyPerIp = totalEnergyPerIp + formula(paramT, paramC, paramM, paramK)

                dataPerIp[0].append(parser.get_row_time(row))
                dataPerIp[1].append(totalEnergyPerIp)

            # update the whole data
            if len(data[0]) == 0:
                data[0] = dataPerIp[0][:]
                data[1] = dataPerIp[1][:]
            else:
                data[1] = [data[1][index] + x for index, x in enumerate(dataPerIp[1][:len(data[1])])]

        self.statisticDataGraph.renderGraph(x=data[0][:len(data[1])], y=data[1])
        print data[0]
        print data[1]

        self.ui.labelTotalEnergy.setText(str('{0}Ec W'.format(data[1][-1])))

        self.updateStatus('分析完成.', 2000)

    def updateProgress(self, value):
        '''update the main progress'''
        if 0 <= value <= 100:
            self.ui.progressBar.setValue(value)

    def updateStatus(self, text, delay=0):
        '''update the text of statusBar'''
        self.ui.statusBar.showMessage(self.tr(text), delay)

    def updateLog(self, log):
        self.ui.plainTextLog.appendPlainText('{0}\n{1}'.format(time.strftime('%H:%M:%S', time.localtime(time.time())), self.tr(log)))

    '''
    ui stuff end
    '''

    def takeResult(self, result):
        r = result.toPyObject()[0]  # !!! notice that result is immutable container

        if r['status'] == 'success':
            self.updateStatus('操作成功。')
        elif r['status'] == 'failure':
            self.updateStatus('操作失败。' + str(r['error']))

        self.operationLock = False

    '''
    actions start
    '''
    def onActionConnect(self):
        dialog = LoginWindow(self)
        if dialog.exec_():
            self.poolMasterInfo = dialog.getPoolMasterInfo()
            try:
                self.xenManager.connect(
                    self.poolMasterInfo['ip'],
                    self.poolMasterInfo['username'],
                    self.poolMasterInfo['password']
                )
            except XenManager.manager.ManagerError, e:
                self.ui.statusBar.showMessage(self.tr('连接失败，' + str(e)))
            else:
                self.ui.statusBar.showMessage(self.tr('连接成功。正在获取虚拟机信息……'))

                # fill treeview with data
                self.buildTreeView(self.xenManager.get_hosts(), self.xenManager.get_vms())

                # build up QActions list for migrating
                for hostRef, hostNode in self.poolDataIndex['hostIndex'].items():
                    if hostNode.data() is None:
                        continue
                    hostAction = QAction(hostNode.name(), self)
                    self.ui.menuVMMigrate.addAction(hostAction)
                    self.migrateMapper.setMapping(hostAction, hostRef)
                    hostAction.triggered.connect(self.migrateMapper.map)

                self.migrateMapper.mapped['QString'].connect(self.asyncMigrate)

                # begin to monitoring state of vm
                self.stateMonitorTimer.start(2000)

                # begin to acquire data
                self.liveDataGraph.bindSession(self.xenManager.get_session_ref())
                self.dataMonitorTimer.start(5000)

                # enable disconnect action
                self.ui.actionDisconnect.setEnabled(True)

                # notify the user
                self.ui.statusBar.showMessage(self.tr('已取得虚拟机信息。'), 2000)

    def onActionDisconnect(self):
        if self.xenManager.is_connected():
            # stop monitoring and clear all data
            self.stateMonitorTimer.stop()
            self.dataMonitorTimer.stop()
            self.liveDataGraph.unbindSession()
            self.xenManager.disconnect()
            self.poolMasterInfo = None
            self.poolTreeModel.clear()
            self.poolDataIndex = {}.fromkeys(('hostIndex', 'vmIndex'))
            self.operationLock = False
            self.ui.actionDisconnect.setEnabled(False)
            self.ui.menuVMMigrate.clear()
        self.ui.statusBar.showMessage(self.tr('已经断开连接。'))

    def onActionQuit(self):
        self.onActionDisconnect()
        self.close()

    def onActionVMMigrate(self, host_ref):
        self.t = task.Task(
            self.xenManager,
            self.xenManager.shutdown_vm,
            (
                self.poolTreeModel.data(self.ui.treeView.selectedIndexes()[0], Qt.UserRole),
                host_ref
            )
        )
        self.connect(self.t, SIGNAL('updateProgress(int)'), self.updateProgress)
        self.connect(self.t, SIGNAL('result(QVariant)'), self.takeResult)
        self.t.start()

    def menuMigrateToShow(self):
        '''figure out which host can receive current vm
        '''
        # TODO finish code
        pass

    def saveLogToFile(self):
        with open('log.txt', 'w') as log:
            log.write(self.ui.plainTextLog.toPlainText())

        self.updateStatus(self.tr('已输出到目录下的log.txt。'), 2000)

    '''
    actions end
    '''
