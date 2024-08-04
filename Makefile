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
	./scripts/format.sh

lint:
	./scripts/lint.sh

#tests:
#	pushd octopus_viz/; \
#	python manage.py test; \
#	popd

update-db:
	pushd octopus_viz/; \
	python manage.py migrate; \
	popd

#destroy-db:
#	rm octopus_viz/meter_readings.sqlite3

create-db: update-db
	pushd octopus_viz/; \
	python manage.py createsuperuser; \
	popd

make-migration:
	pushd octopus_viz/; \
	python manage.py makemigrations ingestion; \
	popd

#
# Help local deployment
#

create-admin-user:
	pushd octopus_viz/; \
	python manage.py createsuperuser; \
	popd

# run the local server using the manage script form django
run-local:
	pushd octopus_viz/; \
	python manage.py runserver; \
	popd
