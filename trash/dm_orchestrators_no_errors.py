from infrastructure import sql_helpers
from service_layer import unit_of_work, messagebus
from domain import commands

def ingest_recent_zk_rows(subiekt_conn):
    for row in sql_helpers.zk_24h_raw(subiekt_conn):
        messagebus.handle(
            message=commands.EnsureRepExists(rep_name=row.rep_group_name),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )
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

def synchronize_recent_companies():
    session = unit_of_work.DEFAULT_SESSION_FACTORY()
    for row in sql_helpers.recent_zk_companies(session=session):
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

def process_warning_candidates():
    session = unit_of_work.DEFAULT_SESSION_FACTORY()
    for row in sql_helpers.warning_5m_candidates(session=session):
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

def process_stale_candidates():
    session = unit_of_work.DEFAULT_SESSION_FACTORY()
    for row in sql_helpers.stale_candidates(session=session):
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