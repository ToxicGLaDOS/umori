#!/usr/bin/env bash
set -e

docker_kill() {
    if [ -n "$container_id" ]; then
        docker kill $container_id
    fi
}

# Clean up docker container when we're done
trap "docker_kill" EXIT

export SECRET_KEY='testingkey'
export DB_USER='postgres'
export DB_PORT=55432

# If you provide a password via the environment
# then we assume that you have a database set up and running
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo "No password found. Starting database"
    password=$(cat /dev/random | base64 | head -c 32)
    export DB_PASSWORD=$password
    container_id=$(docker run --rm -d -p 55432:5432 -e POSTGRES_PASSWORD=$password postgres)
    ./convert_scryfall_to_sql.py "$1" "$2"
else
    export DB_PASSWORD="$POSTGRES_PASSWORD"
fi

if [ -z $2 ]; then
    echo 'Expected 2 arguments. Path to ALL data file, then path to DEFAULT data file'
    exit
fi

ALL_DATA_FILE=$1 DEFAULT_DATA_FILE=$2 DB_PASSWORD=$password python test.py
