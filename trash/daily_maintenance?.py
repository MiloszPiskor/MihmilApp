from typing import Dict, Tuple
from domain import model
from service_layer import messagebus, unit_of_work
from rep_mapper import ZKMapper
import subiekt_gateway

# Global mutable REPS_DATA (thread-safe z lockiem jeśli Celery)
REPS_DATA: Dict[str, Tuple[str, str]] = {}

"""
Pattern: Every handler like a service function, acting on behalf of uow, supported by
SQL queries to work on already predefined candidates for action. Put the operation through messagebus
to utizile queue and pick up all internal events etc. on the way.
 -> Command or Event????? !Dopracuj
 -> CQRS jako sql queries functions?
---
WERSJA 1.0: JEDEN SQL PULL: 
---
return uow.subiekt.execute
(         SELECT DISTINCT 
            ah.adrh_NIP as nip, k.kh_Symbol as name,
            ah.adrh_Ulica as street, ah.adrh_NrLokalu as building_nr,
            ah.adrh_Kod as postal_code, ah.adrh_Miejscowosc as city,
            g.grk_Nazwa as rep_group_name,
            MAX(d.dok_DataWyst) as last_zk_date
        FROM dok__Dokument d 
        JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
        JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId  -- ZŁoty Graal NIP!
        LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
        WHERE d.dok_Typ = 16 AND k.kh_Rodzaj = 2 
        AND d.dok_DataWyst >= DATEADD(day, -1, GETDATE())
        GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrLokalu,
                 ah.adrh_Kod, ah.adrh_Miejscowosc, g.grk_Nazwa
        ORDER BY MAX(d.dok_DataWyst) DESC
).fetchall()  # [cite:4]
---
POTEM 3 handlery na taski na ZK row, zasilane jednym Cmd:
@dataclass(frozen=True)
class ProcessZk24hCmd:
    nip: str
    name: str
    street: str
    building_nr: str
    postal_code: str
    city: str
    rep_group_name: str
    last_zk_date: date
A handler:
def process_zk_24h_row(cmd: ProcessZk24hRowCmd, uow):
    # 1. Szukaj po adresie (unikalny key)
    company = uow.companies.get_by_address(cmd.nip, cmd.street, cmd.building_nr, cmd.postal_code, cmd.city)
    
    # 2. NEW? → create
    if not company:
    create_event = events.CompanyCreated(
        nip=cmd.nip, name=cmd.name, street=cmd.street,
        building_nr=cmd.building_nr, postal_code=cmd.postal_code,
        city=cmd.city, ltd=cmd.last_zk_date
    )
    messagebus.handle(create_event, uow)
        is_new = True
    else:
        is_new = False
    
    # 3. LTD update?
    if cmd.last_zk_date > company.last_transaction_date:
        company.last_transaction_date = cmd.last_zk_date
    
    # 4. Rep logic
    mapper = ZKMapper(uow, REPS_DATA)
    rep = mapper.get_or_create(str(cmd.rep_group_name))
    if is_new or company.current_rep != rep:
        company.assign_to_rep(rep)  # → AssignmentRequired event!
    
    uow.commit()  # Wszystko → events chain
Tymczasem caly maintenance, wraz z dwoma handlers na wlasnej bazie: 
def daily_maintenance():
    with uow:
        # 1. WSZYSTKO z ZK 24h (new + changed rep + LTD)
        for row in zk_24h_raw(uow):
            cmd = ProcessZk24hRowCmd(row.nip, row.name, row.street, 
                                   row.building_nr, row.postal_code, row.city,
                                   row.rep_group_name, row.last_zk_date)
            messagebus.handle(cmd, uow)
        
        # 2. Warnings (stare spółki bez ZK dziś)
        for nip in warning_5m_candidates(uow):
            messagebus.handle(WarnRep5mCmd(nip), uow)
        
        # 3. Stale (>30 dni bez ZK)
        for nip in stale_candidates(uow):
            messagebus.handle(ReleaseStaleCmd(nip), uow)
        
        uow.commit()
"""
#
# def zk_24h_raw(subiekt_conn):
#     return subiekt_conn.execute("""
#     SELECT DISTINCT
#             ah.adrh_NIP as nip, k.kh_Symbol as name,
#             ah.adrh_Ulica as street, ah.adrh_NrLokalu as building_nr,
#             ah.adrh_Kod as postal_code, ah.adrh_Miejscowosc as city,
#             g.grk_Nazwa as rep_group_name,
#             MAX(d.dok_DataWyst) as last_zk_date
#     FROM dok__Dokument d
#     JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
#     JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId  -- ZŁoty Graal NIP!
#     LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
#     WHERE d.dok_Typ = 16 AND k.kh_Rodzaj = 2
#     AND d.dok_DataWyst >= DATEADD(day, -1, GETDATE())
#     GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrLokalu,
#         ah.adrh_Kod, ah.adrh_Miejscowosc, g.grk_Nazwa
#     ORDER BY MAX(d.dok_DataWyst) DESC
#     """).fetchall()
#
# # ADD TO HANDLERS:
# def process_zk_24h_row(cmd: ProcessZk24hRowCmd, uow: unit_of_work.AbstractUnitOfWork):
#
#     # 1. Szukaj po nip i adresie (unikalny key)
#     with uow:
#         address, nip = model.Address(
#             street=cmd.street,
#             building_nr=cmd.building_nr,
#             postal_code=cmd.postal_code,
#             city=cmd.city
#         ), model.NIP(cmd.nip)
#         company = uow.companies.get(nip, address)
#
#         # 2. NEW? → create
#         if not company:
#             company = model.Company(nip=nip, name=cmd.name,
#                                         address=address)  # InvalidNip -> catch this error later (endpoint or cron)
#             uow.companies.add(company)
#             is_new = True
#         else:
#             is_new = False
#
#         # 3. LTD update?
#         if cmd.last_zk_date > company.ltd:
#             company.ltd = cmd.last_zk_date
#
#         # 4. Rep logic
#         mapper = ZKMapper(uow, REPS_DATA)
#         rep = mapper.get_or_create(cmd.rep_group_name)
#
#         if company.current_rep != rep: # Rep release/ new rep required
#             if company.current_rep: # Old rep -> release
#                 company.release_from_rep()
#             # REPS_DATA[rep.name] = (rep.reference, rep.email)
#             company.assign_to_rep(rep)
#
#         uow.commit()
#
# def daily_maintenance(uow: unit_of_work.AbstractUnitOfWork):
#
#     # 1. WSZYSTKO z ZK 24h (new + changed rep + LTD)
#     subiekt_conn = subiekt_gateway.get_subiekt_connection()
#     for row in zk_24h_raw(subiekt_conn):
#         cmd = ProcessZk24hRowCmd(row.nip, row.name, row.street,
#                                  row.building_nr, row.postal_code, row.city,
#                                  row.rep_group_name, row.last_zk_date)
#         messagebus.handle(cmd, uow)
#
#     # 2. Warnings (stare spółki bez ZK dziś)
#     for nip in warning_5m_candidates(uow):
#         messagebus.handle(WarnRep5mCmd(nip), uow)
#
#     # 3. Stale (>30 dni bez ZK)
#     for nip in stale_candidates(uow):
#         messagebus.handle(ReleaseStaleCmd(nip), uow)



# def daily_maintenance():
#     """2AM: Subiekt sync + warnings + releases"""
#
#     with uow:
#         # 1. New Subiekt nips
# #       New nips so confronting each Subiekt ZK Row against a Large Companies SQL CQRS Pull?
#         for new_nip in subiekt_new_nips(uow):
#             create_event = events.CompanyCreated(**new_nip)
#             messagebus.handle(create_event, uow)
#         # 1.5 Assign this new NIP to a rep
#             assignment_event = AssignmentRequired(...)
#             messagebus.handle(assignment_event, uow)
#         uow.commit()
#
#         # 2. LTD sync (batch)
#         for nip in companies_last_24h(uow):
#             company = uow.companies.get(nip)
#             event = UpdateCompanyLtd(ltd=..., nip=...)
#             messagebus.handle(event, uow)
#         uow.commit()
#
#         # 3. Warnings 5m (Twój kod!)
#         # In this function we would have to split in two: one SQL query candidates,
#         # second to evaluate whether the notification is due or not
#         for nip in warning_5m_query(uow):
#             company = uow.companies.get(nip)
#             company.needs_precise_5month_warning() # Internal event
#             # messagebus.handle(event, uow)
#         uow.commit()
#
#         # 4. Stale releases (TWÓJ KOD!)
#         for nip in stale_companies_query(uow):
#             company = uow.companies.get(nip)
#             if company._current_rep:
#                 event = ReleaseCompany(...)
#                 messagebus.handle(event, uow)
#         uow.commit()