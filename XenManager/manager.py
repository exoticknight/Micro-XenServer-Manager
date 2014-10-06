# -*- coding: utf-8 -*-
'''
@auther: exoticknight, JP

!!VM_BASIC_INFORMATION
VM_BASIC_INFORMATION is a dict, including the "ref" as the key, the "ref" of resident host, the "name_label" and the "uuid"
e.g.
{
'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf':
    {
    'resident_on': 'OpaqueRef:5c986432-c0af-cb32-ed14-e0e4572ba603',
    'name_label': 'Windows XP SP3 (32-bit) (2)',
    'uuid': '1c9fc8c4-7a9e-23d0-beab-750e512ef2bb'
    },
'OpaqueRef:70b5ec6c-935d-69bf-92d9-3340bfe403d9':
    {
    'resident_on': 'OpaqueRef:af45a618-ec08-0983-e2ea-d920c051e97e',
    'name_label': 'Windows XP SP3 (32-bit) (1)',
    'uuid': '98b8007e-35b3-e19b-19e3-b64ed8ecdfeb'
    }
}

!!HOST_BASIC_INFORMATION
HOST_BASIC_INFORMATION is a dict, including "name_label", "address", "resident_VMs"
e.g.
{
'OpaqueRef:5c986432-c0af-cb32-ed14-e0e4572ba603':
    {
    'address': '192.168.1.251',
    'name_label': 'xenserver-gcotucod',
    'resident_VMs': ['OpaqueRef:4165e1de-14f7-789d-b0c3-ac750e2b31cf']
    },
'OpaqueRef:af45a618-ec08-0983-e2ea-d920c051e97e':
    {
    'address': '192.168.1.252',
    'name_label': 'xenserver-wdhqtslp',
    'resident_VMs': ['OpaqueRef:da4c572c-b3ea-ca32-b989-c7219601cb44']
    }
}

provided APIs:
---session control---
    void connect(string ip, string username, string password, number cache_timeout=30)
    void disconnect()

---vm control---
    list get_running_vm()
    list get_halted_vm()
    task start_vm(ref vm_ref)
    void suspend_vm(ref vm_ref, bool force_suspend=False)
    void resume_vm(ref vm_ref)
    void shutdown_vm(ref vm_ref, bool force_shutdown=False)
    void reboot_vm(ref vm_ref, bool force_reboot=False)
    task migrate_vm(ref vm_ref, ref host_ref)

---host control---
    list get_hosts()
    void start_host(ref host_ref)
    void shutdown_host(ref host_ref)
    void reboot_host(ref host_ref)
'''

import time
import XenAPI


class ManagerError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class SessionController():
    def __init__(self, url, user, pwd):
        self._url = url
        self._user = user
        self._pwd = pwd
        self.session = None
        # cache
        self._cache = {}.fromkeys(('hosts', 'vms'))

    def get_connection(self):
        '''get the session from the master of the pool'''
        try:
            self.session = XenAPI.Session(self._url)
            self.session.xenapi.login_with_password(self._user, self._pwd)
        except XenAPI.Failure, e:
            raise ManagerError, e

    def abandon_connection(self):
        '''close the session'''
        try:
            self.session.xenapi.session.logout()
        except XenAPI.Failure, e:
            raise ManagerError, e


# Manager
class Manager():

    def __init__(self):
        # cache of VM_BASIC_INFORMATION
        self._cache_data = {}.fromkeys(('hosts', 'vms'))
        # timestamp of current cache data
        self._cache_timeout = 0

        self._sessionController = None
        self.xenapi = None

    '''
    ---session control APIs start---
    '''

    def connect(self, ip, username, password, cache_timeout=30):
        '''create a session and connect to a remote pool master

        Args:
            ip: stander ipv4, xxx.xxx.xxx.xxx
            username: username required for login
            password: password required for login
            cache_timeout: cache timeout, default 30s
        '''
        # disconnect first
        if self._sessionController:
            self.disconnect()
            self._cache_data = {}
        try:
            # set up a session
            self._sessionController = SessionController('http://' + ip, username, password)
            self._sessionController.get_connection()
            self.xenapi = self._sessionController.session.xenapi
            self._cache_timeout = cache_timeout
        except XenAPI.Failure, e:
            self.xenapi = None
            self._cache_timeout = 0
            raise ManagerError, e

    def disconnect(self):
        '''disconnect from remote pool master'''
        try:
            self._sessionController.abandon_connection()
        except XenAPI.Failure, e:
            raise ManagerError, e
        finally:
            # reset session and api
            self._sessionController = None
            self.xenapi = None

    def is_connected(self):
        return self._sessionController is not None

    def get_session_ref(self):
        return self._sessionController.session._session

    '''
    ---session control APIs end---
    '''

    '''
    ---vm control APIs start---
    '''

    def __get_vm_by_power_state(self, state, force_refresh=False):
        '''get a list of brief information about vms that in specific state

        Args:
            state: string, indicating the state of vm, either ''Running' or 'Halted'

        Return:
            the VM_BASIC_INFORMATION, see more on the top
        '''
        try:
            if force_refresh and time.time() - self._cache_timestamp < self._cache_timeout:
                return self._cache_data
            else:
                self._cache_timestamp = time.time()
                vms = []
                all_vm = self.xenapi.VM.get_all()
                for vm in all_vm:
                    record = self.xenapi.VM.get_record(vm)
                    if not record['is_control_domain'] and \
                       not 'Transfer' in record['name_label'] and \
                       not record['is_a_template'] and \
                       record['power_state'] == state:
                        record['OpaqueRef'] = vm
                        vms.append(record)
                return vms
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def get_vms(self, force_refresh=False):
        '''get all true vms in the pool

        Args:
            force_refresh indicates whether it should refresh the cache

        Return:
            the VM_BASIC_INFORMATION, see more on the top
        '''
        try:
            if force_refresh and time.time() - self._cache_timestamp < self._cache_timeout:
                return self._cache_data
            else:
                self._cache_timestamp = time.time()
                vms = []
                all_vm = self.xenapi.VM.get_all()
                for vm in all_vm:
                    record = self.xenapi.VM.get_record(vm)
                    if not record['is_control_domain'] and \
                       not 'Transfer' in record['name_label'] and \
                       not record['is_a_template']:
                        record['OpaqueRef'] = vm
                        vms.append(record)
                return vms
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def get_running_vm(self):
        '''get VM_BASIC_INFORMATION of all running VMs in the pool'''
        return self.__get_vm_by_power_state('Running')

    def get_halted_vm(self):
        '''get VM_BASIC_INFORMATION of all halted VMs in the pool'''
        return self.__get_vm_by_power_state('Halted')

    def start_vm(self, vm_ref):
        '''start a halted VM

        Args:
            vm_ref: the VM to start, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'

        Return:
            a task for async control

        Note:
            use 'void start (VM ref, bool, bool)'
            start_pause is set to be False and
            force is set to be True
        '''
        try:
            return self.xenapi.Async.VM.start(vm_ref, False, True)    # start_pause=False, force=True
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def suspend_vm(self, vm_ref):
        '''suspend VM

        Args:
            vm_ref: the VM to suspend, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'

        Returns:
            a task for async control

        Note:
            use 'void suspend (VM ref)'
        '''
        try:
            return self.xenapi.Async.VM.suspend(vm_ref)
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def resume_vm(self, vm_ref):
        '''resume a suspended VM

        start_pause is set to be False and
        force is set to be True

        Args:
            vm_ref: the VM to resume, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'

        Return:
            a task for async control

        Note:
            use 'void resume (VM ref, bool, bool)'
        '''
        try:
            return self.xenapi.Async.VM.resume(vm_ref, False, True)    # start_pause=False, force=True
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def shutdown_vm(self, vm_ref, force_shutdown=False):
        '''shutdown a VM

        Args:
            vm_ref: the VM to shutdown, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'
            force_shutdown: whether to force to shutdown

        Return:
            a task for async control

        Note:
            use 'void hard_shutdown (VM ref)' and 'void clean_shutdown (VM ref)'
        '''
        try:
            if force_shutdown:
                return self.xenapi.Async.VM.hard_shutdown(vm_ref)
            else:
                return self.xenapi.Async.VM.clean_shutdown(vm_ref)
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def reboot_vm(self, vm_ref, force_reboot=False):
        '''reboot a VM

        Args:
            vm_ref: the VM to reboot, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'
            force_reboot: whether to force to reboot

        Note:
            use 'void hard_reboot (VM ref)' and 'void clean_reboot (VM ref)'
        '''
        try:
            if force_reboot:
                self.xenapi.VM.hard_reboot(vm_ref)
            else:
                self.xenapi.VM.clean_reboot(vm_ref)
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e

    def migrate_vm(self, vm_ref, host_ref):
        '''migrate vm to the host

        migrate a running vm to another host

        Args:
            vm_ref: the vm to migrate, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'
            host_ref: the host which receive the vm, a string like 'OpaqueRef:ff43cebe-ec74-12bd-8669-4f25a145fddf'

        '''
        try:
            return self.xenapi.Async.VM.pool_migrate(vm_ref, host_ref, { 'live': 'true' })
        except XenAPI.Failure, e:
            print e
            self.disconnect()
            raise ManagerError, e


        tasks = []
        for i in range(0, len(vms)):
            vm = vms[i]
            try:
                task = self.xenapi.Async.VM.pool_migrate(vm, host, { 'live': 'true' })
            except XenAPI.Failure, e:
                print e
                self.disconnect()
                raise ManagerError, e
            tasks.append(task)
        # do a while to finish the migration
        finished = False
        records = {}
        while not(finished):
            finished = True
            for task in tasks:
                record = self.xenapi.task.get_record(task)
                records[task] = record
                if record['status'] == 'pending':
                    finished = False
            time.sleep(1)
        # judge the migration if it is all finished
        allok = True
        for task in tasks:
            record = records[task]
            if record['status'] <> 'success':
                allok = False
        if not(allok):
            print "One of the tasks didn't succeed at", time.strftime('%F:%HT%M:%SZ', time.gmtime())
            idx = 0
            # find the fail information which vm migrate
            for task in tasks:
                record = records[task]
                vm_name = self.xenapi.VM.get_name_label(vms[idx])
                host_name = self.xenapi.host.get_name_label(host)
                print '%s : %12s %s -> %s [ status: %s; result = %s; error = %s ]' % (record['uuid'], record['name_label'], vm_name, host_name, record['status'], record['result'], repr(record['error_info']))
                idx = idx + 1
            raise ManagerError
        else:
            for task in tasks:
                self.xenapi.task.destroy(task)

    '''
    ---vm control APIs end---
    '''

    '''
    ---host control APIs start---
    '''

    def get_hosts(self, force_refresh=False):
        '''get a list of all hosts with several information

        should be called after connecting to the pool master

        Return:
            the HOST_BASIC_INFORMATION, see more on the top

        '''
        hosts = []
        # check if cache exists or need to refresh
        if force_refresh or self._cache_data['hosts']:
            allhost = self._cache_data["hosts"]
        else:
            allhost = self.xenapi.host.get_all()
        for host in allhost:
            record = self.xenapi.host.get_record(host)
            record['OpaqueRef'] = host
            hosts.append(record)
        return hosts

    def start_host(self, host_ref):
        pass

    def shutdown_host(self, host_ref):
        pass

    def reboot_host(self, host_ref):
        pass

    '''
    ---host control APIs end---
    '''