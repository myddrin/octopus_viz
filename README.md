# !!! THIS IS A PROTOTYPE !!!

This runs a Django-based website to display information about energy import and export.

Now that you've been warned, let's continue.

# Octopus Viz (Django) [0.2.1]

The current Octopus App (v3.71.2 on Android) does not allow visualisation:
- of monetary value when using the Flux tariff
- of visualising aggregated data for a longer period than 1 day at the half hour rate.

The goal of this project is to:
- create a cache of the electric consumption of a given system
- query said cache to map it to prices
  - to visualise the price of import for a period
  - to visualise the price of export per a period
  - to visualise the usage by half-hour aggregates over longer periods than 1 day

Octopus Energy API documentation: https://developer.octopus.energy/docs/api/
Octopus Energy Developer Dashboard: https://octopus.energy/dashboard/developer/

## Why storing data from octopus in a database?

The Octopus API allows the gathering of data at the half-hour precision with a maximum of 25,000 entries per page (`2 * 24 * 365 = 17,520` so more than enough to see 1 year of half-hour data).

By using a database for that data we:
- do not need to use their API for the visualisation part
- do not risk to get rate-limited if querying multiple time (I'm not sure if any rate limitation applies)

## Visualisation of aggregated data

The current Octopus App or website allow the visualisation of a day:

![original_consumption.PNG](original_consumption.PNG)

But this project should allow to have this view over longer periods of time than a day still accumulating at the half-hour interval.

TODO(tr) add screenshot of views

## Running the server locally

For the moment I recommend running the server locally as dev mode - this is not a finished project.

Do this once:
- First edit the Django [settings.py](octopus_viz/octopus_viz/settings.py) (see Appendix)
- Create the admin user (see below or the Django docs)
  ```bash
  $> make create-admin-user
  ```

Then run the local server:
```bash
$> make run-local
```

To complete the initial setup, visit http://127.0.0.1:8000/admin/ingestion 
- Add your API key
- Add your tariffs
- Add your rates

Alternatively there is a command in the [manage.py](octopus_viz/manage.py) to import a settings file (see Appendix for format).

Afterwards visit http://127.0.0.1:8000/

## Manual commands

The manual commands are available in the `[ingestion]` block with 
```bash
python manage.py --help
```

Each command has more details when running with `--help`.

Note: there are commands to import data from the file format but so far no commands to export to it from the database.

### File ingestion

To ingest cache files use `cache_ingestion`
```bash
python manage.py cache_ingestion [--create-missing-meter] file_path [file_path ...]
```
the files are expected to be in the cache file format described in the appendix.


To ingest configuration use `config_ingestion`
```bash
python manage.py config_ingestion file_path [file_path ...]
```
the files are expected to be the config file file format described in the appendix.

### Get data from Octopus

To get data from Octopus about a particular MPAN use
```bash
python manage.py data_ingestion [--period-from PERIOD_FROM] [--period-to PERIOD_TO] [--meter-mpan METER_MPAN] [--pretend]
```

To update how the data is linked to a tariff configuration use
```bash
python manage.py update_consumption [--all-rows] [--pretend]
```

# Appendices

## Configuration file format

The configuration files can be stored in `configs/` as it is part of the `.gitignore`.
This was the old format for the script version - but can still be used to import configuration with a command line.

The format is JSON and should contain:
- meters: list of `dto.Meter`
- tariffs: list of `dto.Tariff`

Example config for electricity:
```json
{
  "meters": {
    "api_key": "<api key>",
    "serial": "<meter serial>",
    "meters": [
      {
        "mpan": "<exporting mpan>",
        "unit": "electricity_exporting_kwh"
      },
      {
        "mpan": "<importing mpan>",
        "unit": "electricity_importing_kwh"
      }
    ]
  },
  "tariffs": {
    "flux_export_2023-07": {
      "unit": "electricity_exporting_kwh",
      "currency": "GBP",
      "rates": [
        {
          "interval_start": "00:00",
          "interval_end": "02:00",
          "rate": 0.1972
        },
        {
          "interval_start": "02:00",
          "interval_end": "05:00",
          "rate": 0.07432
        },
        {
          "interval_start": "05:00",
          "interval_end": "16:00",
          "rate": 0.1972
        },
        {
          "interval_start": "16:00",
          "interval_end": "19:00",
          "rate": 0.32008
        },
        {
          "interval_start": "19:00",
          "interval_end": "24:00",
          "rate": 0.1972
        }
      ]
    },
    "flux_import_2023-07": {
      "unit": "electricity_importing_kwh",
      "currency": "GBP",
      "rates": [
        {
          "interval_start": "00:00",
          "interval_end": "02:00",
          "rate": 0.30720
        },
        {
          "interval_start": "02:00",
          "interval_end": "05:00",
          "rate": 0.18432
        },
        {
          "interval_start": "05:00",
          "interval_end": "16:00",
          "rate": 0.30720
        },
        {
          "interval_start": "16:00",
          "interval_end": "19:00",
          "rate": 0.43008
        },
        {
          "interval_start": "19:00",
          "interval_end": "24:00",
          "rate": 0.30720
        }
      ]
    }
  }
}
```

The objects are loaded from the configuration JSON with their `from_dict` factory, a trick is applied so that 
fields don't have to be repeated:
```json
{
  "meters": {
    "api_key": "<api key>",
    "serial": "<meter serial>",
    "meters": [
      {
        "mpan": "<exporting mpan>",
        "unit": "electricity_exporting_kwh"
      },
      {
        "mpan": "<importing mpan>",
        "unit": "electricity_importing_kwh"
      }
    ]
  }
}
```
will create:
```json
[
  {
    "api_key": "<api key>",
    "serial": "<meter serial>",
    "mpan": "<exporting mpan>",
    "unit": "electricity_exporting_kwh"
  },
  {
    "api_key": "<api key>",
    "serial": "<meter serial>",
    "mpan": "<importing mpan>",
    "unit": "electricity_importing_kwh"
  }
]
```

The `dto.Tariff` has an optional `valid_from`, `valid_until` range that can be used when tariffs are updated.

## Cache file format

The cache files were created in earlier versions of this tool.
They used to be named following `<MPAN>_<meter id>_<ISO start date>_<ISO end date>.json`.
The format is JSON lines (each line being a full JSON block) containing objects:

```json
{
  "consumption": "float",
  "unit": "unit_str",
  "interval_start": "timestamp ISO format",
  "interval_end": "timestamp ISO format"
}
```

## Modification to Django `settings.py`

They are already done on the provided [settings.py](octopus_viz/octopus_viz/settings.py) file, but here is a summary:
- Configure django-bootstrap5
  - Add `django_bootstrap5` to the `INSTALLED_APPS`
  - Create `BOOTSTRAP5` in `settings.py` (with values for 'css_url' and 'javascript_url')
- Add `ingestion.apps.IngestionConfig` to the `INSTALLED_APPS` the usual way
- Nothing to add to `MIDDLEWARE`
- Add the menu_context to the `TEMPLATES.OPTIONS.context_processors`
- Select a path of the sql-lite database
  - e.g. set `DATABASES.default.NAME` to `BASE_DIR / 'octopus_viz.sqlite3'`


## Note: Octopus Flux

Source: https://octopus.energy/smart/flux/

Is a tariff with 3 levels of price for import and export:
- 1 base price during most of the day, usually slightly lower than the national average.
- 1 low price at the early hours (02:00 to 05:00)
- 1 high price at the peak hours (16:00 to 19:00)
 
![flux_explainer.svg](flux_explainer.svg)
