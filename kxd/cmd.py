#!/usr/bin/python3

import json

try:
    from . import models
except ImportError:
    import models


def cleanup(client, log):
    instances_to_delete = []
    for i in client.instances.all():
        if i.name.startswith("k8s-lxd"):
            log.info("found " + i.name)
            instances_to_delete.append(i)

    for i in instances_to_delete:
        i.stop(wait=True)
        i.delete()
        log.info(i.name + " deleted")


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
            if unmarshalled_json["k8s-lxd-managed"]:
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


def main():
    import pylxd
    import logging
    import argparse

    logging.basicConfig(format="%(funcName)s(): %(message)s")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--create", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument(
        "--channel", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument("-n", type=int, default=3)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--block-devices", type=int, default=0)
    parser.add_argument(
        "--delete", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument(
        "--start", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument(
        "--stop", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument(
        "--kubectl", action="store", nargs="?", default=None, const="default"
    )
    parser.add_argument("--list", "-l", action="store_true")
    args = parser.parse_args()

    client = pylxd.Client()

    if args.start:
        clusters = get_clusters(client, logger)
        for c in clusters:
            if c.name == args.start:
                c.start(client, logger)
    elif args.stop:
        clusters = get_clusters(client, logger)
        for c in clusters:
            if c.name == args.stop:
                c.stop(client, logger)

    if args.clean:
        cleanup(client, logger)

    if args.list:
        clusters = get_clusters(client, logger)
        for c in clusters:
            print("{} | {} nodes".format(c.name, len(c.members)))

    if args.delete:
        clusters = get_clusters(client, logger)
        for c in clusters:
            if c.name == args.delete:
                logger.info("deleting cluster " + c.name)
                c.delete(client, logger, pylxd)

    if args.create:
        k8s = models.Cluster(args.create)

        if not args.channel:
            channel = "latest/stable"
        else:
            channel = args.channel

        k8s.create(args.n, channel, client, logger)
        logger.info("cluster {} created with members:".format(k8s.name))
        for m in k8s.members:
            logger.info(m.name)
        k8s.fetch_kubeconfig(logger)

    if args.kubectl:
        clusters = get_clusters(client, logger)
        for c in clusters:
            if c.name == args.kubectl:
                c.fetch_kubeconfig(logger)
