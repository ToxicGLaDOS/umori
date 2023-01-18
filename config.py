import os

config = {
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'DB_USER': os.environ.get('DB_USER'),
    'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
    'DB_HOST':"0.0.0.0",
    'DB_PORT': os.environ.get('DB_PORT', '5432')
}

def get(config_name: str):
    value = config.get(config_name)
    # Quit because we don't want to get None back from this
    if not value:
        print(f"Config option {config_name} doesn't exist")
        exit(1)
    return value

