import pytest
from datetime import date
from dateutil.relativedelta import relativedelta
from domain.model import (Company, Address, NIP, SalesRep, CompanyAlreadyAssigned, NoRepAssigned, InvalidNip, ZK,
                          WrongZK, NoZK)


def create_address(number: int) -> Address:
    return Address(street=f"Street{number}", building_nr=f"{number}", postal_code=f"00-00{number}", city=f"City-{number}")

def create_nip(number: int) -> NIP:
    return NIP(value=f"000000000{number}")

def create_company(address_num: int, nip_num: int) -> Company:

    address = create_address(address_num)
    nip = create_nip(nip_num)

    return Company(nip = nip, name = "Company", address=address)

def create_zk(number: int, date = date.today()) -> ZK:
    return ZK(nip=f"000000000{number}", name=f"Company", street=f"Street{number}", building_nr=f"{number}",
              postal_code=f"00-00{number}", city=f"City-{number}", transaction_date=date, rep_name=f"Person{number}",)

def test_raises_invalid_nip_on_create_company_with_invalid_nip():
    with pytest.raises(InvalidNip, match="Invalid NIP value 00000000011"):
        create_company(1, 11)

def test_can_assign_when_no_current_rep():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")

    # Act
    rep_ref = company.assign_to_rep(rep)

    assert company.current_rep == rep
    assert rep_ref == rep.reference

def test_assignment_returns_rep_reference():
    company = create_company(1, 1)
    assert company.version == 0
    # Act 1: (assign)
    result = company.assign_to_rep(SalesRep(reference="1", name="Person", email="email"))
    assert result == "1"

def test_raises_company_already_assigned_if_cannot_assign():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    # Act
    company.assign_to_rep(rep)
    assigned_version = company.version
    assert company.current_rep is not None

    with pytest.raises(CompanyAlreadyAssigned, match=f"Already assigned to {rep.name}"):
        company.assign_to_rep(SalesRep(reference="2", name="Person2", email="email"))
    assert company.version == assigned_version

def test_raises_no_rep_assigned_when_cannot_release_without_current_rep():
    company = create_company(1, 1)

    assert company.current_rep is None
    # Act
    with pytest.raises(NoRepAssigned, match="No rep assigned"):
        company.release_from_rep()

def test_can_release_with_current_rep():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    # Act 1: (assign)
    company.assign_to_rep(rep)
    assert company.current_rep == rep
    # Act 2: (release)
    company.release_from_rep()
    assert company.current_rep is None

def test_can_assign_after_release():
    company = create_company(1, 1)
    rep_1 = SalesRep(reference="1", name="Person1", email="email")
    rep_2 = SalesRep(reference="2", name="Person2", email="email")
    # Act 1: (assign)
    company.assign_to_rep(rep_1)
    assert company.current_rep == rep_1
    # Act 2: (release)
    company.release_from_rep()
    assert company.current_rep is None
    # Act 3: (assign again)
    company.assign_to_rep(rep_2)
    assert company.current_rep == rep_2

def test_version_increments_on_assign_or_release():
    company = create_company(1, 1)
    assert company.version == 0
    # Act 1: (assign)
    company.assign_to_rep(SalesRep(reference="1", name="Person", email="email"))
    assert company.version == 1
    # Act 2: (release)
    company.release_from_rep()
    assert company.version == 2

def test_assigning_the_same_rep_is_idempotent():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    initial_version = company.version
    # Act 1: (assign)
    result1 = company.assign_to_rep(rep)
    # Act 2: (assign the same rep again)
    result2 = company.assign_to_rep(rep)
    # Assert: no state changes + idempotent behavior
    assert company.version == initial_version + 1
    assert company.current_rep == rep
    assert result1 == rep.reference
    assert result2 == []

# company.synchronize_rep_from_zk:
def test_assigns_rep_from_zk_if_no_current_rep():
    company = create_company(1, 1)
    zk_rep = SalesRep(reference="1", name="Person1", email="email")
    zk = create_zk(1)

    assert company.current_rep is None
    assert company.last_zk is None

    company.last_zk = zk
    company.synchronize_rep_from_zk(zk_rep)

    assert company.current_rep == zk_rep
    assert len(company.events) == 1

def test_synchronizing_the_same_rep_is_idempotent():
    company = create_company(1, 1)
    zk_rep = SalesRep(reference="1", name="Person1", email="email")
    zk_1 = create_zk(1)
    zk_2 = create_zk(1)

    company.last_zk = zk_1
    company.synchronize_rep_from_zk(zk_rep)

    assert company.current_rep == zk_rep
    assert zk_1.rep_name == company.current_rep.name
    assert len(company.events) == 1

    company.last_zk = zk_2
    company.synchronize_rep_from_zk(zk_rep)
    assert len(company.events) == 1
    assert company.current_rep == zk_rep

def test_assigns_rep_from_zk_if_current_rep():
    company = create_company(1, 1)
    zk_1_rep = SalesRep(reference="1", name="Person1", email="email")
    zk_2_rep = SalesRep(reference="2", name="Person2", email="email")
    zk_1 = create_zk(1)
    zk_2 = create_zk(2)

    company.last_zk = zk_1
    company.synchronize_rep_from_zk(zk_1_rep)

    assert company.current_rep == zk_1_rep
    assert zk_1.rep_name == company.current_rep.name
    assert len(company.events) == 1

    company.last_zk = zk_2
    company.synchronize_rep_from_zk(zk_2_rep)

    assert company.current_rep == zk_2_rep
    assert zk_2.rep_name == company.current_rep.name
    assert len(company.events) == 3

# company.synchronize_ltd_from_zk
def test_updates_ltd_from_zk_if_no_ltd():
    company = create_company(1, 1)
    zk = create_zk(1)

    assert company.ltd is None

    company.last_zk = zk
    company.synchronize_ltd_from_zk()

    assert company.ltd == zk.transaction_date

def test_updates_ltd_from_zk_if_newer():
    company = create_company(1, 1)
    zk = create_zk(1) # date: today

    company.ltd = date.today() - relativedelta(days=1)

    company.last_zk = zk
    company.synchronize_ltd_from_zk()

    assert company.ltd == zk.transaction_date

def test_does_not_update_ltd_from_zk_if_not_newer():
    company = create_company(1, 1)
    zk = create_zk(1, date=date.today() - relativedelta(days=1))  # date: yesterday

    company.ltd = date.today()
    company.last_zk = zk
    company.synchronize_ltd_from_zk()

    assert company.ltd != zk.transaction_date

def test_update_last_zk_sets_last_zk_when_nip_and_address_match():
    company = create_company(1, 1)
    zk = create_zk(1)

    assert company.last_zk is None

    company.update_last_zk(zk)

    assert company.last_zk == zk

def test_update_last_zk_raises_when_nip_or_address_does_not_match():
    company = create_company(1, 1)
    zk = create_zk(2)

    with pytest.raises(WrongZK, match="NIP or Address do not match while updating last ZK"):
        company.update_last_zk(zk)

    assert company.last_zk is None

def test_company_check_for_zk_raises_when_no_zk():
    company = create_company(1, 1)
    with pytest.raises(NoZK, match="Cannot synchronize LTD/Rep without ZK snapshot"):
        company.check_for_zk()

# EVENT TESTS:
    """Pytest import collision workaround: field-by-field assertions instead of 
    direct dataclass comparison of events due to module loading differences."""
def test_records_company_assigned_event_after_assignment():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    # Act
    rep_ref = company.assign_to_rep(rep)
    event = company.events[-1]

    assert event.nip == company.nip.value
    assert event.email == rep.email
    assert event.rep_name == rep.name
    assert len(company.events) == 1
    assert rep_ref == rep.reference

def test_records_company_released_event_after_release():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")

    # Act
    rep_ref = company.assign_to_rep(rep)

    assert len(company.events) == 1
    assert rep_ref == rep.reference

    same_rep_ref = company.release_from_rep()
    release_event = company.events[-1]

    assert len(company.events) == 2
    assert same_rep_ref == rep.reference
    assert release_event.nip == company.nip.value
    assert release_event.email == rep.email
    assert release_event.rep_name == rep.name

def test_records_needs_5m_warning_event():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")

    # Assignment
    company.assign_to_rep(rep)
    assert len(company.events) == 1  # CompanyAssigned

    # Warning setup
    company.ltd = date.today() - relativedelta(months=5)
    assert company._warned_5m is False

    # Waring event
    company.needs_precise_5month_warning()
    warning_event = company.events[-1] # Second event

    assert company._warned_5m is True
    assert len(company.events) == 2
    assert warning_event.nip == company.nip.value
    assert warning_event.email == rep.email
    assert warning_event.rep_name == rep.name
    assert warning_event.last_transaction_date == str(company.ltd)

def test_event_needs_precise_5month_warning_idempotent():
    company = create_company(1, 1)
    rep = SalesRep("1", "Person", "email")

    company.assign_to_rep(rep) # 1 event
    company.ltd = date.today() - relativedelta(months=5)

    company.needs_precise_5month_warning()  # 2 event
    events_before = len(company.events)

    company.needs_precise_5month_warning()  # No new event
    assert len(company.events) == events_before

def test_event_needs_precise_5month_warning_not_triggered_if_not_exactly_5m():
    company = create_company(1, 1)
    company.assign_to_rep(SalesRep("1", "Person", "email"))
    company.ltd = date.today() - relativedelta(months=4, days=1)

    company.needs_precise_5month_warning()
    assert company._warned_5m is False  # No warning!

def test_stale_rep_release_releases_after_6m():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    company.assign_to_rep(rep)
    company.ltd = date.today() - relativedelta(months=6)
    company.stale_rep_release()

    assert company.current_rep is None

def test_stale_rep_release_does_not_release_before_6m():
    company = create_company(1, 1)
    rep = SalesRep(reference="1", name="Person", email="email")
    company.assign_to_rep(rep)
    company.ltd = date.today() - relativedelta(months=5, days=29)
    company.stale_rep_release()

    assert company.current_rep == rep








