ACCOUNT=nandyio
IMAGE=chore-google-daemon
VERSION?=0.1
NAME=$(IMAGE)-$(ACCOUNT)
NETWORK=klot.io
VOLUMES=-v ${PWD}/lib/:/opt/service/lib/ \
		-v ${PWD}/bin/:/opt/service/bin/ \
		-v ${PWD}/test/:/opt/service/test/ \
		-v ${PWD}/secret/:/opt/service/secret/
ENVIRONMENT=-e SLEEP=5 \
			-e RANGE=300 \
			-e REDIS_HOST=redis-klotio \
			-e REDIS_PORT=6379 \
			-e REDIS_PREFIX=nandy.io/chore-google \
			-e CHORE_API=http://chore-api.nandyio

.PHONY: cross build network shell test run start stop push secret install update remove reset tag

cross:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset

build:
	docker build . -t $(ACCOUNT)/$(IMAGE):$(VERSION)

network:
	-docker network create klot-io

shell: network
	-docker run -it --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION) sh

test:
	docker run -it $(VOLUMES) $(ACCOUNT)/$(IMAGE):$(VERSION) sh -c "coverage run -m unittest discover -v test && coverage report -m --include lib/*.py"

run: network
	docker run --rm --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION)

start: network
	docker run -d --name=$(NAME) --network=$(NETWORK) $(VOLUMES) $(ENVIRONMENT) $(ACCOUNT)/$(IMAGE):$(VERSION)

stop:
	docker rm -f $(NAME)

push:
	docker push $(ACCOUNT)/$(IMAGE):$(VERSION)

secret:
	kubectl create -f kubernetes/namespace.yaml
	kubectl -n chore-google-nandy-io create secret generic secret --from-file=secret/calendar.json --from-file=secret/token.json

install:
	kubectl create -f kubernetes/namespace.yaml
	kubectl create -f kubernetes/daemon.yaml

update:
	kubectl replace -f kubernetes/daemon.yaml

remove:
	-kubectl delete -f kubernetes/daemon.yaml
	-kubectl delete -f kubernetes/namespace.yaml

reset: remove install

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags
