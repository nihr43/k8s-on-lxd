# kxd

Provision a k8s cluster on lxd qemu-kvm instances using microk8s.

This cluster is built to mirror my own physical hardware for "staging" and research purposes; [minikube](https://github.com/kubernetes/minikube) is probably of more use to you.

## usage

It is assumed your user is already configured to use lxd.

kxd can be installed using pip:

```
pip3 install git+https://github.com/nihr43/kxd --break-system-packages
```

or run as a directory:

```
python3 kxd/ --help
```

Create a two node cluster:

```
$ kxd --create -n2
create_node(): creating node k8s-lxd-303b5
wait_until_ready(): waiting for lxd agent on k8s-lxd-303b5
bootstrap_node(): snapd installed
bootstrap_node(): root partition extended
__init__(): Fetching snap "microk8s"
Fetching assertions for "microk8s"
Install the snap with:
   snap ack ../tmp/microk8s.assert
   snap install ../tmp/microk8s.snap

__init__(): retrieving initial snap
install_snap(): 2023-01-26T05:14:23Z INFO Waiting for automatic snapd restart...
microk8s v1.26.0 from Canonical** installed
assert_kubernetes_ready(): waiting for k8s to become ready on k8s-lxd-303b5
create_node(): creating node k8s-lxd-77c97
wait_until_ready(): waiting for lxd agent on k8s-lxd-77c97
bootstrap_node(): snapd installed
bootstrap_node(): root partition extended
install_snap(): 2023-01-26T05:16:00Z INFO Waiting for automatic snapd restart...
microk8s v1.26.0 from Canonical** installed
assert_kubernetes_ready(): waiting for k8s to become ready on k8s-lxd-77c97
join_cluster(): generated join token: 10.139.0.159:25000/e94fd0ab0240f013f86f0737e711318a/75bcfcd2e7bd
assert_kubernetes_ready(): waiting for k8s to become ready on k8s-lxd-77c97
join_cluster(): k8s-lxd-77c97 successfully joined cluster
privileged_main(): cluster default created with members:
privileged_main(): k8s-lxd-303b5
privileged_main(): k8s-lxd-77c97
fetch_kubeconfig(): to access cluster, execute:
export KUBECONFIG=$(realpath kubeconfig.yml)
```

when a cluster name is not provided, 'default' is used:

```
$ kxd --list
default | 2 nodes
```

The resulting cluster looks like this in lxd:

```
$ lxc ls
+------------------+---------+-----------------------------+-------------------------------------------------+-----------------+-----------+
|       NAME       |  STATE  |             IPV4            |                      IPV6                       |      TYPE       | SNAPSHOTS |
+------------------+---------+-----------------------------+-------------------------------------------------+-----------------+-----------+
| k8s-lxd-77c97    | RUNNING | 10.139.0.174 (enp5s0)       | fd42:64fd:9854:7831:216:3eff:fe76:84a (enp5s0)  | VIRTUAL-MACHINE | 0         |
|                  |         | 10.1.196.128 (vxlan.calico) |                                                 |                 |           |
+------------------+---------+-----------------------------+-------------------------------------------------+-----------------+-----------+
| k8s-lxd-303b5    | RUNNING | 10.139.0.159 (enp5s0)       | fd42:64fd:9854:7831:216:3eff:fe9a:cec2 (enp5s0) | VIRTUAL-MACHINE | 0         |
|                  |         | 10.1.36.64 (vxlan.calico)   |                                                 |                 |           |
+------------------+---------+-----------------------------+-------------------------------------------------+-----------------+-----------+
```

To access the cluster using `kubectl`, a kubeconfig file is provided in the working directory.
The following will inform your kubectl to use this config; for life of your terminal.
This hint is also provided on stdout:

```
$ export KUBECONFIG=$(realpath kubeconfig.yml)
$ kubectl get nodes
NAME            STATUS   ROLES    AGE     VERSION
k8s-lxd-303b5   Ready    <none>   10m     v1.26.0
k8s-lxd-77c97   Ready    <none>   7m57s   v1.26.0
```

if you have multiple clusters, you can retrieve the kubeconfig for a given cluster at any time:

```
$ kubectl get nodes
NAME            STATUS   ROLES    AGE   VERSION
k8s-lxd-303b5   Ready    <none>   20m   v1.26.0
k8s-lxd-77c97   Ready    <none>   17m   v1.26.0
$ kxd --list
default | 2 nodes
readme | 4 nodes
$ kxd --kubectl readme
fetch_kubeconfig(): to access cluster, execute:
export KUBECONFIG=$(realpath kubeconfig.yml)
$ kubectl get nodes
NAME            STATUS   ROLES    AGE     VERSION
k8s-lxd-74e19   Ready    <none>   9m36s   v1.26.0
k8s-lxd-83ff4   Ready    <none>   16m     v1.26.0
k8s-lxd-1138e   Ready    <none>   14m     v1.26.0
k8s-lxd-9302d   Ready    <none>   11m     v1.26.0
```

delete a cluster:

```
$ kxd --delete mycluster
privileged_main(): deleting cluster mycluster
delete(): deleting node k8s-lxd-20f22
delete(): deleting node k8s-lxd-c21a7
delete(): deleting node k8s-lxd-035ea
delete(): deleting node k8s-lxd-6e625
delete(): deleting node k8s-lxd-e09b2
```
