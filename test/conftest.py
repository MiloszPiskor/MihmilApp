import sys
import os

from service_layer import unit_of_work

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
from pathlib import Path
import pytest
import requests
from requests.exceptions import ConnectionError
from sqlalchemy.exc import OperationalError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, clear_mappers
import config
from adapters.orm import metadata, start_mappers
from entrypoints.flask_app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def in_memory_db():
    engine = create_engine('sqlite:///:memory:')
    metadata.create_all(engine)
    return engine

@pytest.fixture
def session_factory(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db, expire_on_commit=False)
    clear_mappers()

@pytest.fixture
def session(session_factory):
    return session_factory()


def wait_for_postgres_to_come_up(engine):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            return engine.connect()
        except OperationalError:
            time.sleep(0.5)
    pytest.fail('Postgres never came up')


def wait_for_webapp_to_come_up():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail('API never came up')



@pytest.fixture(scope='session')
def postgres_db():
    engine = create_engine(config.get_postgres_uri())
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine

@pytest.fixture
def postgres_session_factory(postgres_db):
    start_mappers()
    yield sessionmaker(bind=postgres_db)
    clear_mappers()

@pytest.fixture
def postgres_session(postgres_session_factory):
    session = postgres_session_factory()
    yield session
    session.close()

# @pytest.fixture
# def postgres_session(postgres_db):
#     start_mappers()
#
#     connection = postgres_db.connect()
#     transaction = connection.begin()
#
#     session = sessionmaker(bind=connection)()
#
#     yield session
#
#     session.close()
#     if transaction.is_active:
#         transaction.rollback()
#     connection.close()
#
#     clear_mappers()

@pytest.fixture
def test_uow_factory(postgres_session_factory, monkeypatch):
    monkeypatch.setattr(unit_of_work, "DEFAULT_SESSION_FACTORY", postgres_session_factory)
    yield postgres_session_factory

@pytest.fixture
def restart_api():
    (Path(__file__).parent / '../src/allocation/entrypoints/flask_app.py').touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()