import pytest
from dateutil.relativedelta import relativedelta

from domain import commands, events, model
from service_layer import unit_of_work, messagebus
from adapters import repository
from datetime import date

class FakeCompanyRepository(repository.AbstractCompanyRepository):
    def __init__(self, companies):
        super().__init__()
        self._companies = set(companies)

    def _add(self, company: model.Company):

        self._companies.add(company)

    def _get(self, nip: model.NIP, address: model.Address) -> model.Company:

        return next((c for c in self._companies if c.nip == nip and c.address == address), None)

class FakeRepRepository(repository.AbstractRepRepository):
    def __init__(self, reps):
        super().__init__()
        self._reps = set(reps)

    def add(self, rep: model.SalesRep):

        self._reps.add(rep)

    def get(self, ref) -> model.SalesRep:

        return next((r for r in self._reps if r.reference == ref), None)

# Imitacja jednostki do testów serwisowych
class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.companies = FakeCompanyRepository([])
        self.reps = FakeRepRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def commit(self):
        self._commit()

    def rollback(self):
        pass

    def collect_new_events(self):
        for company in self.companies._companies:
            while company.events:
                yield company.events.pop(0)


# TODO: write tests for all the handlers (including daily maintenance), write endpoints for 2 of them

class TestEnsureRep:

    def test_ensure_rep_creates_new_rep(self):
        uow = FakeUnitOfWork()
        command = commands.EnsureRepExists(rep_name="Jan Kowalski")

        messagebus.handle(command, uow)

        assert uow.committed is True
        rep = uow.reps.get("jankow")
        assert rep is not None
        assert rep.reference == "jankow"
        assert rep.name == "jan kowalski"
        assert rep.email == "jan.kowalski@zeppolska.pl"

    def test_ensure_rep_does_not_duplicate_existing_rep(self):
        uow = FakeUnitOfWork()
        existing_rep = model.SalesRep("jankow", "jan kowalski", "jan.kowalski@zeppolska.pl")
        uow.reps.add(existing_rep)

        command = commands.EnsureRepExists(rep_name="Jan Kowalski")

        messagebus.handle(command, uow)

        assert uow.committed is True
        assert len(uow.reps._reps) == 1
        rep = uow.reps.get("jankow")
        assert rep == existing_rep

class TestEnsureCompany:

    def test_ensure_company_creates_new_company(self):
        uow = FakeUnitOfWork()
        command = commands.EnsureCompanyExists(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )

        messagebus.handle(command, uow)

        assert uow.committed is True
        company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert company is not None
        assert company.nip == model.NIP("0000000000")
        assert company.name == "Company1"
        assert company.address == model.Address("Street1", "1", "00-000", "City1")

    def test_ensure_company_does_not_duplicate_existing_company(self):
        uow = FakeUnitOfWork()
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        uow.companies.add(company)

        command = commands.EnsureCompanyExists(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )

        messagebus.handle(command, uow)

        assert uow.committed is True
        assert len(uow.companies._companies) == 1

class TestUpdateLastZk:

    def test_update_last_zk_sets_last_zk(self):
        uow = FakeUnitOfWork()
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        uow.companies.add(company)

        command = commands.UpdateLastZK(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
            zk_date=date(2025, 1, 1),
            rep_name="Jan Kowalski",
        )

        messagebus.handle(command, uow)

        assert uow.committed is True
        updated_company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert updated_company.last_zk is not None
        assert updated_company.last_zk.nip == "0000000000"
        assert updated_company.last_zk.rep_name == "Jan Kowalski"
        assert updated_company.last_zk.transaction_date == date(2025, 1, 1)

class TestSynchronizeRep:

    def test_synchronize_rep_from_zk(self):
        uow = FakeUnitOfWork()
        # Data preparation phase, simulation of the whole maintenance process through handlers:
        rep_command = commands.EnsureRepExists(rep_name="Jan Kowalski")
        company_command = commands.EnsureCompanyExists(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        zk_command = commands.UpdateLastZK(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
            zk_date=date(2025, 1, 1),
            rep_name="Jan Kowalski",
        )
        messagebus.handle(rep_command, uow)
        messagebus.handle(company_command, uow)
        messagebus.handle(zk_command, uow)
        company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert company is not None
        assert company.last_zk is not None
        assert company.last_zk.rep_name == "Jan Kowalski"
        assert company.current_rep is None

        # The target handler operation: rep synchronization from company's last_zk:
        synchronize_rep_command = commands.SynchronizeRep(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        rep = uow.reps.get("jankow")

        messagebus.handle(synchronize_rep_command, uow)
        updated_company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert updated_company.current_rep == rep

    def test_synchronize_rep_raises_when_no_last_zk(self):
        uow = FakeUnitOfWork()
        # Data preparation phase:
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        uow.companies.add(company)
        # Target handler:
        target_command = commands.SynchronizeRep(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        with pytest.raises(model.NoZK, match="Cannot synchronize LTD/Rep without ZK snapshot for company "
                                             f"NIP={company.nip.value}, street={company.address.street},"
                                             f" building_nr={company.address.building_nr}, "
                                             f"postal_code={company.address.postal_code}, city={company.address.city}"):
            messagebus.handle(target_command, uow)
        assert uow.committed is False

class TestSynchronizeLTD:

    def test_synchronize_ltd_from_zk(self):
        uow = FakeUnitOfWork()

        # Data preparation phase, simulation of the whole maintenance process through handlers:
        rep_command = commands.EnsureRepExists(rep_name="Jan Kowalski")
        company_command = commands.EnsureCompanyExists(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        zk_command = commands.UpdateLastZK(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
            zk_date=date(2025, 1, 1),
            rep_name="Jan Kowalski",
        )
        messagebus.handle(rep_command, uow)
        messagebus.handle(company_command, uow)
        messagebus.handle(zk_command, uow)

        company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert company is not None
        assert company.last_zk is not None
        assert company.ltd is None

        target_command = commands.SynchronizeLTD(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )

        messagebus.handle(target_command, uow)
        updated_company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert updated_company.ltd == date(2025, 1, 1)

    def test_synchronize_ltd_raises_when_no_last_zk(self):
        uow = FakeUnitOfWork()
        # Data preparation phase:
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        uow.companies.add(company)
        # Target handler:
        target_command = commands.SynchronizeLTD(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )

        with pytest.raises(
                model.NoZK,
                match="Cannot synchronize LTD/Rep without ZK snapshot for company "
                                             f"NIP={company.nip.value}, street={company.address.street},"
                                             f" building_nr={company.address.building_nr}, "
                                             f"postal_code={company.address.postal_code}, city={company.address.city}"):
            messagebus.handle(target_command, uow)

        assert uow.committed is False

class TestWarnRepAfter5Months:

    def prepare_company_ready_for_5m_warning(self, uow: FakeUnitOfWork):
        rep = model.SalesRep(
            reference="jankow",
            name="Jan Kowalski",
            email="jan.kowalski@zeppolska.pl",
        )
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        company.assign_to_rep(rep)
        company.ltd = date.today() - relativedelta(months=5)

        uow.companies.add(company)
        uow.reps.add(rep)
        return company

    def test_warns_rep_after_5_month_ltd_period(self):
        uow = FakeUnitOfWork()
        # State preparation
        # Data preparation phase, simulation of the whole process:
        rep_command = commands.EnsureRepExists(rep_name="Jan Kowalski")
        company_command = commands.EnsureCompanyExists(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        zk_command = commands.UpdateLastZK(
            nip="0000000000",
            name="Company1",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
            zk_date=date.today() - relativedelta(months=5),
            rep_name="Jan Kowalski",
        )
        rep_sync_command = commands.SynchronizeRep(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        ltd_sync_command = commands.SynchronizeLTD(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        messagebus.handle(rep_command, uow)
        messagebus.handle(company_command, uow)
        messagebus.handle(zk_command, uow)
        messagebus.handle(rep_sync_command, uow)
        messagebus.handle(ltd_sync_command, uow)

        company = uow.companies.get(
            model.NIP("0000000000"),
            model.Address("Street1", "1", "00-000", "City1"),
        )
        assert company.last_zk is not None
        assert company.ltd == date.today() - relativedelta(months=5)
        assert company.current_rep.reference == "jankow"
        assert company.current_rep.name == "jan kowalski"
        assert company.current_rep.email == "jan.kowalski@zeppolska.pl"
        assert company._warned_5m == False

        # Target handler operation (triggering the 5m warning basing on ltd):
        target_command = commands.WarnRepAfter5Months(
            nip="0000000000",
            street="Street1",
            building_nr="1",
            postal_code="00-000",
            city="City1",
        )
        messagebus.handle(target_command, uow)

        assert company._warned_5m == True

    def test_warns_rep_after_5_month_ltd_period_isolated(self):
        uow = FakeUnitOfWork()
        company = self.prepare_company_ready_for_5m_warning(uow)
        assert company._warned_5m == False
        messagebus.handle(
            commands.WarnRepAfter5Months(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )

        assert company._warned_5m is True

    def test_warn_rep_after_5_months_does_nothing_when_already_warned(self):
        uow = FakeUnitOfWork()
        company = self.prepare_company_ready_for_5m_warning(uow)
        company._warned_5m = True

        messagebus.handle(
            commands.WarnRepAfter5Months(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )

        assert company._warned_5m is True

    def test_warn_rep_after_5_months_does_nothing_without_rep(self):
        uow = FakeUnitOfWork()
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        company.ltd = date.today() - relativedelta(months=5)
        uow.companies.add(company)

        messagebus.handle(
            commands.WarnRepAfter5Months(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )

        assert company._warned_5m is False

    def test_warn_rep_after_5_months_does_nothing_if_not_in_warning_window(self):
        uow = FakeUnitOfWork()
        rep = model.SalesRep(
            reference="jankow",
            name="Jan Kowalski",
            email="jan.kowalski@zeppolska.pl",
        )
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        company.assign_to_rep(rep)
        company.ltd = date.today() - relativedelta(months=4, days=1)
        uow.companies.add(company)
        uow.reps.add(rep)

        messagebus.handle(
            commands.WarnRepAfter5Months(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )

        assert company._warned_5m is False

class TestReleaseStale:

    def prepare_company_ready_for_stale_release(self, uow: FakeUnitOfWork):
        rep = model.SalesRep(
            reference="jankow",
            name="Jan Kowalski",
            email="jan.kowalski@zeppolska.pl",
        )
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        company.assign_to_rep(rep)
        company.ltd = date.today() - relativedelta(months=6)

        uow.companies.add(company)
        uow.reps.add(rep)
        return company

    def test_release_stale_releases_after_6m_isolated(self):
        uow = FakeUnitOfWork()
        company = self.prepare_company_ready_for_stale_release(uow)

        assert company.current_rep is not None

        messagebus.handle(
            commands.ReleaseStale(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )
        assert company.current_rep is None

    def test_release_stale_does_nothing_when_no_rep(self):
        uow = FakeUnitOfWork()
        company = model.Company(
            nip=model.NIP("0000000000"),
            name="Company1",
            address=model.Address("Street1", "1", "00-000", "City1"),
        )
        uow.companies.add(company)

        assert company.current_rep is None

        messagebus.handle(
            commands.ReleaseStale(
                nip="0000000000",
                street="Street1",
                building_nr="1",
                postal_code="00-000",
                city="City1",
            ),
            uow,
        )
        assert company.current_rep is None


# """
# Juz nie
# """
# class TestAssign:
#
#     def test_returns_reference(self):
#         # 1. Create company and rep FIRST
#         uow = FakeUnitOfWork()
#         company_event = events.CompanyCreated("000000000", "Company", "Street", "1", "00-000", "City1")
#         messagebus.handle(company_event, uow)  # Now repo has the company
#
#         rep_event = events.SalesRepCreated("namsur", "Name Surname", "email@gmail.com")
#         messagebus.handle(rep_event, uow)
#         # 2. THEN assign
#         assignment_event = events.AssignmentRequired("000000000", "Street", "1", "00-000", "City1", "namsur")
#         result = messagebus.handle(assignment_event, uow)
#
#         assert result[0] == "namsur"
#
#     def test_raises_company_already_assigned_event_if_cannot_assign(self):
#
#         uow = FakeUnitOfWork()
#         messagebus.handle(events.CompanyCreated("000000000", "Company", "Street", "1", "00-000", "City1"), uow)  # Now repo has the company
#         messagebus.handle(events.SalesRepCreated("namsur", "Name Surname", "email@gmail.com"), uow) # First Rep
#         messagebus.handle(events.SalesRepCreated("jankow", "Jan Kowalski", "jank@gmail.com"), uow) # Second Rep
#         messagebus.handle(events.AssignmentRequired("000000000", "Street", "1", "00-000", "City1", "namsur"),
#                           uow) # Assignment of the first rep
#         with pytest.raises(model.CompanyAlreadyAssigned):
#             messagebus.handle(events.AssignmentRequired("000000000", "Street", "1", "00-000", "City1", "jankow"),
#                               uow)  # Assignment of the second rep -> throws AlreadyAssigned Exception
#
#         # assert product.events[-1] == events.OutOfStock(event.sku)
#         # assert empty_assignment[-1] is None