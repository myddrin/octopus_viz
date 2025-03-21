#!/usr/bin/env bash

/venv/bin/python -m gunicorn myproject.asgi:application -k uvicorn_worker.UvicornWorker
