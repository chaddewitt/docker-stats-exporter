# Copyright 2015 Chad Dewitt
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

DOCKER                 ?= docker
DOCKER_REPOSITORY_NAME ?= development
DOCKER_IMAGE_NAME      ?= docker-stats-exporter
DOCKER_IMAGE_TAG       ?= $(subst /,-,$(shell git rev-parse --abbrev-ref HEAD))

VIRTUALENV     ?= virtualenv
VIRTUALENV_DIR ?= venv

all: docker

docker:
	@echo ">> building docker image"
	@$(DOCKER) build -t "$(DOCKER_REPOSITORY_NAME)/$(DOCKER_IMAGE_NAME):$(DOCKER_IMAGE_TAG)" .

venv:
	@echo ">> setting up virtualenv"
	@$(VIRTUALENV) "$(VIRTUALENV_DIR)"

requirements:
	$(VIRTUALENV_DIR)/bin/pip install -U -r requirements.txt

format:
	$(VIRTUALENV_DIR)/bin/pip install yapf
	sudo $(VIRTUALENV_DIR)/bin/yapf -i -r --style google ./src ./tests

generate-unit-tests: clean # TODO remove this once generated unit tests have been completely implemented
	pip install -U pythoscope # Note this package is installed outside the virtualenv
	pythoscope --init .
	pythoscope src/*.py

clean:
	-rm -rf .pythoscope
	-rm -rf venv
	-$(DOCKER) rmi -f $(DOCKER_IMAGE_NAME)
