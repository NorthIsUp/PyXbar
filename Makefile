RSS=
.PHONY: clean check_version local_version

guard-env-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	else \
		echo "Environment variable $* found"; \
	fi


check_version:
	curl --silent https://pypi.org/rss/project/pyxbar/releases.xml \
		| awk -F '[<>]' '/title/ { if ($$3 ~ /[0-9].[0-9].[0-9]/){print $$3 ; exit} }'

local_version:
	cat pyxbar/__init__.py \
		| awk '/__version__/ {gsub(/"/, "") ; print $$3; exit}'

clean:
	rm -rf build dist *.egg-info

build: clean
	python3 -m pip install --upgrade build
	python3 -m build

tag: pypi
	git stash
	git tag -a $(shell make local_version) -m "Bump version to $(shell make local_version)"
	git push origin main --tags
	git stash pop

pypi: guard-env-TWINE_USERNAME
pypi: guard-env-TWINE_PASSWORD
pypi: build
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
	make clean

upload: pypi
