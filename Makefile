RSS=https://pypi.org/rss/project/pyxbar/releases.xml
VERSION_FILE=pyxbar/__init__.py

.PHONY: clean check_version local_version

guard-env-%:
	@ if [ "${${*}}" = "" ]; then \
		echo "Environment variable $* not set"; \
		exit 1; \
	else \
		echo "Environment variable $* found"; \
	fi


check_version:
	@echo $(shell /usr/bin/curl --silent ${RSS} \
		| awk -F '[<>]' '/title/ { if ($$3 ~ /[0-9].[0-9].[0-9]/){print $$3 ; exit} }' \
	)

local_version:
	@echo $(shell \
		awk '/__version__/ {gsub(/"/, "") ; print $$3; exit}' ${VERSION_FILE} \
	)

clean:
	rm -rf build dist *.egg-info

bump:
	git stash
	$(eval CURRENT_VERSION=$(shell make check_version))
	$(eval NEXT_VERSION=$(shell \
		echo "${CURRENT_VERSION}" \
		| awk -F. '/[0-9]+\./{$$NF++;print}' OFS=. \
	))
	$(eval $(shell \
		sed -i "s/^__version__\s*=\s*\".*\"$$/__version__ = \"${NEXT_VERSION}\"/" \
		${VERSION_FILE} \
	))
	$(eval LOCAL_VERSION=$(shell make local_version))

	if [ ${LOCAL_VERSION} = ${NEXT_VERSION} ] ; then \
		echo "bumping from published version: ${CURRENT_VERSION} -> to ${NEXT_VERSION}" ; \
		git commit -m "Publish v${NEXT_VERSION}" ; \
		git tag -a v${NEXT_VERSION} -m "Publish v${NEXT_VERSION}" ; \
		git push origin v${NEXT_VERSION} ; \
	else \
		echo "error in bumping" ; \
		git stash pop ; \
	fi



build: clean
	python3 -m pip install --upgrade build
	python3 -m build

pypi: guard-env-TWINE_USERNAME
pypi: guard-env-TWINE_PASSWORD
pypi: build
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
	make clean

publish: bump
publish: pypi
