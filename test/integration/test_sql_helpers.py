from sqlalchemy import text
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from infrastructure import sql_helpers
from domain import model

def test_recent_zk_companies_query_returns_only_companies_with_zk_dated_last_24h(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO companies (nip, name, street, building_nr, postal_code, city, last_zk_transaction_date, version)
        VALUES
        (:nip1, :name1, :street1, :building_nr1, :postal_code1, :city1, :last_zk_date1, :version1),
        (:nip2, :name2, :street2, :building_nr2, :postal_code2, :city2, :last_zk_date2, :version2)
    """), {
        "nip1": "1111111111",
        "name1": "Recent Company",
        "street1": "Main",
        "building_nr1": "1",
        "postal_code1": "00-001",
        "city1": "Warsaw",
        "last_zk_date1": date.today(),
        "version1": 1,
        "nip2": "222222222",
        "name2": "Old Company",
        "street2": "Side",
        "building_nr2": "2",
        "postal_code2": "00-002",
        "city2": "Krakow",
        "last_zk_date2": date.today() - timedelta(days=2),
        "version2": 1,
    })

    result = sql_helpers.recent_zk_companies(postgres_session)

    assert result == [
        model.CompanyCandidate(
            nip="1111111111",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        )
    ]

def test_warning_5m_candidates_returns_only_assigned_companies_in_warning_window(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO sales_reps (reference, name, email)
        VALUES
        (:reference1, :name1, :email1),
        (:reference2, :name2, :email2)
    """), dict(
        reference1="rep-1",
        name1="Rep One",
        email1="rep1@example.com",
        reference2="rep-2",
        name2="Rep Two",
        email2="rep2@example.com",
    ))

    postgres_session.execute(text("""
        INSERT INTO companies (
            nip, name, street, building_nr, postal_code, city,
            last_zk_transaction_date, version
        )
        VALUES
        (:nip1, :name1, :street1, :building_nr1, :postal_code1, :city1,
         :last_zk_date1, :version1),
        (:nip2, :name2, :street2, :building_nr2, :postal_code2, :city2,
         :last_zk_date2, :version2),
        (:nip3, :name3, :street3, :building_nr3, :postal_code3, :city3,
         :last_zk_date3, :version3)
    """), dict(
        nip1="1111111111",
        name1="Eligible Company",
        street1="Main",
        building_nr1="1",
        postal_code1="00-001",
        city1="Warsaw",
        last_zk_date1=date.today() - relativedelta(months=5, days=1),
        version1=1,

        nip2="2222222222",
        name2="Not Assigned",
        street2="Side",
        building_nr2="2",
        postal_code2="00-002",
        city2="Krakow",
        last_zk_date2=date.today() - relativedelta(months=5, days=1),
        version2=1,

        nip3="3333333333",
        name3="Too Recent",
        street3="Other",
        building_nr3="3",
        postal_code3="00-003",
        city3="Gdansk",
        last_zk_date3=date.today(),
        version3=1,
    ))

    [[company_id_1]] = postgres_session.execute(text("""
        SELECT id FROM companies
        WHERE nip=:nip AND street=:street AND building_nr=:building_nr
          AND postal_code=:postal_code AND city=:city AND version=:version
    """), dict(
        nip="1111111111",
        street="Main",
        building_nr="1",
        postal_code="00-001",
        city="Warsaw",
        version=1,
    ))

    [[company_id_3]] = postgres_session.execute(text("""
        SELECT id FROM companies
        WHERE nip=:nip AND street=:street AND building_nr=:building_nr
          AND postal_code=:postal_code AND city=:city AND version=:version
    """), dict(
        nip="3333333333",
        street="Other",
        building_nr="3",
        postal_code="00-003",
        city="Gdansk",
        version=1,
    ))

    [[rep_id]] = postgres_session.execute(text("""
        SELECT id FROM sales_reps
        WHERE reference=:reference AND name=:name AND email=:email
    """), dict(
        reference="rep-1",
        name="Rep One",
        email="rep1@example.com",
    ))

    postgres_session.execute(text("""
        INSERT INTO company_assignments (company_id, rep_id)
        VALUES 
        (:company_id1, :rep_id1), 
        (:company_id2, :rep_id2)
    """), dict(
        company_id1=company_id_1, rep_id1=rep_id,
        company_id2=company_id_3, rep_id2=rep_id
    ))

    result = sql_helpers.warning_5m_candidates(postgres_session)

    assert result == [
        model.CompanyCandidate(
            nip="1111111111",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        )
    ]

def test_stale_candidates_returns_only_assigned_companies_older_than_6_months(postgres_session):
    postgres_session.execute(text("""
        INSERT INTO sales_reps (reference, name, email)
        VALUES
        (:reference1, :name1, :email1),
        (:reference2, :name2, :email2)
    """), dict(
        reference1="rep-1",
        name1="Rep One",
        email1="rep1@example.com",
        reference2="rep-2",
        name2="Rep Two",
        email2="rep2@example.com",
    ))

    postgres_session.execute(text("""
        INSERT INTO companies (
            nip, name, street, building_nr, postal_code, city,
            last_zk_transaction_date, version
        )
        VALUES
        (:nip1, :name1, :street1, :building_nr1, :postal_code1, :city1,
         :last_zk_date1, :version1),
        (:nip2, :name2, :street2, :building_nr2, :postal_code2, :city2,
         :last_zk_date2, :version2),
        (:nip3, :name3, :street3, :building_nr3, :postal_code3, :city3,
         :last_zk_date3, :version3)
    """), dict(
        nip1="1111111111",
        name1="Eligible Stale",
        street1="Main",
        building_nr1="1",
        postal_code1="00-001",
        city1="Warsaw",
        last_zk_date1=date.today() - relativedelta(months=6, days=1),
        version1=1,

        nip2="2222222222",
        name2="Not Assigned",
        street2="Side",
        building_nr2="2",
        postal_code2="00-002",
        city2="Krakow",
        last_zk_date2=date.today() - relativedelta(months=6, days=1),
        version2=1,

        nip3="3333333333",
        name3="Too Recent",
        street3="Other",
        building_nr3="3",
        postal_code3="00-003",
        city3="Gdansk",
        last_zk_date3=date.today() - relativedelta(months=5),
        version3=1,
    ))

    [[company_id_1]] = postgres_session.execute(text("""
        SELECT id FROM companies
        WHERE nip=:nip AND street=:street AND building_nr=:building_nr
          AND postal_code=:postal_code AND city=:city AND version=:version
    """), dict(
        nip="1111111111",
        street="Main",
        building_nr="1",
        postal_code="00-001",
        city="Warsaw",
        version=1,
    ))

    [[company_id_3]] = postgres_session.execute(text("""
        SELECT id FROM companies
        WHERE nip=:nip AND street=:street AND building_nr=:building_nr
          AND postal_code=:postal_code AND city=:city AND version=:version
    """), dict(
        nip="3333333333",
        street="Other",
        building_nr="3",
        postal_code="00-003",
        city="Gdansk",
        version=1,
    ))

    [[rep_id]] = postgres_session.execute(text("""
        SELECT id FROM sales_reps
        WHERE reference=:reference AND name=:name AND email=:email
    """), dict(
        reference="rep-1",
        name="Rep One",
        email="rep1@example.com",
    ))

    postgres_session.execute(text("""
        INSERT INTO company_assignments (company_id, rep_id)
        VALUES 
        (:company_id1, :rep_id1), 
        (:company_id2, :rep_id2)
    """), dict(
        company_id1=company_id_1, rep_id1=rep_id,
        company_id2=company_id_3, rep_id2=rep_id
    ))

    result = sql_helpers.stale_candidates(postgres_session)

    assert result == [
        model.CompanyCandidate(
            nip="1111111111",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        )
    ]



