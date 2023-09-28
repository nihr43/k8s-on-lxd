from kxd import models
from kxd import utils


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
        clusters = utils.get_clusters(client, logger)
        for c in clusters:
            if c.name == args.start:
                c.start(client, logger)
    elif args.stop:
        clusters = utils.get_clusters(client, logger)
        for c in clusters:
            if c.name == args.stop:
                c.stop(client, logger)

    if args.clean:
        clusters = utils.get_clusters(client, logger)
        for c in clusters:
            c.delete(client, logger, pylxd)

    if args.list:
        clusters = utils.get_clusters(client, logger)
        for c in clusters:
            print("{} | {} nodes".format(c.name, len(c.members)))

    if args.delete:
        clusters = utils.get_clusters(client, logger)
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
        clusters = utils.get_clusters(client, logger)
        for c in clusters:
            if c.name == args.kubectl:
                c.fetch_kubeconfig(logger)
