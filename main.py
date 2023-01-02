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


if __name__ == '__main__':
    def privileged_main():
        import pylxd
        import logging

        logging.basicConfig(level=logging.INFO)
        client = pylxd.Client()

        cluster_size = 5

        for i in range(cluster_size):
            create_node(client, logging)

    privileged_main()
