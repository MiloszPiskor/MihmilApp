from dataclasses import dataclass
from datetime import date


class Event:
    pass

@dataclass
class CompanyReleased(Event):
    nip: str
    email: str
    rep_name: str

@dataclass
class CompanyAssigned(Event):
    nip: str
    email: str
    rep_name: str

@dataclass
class RepWarned5Months(Event):
    nip: str
    email:str
    rep_name: str
    last_transaction_date: str

# Old Company but different SalesRep assigned
class OwnershipChange(Event):
    pass

#Implement those if needed:
@dataclass
class DashboardRequired(Event):
    pass

@dataclass
class CompanyLookupRequest(Event):
    pass



