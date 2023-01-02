import uuid


def create_node(client, logging):
    name = 'k8s-lxd-' + str(uuid.uuid4())
    config = {'name': name,
              'source': {'type': 'image',
                         'mode': 'pull',
                         'server': 'https://images.linuxcontainers.org',
                         'protocol': 'simplestreams',
                         'alias': 'debian/12'},
              'config': {'limits.cpu': '2',
                         'limits.memory': '8GB'},
              'type': 'virtual-machine'}
    logging.info('creating node ' + name)
    inst = client.instances.create(config, wait=True)
    inst.start(wait=True)
    return name


def cleanup(client, logging):
    instances_to_delete = []
    for i in client.instances.all():
        if i.name.startswith('k8s-lxd'):
            logging.info('found ' + i.name)
            instances_to_delete.append(i)

    for i in instances_to_delete:
        i.stop(wait=True)
        i.delete()
        logging.info(i.name + ' deleted')


if __name__ == '__main__':
    def privileged_main():
        import pylxd
        import logging
        import argparse

        logging.basicConfig(level=logging.INFO)
        client = pylxd.Client()

        parser = argparse.ArgumentParser()
        parser.add_argument('-n', type=int, default=3)
        parser.add_argument('--clean', action='store_true')
        args = parser.parse_args()

        if args.clean:
            cleanup(client, logging)
            exit()

        cluster_size = args.n

        for i in range(cluster_size):
            create_node(client, logging)

    privileged_main()
