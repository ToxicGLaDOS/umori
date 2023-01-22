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
    # Sleep to wait for database to start up
    sleep 4
else
    password="$POSTGRES_PASSWORD"
fi

DB_PASSWORD=$password python test.py
