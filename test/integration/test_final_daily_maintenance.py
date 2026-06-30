"""
Prosty test integracyjny: final_daily_maintenance() na prawdziwych danych z Subiekta.
Sprawdza, czy nasza baza (PREXPOL_Test) się spopuluje.
"""
import pytest
from sqlalchemy import text
from infrastructure import subiekt_gateway
from infrastructure import full_integration_test_config as test_config
import logging_config

logger = logging_config.get_logger(__name__)


def clear_test_db(postgres_session):
    postgres_session.execute(text("""
        TRUNCATE TABLE company_assignments, sales_reps, companies RESTART IDENTITY CASCADE
    """))
    postgres_session.commit()


@pytest.mark.integration
def test_final_daily_maintenance_populates_db(postgres_session, test_uow_factory):
    clear_test_db(postgres_session)

    logger.info("=" * 80)
    logger.info("START TESTU INTEGRACYJNEGO: daily_maintenance()")
    logger.info("=" * 80)

    subiekt_conn = subiekt_gateway.get_subiekt_connection()
    zk_rows = test_config.zk_all_raw(subiekt_conn)
    assert len(zk_rows) > 0, "Brak ZK w Subiekcie!"
    subiekt_conn.close()

    before_count = postgres_session.execute(text("SELECT COUNT(*) FROM companies")).scalar_one()
    before_rep_count = postgres_session.execute(text("SELECT COUNT(*) FROM sales_reps")).scalar_one()

    logger.info(f"companies PRZED: {before_count}")
    logger.info(f"sales_reps PRZED: {before_rep_count}")

    test_config.daily_maintenance()

    after_count = postgres_session.execute(text("SELECT COUNT(*) FROM companies")).scalar_one()
    after_rep_count = postgres_session.execute(text("SELECT COUNT(*) FROM sales_reps")).scalar_one()

    logger.info(f"companies PO: {after_count}")
    logger.info(f"sales_reps PO: {after_rep_count}")

    sample_companies = postgres_session.execute(text("""
        SELECT nip, name, last_zk_transaction_date, version
        FROM companies
        ORDER BY last_zk_transaction_date DESC
        LIMIT 5
    """)).all()

    for row in sample_companies:
        logger.info(f"NIP={row.nip}, name={row.name}, last_zk={row.last_zk_transaction_date}")

    assert after_count > 0, "Baza nie spopulowała się! Brak Company."
    assert after_count > before_count, f"Brak nowych: {before_count} → {after_count}"
    assert after_rep_count > 0, "Baza nie spopulowała się! Brak sales_reps."
    logger.info("=" * 80)
    logger.info("🎉 TEST ZAKOŃCZONY SUKCESEM")


