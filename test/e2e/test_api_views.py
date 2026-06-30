from datetime import date
import pytest
from sqlalchemy import text
from adapters.orm import company_assignments
from service_layer import unit_of_work
from domain import model

@pytest.fixture(autouse=True)
def clean_db(postgres_session):
    postgres_session.execute(text("""
        TRUNCATE TABLE company_assignments, sales_reps, companies RESTART IDENTITY CASCADE
    """))
    postgres_session.commit()

def test_search_reps_api(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        rep = model.SalesRep(reference="r1", name="Jan Kowalski", email="jan@example.com")
        company = model.Company(
            nip=model.NIP("1234567890"),
            name="Company1",
            address=model.Address("Main", "1", "00-001", "Warszawa"),
        )
        uow.session.add(rep)
        uow.session.add(company)
        uow.session.flush()
        uow.session.execute(company_assignments.insert().values(company_id=company.id, rep_id=rep.id))
        uow.commit()

    response = client.get("/api/managers/reps/search", query_string={"query": "Jan"})

    assert response.status_code == 200
    assert response.get_json() == [
        {"rep_reference": "r1", "rep_name": "Jan Kowalski"}
    ]

def test_rep_dashboard_api(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        rep = model.SalesRep(reference="r1", name="Jan Kowalski", email="jan@example.com")
        company = model.Company(
            nip=model.NIP("1234567890"),
            name="Acme",
            address=model.Address("Main", "1", "00-001", "Warszawa"),
        )
        company.ltd = date(2026, 6, 1)
        uow.session.add(rep)
        uow.session.add(company)
        uow.session.flush()
        uow.session.execute(company_assignments.insert().values(company_id=company.id, rep_id=rep.id))
        uow.commit()

    response = client.get("/api/reps/r1/dashboard")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "nip": "1234567890",
            "company_name": "Acme",
            "street": "Main",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
            "status": "ACTIVE",
            "last_transaction_date": "2026-06-01",
        }
    ]

def test_manager_rep_dashboard_api(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        rep = model.SalesRep(reference="r1", name="Jan Kowalski", email="jan@example.com")
        company = model.Company(
            nip=model.NIP("1234567890"),
            name="Acme",
            address=model.Address("Main", "1", "00-001", "Warszawa"),
        )
        company.ltd = date(2026, 6, 1)
        uow.session.add(rep)
        uow.session.add(company)
        uow.session.flush()
        uow.session.execute(
            company_assignments.insert().values(company_id=company.id, rep_id=rep.id)
        )
        uow.commit()

    response = client.get("/api/managers/reps/r1/dashboard")

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "rep_name": "Jan Kowalski",
            "company_name": "Acme",
            "nip": "1234567890",
            "street": "Main",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
            "status": "ACTIVE",
            "last_transaction_date": "2026-06-01",
        }
    ]

def test_company_lookup_api_returns_occupied_other_address(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        rep = model.SalesRep(reference="r1", name="Jan Kowalski", email="jan@example.com")
        company = model.Company(
            nip=model.NIP("1234567890"),
            name="Acme HQ",
            address=model.Address("Main", "1", "00-001", "Warszawa"),
        )
        company.ltd = date(2026, 6, 1)
        uow.session.add(rep)
        uow.session.add(company)
        uow.session.flush()
        uow.session.execute(
            company_assignments.insert().values(company_id=company.id, rep_id=rep.id)
        )
        uow.commit()

    response = client.post(
        "/api/reps/company-lookup",
        json={
            "nip": "1234567890",
            "street": "Other",
            "building_nr": "2",
            "postal_code": "00-002",
            "city": "Kraków",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == [
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

def test_company_lookup_api_rejects_missing_json(client):
    response = client.post(
        "/api/reps/company-lookup",
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "invalid or missing JSON body"}


def test_company_lookup_api_rejects_missing_fields(client):
    response = client.post(
        "/api/reps/company-lookup",
        json={
            "nip": "1234567890",
            "street": "Main",
            "building_nr": "1",
            # missing postal_code and city
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "error": "missing fields",
        "missing": ["postal_code", "city"],
    }

def test_manager_company_lookup_api_returns_active(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        rep = model.SalesRep(reference="r1", name="Jan Kowalski", email="jan@example.com")
        company = model.Company(
            nip=model.NIP("1234567890"),
            name="Acme HQ",
            address=model.Address("Main", "1", "00-001", "Warszawa"),
        )
        company.ltd = date(2026, 6, 1)
        uow.session.add(rep)
        uow.session.add(company)
        uow.session.flush()
        uow.session.execute(company_assignments.insert().values(company_id=company.id, rep_id=rep.id))
        uow.commit()

    response = client.post(
        "/api/managers/company-lookup",
        json={
            "nip": "1234567890",
            "street": "Main",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == [
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
                "last_transaction_date": "2026-06-01",
                "assigned_rep_reference": "r1",
                "assigned_rep_name": "Jan Kowalski",
            },
            "other_addresses": [],
        }
    ]

def test_manager_company_lookup_api_returns_not_found(client, postgres_session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:
        uow.commit()

    response = client.post(
        "/api/managers/company-lookup",
        json={
            "nip": "1234567890",
            "street": "Main",
            "building_nr": "1",
            "postal_code": "00-001",
            "city": "Warszawa",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == [
        {
            "status": "NOT_FOUND",
            "message": "No matching company found.",
            "other_addresses": [],
        }
    ]
