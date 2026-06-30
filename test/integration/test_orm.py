import pytest
from sqlalchemy.exc import IntegrityError
from domain import model
from datetime import date
from sqlalchemy import text

@pytest.fixture(autouse=True)
def clean_db(postgres_session):
    postgres_session.execute(text("""
        TRUNCATE TABLE company_assignments, sales_reps, companies RESTART IDENTITY CASCADE
    """))
    postgres_session.commit()

def test_sales_rep_mapper_can_load_reps(postgres_session):
    postgres_session.execute(text(
        "INSERT INTO sales_reps (reference, name, email) VALUES "
        "('bartchyl', 'Bartosz Chyliński', 'bartosz.chylinski@zeppolska.pl'),"
        "('michnoj', 'Michał Nojman', 'michal.nojman@zeppolska.pl'),"
        "('piosik', 'Piotr Sikorski', 'piotr.sikorski@zeppolska.pl')"
    ))
    expected = [
        model.SalesRep("bartchyl", "Bartosz Chyliński", "bartosz.chylinski@zeppolska.pl"),
        model.SalesRep("michnoj", "Michał Nojman", "michal.nojman@zeppolska.pl"),
        model.SalesRep("piosik", "Piotr Sikorski", "piotr.sikorski@zeppolska.pl"),
    ]
    assert postgres_session.query(model.SalesRep).all() == expected

def test_sales_rep_mapper_can_save_reps(postgres_session):
    new_rep = model.SalesRep(reference="new_rep", name="New Rep", email="mail@.pl")
    postgres_session.add(new_rep)
    postgres_session.commit()

    rows = list(postgres_session.execute(text("SELECT reference, name, email FROM sales_reps")))

    assert rows == [(new_rep.reference, new_rep.name, new_rep.email)]

def test_retrieving_companies(postgres_session):
    postgres_session.execute(text("""
    INSERT INTO companies (nip, name, street, building_nr, postal_code, city, version)
     VALUES ('0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', '1')
     """))

    postgres_session.execute(text("""
    INSERT INTO companies (nip, name, street, building_nr, postal_code, city, version)
     VALUES ('0000000001', 'Company2', 'Street2', '2', '00-002', 'City2', '1')
     """))

    expected = [
        model.Company(model.NIP("0000000000"), "Company1", model.Address("Street1", "1", "00-000", "City1"), 1),
        model.Company(model.NIP("0000000001"), "Company2",model.Address("Street2", "2", "00-002", "City2"),1)
    ]

    assert postgres_session.query(model.Company).all() == expected

def test_saving_companies(postgres_session):
    company = model.Company(model.NIP('0000000000'), 'Company1',model.Address('Street1', '1', '00-000', 'City1'), 1)
    postgres_session.add(company)
    postgres_session.commit()
    rows = list(postgres_session.execute(text("""
        SELECT nip, name, street, building_nr, postal_code, city, version from companies              
    """)))

    assert rows == [(company.nip.value, company.name,company.address.street, company.address.building_nr, company.address.postal_code,company.address.city, company.version)]

def test_saving_assignments(postgres_session):
    company = model.Company(model.NIP('0000000000'), 'Company1', model.Address('Street1', '1', '00-000', 'City1'), 1)
    rep = model.SalesRep(reference="new_rep", name="New Rep", email="mail@.pl")
    company.assign_to_rep(rep)
    postgres_session.add(rep)
    postgres_session.add(company)
    postgres_session.commit()

    rows = list(postgres_session.execute(text("""
        SELECT company_id, rep_id FROM company_assignments
    """)))

    assert rows == [(company.id, rep.id)]

def test_retrieving_assignments(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO companies (nip, name, street, building_nr, postal_code, city, version)
        VALUES ('0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', '1')
    """))
    [[company_id]] = postgres_session.execute(text("""
        SELECT id FROM companies WHERE nip=:nip AND street=:street AND building_nr=:building_nr 
        AND postal_code=:postal_code AND city=:city AND version=:version"""),
        dict(nip = "0000000000", street = "Street1", building_nr = "1", postal_code = "00-000", city = "City1", version = 1)
    )

    postgres_session.execute(text("""
        INSERT INTO sales_reps (reference, name, email) VALUES
        ('rep', 'Name', 'email@gmail.com')
    """))
    [[rep_id]] = postgres_session.execute(text("""
        SELECT id FROM sales_reps WHERE reference=:reference AND name=:name AND email=:email
        """),
        dict(reference="rep", name="Name", email="email@gmail.com")
    )

    postgres_session.execute(text("""
        INSERT INTO company_assignments (company_id, rep_id) VALUES
        (:company_id, :rep_id)
        """),
        dict(company_id=company_id, rep_id=rep_id)
    )

    company = postgres_session.query(model.Company).one()

    assert company.current_rep == model.SalesRep("rep", "Name", "email@gmail.com")
    assert company.current_rep.id == rep_id

def test_full_assignment_roundtrip(postgres_session):
    company = model.Company(model.NIP("0000000000"), 'Company1', model.Address('Street1', '1', '00-000', 'City1'), 1)
    rep = model.SalesRep(reference="new_rep", name="New Rep", email="mail@.pl")

    company.assign_to_rep(rep)

    postgres_session.add_all([company, rep])
    postgres_session.commit()

    postgres_session.expire_all()

    loaded = postgres_session.query(model.Company).one()

    assert loaded.current_rep == rep

# ZK and Address composites
def test_loading_company_with_address_and_zk_vo(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO companies (nip, name, street, building_nr, postal_code, city, 
        last_zk_nip, last_zk_name, last_zk_street, last_zk_building_nr, last_zk_postal_code, 
        last_zk_city, last_zk_transaction_date, last_zk_rep_name, 
        version)
        VALUES ('0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', 
        '0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', '2025-01-01'::date, 'Name Surname',
        1)
    """))

    company = postgres_session.query(model.Company).one()

    assert company.address == model.Address("Street1", "1", "00-000", "City1")
    assert company.last_zk == model.ZK("0000000000", "Company1", "Street1", "1", "00-000", "City1", date(2025, 1, 1), "Name Surname")

def test_saving_company_with_address_and_zk_vo(postgres_session):
    address = model.Address("Street1", "1", "00-000", "City1")
    last_zk = model.ZK("0000000000", "Company1", "Street1", "1", "00-000", "City1", date(2025, 1, 1), "Name Surname")
    company = model.Company(nip=model.NIP("0000000000"), name="Company1", address=address, last_zk=last_zk, version_number=1)

    postgres_session.add(company)
    postgres_session.commit()

    row_address = postgres_session.execute(text("""
        SELECT street, building_nr, postal_code, city FROM companies
    """)).one()
    row_last_zk = postgres_session.execute(text("""
    SELECT last_zk_nip, last_zk_name, last_zk_street, last_zk_building_nr, last_zk_postal_code, last_zk_city,
     last_zk_transaction_date, last_zk_rep_name FROM companies
     """)).one()
    saved = postgres_session.query(model.Company).one()
    assert row_address == ("Street1", "1", "00-000", "City1")
    assert row_last_zk == ("0000000000", "Company1", "Street1", "1", "00-000", "City1", date(2025, 1, 1), "Name Surname")
    assert saved.address == address
    assert saved.last_zk == last_zk

def test_loading_company_with_null_zk_returns_none(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO companies (
            nip, name, street, building_nr, postal_code, city, version,
            last_zk_nip, last_zk_name, last_zk_street, last_zk_building_nr,
            last_zk_postal_code, last_zk_city, last_zk_transaction_date, last_zk_rep_name
        )
        VALUES (
            '0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', 1,
            NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
        )
    """))

    company = postgres_session.query(model.Company).one()

    assert company.last_zk is None

# Business rule:
# - Company identity = NIP + Address
# - Same NIP + Address → forbidden
# - Same NIP + different Address → allowed (separate divisions)
def test_unique_constraint_protects_against_collisions(postgres_session):
    company_1 = model.Company(
        model.NIP("0000000000"),
        'Company1',
        model.Address('Street1', '1', '00-000', 'City1'),
        1
    )

    company_2 = model.Company(
        model.NIP("0000000000"),
        'Company2',  # different name SHOULD NOT matter
        model.Address('Street1', '1', '00-000', 'City1'),
        1
    )

    postgres_session.add_all([company_1, company_2])

    with pytest.raises(IntegrityError):
        postgres_session.commit()

    postgres_session.rollback()

    rows = list(postgres_session.execute(text("SELECT * FROM companies")))
    assert len(rows) in (0, 1)

def test_unique_constraint_allows_for_same_nip_with_multiple_addresses(postgres_session):
    company_1 = model.Company(
        model.NIP("0000000000"),
        'Company1',
        model.Address('Street1', '1', '00-000', 'City1'),
        1
    )

    company_2 = model.Company(
        model.NIP("0000000000"),
        'Company1',
        model.Address('Street2', '2', '00-000', 'City1'),
        1
    )

    postgres_session.add_all([company_1, company_2])
    postgres_session.commit()

    results = postgres_session.query(model.Company).all()
    assert set(results) == {company_1, company_2}

# Business rule:
# - Sales Rep identity = reference
# - Same references → forbidden
def test_sales_rep_reference_must_be_unique(postgres_session):
    rep_a = model.SalesRep("namsur", "Name Surname", "mail@gmail.com")
    rep_b = model.SalesRep("namsur", "Surname Name", "gmail@mail.com")

    postgres_session.add(rep_a)
    postgres_session.add(rep_b)

    with pytest.raises(IntegrityError):
        postgres_session.commit()

    postgres_session.rollback()

    rows = list(postgres_session.execute(text("SELECT * FROM companies")))
    assert len(rows) == 0

