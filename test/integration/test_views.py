from datetime import date
import pytest
from sqlalchemy import text
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import clear_mappers
from domain import model
from service_layer import views, unit_of_work
from adapters.orm import company_assignments

@pytest.fixture(autouse=True)
def clean_db(postgres_session):
    postgres_session.execute(text("""
        TRUNCATE TABLE company_assignments, sales_reps, companies RESTART IDENTITY CASCADE
    """))
    postgres_session.commit()

def insert_rep(session, reference="r1", name="Jan Kowalski", email="jan@example.com"):
    session.execute(text("""
        INSERT INTO sales_reps (reference, name, email)
        VALUES (:reference, :name, :email)
    """), dict(reference=reference, name=name, email=email))

def insert_company(
    session,
    nip="1234567890",
    name="Company1",
    street="Main",
    building_nr="1",
    postal_code="00-001",
    city="Warszawa",
    ltd = None,
    version=1,
):
    session.execute(text("""
        INSERT INTO companies (nip, name, street, building_nr, postal_code, city, ltd, version)
        VALUES (:nip, :name, :street, :building_nr, :postal_code, :city, :ltd, :version)
    """), dict(
        nip=nip,
        name=name,
        street=street,
        building_nr=building_nr,
        postal_code=postal_code,
        city=city,
        ltd = ltd,
        version=version,
    ))

def assign_company(session, company_id, rep_id):
    session.execute(text("""
        INSERT INTO company_assignments (company_id, rep_id)
        VALUES (:company_id, :rep_id)
    """), dict(company_id=company_id, rep_id=rep_id))

def get_rep_id(session, reference, name, email):
    [[rep_id]] = session.execute(text("""
        SELECT id FROM sales_reps
        WHERE reference=:reference AND name=:name AND email=:email
    """), dict(
        reference=reference,
        name=name,
        email=email,
    ))
    return rep_id

def get_company_id(session, nip, street, building_nr, postal_code, city, version):
    [[company_id]] = session.execute(text("""
        SELECT id FROM companies
        WHERE nip=:nip AND street=:street AND building_nr=:building_nr
          AND postal_code=:postal_code AND city=:city AND version=:version
    """), dict(
        nip=nip,
        street=street,
        building_nr=building_nr,
        postal_code=postal_code,
        city=city,
        version=version,
    ))
    return company_id

def test_manager_search_reps_returns_matching_rep(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(uow.session)
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.manager_search_reps("Jan", unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)) # Works by Name, Surname, Name + Surname or Reference

    assert rows == [
        {"rep_reference": "r1", "rep_name": "Jan Kowalski"}
    ]

def test_rep_dashboard_returns_companies_for_rep(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(
            uow.session,
            nip="1111111111",
            name="Alpha",
            street="A",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            version=1,
        )
        company_id = get_company_id(uow.session, "1111111111", "A", "1", "00-001", "Warszawa", 1)
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.rep_dashboard("r1", unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory))

    assert rows == [
        {
            "nip": "1111111111",
            "company_name": "Alpha",
            "street": "A",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
            "last_transaction_date": None,
            "status" : "UNKNOWN",
        }
    ]

def test_manager_dashboard_returns_status(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")

        insert_company(
            uow.session,
            nip="1111111111",
            name="Alpha",
            street="A",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd = date.today() - relativedelta(months=1),
            version=1,
        )
        insert_company(
            uow.session,
            nip="2222222222",
            name="Beta",
            street="B",
            building_nr="2",
            postal_code="00-002",
            city="Kraków",
            ltd = date.today() - relativedelta(months=5),
            version=1,
        )
        insert_company(
            uow.session,
            nip="3333333333",
            name="Gamma",
            street="C",
            building_nr="3",
            postal_code="00-003",
            city="Gdańsk",
            ltd = date.today() - relativedelta(months=6),
            version=1,
        )

        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        c1 = get_company_id(uow.session, "1111111111", "A", "1", "00-001", "Warszawa", 1)
        c2 = get_company_id(uow.session, "2222222222", "B", "2", "00-002", "Kraków", 1)
        c3 = get_company_id(uow.session, "3333333333", "C", "3", "00-003", "Gdańsk", 1)

        assign_company(uow.session, c1, rep_id)
        assign_company(uow.session, c2, rep_id)
        assign_company(uow.session, c3, rep_id)

        uow.commit()

    rows = views.manager_dashboard("r1", unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory))

    assert rows == [
        {
            "rep_name": "Jan Kowalski",
            "company_name": "Alpha",
            "nip": "1111111111",
            "street": "A",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
            "last_transaction_date": date.today() - relativedelta(months=1),
            "status": "ACTIVE",
        },
        {
            "rep_name": "Jan Kowalski",
            "company_name": "Beta",
            "nip": "2222222222",
            "street": "B",
            "building_nr": "2",
            "postal_code": "00-002",
            "city": "Kraków",
            "last_transaction_date": date.today() - relativedelta(months=5),
            "status": "WARNING",
        },
        {
            "rep_name": "Jan Kowalski",
            "company_name": "Gamma",
            "nip": "3333333333",
            "street": "C",
            "building_nr": "3",
            "postal_code": "00-003",
            "city": "Gdańsk",
            "last_transaction_date": date.today() - relativedelta(months=6),
            "status": "STALE",
        },
    ]

def test_lookup_company_returns_available(postgres_session_factory):
    """
    The company, present in our system, which is unassigned, will return AVAILABLE upon a search
    without matching assigned other Address with the same NIP.
    """
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")

        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date(2026, 6, 1),
            version=1,
        )

        insert_company(
            uow.session,
            nip="1234567899",
            name="Company 2",
            street="Other",
            building_nr="2",
            postal_code="00-002",
            city="Kraków",
            ltd=None,
            version=1,
        )

        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)

        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.lookup_company_by_nip_and_address(
        "1234567899",
        model.Address("Other", "2", "00-002", "Kraków"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "nip": "1234567899",
            "status" : "AVAILABLE",
            "message" : "No matching company found in the system."
        }
    ]

def test_lookup_company_returns_occupied_other_address(postgres_session_factory):
    """
    The company, even though present in our system, which is unassigned, will return OCCUPIED_OTHER_ADDRESS upon a search
    for matching NIP with other company in the system.
    """
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")

        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date(2026, 6, 1),
            version=1,
        )

        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Warehouse",
            street="Side",
            building_nr="12",
            postal_code="00-100",
            city="Warszawa",
            ltd=date(2026, 6, 1),
            version=1,
        )

        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Other", "2", "00-002", "Kraków"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "nip": "1234567890",
            "status": "OCCUPIED_OTHER_ADDRESS",
            "message": (
                "This NIP exists in the system and is assigned to another rep, "
                "but this exact address was not found."
            ),
            "occupied_addresses": [
                {
                    "nip": "1234567890",
                    "company_name": "Acme HQ",
                    "street": "Main",
                    "building_nr": "1",
                    "postal_code": "00-001",
                    "city": "Warszawa",
                }
            ],
        }
    ]

def test_lookup_company_returns_all_occupied_addresses(postgres_session_factory):
    """
    When the same NIP exists in multiple occupied addresses, the lookup returns all of them
    in occupied_addresses without revealing rep identity.
    """
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_rep(uow.session, reference="r2", name="Anna Nowak")

        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date(2026, 6, 1),
            version=1,
        )
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Warehouse",
            street="Side",
            building_nr="12",
            postal_code="00-100",
            city="Warszawa",
            ltd=date(2026, 6, 1),
            version=1,
        )

        rep1_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        rep2_id = get_rep_id(uow.session, "r2", "Anna Nowak", "jan@example.com")

        c1 = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        c2 = get_company_id(uow.session, "1234567890", "Side", "12", "00-100", "Warszawa", 1)

        assign_company(uow.session, c1, rep1_id)
        assign_company(uow.session, c2, rep2_id)
        uow.commit()

    rows = views.lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Other", "2", "00-002", "Kraków"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "nip": "1234567890",
            "status": "OCCUPIED_OTHER_ADDRESS",
            "message": (
                "This NIP exists in the system and is assigned to another rep, "
                "but this exact address was not found."
            ),
            "occupied_addresses": [
                {
                    "nip": "1234567890",
                    "company_name": "Acme HQ",
                    "street": "Main",
                    "building_nr": "1",
                    "postal_code": "00-001",
                    "city": "Warszawa",
                },
                {
                    "nip": "1234567890",
                    "company_name": "Acme Warehouse",
                    "street": "Side",
                    "building_nr": "12",
                    "postal_code": "00-100",
                    "city": "Warszawa",
                },
            ],
        }
    ]

def test_manager_lookup_company_returns_active(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=1),
            version=1,
        )
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Main", "1", "00-001", "Warszawa"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "status": "ACTIVE",
            "message": "Company found.",
            "company": {
                "nip": "1234567890",
                "company_name": "Acme HQ",
                "street": "Main",
                "building_nr": "1",
                "postal_code": "00-001",
                "city": "Warszawa",
                "last_transaction_date": date.today() - relativedelta(months=1),
                "assigned_rep_reference": "r1",
                "assigned_rep_name": "Jan Kowalski",
            },
            "other_addresses": [],
        }
    ]

def test_manager_lookup_company_returns_warning(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=5),
            version=1,
        )
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Main", "1", "00-001", "Warszawa"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows[0]["status"] == "WARNING"

def test_manager_lookup_company_returns_stale(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=6),
            version=1,
        )
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Main", "1", "00-001", "Warszawa"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows[0]["status"] == "STALE"

def test_manager_lookup_company_returns_unassigned(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=1),
            version=1,
        )
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Main", "1", "00-001", "Warszawa"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "status": "UNASSIGNED",
            "message": "Company found.",
            "company": {
                "nip": "1234567890",
                "company_name": "Acme HQ",
                "street": "Main",
                "building_nr": "1",
                "postal_code": "00-001",
                "city": "Warszawa",
                "last_transaction_date": date.today() - relativedelta(months=1),
                "assigned_rep_reference": None,
                "assigned_rep_name": None,
            },
            "other_addresses": [],
        }
    ]

def test_manager_lookup_company_returns_not_found_with_other_addresses(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=1),
            version=1,
        )
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Branch",
            street="Side",
            building_nr="2",
            postal_code="00-002",
            city="Kraków",
            ltd=date.today() - relativedelta(months=5),
            version=1,
        )
        rep_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        company_id = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        assign_company(uow.session, company_id, rep_id)
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Other", "9", "00-009", "Poznań"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "status": "NOT_FOUND",
            "message": "No exact company found for this NIP and address.",
            "other_addresses": [
                {
                    "nip": "1234567890",
                    "company_name": "Acme HQ",
                    "street": "Main",
                    "building_nr": "1",
                    "postal_code": "00-001",
                    "city": "Warszawa",
                    "last_transaction_date": date.today() - relativedelta(months=1),
                    "assigned_rep_reference": "r1",
                    "assigned_rep_name": "Jan Kowalski",
                    "status": "ACTIVE",
                },
                {
                    "nip": "1234567890",
                    "company_name": "Acme Branch",
                    "street": "Side",
                    "building_nr": "2",
                    "postal_code": "00-002",
                    "city": "Kraków",
                    "last_transaction_date": date.today() - relativedelta(months=5),
                    "assigned_rep_reference": None,
                    "assigned_rep_name": None,
                    "status": "UNASSIGNED",
                },
            ],
        }
    ]

def test_manager_lookup_company_returns_not_found_without_other_addresses(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "9999999999",
        model.Address("X", "1", "00-000", "Nowhere"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "status": "NOT_FOUND",
            "message": "No matching company found.",
            "other_addresses": [],
        }
    ]

def test_manager_lookup_company_returns_full_mixed_set(postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        insert_rep(uow.session, reference="r1", name="Jan Kowalski")
        insert_rep(uow.session, reference="r2", name="Anna Nowak")
        insert_rep(uow.session, reference="r3", name="Piotr Zieliński")

        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme HQ",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warszawa",
            ltd=date.today() - relativedelta(months=1),
            version=1,
        )
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Branch A",
            street="Side",
            building_nr="2",
            postal_code="00-002",
            city="Kraków",
            ltd=date.today() - relativedelta(months=5),
            version=1,
        )
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Branch B",
            street="Depot",
            building_nr="3",
            postal_code="00-003",
            city="Gdańsk",
            ltd=date.today() - relativedelta(months=6),
            version=1,
        )
        insert_company(
            uow.session,
            nip="1234567890",
            name="Acme Branch C",
            street="Park",
            building_nr="4",
            postal_code="00-004",
            city="Poznań",
            ltd=None,
            version=1,
        )
        insert_company(
            uow.session,
            nip="9999999999",
            name="Other Corp",
            street="Else",
            building_nr="9",
            postal_code="99-999",
            city="Łódź",
            ltd=date.today() - relativedelta(months=1),
            version=1,
        )

        r1_id = get_rep_id(uow.session, "r1", "Jan Kowalski", "jan@example.com")
        r2_id = get_rep_id(uow.session, "r2", "Anna Nowak", "jan@example.com")
        r3_id = get_rep_id(uow.session, "r3", "Piotr Zieliński", "jan@example.com")

        c1 = get_company_id(uow.session, "1234567890", "Main", "1", "00-001", "Warszawa", 1)
        c2 = get_company_id(uow.session, "1234567890", "Side", "2", "00-002", "Kraków", 1)
        c3 = get_company_id(uow.session, "1234567890", "Depot", "3", "00-003", "Gdańsk", 1)
        c4 = get_company_id(uow.session, "1234567890", "Park", "4", "00-004", "Poznań", 1)

        assign_company(uow.session, c1, r1_id)
        assign_company(uow.session, c2, r2_id)
        assign_company(uow.session, c3, r3_id)
        uow.commit()

    rows = views.manager_lookup_company_by_nip_and_address(
        "1234567890",
        model.Address("Main", "1", "00-001", "Warszawa"),
        unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory),
    )

    assert rows == [
        {
            "status": "ACTIVE",
            "message": "Company found.",
            "company": {
                "nip": "1234567890",
                "company_name": "Acme HQ",
                "street": "Main",
                "building_nr": "1",
                "postal_code": "00-001",
                "city": "Warszawa",
                "last_transaction_date": date.today() - relativedelta(months=1),
                "assigned_rep_reference": "r1",
                "assigned_rep_name": "Jan Kowalski",
            },
            "other_addresses": [
                {
                    "nip": "1234567890",
                    "company_name": "Acme Branch B",
                    "street": "Depot",
                    "building_nr": "3",
                    "postal_code": "00-003",
                    "city": "Gdańsk",
                    "last_transaction_date": date.today() - relativedelta(months=6),
                    "assigned_rep_reference": "r3",
                    "assigned_rep_name": "Piotr Zieliński",
                    "status": "STALE",
                },
                {
                    "nip": "1234567890",
                    "company_name": "Acme Branch C",
                    "street": "Park",
                    "building_nr": "4",
                    "postal_code": "00-004",
                    "city": "Poznań",
                    "last_transaction_date": None,
                    "assigned_rep_reference": None,
                    "assigned_rep_name": None,
                    "status": "UNASSIGNED",
                },
                {
                    "nip": "1234567890",
                    "company_name": "Acme Branch A",
                    "street": "Side",
                    "building_nr": "2",
                    "postal_code": "00-002",
                    "city": "Kraków",
                    "last_transaction_date": date.today() - relativedelta(months=5),
                    "assigned_rep_reference": "r2",
                    "assigned_rep_name": "Anna Nowak",
                    "status": "WARNING",
                },
            ],
        }
    ]







