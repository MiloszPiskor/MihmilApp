"""
Full integration test config — daily maintenance bez filtra czasu (TOP 100 dla performance).
"""
from infrastructure import sql_helpers, subiekt_gateway, dm_orchestrators
from service_layer import unit_of_work, messagebus
from domain import commands
from sqlalchemy import text
from domain import model
from . import cqrs
import logging_config

logger = logging_config.get_logger(__name__)

def zk_all_raw(subiekt_conn) -> list[model.ZKRow]:
    """Test: Wszystkie ZK (bez filtra czasu, TOP 100)."""
    rows = subiekt_conn.execute(cqrs.QUERY_ZK_ALL).fetchall()
    return [
        model.ZKRow(
            nip=row.nip,
            name=row.name,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
            rep_group_name=row.rep_group_name,
            zk_date=row.zk_date,
        )
        for row in rows
    ]


def ingest_all_zk_rows(subiekt_conn):
    """Ingestuje TOP 100 ZK z Subiekta (bez filtra czasu)."""
    count = 0
    for row in zk_all_raw(subiekt_conn):
        try:
            logger.info(f"Zaczynam ingest, porcja rep: {count}")
            messagebus.handle(
                message=commands.EnsureRepExists(rep_name=row.rep_group_name),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
            logger.info("Zaczynam ingest, porcja company:")
            messagebus.handle(
                message=commands.EnsureCompanyExists(
                    nip=row.nip,
                    name=row.name,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
            logger.info("Zaczynam ingest, porcja ZK:")
            messagebus.handle(
                message=commands.UpdateLastZK(
                    nip=row.nip,
                    name=row.name,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                    zk_date=row.zk_date,
                    rep_name=row.rep_group_name,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        except Exception as e:
            logger.exception(
                f"Ingest failed for row, reason: {e}",
                extra={"count": count, "nip": getattr(row, "nip", None), "rep": getattr(row, "rep_group_name", None)},
            )
        finally:
            count += 1


def recent_zk_companies_all(session) -> list[model.CompanyCandidate]:
    """Test: Wszystkie companies z last_zk_transaction_date (bez filtra czasu)."""
    rows = session.execute(text(cqrs.QUERY_ALL_ZK_COMPANIES)).fetchall()
    return [
        model.CompanyCandidate(
            nip=row.nip,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
        )
        for row in rows
    ]


def synchronize_all_companies():
    """Synchronizuje wszystkie companies z last_zk_transaction_date (bez filtra czasu)."""
    session = unit_of_work.DEFAULT_SESSION_FACTORY()
    try:
        for row in recent_zk_companies_all(session):
            messagebus.handle(
                message=commands.SynchronizeRep(
                    nip=row.nip,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
            messagebus.handle(
                message=commands.SynchronizeLTD(
                    nip=row.nip,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        session.commit()
    finally:
        session.close()


def daily_maintenance():
    """
    Pełna daily maintenance (testowa wersja bez filtra czasu).
    """
    subiekt_conn = subiekt_gateway.get_subiekt_connection()

    ingest_all_zk_rows(subiekt_conn)
    logger.info("ingestion completed")
    synchronize_all_companies()
    logger.info("synchro zakończona")
    dm_orchestrators.process_warning_candidates()  # Nie zmieniać — działa z 5 miesięcy
    logger.info("warnings zakończona")
    dm_orchestrators.process_stale_candidates()  # Nie zmieniać — działa z 6 miesięcy
    logger.info("stale release zakończona")

    subiekt_conn.close()
