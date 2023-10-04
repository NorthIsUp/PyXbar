clean:
	rm -rf build dist *.egg-info

build: clean
	python3 -m pip install --upgrade build
	python3 -m build

upload: export TWINE_USERNAME = __token__
upload: build
	git push origin main
	python3 -m pip install --upgrade twine
	python3 -m twine upload dist/*
