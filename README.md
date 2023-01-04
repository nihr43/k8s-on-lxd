# k8s-on-lxd

Provision a k8s cluster on lxd qemu-kvm instances for integration testing of real-world processes.

This cluster is built to mirror my own physical hardware as much as possible; [minikube](https://github.com/kubernetes/minikube) is probably of more use to you.

## usage

It is assumed your user account is already configured to use lxd.

Create a two node cluster:

```
$ ./k8s-on-lxd -n2
INFO:k8s-on-lxd:creating node k8s-lxd-554ae2
INFO:k8s-on-lxd:waiting for lxd agent on k8s-lxd-554ae2
INFO:k8s-on-lxd:snapd installed
INFO:k8s-on-lxd:2023-01-03T22:21:22Z INFO Waiting for automatic snapd restart...
microk8s (1.25/stable) v1.25.4 from Canonical** installed

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-554ae2
INFO:k8s-on-lxd:Error from server (NotFound): nodes "k8s-lxd-554ae2" not found

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-554ae2
INFO:k8s-on-lxd:Error from server (NotFound): nodes "k8s-lxd-554ae2" not found

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-554ae2
INFO:k8s-on-lxd:creating node k8s-lxd-125843
INFO:k8s-on-lxd:waiting for lxd agent on k8s-lxd-125843
INFO:k8s-on-lxd:snapd installed
INFO:k8s-on-lxd:2023-01-03T22:23:01Z INFO Waiting for automatic snapd restart...
microk8s (1.25/stable) v1.25.4 from Canonical** installed

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-125843
INFO:k8s-on-lxd:Error from server (NotFound): nodes "k8s-lxd-125843" not found

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-125843
INFO:k8s-on-lxd:Error from server (NotFound): nodes "k8s-lxd-125843" not found

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-125843
INFO:k8s-on-lxd:generated join token: 10.139.0.193:25000/6bd5a5a0041ff90b20c832fee6b364cc/686045620c28
INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-125843
INFO:k8s-on-lxd:Error from server (NotFound): nodes "k8s-lxd-125843" not found

INFO:k8s-on-lxd:waiting for k8s to become ready on k8s-lxd-125843
INFO:k8s-on-lxd:k8s-lxd-125843 successfully joined cluster
INFO:k8s-on-lxd:to access cluster, execute: export KUBECONFIG=$(realpath kubeconfig.yml)
```

The resulting cluster looks like this:

```
$ lxc ls
+------------------+---------+----------------------------+-------------------------------------------------+-----------------+-----------+
|       NAME       |  STATE  |            IPV4            |                      IPV6                       |      TYPE       | SNAPSHOTS |
+------------------+---------+----------------------------+-------------------------------------------------+-----------------+-----------+
| k8s-lxd-554ae2   | RUNNING | 10.139.0.193 (enp5s0)      | fd42:64fd:9854:7831:216:3eff:fefb:fd0a (enp5s0) | VIRTUAL-MACHINE | 0         |
|                  |         | 10.1.212.64 (vxlan.calico) |                                                 |                 |           |
+------------------+---------+----------------------------+-------------------------------------------------+-----------------+-----------+
| k8s-lxd-125843   | RUNNING | 10.139.0.194 (enp5s0)      | fd42:64fd:9854:7831:216:3eff:fec1:2c60 (enp5s0) | VIRTUAL-MACHINE | 0         |
|                  |         | 10.1.33.192 (vxlan.calico) |                                                 |                 |           |
+------------------+---------+----------------------------+-------------------------------------------------+-----------------+-----------+

```

To access the cluster using `kubectl`, a kubeconfig file is provided in the working directory.
The following will inform your kubectl to use this config; for life of your terminal.
This hint is also provided on stdout:

```
$ export KUBECONFIG=$(realpath kubeconfig.yml)
$ kubectl get nodes
k8s-lxd-554ae2   Ready    <none>   3m39s   v1.25.4
k8s-lxd-125843   Ready    <none>   69s     v1.25.4
```

Clean up when you're done:

```
$ ./k8s-on-lxd --clean
INFO:k8s-on-lxd:found k8s-lxd-554ae2
INFO:k8s-on-lxd:found k8s-lxd-125843
INFO:k8s-on-lxd:k8s-lxd-554ae2 deleted
INFO:k8s-on-lxd:k8s-lxd-125843 deleted
```
