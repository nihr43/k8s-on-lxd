lint:
	black .
	flake8 kxd/ --ignore E501

install: lint
	pip3 install --user . --break-system-packages
