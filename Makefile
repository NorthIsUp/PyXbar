RSS=
.PHONY: clean check_version

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
	python pyxbar/__version__.py

clean:
	rm -rf build dist *.egg-info

build: clean
	python3 -m pip install --upgrade build
	python3 -m build

upload: guard-env-TWINE_USERNAME
upload: guard-env-TWINE_PASSWORD
upload: build
	git commit -main -m "Bump version to $(shell make local_version)"
	git push origin main
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
	make clean

