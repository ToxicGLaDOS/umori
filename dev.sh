#!/usr/bin/env bash

export FLASK_APP=main
export FLASK_ENV=development
source ./env/bin/activate
python -m flask run
