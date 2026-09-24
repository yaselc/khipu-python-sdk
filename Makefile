# ------------------------------------------------------------
# Khipu Python SDK - Make targets
# ------------------------------------------------------------

PYTHON ?= python
OPENAPI_CLIENT ?= openapi-python-client
CURL ?= curl

OPENAPI_DIR := openapi
GENERATED_DIR := generated

# OpenAPI specs
INSTANT_SPEC := $(OPENAPI_DIR)/khipu-instant-payments.yaml
AUTOMATIC_SPEC := $(OPENAPI_DIR)/khipu-automatic-payments.yaml

# OpenAPI download URLs
INSTANT_SPEC_URL := https://docs.khipu.com/_bundle/apis/v3/instant-payments/openapi.yaml?download
AUTOMATIC_SPEC_URL := https://docs.khipu.com/_bundle/apis/v1/automatic-payments/openapi.yaml?download

# Instant Payments is generated from a derived copy of the committed spec with
# the compatibility overlay in tools/spec_compat.py applied (#15). The committed
# spec itself stays verbatim; the derived copy is a build artifact.
INSTANT_COMPAT_SPEC := build/openapi/khipu-instant-payments.yaml

# Generated clients output
INSTANT_OUT := $(GENERATED_DIR)/instant_payments
AUTOMATIC_OUT := $(GENERATED_DIR)/automatic_payments


# ------------------------------------------------------------
# Help
# ------------------------------------------------------------

.PHONY: help
help:
	@echo ""
	@echo "Khipu Python SDK - Make targets"
	@echo ""
	@echo "OpenAPI specs:"
	@echo "  make download-specs         Download all OpenAPI specifications"
	@echo "  make download-instant       Download Instant Payments spec"
	@echo "  make download-automatic     Download Automatic Payments spec"
	@echo ""
	@echo "Code generation:"
	@echo "  make generate-instant       Generate Instant Payments client"
	@echo "  make generate-automatic     Generate Automatic Payments client"
	@echo "  make generate-all           Generate all clients"
	@echo "  make check-spec-compat      Verify the Instant Payments overlay still applies"
	@echo ""
	@echo "Development:"
	@echo "  make install                Install SDK in editable mode"
	@echo "  make install-dev            Install SDK with dev dependencies"
	@echo "  make test                   Run test suite"
	@echo "  make lint                   Run ruff"
	@echo "  make typecheck              Run mypy"
	@echo "  make check                  Run lint, typecheck, and tests"
	@echo "  make clean-generated        Remove generated clients"
	@echo ""
	@echo "Distribution:"
	@echo "  make build                  Build the wheel"
	@echo "  make smoke-dist             Install built wheel in a clean venv and smoke test it"
	@echo ""


# ------------------------------------------------------------
# OpenAPI spec download
# ------------------------------------------------------------

.PHONY: download-instant
download-instant:
	@echo "Downloading Instant Payments OpenAPI spec..."
	mkdir -p $(OPENAPI_DIR)
	$(CURL) -fsSL "$(INSTANT_SPEC_URL)" -o "$(INSTANT_SPEC)"
	@echo "Saved to $(INSTANT_SPEC)"


.PHONY: download-automatic
download-automatic:
	@echo "Downloading Automatic Payments OpenAPI spec..."
	mkdir -p $(OPENAPI_DIR)
	$(CURL) -fsSL "$(AUTOMATIC_SPEC_URL)" -o "$(AUTOMATIC_SPEC)"
	@echo "Saved to $(AUTOMATIC_SPEC)"


.PHONY: download-specs
download-specs: download-instant download-automatic
	@echo "All OpenAPI specs downloaded successfully"


# ------------------------------------------------------------
# OpenAPI client generation
# ------------------------------------------------------------

.PHONY: ensure-generated-package
ensure-generated-package:
	@mkdir -p $(GENERATED_DIR)
	@printf '%s\n' \
		'"""Namespace package for OpenAPI-generated Khipu clients.' \
		'' \
		'This file exists so that the generated clients are discovered by setuptools and' \
		'shipped inside the built distribution. It is recreated deterministically by' \
		'``make generate-all`` (see the ``ensure-generated-package`` target) so it' \
		'survives regeneration.' \
		'' \
		'Do not add logic here. All hand-written code belongs in ``khipu_sdk``.' \
		'"""' \
		> $(GENERATED_DIR)/__init__.py
	@echo "Ensured $(GENERATED_DIR)/__init__.py (required for packaging)"


.PHONY: check-spec-compat
check-spec-compat:
	$(PYTHON) tools/spec_compat.py --check $(INSTANT_SPEC)


.PHONY: generate-instant
generate-instant:
	@echo "Generating Instant Payments client..."
	$(PYTHON) tools/spec_compat.py $(INSTANT_SPEC) $(INSTANT_COMPAT_SPEC)
	rm -rf $(INSTANT_OUT)
	mkdir -p $(INSTANT_OUT)
	$(OPENAPI_CLIENT) generate \
		--path $(INSTANT_COMPAT_SPEC) \
		--output-path $(INSTANT_OUT) \
		--overwrite \
		--meta none
	@echo "Instant Payments client generated in $(INSTANT_OUT)"


.PHONY: generate-automatic
generate-automatic:
	@echo "Generating Automatic Payments client..."
	rm -rf $(AUTOMATIC_OUT)
	mkdir -p $(AUTOMATIC_OUT)
	$(OPENAPI_CLIENT) generate \
		--path $(AUTOMATIC_SPEC) \
		--output-path $(AUTOMATIC_OUT) \
		--overwrite \
		--meta none
	@echo "Automatic Payments client generated in $(AUTOMATIC_OUT)"


.PHONY: generate-all
generate-all: generate-instant generate-automatic ensure-generated-package
	@echo "All Khipu clients generated successfully"


# ------------------------------------------------------------
# Cleanup
# ------------------------------------------------------------

.PHONY: clean-generated
clean-generated:
	@echo "Removing generated clients..."
	rm -rf $(GENERATED_DIR)
	@echo "Generated directory cleaned"


# ------------------------------------------------------------
# Python / Development helpers
# ------------------------------------------------------------

.PHONY: install
install:
	pip install -U pip
	pip install -e .


.PHONY: install-dev
install-dev:
	pip install -U pip
	pip install -e ".[dev]"


.PHONY: test
test:
	pytest -q


.PHONY: lint
lint:
	ruff check .


.PHONY: typecheck
typecheck:
	mypy khipu_sdk


.PHONY: check
check: lint typecheck test
	@echo "All checks passed"


# ------------------------------------------------------------
# OpenAPI spec locking (sha256)
# ------------------------------------------------------------

.PHONY: lock-specs
lock-specs:
	@echo "Writing OPENAPI_SPECS.lock.json..."
	$(PYTHON) tools/lock_specs.py

.PHONY: verify-spec-lock
verify-spec-lock:
	@echo "Verifying OpenAPI specs against OPENAPI_SPECS.lock.json..."
	$(PYTHON) tools/verify_spec_lock.py


# ------------------------------------------------------------
# Distribution build + clean-install smoke test
# ------------------------------------------------------------

DIST_DIR := dist

.PHONY: build
build:
	@echo "Building distribution..."
	# build/ too, not just dist/: setuptools copies the wheel contents out of
	# build/lib, so a module deleted from the source tree (for instance when a
	# spec refresh removes a generated model) keeps being shipped until that
	# directory is cleared.
	rm -rf $(DIST_DIR) build
	$(PYTHON) -m build --wheel --outdir $(DIST_DIR)
	@echo "Wheel built in $(DIST_DIR)"

.PHONY: smoke-dist
smoke-dist: build
	@echo "Installing built wheel into a clean virtualenv and running smoke test..."
	@set -eu; \
	WHEEL="$$(ls $(DIST_DIR)/*.whl | head -1)"; \
	WORK="$$(mktemp -d)"; \
	trap 'rm -rf "$$WORK"' EXIT; \
	$(PYTHON) -m venv "$$WORK/venv"; \
	"$$WORK/venv/bin/python" -m pip install -q -U pip; \
	"$$WORK/venv/bin/python" -m pip install -q "$$WHEEL"; \
	cp tools/smoke_installed.py "$$WORK/smoke_installed.py"; \
	cd "$$WORK" && "$$WORK/venv/bin/python" "$$WORK/smoke_installed.py"
	@echo "Distribution smoke test passed"
