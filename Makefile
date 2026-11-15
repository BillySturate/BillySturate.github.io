PYTHON ?= python3
.PHONY: install build check preview browser preview-build
install:
	$(PYTHON) -m pip install -r requirements-dev.txt
build:
	$(PYTHON) scripts/build.py
check: build
	$(PYTHON) scripts/validate.py
browser: check
	$(PYTHON) scripts/browser_test.py
preview:
	$(PYTHON) scripts/preview.py
preview-build:
	$(PYTHON) scripts/build.py --base-path /silas-homepage-preview --site-url https://billysturate.github.io --output dist-preview
	$(PYTHON) scripts/validate.py --directory dist-preview
