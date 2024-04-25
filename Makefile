# Control the poetry installation
POETRY_BIN := $(or $(POETRY_BIN), "poetry")
# This is ready to "live dangerously" and assumes poetry will be installed in the same venv than this project
# alternatives:
# - add it to the ENV variables.
#   e.g export POETRY_BIN="$(pyenv root)/versions/poetry-3.12.2/bin/poetry"
# - explicit path when running
#   e.g. POETRY=my_poetry_bin_path make install-dev

install-dev:
    # refresh python tools while doing dev
	pip install --upgrade pip wheel setuptools
	$(POETRY_BIN) install

install:
	$(POETRY_BIN) install --no-dev

format:
	ruff format --preview octopus_viz
	ruff check --preview --fix octopus_viz

lint:
	ruff check --preview octopus_viz
