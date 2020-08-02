VERSION?=0.5
TILT_PORT=26771
.PHONY: settings up down tag untag

settings:
	kubectl -n chore-google-nandy-io get configmap config -o jsonpath='{.data.settings\.yaml}' > config/settings.yaml

up:
	mkdir -p config
	echo "- op: add\n  path: /spec/template/spec/volumes/0/hostPath/path\n  value: $(PWD)/config" > tilt/config.yaml
	if test ! -f config/settings.yaml; then echo "\n!!! need settings !!!\n" && exit 1; fi
	kubectx docker-desktop
	tilt --port $(TILT_PORT) up

down:
	kubectx docker-desktop
	tilt down

tag:
	-git tag -a "v$(VERSION)" -m "Version $(VERSION)"
	git push origin --tags

untag:
	-git tag -d "v$(VERSION)"
	git push origin ":refs/tags/v$(VERSION)"