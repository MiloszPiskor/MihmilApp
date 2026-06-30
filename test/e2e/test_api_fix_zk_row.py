from datetime import date
import pytest
from service_layer.unit_of_work import SqlAlchemyUnitOfWork as RealSqlAlchemyUnitOfWork
from sqlalchemy import text
from domain import model

def test_fix_zk_row_endpoint_happy_path(client, postgres_session_factory, monkeypatch):
    import entrypoints.flask_app as flask_app # <- moduł, gdzie jest endpoint fix_zk_row

    def patched_uow(*args, **kwargs):
        return RealSqlAlchemyUnitOfWork(postgres_session_factory)

    monkeypatch.setattr(flask_app.unit_of_work, "SqlAlchemyUnitOfWork", patched_uow)

    payload = {
        "rep_name": "Jan Kowalski",
        "nip": "1234567890",
        "name": "Company1",
        "street": "Main",
        "building_nr": "1",
        "postal_code": "00-001",
        "city": "Warszawa",
        "zk_date": "2026-06-24",
    }

    response = client.post("/api/office/fix-zk-row", json=payload)
    assert response.status_code == 204

    # Additional assertions checking for consistency of the data
    uow = RealSqlAlchemyUnitOfWork(postgres_session_factory)
    with uow:

        address = model.Address("Main", "1", "00-001", "Warszawa")
        nip = model.NIP("1234567890")
        company = uow.companies.get(nip=nip, address=address)

        rep_row = uow.session.execute(text("""
            SELECT reference, name
            FROM sales_reps
            WHERE name = :name
        """), {"name": "jan kowalski"}).mappings().one()

        company_row = uow.session.execute(text("""
            SELECT id, nip, name, street, building_nr, postal_code, city, ltd, last_zk_transaction_date
            FROM companies
            WHERE nip = :nip
        """), {"nip": "1234567890"}).mappings().one()

        assignment_row = uow.session.execute(text("""
            SELECT ca.company_id, ca.rep_id
            FROM company_assignments ca
            JOIN companies c ON c.id = ca.company_id
            JOIN sales_reps sr ON sr.id = ca.rep_id
            WHERE c.nip = :nip AND sr.name = :rep_name
        """), {"nip": "1234567890", "rep_name": "jan kowalski"}).mappings().one()

        assert company.current_rep is not None
        assert company.current_rep.reference == rep_row["reference"]
        assert company.current_rep.name == rep_row["name"]

        assert company.last_zk is not None
        assert company.last_zk.transaction_date == date(2026, 6, 24)
        assert company.last_zk.rep_name == "Jan Kowalski"
        assert company.last_zk.nip == "1234567890"
        assert company.last_zk.name == "Company1"
        assert company.last_zk.street == "Main"
        assert company.last_zk.building_nr == "1"
        assert company.last_zk.postal_code == "00-001"
        assert company.last_zk.city == "Warszawa"

    assert rep_row["reference"] is not None # or == "jankow"
    assert rep_row["name"] == "jan kowalski"
    assert company_row["last_zk_transaction_date"] == date(2026, 6, 24)
    assert company_row["ltd"] == date(2026, 6, 24)
    assert assignment_row["company_id"] == company_row["id"]
    assert assignment_row["rep_id"] is not None

def test_fix_zk_row_endpoint_rejects_bad_date(client):
    payload = {
        "rep_name": "Jan Kowalski",
        "nip": "1234567890",
        "name": "Company1",
        "street": "Main",
        "building_nr": "1",
        "postal_code": "00-001",
        "city": "Warszawa",
        "zk_date": "24-06-2026",
    }

    response = client.post("/api/office/fix-zk-row", json=payload)

    assert response.status_code == 400
    assert response.get_json()["error"] == "zk_date must be in YYYY-MM-DD format"

def test_fix_zk_row_endpoint_missing_rep_name(client):
    payload = {
        "nip": "1234567890",
        "name": "Company1",
        "street": "Main",
        "building_nr": "1",
        "postal_code": "00-001",
        "city": "Warszawa",
        "zk_date": "2026-06-24",
    }

    response = client.post("/api/office/fix-zk-row", json=payload)

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "missing fields"
    assert "rep_name" in body["missing"]
