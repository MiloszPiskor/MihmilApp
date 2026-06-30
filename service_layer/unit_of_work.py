from __future__ import annotations
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from adapters import repository
import config

DEFAULT_SESSION_FACTORY = sessionmaker(bind=create_engine(
    config.get_postgres_uri(),
    isolation_level="REPEATABLE READ", # This ensures concurrency problems solved elegantly, with serialization for
    # catching problems
))

# UoW tracks Events and passes them to messagebus:
# Uses aggregate monitoring mechanism through repository thanks to .seen

class AbstractUnitOfWork(abc.ABC):
    companies: repository.AbstractCompanyRepository
    reps: repository.AbstractRepRepository

    def __enter__(self) -> AbstractUnitOfWork:
        return self

    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        self._commit()

    def collect_new_events(self):
        for company in self.companies.seen:
            while company.events:
                yield company.events.pop(0)

    @abc.abstractmethod
    def _commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError

class SqlAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()  # type: Session
        self.companies = repository.SQLAlchemyCompanyRepository(self.session)
        self.reps = repository.SQLAlchemyRepRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()