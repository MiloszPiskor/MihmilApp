# from datetime import datetime, timedelta
#
# from domain import commands, model
# from service_layer import messagebus, unit_of_work
# from infrastructure import subiekt_gateway
#
#
# def final_daily_maintenance():
#     subiekt_conn = subiekt_gateway.get_subiekt_connection()
#
#     ingest_recent_zk_rows(subiekt_conn)
#     synchronize_recent_companies()
#     process_warning_candidates()
#     process_stale_candidates()
#
#
#
#
#
# # Phase 1
# def ingest_recent_zk_rows(subiekt_conn):
#     for row in zk_24h_raw(subiekt_conn):
#         messagebus.handle(
#             message=commands.EnsureRepExists(rep_name=row.rep_group_name),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#         messagebus.handle(
#             message=commands.EnsureCompanyExists(
#                 nip=row.nip,
#                 name=row.name,
#                 street=row.street,
#                 building_nr=row.building_nr,
#                 postal_code=row.postal_code,
#                 city=row.city,
#             ),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#         messagebus.handle(
#             message=commands.UpdateLastZK(
#                 nip=row.nip,
#                 name=row.name,
#                 street=row.street,
#                 building_nr=row.building_nr,
#                 postal_code=row.postal_code,
#                 city=row.city,
#                 zk_date=row.zk_date,
#                 rep_name=row.rep_group_name,
#             ),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#
# # Phase 2
# def synchronize_recent_companies():
#     for row in recent_zk_companies():
#         messagebus.handle(
#             message=commands.SynchronizeRep(
#                 nip=row.nip,
#                 street=row.street,
#                 building_nr=row.building_nr,
#                 postal_code=row.postal_code,
#                 city=row.city,
#             ),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#         messagebus.handle(
#             message=commands.SynchronizeLTD(
#                 nip=row.nip,
#                 street=row.street,
#                 building_nr=row.building_nr,
#                 postal_code=row.postal_code,
#                 city=row.city,
#             ),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#
# # Phase 3
# def process_warning_candidates():
#     for row in warning_5m_candidates():
#         messagebus.handle(
#             message=commands.WarnRep5mCmd(row.nip, row.address),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#
# #Phase 4
# def process_stale_candidates():
#     for row in stale_candidates():
#         messagebus.handle(
#             message=commands.ReleaseStaleCmd(row.nip, row.address),
#             uow=unit_of_work.SqlAlchemyUnitOfWork(),
#         )
#
# CQRS SQL QUERIES
QUERY_ZK_24H = """
SELECT DISTINCT
    ah.adrh_NIP as nip,
    k.kh_Symbol as name,
    ah.adrh_Ulica as street,
    ah.adrh_NrLokalu as building_nr,
    ah.adrh_Kod as postal_code,
    ah.adrh_Miejscowosc as city,
    g.grk_Nazwa as rep_group_name,
    MAX(d.dok_DataWyst) as zk_date
FROM dok__Dokument d
JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId
LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
WHERE d.dok_Typ = 16
  AND k.kh_Rodzaj = 2
  AND d.dok_DataWyst >= DATEADD(day, -1, GETDATE())
GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrLokalu,
         ah.adrh_Kod, ah.adrh_Miejscowosc, g.grk_Nazwa
ORDER BY MAX(d.dok_DataWyst) DESC
"""


QUERY_RECENT_ZK_COMPANIES = """
SELECT DISTINCT
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_date >= DATEADD(day, -1, GETDATE())
ORDER BY c.last_zk_date DESC
"""
QUERY_WARNING_5M = """
SELECT DISTINCT
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_date < DATEADD(month, -5, GETDATE())
  AND c.last_zk_date >= DATEADD(month, -6, GETDATE())
  AND c.warning_sent_at IS NULL
ORDER BY c.last_zk_date ASC
"""
QUERY_STALE = """
SELECT DISTINCT  # MUST INCLUDE CONTAINS CURRENT REP
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_date < DATEADD(month, -6, GETDATE())
  AND c.stale_processed_at IS NULL
ORDER BY c.last_zk_date ASC
"""

# Helpers with SQL queries (CQRS):
# def zk_24h_raw(subiekt_conn) -> list[ZKRow]:
#     rows = subiekt_conn.execute(QUERY_ZK_24H).fetchall()
#     return [
#         ZKRow(
#             nip=row.nip,
#             name=row.name,
#             street=row.street,
#             building_nr=row.building_nr,
#             postal_code=row.postal_code,
#             city=row.city,
#             rep_group_name=row.rep_group_name,
#             zk_date=row.zk_date,
#         )
#         for row in rows
#     ]

# @dataclass(frozen=True)
# class CompanyCandidate:
#     nip: str
#     street: str
#     building_nr: str
#     postal_code: str
#     city: str
#
# def recent_zk_companies(session) -> list[CompanyCandidate]:
#     rows = session.execute(QUERY_RECENT_ZK_COMPANIES).fetchall()
#     return [
#         CompanyCandidate(
#             nip=row.nip,
#             street=row.street,
#             building_nr=row.building_nr,
#             postal_code=row.postal_code,
#             city=row.city,
#         )
#         for row in rows
#     ]
#
# def warning_5m_candidates(session) -> list[CompanyCandidate]:
#     rows = session.execute(QUERY_WARNING_5M).fetchall()
#     return [
#         CompanyCandidate(
#             nip=row.nip,
#             street=row.street,
#             building_nr=row.building_nr,
#             postal_code=row.postal_code,
#             city=row.city,
#         )
#         for row in rows
#     ]
#
# def stale_candidates(session) -> list[CompanyCandidate]:
#     rows = session.execute(QUERY_STALE).fetchall()
#     return [
#         CompanyCandidate(
#             nip=row.nip,
#             street=row.street,
#             building_nr=row.building_nr,
#             postal_code=row.postal_code,
#             city=row.city,
#         )
#         for row in rows
#     ]
