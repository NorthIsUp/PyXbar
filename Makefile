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

upload: guard-env-TWINE_USERNAME
upload: guard-env-TWINE_PASSWORD
upload: build
	git stash
	git commit -main -m "Bump version to $(shell make local_version)"
	git push origin main
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
	git stash pop
	make clean

