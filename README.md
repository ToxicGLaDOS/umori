## Converting from scryfall
1. Export your inventory as Printable
2. Get scryfall bulk data for default cards [here](https://scryfall.com/docs/api/bulk-data)
3. Run `shrink_database.py <path to bulk data>`
4. Run `convert.py`
5. Output is in `output.csv`

## Installing dependencies

`pip install -r requirements.txt`

## Running tests

This method sets up the database and runs the tests for you. It should be automagic, but setting up the database takes a while, so you can set up a database yourself and pass the password in via an environment variable `POSTGRES_PASSWORD` to use it instead of setting it up every time.

`./test.sh all-cards-<datestamp>.json default-cards-<datestamp>.json`

This expects you to have `docker` installed.

You can get the scryfall bulk data from [here](https://scryfall.com/docs/api/bulk-data)
