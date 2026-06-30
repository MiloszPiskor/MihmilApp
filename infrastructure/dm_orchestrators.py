from infrastructure import sql_helpers
from service_layer import unit_of_work, messagebus
from domain import commands
import logging_config

logger = logging_config.get_logger(__name__)

def ingest_recent_zk_rows(subiekt_conn, report_writer):
    logger.info("Zaczynam proces pobierania danych z serwera Subiekt.")

    for idx, row in enumerate(sql_helpers.zk_24h_raw(subiekt_conn), start=1):
        logger.info(f"IDX: '{idx}' rozpoczęty.")
        try:
            logger.info("Porcja Rep rozpoczęta.")
            messagebus.handle(
                message=commands.EnsureRepExists(rep_name=row.rep_group_name),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
            logger.info("Porcja Company rozpoczęta.")
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
            logger.info("Porcja ZK rozpoczęta.")
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
            report_writer.write_line(
                f"ingest_recent_zk_rows failed. idx={idx}, "
                f"nip={getattr(row, 'nip', None)}, "
                f"zk_date={getattr(row, 'zk_date', None)}, "
                f"rep_group_name={getattr(row, 'rep_group_name', None)}, "
                f"error={repr(e)}"
            )
            logger.exception(
                f"Ingest failed for row, reason: {e}",
                extra={"idx": idx, "nip": getattr(row, "nip", None), "rep": getattr(row, "rep_group_name", None)},
            )

def synchronize_recent_companies():
    logger.info("Starting synchronizing recent companies")
    session = unit_of_work.DEFAULT_SESSION_FACTORY()

    for idx, row in enumerate(sql_helpers.recent_zk_companies(session=session), start=1):
        logger.info(f"Synchronizing companies, idx: {idx}")
        try:
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
        except Exception as e:
            logger.exception(
                "synchronize_recent_companies failed",
                extra={
                    "idx": idx, "nip": getattr(row, "nip", None), "street": getattr(row, "street", None),
                    "building_nr": getattr(row, "building_nr", None),
                    "postal_code": getattr(row, "postal_code", None), "city": getattr(row, "city", None),
                    "error": repr(e)
                },
            )
            continue

def process_warning_candidates():
    logger.info("Starting warning candidates")
    session = unit_of_work.DEFAULT_SESSION_FACTORY()

    for idx, row in enumerate(sql_helpers.warning_5m_candidates(session=session), start=1):
        logger.info(f"Processing warning candidates, idx: {idx}")
        try:
            messagebus.handle(
                message=commands.WarnRepAfter5Months(
                    nip=row.nip,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        except Exception as e:
            logger.exception(
                "process_warning_candidates failed",
                extra={
                    "idx": idx, "nip": getattr(row, "nip", None), "street": getattr(row, "street", None),
                    "building_nr": getattr(row, "building_nr", None),
                    "postal_code": getattr(row, "postal_code", None), "city": getattr(row, "city", None),
                    "error": repr(e)
                },
            )
            continue

def process_stale_candidates():
    logger.info("Starting processing stale")
    session = unit_of_work.DEFAULT_SESSION_FACTORY()

    for idx, row in enumerate(sql_helpers.stale_candidates(session=session), start=1):
        logger.info(f"Processing stale, idx: {idx}")
        try:
            messagebus.handle(
                message=commands.ReleaseStale(
                    nip=row.nip,
                    street=row.street,
                    building_nr=row.building_nr,
                    postal_code=row.postal_code,
                    city=row.city,
                ),
                uow=unit_of_work.SqlAlchemyUnitOfWork(),
            )
        except Exception as e:
            logger.exception(
                "process_stale_candidates failed",
                extra={
                    "idx": idx, "nip": getattr(row, "nip", None), "street": getattr(row, "street", None),
                    "building_nr": getattr(row, "building_nr", None),
                    "postal_code": getattr(row, "postal_code", None), "city": getattr(row, "city", None),
                    "error": repr(e)
                },
            )
            continue