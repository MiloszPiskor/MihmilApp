from dataclasses import dataclass
from datetime import date


# Replacing Events: CompanyCreated, SalesRepCreated, AssignmentRequired,
# RepWarning5Months

# New ones: Release
class Command:
    pass

@dataclass
class CreateCompany(Command):
    nip:str
    name:str
    # Address Class components:
    street: str
    building_nr: str
    postal_code: str
    city: str

@dataclass
class CreateSalesRep(Command):
    reference: str
    name: str
    email: str

@dataclass
class Assign(Command):
    """Either used in entrypoints or in cron jobs -> depends on implementation"""
    # Company.nip:
    nip:str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str
    # SalesRep.reference:
    rep_ref: str

@dataclass
class ReleaseStale(Command):
    # Company.nip:
    nip:str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str

@dataclass
class WarnRepAfter5Months(Command):
    # Company.nip:
    nip:str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str

# Maintenance CMD's:
@dataclass
class EnsureCompanyExists(Command):
    nip: str
    name: str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str

@dataclass
class EnsureRepExists(Command):
    rep_name: str

@dataclass
class UpdateLastZK(Command):
    nip: str
    name: str
    rep_name: str
    zk_date: date
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str

# Synchronizing CMD's:
@dataclass
class SynchronizeRep(Command):
    nip: str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str

@dataclass
class SynchronizeLTD(Command):
    nip: str
    # Company.address:
    street: str
    building_nr: str
    postal_code: str
    city: str