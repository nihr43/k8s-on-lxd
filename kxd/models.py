import json
from pathlib import Path

try:
    from . import utils
except ImportError:
    import utils


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
            raise RuntimeError(err.stderr)
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
            node = utils.create_node(client, 0, log)
            node.description = '{"kxd-managed": true, "name": "%s"}' % self.name
            node.save(wait=True)
            utils.bootstrap_node(node, log)
            self.members.append(node)

            # only use the fist node to download the Snap
            if i == 0:
                microk8s = Snap("microk8s", channel, node, log)

            utils.install_snap(node, microk8s, log)
            utils.assert_kubernetes_ready(node, log)

            if i != 0:
                utils.join_cluster(self.members[0], node, log)

    def fetch_kubeconfig(self, log):
        """
        generates and writes a valid kubeconfig to kubeconfig.yml
        """
        cmd = self.members[0].execute(
            ["/snap/bin/microk8s", "kubectl", "config", "view", "--raw"]
        )
        if cmd.exit_code != 0:
            log.info("failed fetching kubeconfig")
            raise RuntimeError(cmd.stderr)

        # we need to swap '127.0.0.1' for an ip reachable from the host
        #   counting on enp5s0 .. [0] to be consistent for now..
        ip = self.members[0].state().network["enp5s0"]["addresses"][0]["address"]
        yaml = cmd.stdout.replace("127.0.0.1", ip)

        Path("/tmp/kxd").mkdir(parents=True, exist_ok=True)

        with open("/tmp/kxd/kubeconfig.yml", "w") as kubeconfig_yml:
            kubeconfig_yml.truncate()
            kubeconfig_yml.write(yaml)
        log.info("to access cluster, execute:")
        print("export KUBECONFIG=/tmp/kxd/kubeconfig.yml")

    def fetch_members(self, client):
        """
        fetch Instances from lxd and populate members[]
        """
        self.members = []
        for i in client.instances.all():
            try:
                js = json.loads(i.description)
                if js["kxd-managed"] is True and js["name"] == self.name:
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
                    raise RuntimeError(lxdapi_exception)
            i.delete(wait=True)
            log.info("{} deleted".format(i.name))

    def start(self, client, log):
        """
        start all nodes in a cluster
        """
        for i in self.members:
            log.info("starting node {}".format(i.name))
            i.start(wait=True)

    def stop(self, client, log):
        """
        stop all nodes in a cluster
        """
        for i in self.members:
            log.info("stopping node {}".format(i.name))
            i.stop(wait=True)
