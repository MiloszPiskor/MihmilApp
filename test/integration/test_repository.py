from domain import model
from adapters import repository
from sqlalchemy import text
import pytest

# Buidling the persistence adapter around our domain
# Company:

@pytest.fixture(autouse=True)
def clean_db(postgres_session):
    postgres_session.execute(text("""
        TRUNCATE TABLE company_assignments, sales_reps, companies RESTART IDENTITY CASCADE
    """))
    postgres_session.commit()

def test_repository_can_save_company(postgres_session):

    company = model.Company(model.NIP("0000000000"), 'Company1', model.Address('Street1', '1', '00-000', 'City1'), 1)

    repo = repository.SQLAlchemyCompanyRepository(postgres_session)
    repo.add(company)
    postgres_session.commit()

    rows = list(postgres_session.execute(text("""
    SELECT nip, name, street, building_nr,postal_code, city, version from companies
    """)))

    assert rows == [(model.NIP("0000000000").value, 'Company1', 'Street1', '1', '00-000', 'City1', 1)]

def test_repository_can_retrieve_company_with_assigned_rep(postgres_session):
    # Manually add company
    postgres_session.execute(text("""
        INSERT INTO companies (nip, name, street, building_nr, postal_code, city, version)
        VALUES ('0000000000', 'Company1', 'Street1', '1', '00-000', 'City1', 1)
    """))

    # Manually add sales rep
    postgres_session.execute(text("""
        INSERT INTO sales_reps (reference, name, email) VALUES
        ('rep', 'Name', 'email@gmail.com')
    """))

    # Select IDs from the tables
    [[company_id]] = postgres_session.execute(text("""
        SELECT id FROM companies WHERE nip=:nip AND street=:street AND building_nr=:building_nr 
        AND postal_code=:postal_code AND city=:city AND version=:version"""),
        dict(nip = "0000000000", street = "Street1", building_nr = "1", postal_code = "00-000", city = "City1", version = 1)
    )
    [[rep_id]] = postgres_session.execute(text("""
        SELECT id FROM sales_reps WHERE reference=:reference AND name=:name AND email=:email
        """),
        dict(reference="rep", name="Name", email="email@gmail.com")
    )

    # Tie them through intermediary table
    postgres_session.execute(text("""
        INSERT INTO company_assignments (company_id, rep_id) VALUES
        (:company_id, :rep_id)
        """),
        dict(company_id=company_id, rep_id=rep_id)
    )
    postgres_session.commit()

    expected = model.Company(model.NIP("0000000000"), "Company1", model.Address('Street1', '1', '00-000', 'City1'), 1)

    # Retrieve through repository (should hydrate relationships)
    repo = repository.SQLAlchemyCompanyRepository(postgres_session)
    retrieved = repo.get(nip=model.NIP("0000000000"), address=model.Address('Street1', '1', '00-000', 'City1'))

    # Assert the assignment was successful and repo correctly sees it
    assert expected == retrieved
    assert retrieved.current_rep == model.SalesRep(reference="rep", name="Name", email="email@gmail.com")
    assert retrieved.current_rep.id == rep_id


def test_repository_can_save_sales_rep(postgres_session):
    repo = repository.SQLAlchemyRepRepository(postgres_session)

    rep = model.SalesRep("namsur", "Name Surname", "mail@gmail.com")
    repo.add(rep)
    postgres_session.commit()

    rows = list(postgres_session.execute(text("""
        SELECT reference, name, email
        FROM sales_reps
        WHERE reference = :reference
    """), {"reference": rep.reference}))

    assert rows == [(rep.reference, rep.name, rep.email)]

def test_repository_can_retrieve_sales_rep(postgres_session):

    # Manually add sales rep
    postgres_session.execute(text("""
        INSERT INTO sales_reps (reference, name, email) VALUES
        ('namsur', 'Name Surname', 'email@gmail.com')
    """))

    [[rep_id]] = postgres_session.execute(text("""
        SELECT id FROM sales_reps WHERE reference=:reference AND name=:name AND email=:email
        """),
        dict(reference="namsur", name="Name Surname", email="email@gmail.com")
    )
    expected = model.SalesRep('namsur', 'Name Surname', 'email@gmail.com')

    repo = repository.SQLAlchemyRepRepository(postgres_session)
    retrieved = repo.get('namsur')

    assert expected == retrieved
    assert retrieved.id == rep_id


















