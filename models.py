import uuid
import time
import json


def bootstrap_node(instance, log):
    '''
    installs microk8s on given instance
    returns when microk8s node is "ready"
    '''
    # "(execute) returns a tuple of (exit_code, stdout, stderr).
    #  This method will block while the command is executed"
    # snapd appears to perform some bootstrapping actions after this exits
    out = instance.execute(['apt', 'install', 'snapd', '-y'])
    log.info('snapd installed')
    instance.execute(['growpart', '/dev/sda', '2'])
    instance.execute(['resize2fs', '/dev/sda2'])
    log.info('root partition extended')

    '''
    snapd performs some bootstrapping asynchronously with 'apt install',
    so subsequent 'snap install's can fail for a monent.
    '''
    count = 30
    for i in range(count):
        out = instance.execute(['snap', 'install', 'microk8s', '--classic'])
        if out.exit_code == 0:
            log.info(out.stdout)
            break
        if i == count-1:
            log.info('timed out waiting for snapd')
            exit(1)
        log.info(out.stderr)
        time.sleep(2)
    assert_kubernetes_ready(instance, log)


def assert_kubernetes_ready(instance, log):
    '''
    shutting down before the microk8s finishes bootstrapping appears to trash the installation.
    here we wait for `/snap/bin/microk8s kubectl` to become executable, and then for the
    kubernetes 'node' to become 'ready'.
    '''
    count = 30
    for i in range(count):
        log.info('waiting for k8s to become ready on ' + instance.name)
        out = instance.execute(['/snap/bin/microk8s', 'kubectl', 'wait', '--for=condition=ready', 'node', instance.name])
        if out.exit_code == 0:
            break
        if i == count-1:
            log.info('timed out waiting for microk8s')
            exit(1)
        log.info(out.stderr)
        time.sleep(2)


def join_cluster(leader, join_node, log):
    '''
    given the leader node and a node to be joined,
    add the new node and wait until ready.
    both are of type lxd instance.
    '''
    add_node = leader.execute(['/snap/bin/microk8s', 'add-node', '--format=json'])
    if add_node.exit_code != 0:
        log.info('unable to generate cluster join token')
        exit(1)
    add_node_json = json.loads(add_node.stdout)
    join_token = add_node_json["urls"][0]
    log.info('generated join token: ' + join_token)

    join_node.execute(['/snap/bin/microk8s', 'join', join_token])
    assert_kubernetes_ready(join_node, log)
    log.info(join_node.name + ' successfully joined cluster')


def create_node(client, block_devices, log):
    name = 'k8s-lxd-' + str(uuid.uuid4())[0:5]
    config = {'name': name,
              'source': {'type': 'image',
                         'mode': 'pull',
                         'server': 'https://images.linuxcontainers.org',
                         'protocol': 'simplestreams',
                         'alias': 'ubuntu/22.10'},
              'config': {'limits.cpu': '2',
                         'limits.memory': '8GB'},
              'type': 'virtual-machine'}
    log.info('creating node ' + name)
    inst = client.instances.create(config, wait=True)
    '''
    # these are ~additional~ block devices
    if block_devices != 0:
        storage_pool = client.storage_pools.get('default')
        for d in range(block_devices):
            storage_pool.volumes.create({'name': 'k8sblock', 'type': 'virtual-machine'})
    '''
    inst.start(wait=True)
    wait_until_ready(inst, log)
    return inst


def wait_until_ready(instance, log):
    '''
    waits until an instance is executable
    '''
    count = 30
    for i in range(count):
        if instance.execute(['hostname']).exit_code == 0:
            break
        if i == count-1:
            log.info('timed out waiting')
            exit(1)
        log.info('waiting for lxd agent on ' + instance.name)
        time.sleep(2)


class Cluster:
    '''
    a k8s cluster
    '''
    def __init__(self, name):
        self.name = name
        self.members = []  # list of lxd Instances https://github.com/lxc/pylxd/blob/master/pylxd/models/instance.py

    def create(self, size, client, log):
        '''
        a cluster object can exist without having been 'created'.
        given a cluster, create the nodes in lxd.
        '''
        for i in range(size):
            node = create_node(client, 0, log)
            node.description = '{"k8s-lxd-managed": true, "name": "%s"}'%self.name
            node.save(wait=True)
            bootstrap_node(node, log)
            self.members.append(node)
            if i != 0:
                join_cluster(self.members[0], node, log)

    def fetch_kubeconfig(self, log):
        cmd = self.members[0].execute(['/snap/bin/microk8s', 'kubectl', 'config', 'view', '--raw'])
        if cmd.exit_code != 0:
            log.info('failed fetching kubeconfig')
            log.info(cmd.stderr)
            exit(1)

        # we need to swap '127.0.0.1' for an ip reachable from the host
        #   counting on enp5s0 .. [0] to be consistent for now..
        ip = self.members[0].state().network['enp5s0']['addresses'][0]['address']
        yaml = cmd.stdout.replace('127.0.0.1', ip)
        return yaml

    def fetch_members(self, client):
        '''
        fetch Instances from lxd and populate members[]
        '''
        self.members = []
        for i in client.instances.all():
            try:
                js = json.loads(i.description)
                if js["k8s-lxd-managed"] is True and js["name"] == self.name:
                    self.members.append(i)
            except json.decoder.JSONDecodeError:
                continue

    def delete(self, client, log):
        '''
        delete a cluster
        '''
        for i in self.members:
            log.info('deleting node ' + i.name)
            i.stop(wait=True)
            i.delete(wait=True)

    def start(self, client, log):
        '''
        start all nodes in a cluster
        '''
        for i in self.members:
            log.info('starting node ' + i.name)
            i.start(wait=True)

    def stop(self, client, log):
        '''
        stop all nodes in a cluster
        '''
        for i in self.members:
            log.info('stopping node ' + i.name)
            i.stop(wait=True)
