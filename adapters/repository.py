import abc
from typing import Set, Optional
from domain import model

class AbstractCompanyRepository(abc.ABC):

    def __init__(self):
        self.seen = set() # type: Set[model.Company]

    def add(self, company: model.Company):
        self._add(company)
        self.seen.add(company)

    def get(self, nip, address) -> model.Company:
        company = self._get(nip, address)
        if company:
            self.seen.add(company)
        return company

    @abc.abstractmethod
    def _add(self, company: model.Company):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, nip: model.NIP, address: model.Address) -> Optional[model.Company]:
        raise NotImplementedError

class AbstractRepRepository(abc.ABC):
    @abc.abstractmethod
    def add(self, sales_rep: model.SalesRep):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, reference: str) -> Optional[model.SalesRep]:
        raise NotImplementedError

# Aggregate Root Repository (only Write operations access to data)
class SQLAlchemyCompanyRepository(AbstractCompanyRepository):

    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, company: model.Company):
        # Tracks for commit
        self.session.add(company)

    def _get(self, nip:model.NIP, address: model.Address) -> model.Company:
        # Returns live mapped opbject
        return (
            self.session.query(model.Company)
            .filter_by(nip=nip, address=address)
            #.with_for_update() THIS WOULD BE PESIMISTIC VERSIONING: read1, write1, read2, write2 !!!PERFORMACNE FLOP
            .first()
        )

class SQLAlchemyRepRepository(AbstractRepRepository):
    def __init__(self, session):
        self.session = session

    def add(self, sales_rep: model.SalesRep):
        self.session.add(sales_rep)

    def get(self, reference:str) -> model.SalesRep:
        return(
            self.session.query(model.SalesRep)
            .filter_by(reference=reference)
            .first()
        )
