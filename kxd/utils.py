import uuid
import time
import json

from kxd import models


def get_clusters(client, log):
    """
    find clusters from json embedded in Instance descriptions.
    using these cluster names, construct and return list of Cluster objects.
    """
    cluster_tags_found = []
    for i in client.instances.all():
        cluster_tags_found.append(i.description)

    distinct_tags = []
    for t in cluster_tags_found:
        try:
            unmarshalled_json = json.loads(t)
            if unmarshalled_json["kxd-managed"]:
                if unmarshalled_json["name"] not in distinct_tags:
                    distinct_tags.append(unmarshalled_json["name"])
        except json.decoder.JSONDecodeError:
            continue

    clusters = []
    for t in distinct_tags:
        c = models.Cluster(t)
        c.fetch_members(client)
        clusters.append(c)
    return clusters


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
        raise RuntimeError(err.stderr)
    log.info(err.stdout)

    err = instance.execute(
        ["snap", "install", "/root/{}.snap".format(snap.name), "--classic"]
    )
    if err.exit_code != 0:
        raise RuntimeError(err.stderr)
    log.info(err.stdout)


def assert_kubernetes_ready(instance, log):
    """
    shutting down before the microk8s finishes bootstrapping appears to trash the installation.
    here we wait for `/snap/bin/microk8s kubectl` to become executable, and then for the
    kubernetes 'node' to become 'ready'.
    """
    count = 30
    for i in range(count):
        log.info("waiting for k8s to become ready on {}".format(instance.name))
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
            raise RuntimeError("timed out waiting for microk8s")
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
        raise RuntimeError("unable to generate cluster join token")
    add_node_json = json.loads(add_node.stdout)
    join_token = add_node_json["urls"][0]
    log.info("generated join token: {}".format(join_token))

    join_node.execute(["/snap/bin/microk8s", "join", join_token])
    assert_kubernetes_ready(join_node, log)
    log.info("{} successfully joined cluster".format(join_node.name))


def create_node(client, block_devices, log):
    name = "kxd-{}".format(str(uuid.uuid4())[0:5])
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
    log.info("creating node {}".format(name))
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
                raise RuntimeError("timed out waiting")
            log.info("waiting for lxd agent on {}".format(instance.name))
        except ConnectionResetError:
            pass
        except BrokenPipeError:
            pass
        time.sleep(2)
