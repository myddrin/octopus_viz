
install-dev:
	uv sync

install:
	uv sync --no-dev

format:
	@pre-commit run -a

lint:
	@pre-commit run ruff-check -a

#tests:
#	cd octopus_viz/; python manage.py test

update-db:
	cd octopus_viz/; uv run manage.py migrate

#destroy-db:
#	rm octopus_viz/meter_readings.sqlite3

create-db: update-db
	cd octopus_viz/; uv run manage.py createsuperuser

make-migration:
	cd octopus_viz/; uv run manage.py makemigrations ingestion

#
# Help local deployment
#

create-admin-user:
	cd octopus_viz/; uv run manage.py createsuperuser;

db-shell:
	cd octopus_viz/; uv run manage.py dbshell


# run the local server using the manage script form django
run-local:
	cd octopus_viz/; uv run manage.py runserver
