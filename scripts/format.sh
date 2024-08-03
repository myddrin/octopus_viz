#!/usr/bin/env bash

ruff format --preview octopus_viz
ruff check --preview --fix octopus_viz
