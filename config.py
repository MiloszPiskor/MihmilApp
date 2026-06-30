import os
from dotenv import load_dotenv

load_dotenv()

def get_postgres_uri():
    host = os.environ.get('DB_HOST', 'localhost')
    port = 54321 if host == 'localhost' else 5432
    password = os.environ.get('DB_PASSWORD', 'abc123')
    user, db_name = 'prexpol', 'prexpol'
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url():
    host = os.environ.get('API_HOST', 'localhost')
    port = 5005 if host == 'localhost' else 5005
    return f"http://{host}:{port}"

host = "smtp.gmail.com"
port = 587
username = "miloszpiskor97@gmail.com"
password = "vsew diek xqsm habi"
recipient = "biuro@prexpol.eu"

import os

class Config:
    OKTA_DOMAIN = os.getenv("OKTA_DOMAIN")
    OKTA_ISSUER = os.getenv("OKTA_ISSUER")
    OKTA_AUDIENCE = os.getenv("OKTA_AUDIENCE")
    OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
    OKTA_REDIRECT_URI = os.getenv("OKTA_REDIRECT_URI")
