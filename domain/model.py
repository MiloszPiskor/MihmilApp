import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from . import events, commands
from dataclasses import dataclass
from typing import Optional, List
from datetime import date
from dateutil.relativedelta import relativedelta

class InvalidNip(Exception):
    pass

class CompanyAlreadyAssigned(Exception):
    pass

class NoRepAssigned(Exception):
    pass

class WrongZK(Exception):
    pass

class NoZK(Exception):
    pass

@dataclass(frozen=True)
class UserId:
    value: str

@dataclass(frozen=True)
class UserRole:
    value: str

    REP = "rep"
    OFFICE = "office"
    ADMIN = "admin"

@dataclass
class User:
    sub: str
    email: str
    name: str
    role: str
    rep_reference: Optional[str] = None
    is_active: bool = True
    okta_groups: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_office(self) -> bool:
        return self.role == "office"

    @property
    def is_rep(self) -> bool:
        return self.role == "rep"

# Value Objects (pure, immutable)
@dataclass(frozen=True)
class NIP:
    value: str

    def __post_init__(self):
        if not self._validate():
            raise InvalidNip(f"Invalid NIP value {self.value}")

    def _validate(self) -> bool:
        return len(self.value) == 10 and self.value.isdigit()

# Dataclass helper to extract data from Subiekt SQL Query
@dataclass
class ZKRow:
    nip: str
    name: str
    street: str
    building_nr: str
    postal_code: str
    city: str
    rep_group_name: str
    zk_date: date

    @classmethod
    def from_sql_row(cls, sql_row):
        return cls(
            sql_row.nip, sql_row.name, sql_row.street, sql_row.building_nr,
            sql_row.postal_code, sql_row.city, sql_row.rep_group_name,
            sql_row.zk_date
        )

@dataclass(frozen=True)
class CompanyCandidate:
    nip: str
    street: str
    building_nr: str
    postal_code: str
    city: str

# Snapshot danych potrzebnych do przetwarzania przez Company, codzienne jobs dla
# 'last_zk_transaction_date' z ostatnich 24h celem synchronizacji daty transakcji i repa
@dataclass(frozen=True)
class ZK:
    nip: str
    name: str
    street: str
    building_nr: str
    postal_code: str
    city: str
    transaction_date: date
    rep_name: str

    def __composite_values__(self):
        return (
            self.nip,
            self.name,
            self.street,
            self.building_nr,
            self.postal_code,
            self.city,
            self.transaction_date,
            self.rep_name,
        )

    @classmethod
    def as_composite(
        cls,
        nip, name, street, building_nr, postal_code, city, transaction_date, rep_name
    ):
        if all(v is None for v in (nip, name, street, building_nr, postal_code, city, transaction_date, rep_name)):
            return None
        return cls(nip, name, street, building_nr, postal_code, city, transaction_date, rep_name)

@dataclass(frozen=True)
class Address:
    street: str
    building_nr: str
    postal_code: str
    city: str

    def __composite_values__(self):
        return self.street, self.building_nr, self.postal_code, self.city

# SalesRep → Simple Entity (NO aggregate)
@dataclass#(frozen=True)
class SalesRep:
    reference: str
    name: str
    email: str

    def __eq__(self, other):
        return (
            isinstance(other, SalesRep)
            and self.reference == other.reference
            and self.name == other.name
            and self.email == other.email
        )

    def __hash__(self):
        return hash(self.reference)

class Company:
    def __init__(self, nip: NIP, name: str, address: Address, version_number: int = 0, last_zk: Optional[ZK] = None):
        self.nip = nip
        self.name = name
        self.address = address
        self.ltd: Optional[date] = None  # Last Transaction Date
        self._current_rep: Optional[SalesRep] = None
        self.last_zk = last_zk
        self.version = version_number
        self._warned_5m = False
        self.events = []  # type: List[events.Event]

    def __eq__(self, other):
        if not isinstance(other, Company):
            return False
        return (
            other.nip == self.nip and
            other.address == self.address
        )

    def __hash__(self):
        return hash((self.nip, self.address))

    @property
    def current_rep(self) -> Optional[SalesRep]:
        return self._current_rep

    def needs_precise_5month_warning(self) -> None:
        if self._warned_5m or not self._current_rep:
            return None
        if self._exactly_5_calendar_months():
            self._warned_5m = True
            self.events.append(events.RepWarned5Months(
                nip=self.nip.value,
                email=self._current_rep.email,
                rep_name=self._current_rep.name,
                last_transaction_date=str(self.ltd)
            ))

    def _exactly_5_calendar_months(self):
        if not self.ltd or not self._current_rep:
            return False
        warning_date = self.ltd + relativedelta(months=+5)
        return date.today().replace(day=1) == warning_date.replace(day=1)

    def stale_rep_release(self):
        if not self._current_rep:
            return None
        if self.ltd and self.ltd + relativedelta(months=+6) <= date.today():
            self.release_from_rep()

    def assign_to_rep(self, rep: SalesRep):
        if self._current_rep:
            if self._current_rep.reference == rep.reference:
                return []  # idempotent, no state change, remember to: for event in company.events and nothing happens

            raise CompanyAlreadyAssigned(
                f"Already assigned to {self._current_rep.name}"
            )

        self._current_rep = rep
        self.version += 1

        self.events.append(events.CompanyAssigned(
            nip=self.nip.value,
            email=rep.email,
            rep_name=rep.name,
        ))

        return self._current_rep.reference

    def release_from_rep(self):
        if not self._current_rep:
            raise NoRepAssigned("No rep assigned")

        # rep_ref = self._current_rep.reference
        released_rep = self._current_rep
        self._current_rep = None
        self.version += 1

        self.events.append(events.CompanyReleased(
            nip=self.nip.value,
            email = released_rep.email,
            rep_name=released_rep.name)
        )

        return released_rep.reference

    def check_for_zk(self):
        if self.last_zk is None:
            raise NoZK(
                f"Cannot synchronize LTD/Rep without ZK snapshot for company "
                f"NIP={self.nip.value}, "
                f"street={self.address.street}, "
                f"building_nr={self.address.building_nr}, "
                f"postal_code={self.address.postal_code}, "
                f"city={self.address.city}"
            )

    def update_last_zk(self, zk: ZK):

        if self.nip.value == zk.nip and self.address == Address(zk.street, zk.building_nr, zk.postal_code, zk.city):
            self.last_zk = zk
        else:
            raise WrongZK("NIP or Address do not match while updating last ZK")

    def synchronize_rep_from_zk(self, sales_rep: SalesRep):

        rep = sales_rep
        # Scenario 1 -> no current_rep:
        if not self.current_rep:
            self.assign_to_rep(rep)

        #Scenario 2 -> current_rep different from last_zk.rep_name
        elif self._current_rep != rep:
            self.release_from_rep()
            self.assign_to_rep(rep)

        #Scenario 3 -> current_rep same as last_zk.rep_name -> No action needed !

    def synchronize_ltd_from_zk(self):

        if not self.ltd or self.last_zk.transaction_date > self.ltd:
            # old_ltd = self.ltd
            self.ltd = self.last_zk.transaction_date
            # self._add_event(LTDUpdated(self.nip, old_ltd, self.ltd))  # Event!



