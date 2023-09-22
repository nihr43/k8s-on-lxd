from setuptools import setup

setup(
    name="kxd",
    version="0.1",
    description="Bootstrap microk8s clusters on LXD",
    author="Nathan Hensel",
    packages=["kxd"],
    install_requires=["pylxd"],
    entry_points={
        "console_scripts": [
            "kxd = kxd.cmd:main",
        ]
    },
)
