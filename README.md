# k8s-on-lxd

Provision a k8s cluster on lxd qemu-kvm instances for integration testing of real-world processes.

This cluster is built to mirror my own physical hardware as much as possible; [minikube](https://github.com/kubernetes/minikube) is probably of more use to you.

## usage

It is assumed your user account is already configured to use lxd.

Create a five node cluster:

```
./k8s-on-lxd -n 5
INFO:root:creating node k8s-lxd-03c98b3e-e8d7-4f11-95b2-7ac50e09651b
INFO:root:creating node k8s-lxd-a799493f-8f9e-4d52-83a9-a2538ca15381
INFO:root:creating node k8s-lxd-28ca2599-f948-4dad-8455-3d4d58ee6ecb
INFO:root:creating node k8s-lxd-3f301501-fc3d-4794-8bb0-a755a6e51533
INFO:root:creating node k8s-lxd-06ba0c0d-aaff-4753-bc77-aa91d43b5e57
```

Clean up when you're done:

```
./k8s-on-lxd --clean
INFO:root:found k8s-lxd-03c98b3e-e8d7-4f11-95b2-7ac50e09651b
INFO:root:found k8s-lxd-a799493f-8f9e-4d52-83a9-a2538ca15381
INFO:root:found k8s-lxd-28ca2599-f948-4dad-8455-3d4d58ee6ecb
INFO:root:found k8s-lxd-3f301501-fc3d-4794-8bb0-a755a6e51533
INFO:root:found k8s-lxd-06ba0c0d-aaff-4753-bc77-aa91d43b5e57
INFO:root:k8s-lxd-03c98b3e-e8d7-4f11-95b2-7ac50e09651b deleted
INFO:root:k8s-lxd-a799493f-8f9e-4d52-83a9-a2538ca15381 deleted
INFO:root:k8s-lxd-28ca2599-f948-4dad-8455-3d4d58ee6ecb deleted
INFO:root:k8s-lxd-3f301501-fc3d-4794-8bb0-a755a6e51533 deleted
INFO:root:k8s-lxd-06ba0c0d-aaff-4753-bc77-aa91d43b5e57 deleted
```
