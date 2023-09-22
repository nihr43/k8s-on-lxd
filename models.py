import uuid
import time
import json


def bootstrap_node(instance, log):
    """
    configures a given Instance
    blocks until snapd is "ready"
    """
    # "(execute) returns a tuple of (exit_code, stdout, stderr).
    #  This method will block while the command is executed"
    # snapd appears to perform some bootstrapping actions after this exits
    poll_cmd(instance, "apt install snapd -y", log)
    log.info("snapd installed")
    instance.execute(["growpart", "/dev/sda", "2"])
    instance.execute(["resize2fs", "/dev/sda2"])
    log.info("root partition extended")

    """
    snapd performs some bootstrapping asynchronously with 'apt install',
    so subsequent 'snap install's can fail for a moment.
    therefore we run this 'snap refesh' as a dummy-op to ensure snapd is
    up before continuing.
    """
    poll_cmd(instance, "snap refresh", log)


def poll_cmd(instance, cmd, log):
    """
    given a shell string, retries for up to a minute for return code == 1.
    """
    count = 30
    for i in range(count):
        if i == count - 1:
            raise RuntimeError(
                "timed out waiting for command `{}` on {}".format(cmd, instance.name)
            )

        log.debug("waiting for command `{}` on {}".format(cmd, instance.name))
        time.sleep(2)
        try:
            res = wrap_cmd(instance, cmd, log)
            if res.exit_code == 0:
                return res
        except RuntimeError:
            continue
        except BrokenPipeError:
            continue
        except ConnectionResetError:
            continue


def wrap_cmd(instance, cmd, log):
    log.debug("executing `{}` on {}".format(cmd, instance.name))
    res = instance.execute(cmd.split())
    if res.exit_code != 0:
        raise RuntimeError(res.stderr)
    if res.stdout:
        log.debug(res.stdout)
    return res


def install_snap(instance, snap, log):
    """
    given an Instance, install the Snap
    """
    instance.files.put("/root/{}.snap".format(snap.name), snap.snap)
    instance.files.put("/root/{}.assert".format(snap.name), snap.assertion)
    err = instance.execute(["snap", "ack", "/root/{}.assert".format(snap.name)])
    if err.exit_code != 0:
        log.info(err.stderr)
        exit(1)
    log.info(err.stdout)

    err = instance.execute(
        ["snap", "install", "/root/{}.snap".format(snap.name), "--classic"]
    )
    if err.exit_code != 0:
        log.info(err.stderr)
        exit(1)
    log.info(err.stdout)


def assert_kubernetes_ready(instance, log):
    """
    shutting down before the microk8s finishes bootstrapping appears to trash the installation.
    here we wait for `/snap/bin/microk8s kubectl` to become executable, and then for the
    kubernetes 'node' to become 'ready'.
    """
    count = 30
    for i in range(count):
        log.info("waiting for k8s to become ready on " + instance.name)
        out = instance.execute(
            [
                "/snap/bin/microk8s",
                "kubectl",
                "wait",
                "--for=condition=ready",
                "node",
                instance.name,
            ]
        )
        if out.exit_code == 0:
            break
        if i == count - 1:
            log.info("timed out waiting for microk8s")
            exit(1)
        log.info(out.stderr)
        time.sleep(2)


def join_cluster(leader, join_node, log):
    """
    given the leader node and a node to be joined,
    add the new node and wait until ready.
    both are of type lxd instance.

    channels below 1.24 do not support the '--format=json' feature.
    """
    add_node = leader.execute(["/snap/bin/microk8s", "add-node", "--format=json"])
    if add_node.exit_code != 0:
        log.info("unable to generate cluster join token")
        exit(1)
    add_node_json = json.loads(add_node.stdout)
    join_token = add_node_json["urls"][0]
    log.info("generated join token: " + join_token)

    join_node.execute(["/snap/bin/microk8s", "join", join_token])
    assert_kubernetes_ready(join_node, log)
    log.info(join_node.name + " successfully joined cluster")


def create_node(client, block_devices, log):
    name = "k8s-lxd-" + str(uuid.uuid4())[0:5]
    config = {
        "name": name,
        "source": {
            "type": "image",
            "mode": "pull",
            "server": "https://images.linuxcontainers.org",
            "protocol": "simplestreams",
            "alias": "ubuntu/mantic",
        },
        "config": {"limits.cpu": "3", "limits.memory": "8GB"},
        "type": "virtual-machine",
        "devices": {
            "root": {"path": "/", "pool": "default", "size": "16GB", "type": "disk"}
        },
    }
    log.info("creating node " + name)
    inst = client.instances.create(config, wait=True)
    """
    # these are ~additional~ block devices
    if block_devices != 0:
        storage_pool = client.storage_pools.get('default')
        for d in range(block_devices):
            storage_pool.volumes.create({'name': 'k8sblock', 'type': 'virtual-machine'})
    """
    inst.start(wait=True)
    wait_until_ready(inst, log)
    return inst


def wait_until_ready(instance, log):
    """
    waits until an instance is executable
    """
    count = 30
    for i in range(count):
        try:
            if instance.execute(["hostname"]).exit_code == 0:
                break
            if i == count - 1:
                log.info("timed out waiting")
                exit(1)
            log.info("waiting for lxd agent on " + instance.name)
        except ConnectionResetError:
            pass
        time.sleep(2)


class Snap:
    """
    a snap assertion and data file
    """

    def __init__(self, name, channel, inst, log):
        """
        to initialize a Snap, we need a name and an Instance

        i would of course prefer to get these directly from the snapcraft api, but
        it is not trivial to retrieve the assertions.
        curiously, it is trivial to pull assertions out of the snapd rest api
        itself, but we are not assuming the user has snapd running; only lxd.

        heres a one-liner to inspect snap metadata of a given channel:

        curl -H 'Snap-Device-Series: 16' http://api.snapcraft.io/v2/snaps/info/microk8s\
          | jq '."channel-map"[] | select(.channel.name | index("1.26/stable"))'
        """
        self.name = name

        err = inst.execute(
            [
                "snap",
                "download",
                self.name,
                "--channel={}".format(channel),
                "--target-directory=/tmp/",
                "--basename={}".format(self.name),
            ]
        )
        if err.exit_code != 0:
            log.info(err.stderr)
            exit(1)
        log.info(err.stdout)

        log.info("retrieving initial snap")
        self.snap = inst.files.get("/tmp/{}.snap".format(self.name))
        self.assertion = inst.files.get("/tmp/{}.assert".format(self.name))


class Cluster:
    """
    a k8s cluster
    """

    def __init__(self, name):
        self.name = name
        self.members = (
            []
        )  # list of lxd Instances https://github.com/lxc/pylxd/blob/master/pylxd/models/instance.py

    def create(self, size, channel, client, log):
        """
        a cluster object can exist without having been 'created'.
        given a cluster, create the nodes in lxd.
        """

        for i in range(size):
            node = create_node(client, 0, log)
            node.description = '{"k8s-lxd-managed": true, "name": "%s"}' % self.name
            node.save(wait=True)
            bootstrap_node(node, log)
            self.members.append(node)

            # only use the fist node to download the Snap
            if i == 0:
                microk8s = Snap("microk8s", channel, node, log)

            install_snap(node, microk8s, log)
            assert_kubernetes_ready(node, log)

            if i != 0:
                join_cluster(self.members[0], node, log)

    def fetch_kubeconfig(self, log):
        """
        generates and writes a valid kubeconfig to kubeconfig.yml
        """
        cmd = self.members[0].execute(
            ["/snap/bin/microk8s", "kubectl", "config", "view", "--raw"]
        )
        if cmd.exit_code != 0:
            log.info("failed fetching kubeconfig")
            log.info(cmd.stderr)
            exit(1)

        # we need to swap '127.0.0.1' for an ip reachable from the host
        #   counting on enp5s0 .. [0] to be consistent for now..
        ip = self.members[0].state().network["enp5s0"]["addresses"][0]["address"]
        yaml = cmd.stdout.replace("127.0.0.1", ip)

        with open("kubeconfig.yml", "w") as kubeconfig_yml:
            kubeconfig_yml.truncate()
            kubeconfig_yml.write(yaml)
        log.info("to access cluster, execute:")
        print("export KUBECONFIG=$(realpath kubeconfig.yml)")

    def fetch_members(self, client):
        """
        fetch Instances from lxd and populate members[]
        """
        self.members = []
        for i in client.instances.all():
            try:
                js = json.loads(i.description)
                if js["k8s-lxd-managed"] is True and js["name"] == self.name:
                    self.members.append(i)
            except json.decoder.JSONDecodeError:
                continue

    def delete(self, client, log, pylxd):
        """
        delete a cluster
        """
        for i in self.members:
            try:
                i.stop(wait=True)
            except pylxd.exceptions.LXDAPIException as lxdapi_exception:
                if str(lxdapi_exception) == "The instance is already stopped":
                    pass
                else:
                    log.info(lxdapi_exception)
                    exit(1)
            i.delete(wait=True)
            log.info(i.name + " deleted")

    def start(self, client, log):
        """
        start all nodes in a cluster
        """
        for i in self.members:
            log.info("starting node " + i.name)
            i.start(wait=True)

    def stop(self, client, log):
        """
        stop all nodes in a cluster
        """
        for i in self.members:
            log.info("stopping node " + i.name)
            i.stop(wait=True)
