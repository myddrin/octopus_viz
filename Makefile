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
	@pre-commit run -a

lint:
	@pre-commit run ruff-check -a

#tests:
#	pushd octopus_viz/; \
#	python manage.py test; \
#	popd

update-db:
	cd octopus_viz/; python manage.py migrate

#destroy-db:
#	rm octopus_viz/meter_readings.sqlite3

create-db: update-db
	cd octopus_viz/; python manage.py createsuperuser

make-migration:
	pushd octopus_viz/; python manage.py makemigrations ingestion

#
# Help local deployment
#

create-admin-user:
	cd octopus_viz/; python manage.py createsuperuser;

db-shell:
	cd octopus_viz/; python manage.py dbshell


# run the local server using the manage script form django
run-local:
	cd octopus_viz/; python manage.py runserver
