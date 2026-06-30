# from typing import Dict, Tuple
# from domain import model, commands
# from service_layer import messagebus, unit_of_work, handlers
# from rep_mapper import ZKMapper
# import subiekt_gateway
#
# REPS_DATA: Dict[str, Tuple[str, str]] = {}
# # def zk_24h_raw(subiekt_conn):
# #     return subiekt_conn.execute("""
# #     SELECT DISTINCT
# #             ah.adrh_NIP as nip, k.kh_Symbol as name,
# #             ah.adrh_Ulica as street, ah.adrh_NrLokalu as building_nr,
# #             ah.adrh_Kod as postal_code, ah.adrh_Miejscowosc as city,
# #             g.grk_Nazwa as rep_group_name,
# #             MAX(d.dok_DataWyst) as last_zk_date
# #     FROM dok__Dokument d
# #     JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
# #     JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId  -- ZŁoty Graal NIP!
# #     LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
# #     WHERE d.dok_Typ = 16 AND k.kh_Rodzaj = 2
# #     AND d.dok_DataWyst >= DATEADD(day, -1, GETDATE())
# #     GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrLokalu,
# #         ah.adrh_Kod, ah.adrh_Miejscowosc, g.grk_Nazwa
# #     ORDER BY MAX(d.dok_DataWyst) DESC
# #     """).fetchall()
# QUERY = """
# #     SELECT DISTINCT
# #             ah.adrh_NIP as nip, k.kh_Symbol as name,
# #             ah.adrh_Ulica as street, ah.adrh_NrLokalu as building_nr,
# #             ah.adrh_Kod as postal_code, ah.adrh_Miejscowosc as city,
# #             g.grk_Nazwa as rep_group_name,
# #             MAX(d.dok_DataWyst) as zk_date
# #     FROM dok__Dokument d
# #     JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
# #     JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId  -- ZŁoty Graal NIP!
# #     LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
# #     WHERE d.dok_Typ = 16 AND k.kh_Rodzaj = 2
# #     AND d.dok_DataWyst >= DATEADD(day, -1, GETDATE())
# #     GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrLokalu,
# #         ah.adrh_Kod, ah.adrh_Miejscowosc, g.grk_Nazwa
# #     ORDER BY MAX(d.dok_DataWyst) DESC
# #     """
#
# def zk_24h_raw(subiekt_conn):
#     rows = subiekt_conn.execute(QUERY).fetchall()
#     return [model.ZKRow.from_sql_row(row) for row in rows]
#
# def update_last_zk(command: commands.UpdateLastZK, uow: unit_of_work.AbstractUnitOfWork):
#     nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code, command.city)
#
#     with uow:
#
#         zk = model.ZK(command.nip, command.name, command.street, command.building_nr, command.postal_code, command.city,
#                  command.zk_date, command.rep_name)
#
#         company = uow.companies.get(nip, address)
#
#         company.last_zk = zk
#         uow.commit()
#
# def ensure_company(command: commands.EnsureCompanyExists, uow: unit_of_work.AbstractUnitOfWork):
#     """
#     The command takes the data from Subiekt SQL query (ZK, Dok Typ 16) and makes sure the company
#     that made the order exists in the system.
#     """
#     with uow:
#         address, nip = model.Address(
#             street=command.street,
#             building_nr=command.building_nr,
#             postal_code=command.postal_code,
#             city=command.city
#         ), model.NIP(command.nip)
#         company = uow.companies.get(nip= nip, address=address)
#
#         if company is None:
#             new_company = model.Company(nip=nip, name=command.name,
#                                         address=address)  # InvalidNip -> catch this error later (endpoint or cron)
#             uow.companies.add(new_company)
#             uow.commit()
#
#         # return company.id  Dla chain!
#
# def ensure_rep(command: commands.EnsureRepExists, uow: unit_of_work.AbstractUnitOfWork):
#     """
#     The command takes the data from Subiekt SQL query (ZK, Dok Typ 16) and makes sure the sales rep
#     responsible for the order exists in the system.
#     """
#     with uow:
#         rep_name, mapper = command.rep_name, ZKMapper()
#         reference = mapper.get_or_create_reference(rep_name)
#         sales_rep = uow.reps.get(reference)
#
#         if sales_rep is None:
#             reference, email = mapper.get_rep_info(rep_name)
#             sales_rep = (model.SalesRep(reference=reference, name=rep_name, email=email))
#             uow.reps.add(sales_rep)
#             uow.commit()
#
#         # return reference  Dla AssignRepCmd!
# # def synchronize_rep_from_zk(commands.SynchronizeRepFromZk, uow)
#
# def final_daily_maintenance():
# """uow for each, like below, not for one initiated above, right?"""
#     subiekt_conn = subiekt_gateway.get_subiekt_connection()
#
#     for row in zk_24h_raw(subiekt_conn):
#         # 1: SQL Subiekt Query (ZK's from past 24h)
#         # Intercept Sales Rep from ZK
#         messagebus.handle(message=commands.EnsureRepExists(rep_name=row.rep_group_name), uow=unit_of_work.SqlAlchemyUnitOfWork())
#         # Intercept Company from ZK
#         messagebus.handle(message=commands.EnsureCompanyExists(
#             nip=row.nip, name=row.name, street=row.street,
#             building_nr=row.building_nr, postal_code=row.postal_code, city=row.city),
#             uow=unit_of_work.SqlAlchemyUnitOfWork()
#         )
#         # Assign ZK to appropriate Company
#         messagebus.handle(message=commands.UpdateLastZK(
#             nip=row.nip, name=row.name, rep_name=row.rep_group_name,
#             zk_date= row.zk_date,street=row.street, building_nr=row.building_nr,
#             postal_code=row.postal_code, city=row.city),
#             uow=unit_of_work.SqlAlchemyUnitOfWork()
#         )
#         # Internal DB Actions:
#         # 2. Synchronizing Sales Rep and LTD of recent Companies (the ones with ZK from past 24h)
#         for row in recent_zk_companies():
#             messagebus.handle(message=commands.SynchronizeRep(
#                 nip=row.nip, street=row.street, building_nr=row.building_nr,
#                 postal_code=row.postal_code, city=row.city),
#                 uow=unit_of_work.SqlAlchemyUnitOfWork()
#             )
#             messagebus.handle(message=commands.SynchronizeLTD(
#                 nip=row.nip, street=row.street, building_nr=row.building_nr,
#                 postal_code=row.postal_code, city=row.city),
#                 uow=unit_of_work.SqlAlchemyUnitOfWork()
#             )
#
#         # 3. Warnings (>=5m company.last_zk.transaction_date <6m)
#         for row in warning_5m_candidates():
#             messagebus.handle(WarnRep5mCmd(row.nip, row.address), uow)
#
#         # 4. Stale (>=6m company.last_zk.transaction_date)
#         for row in stale_candidates():
#             messagebus.handle(ReleaseStaleCmd(row.nip, row.address), uow)
#
# # Synchronizers:
# def synchronize_rep(command: commands.SynchronizeRep, uow: unit_of_work.AbstractUnitOfWork):
#     nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code,
#                                                          command.city)
#
#     with uow:
#         company = uow.companies.get(nip, address)
#         rep_name = company.last_zk.rep_name
#         reference = REPS_DATA.get(rep_name)[0]
#         sales_rep = uow.reps.get(reference)
#         company.synchronize_rep_from_zk(sales_rep)
#         uow.commit()
#
# def synchronize_ltd(command: commands.SynchronizeLTD, uow: unit_of_work.AbstractUnitOfWork):
#     nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code,
#                                                          command.city)
#
#     with uow:
#         company = uow.companies.get(nip, address)
#         company.synchronize_ltd_from_zk()
#         uow.commit()
#
#
# # def daily_maintenance(uow: unit_of_work.AbstractUnitOfWork):
# #
# #     # 1. WSZYSTKO z ZK 24h (new + changed rep + LTD)
# #     subiekt_conn = subiekt_gateway.get_subiekt_connection()
# #     # 1. WSZYSTKO z ZK 24h (new + changed rep + LTD)
# #     for row in zk_24h_raw(subiekt_conn):
# #
# #
# #         # 1. Company (potrzebny do LTD + assign)
# #         messagebus.handle(CreateCompanyCmd.from_row(row), uow)
# #         # 2. LTD update
# #         messagebus.handle(UpdateLTDCmd.from_row(row), uow)
# #         # 3. ODKRYJ/CREATE rep (jeśli nowy)
# #         messagebus.handle(DiscoverRepCmd.from_row(row), uow)
# #         # 4. ASSIGN rep (teraz reference istnieje!)
# #         messagebus.handle(AssignRepCmd.from_row(row), uow)
# #
# #     # 2. Warnings (stare spółki bez ZK dziś)
# #     for nip in warning_5m_candidates(uow):
# #         messagebus.handle(WarnRep5mCmd(nip), uow)
# #
# #     # 3. Stale (>30 dni bez ZK)
# #     for nip in stale_candidates(uow):
# #         messagebus.handle(ReleaseStaleCmd(nip), uow)
# #
# # # Aim at pure Events flow, no conditional logic, Events for logic like DiscoverCompany or DiscoverRep? They trigger creation if needed through domain and another CMD
# # # company.create_new() -> CMD CreateCompany
# # def daily_maintenance(uow: unit_of_work.AbstractUnitOfWork):
# # """
# # W ksiazce mowia ze jest lepszy sposob komunikacji eventow niz messagebus zwracajacy results ->
# # poczytaj dalej, popraw to i naucz sie cmd.
# # Cmd -> Nie powinno zwracac result -> 12. rozdział wyjaśni, podział odpowiedzialności i CQRS
# # """
# #     # 1. WSZYSTKO z ZK 24h (new + changed rep + LTD)
# #     subiekt_conn = subiekt_gateway.get_subiekt_connection()
# #     for row in zk_24h_raw(subiekt_conn):
# #         # 1. Company (potrzebny do LTD + assign)
# #         company = messagebus.handle(GetCompanyCmd.from_row(row), uow)
# #         if not company:
# #             messagebus.handle(CreateCompanyCmd.from_row(row), uow)
# #         # 2. LTD update
# #         messagebus.handle(UpdateLTDCmd.from_row(row), uow)
# #         # 3. ODKRYJ/CREATE rep (jeśli nowy)
# #         rep = messagebus.handle(GetRepCmd.from_row(row), uow)
# #         if not rep:
# #             messagebus.handle(CreateRepCmd(row), uow)
# #         # 4. ASSIGN rep (teraz reference istnieje!)
# #         messagebus.handle(AssignRepCmd.from_row(row), uow)
# #
# # """
# # Another idea? Use a 'rozrusznik' domain service, which will coordinate ZK row actions and fire another handlers by
# # adding Messages to self.events?
# # """
# #
# #
# #
# #
# #
# #
#
# # ZKMapper bez handlerow:
# class ZKMapper:
#     def __init__(self, rep_ Dict[str, Tuple[str, str]]
#
#     ):  # NO uow!
#     self.rep_data = rep_data  # Tylko lookup + create logic
#
#
# def get_reference(self, rep_name: str) -> str:
#     """Pobierz reference (fallback create)"""
#     rep_info = self.rep_data.get(str(rep_name))
#     if rep_info:
#         return rep_info[0]  # Istniejący
#
#     # Nowy → zapisz do REPS_DATA (bez DB!)
#     ref = self.name_to_reference(rep_name)
#     email = self.name_to_email(rep_name)
#     self.rep_data[rep_name] = (ref, email)
#     return ref  # Handler później zrobi SalesRep!
#
# # remove_diacritics, name_to_reference, name_to_email - bez zmian
#
# # DIscoverRepCmd:
# def discover_rep(cmd: DiscoverRepCmd, uow):
#     """1. Lookup/create reference w REPS_DATA"""
#     mapper = ZKMapper(REPS_DATA)  # Globalny!
#     ref = mapper.get_reference(cmd.rep_name)  # Mutuje REPS_DATA!
#
#     """2. Sprawdź czy SalesRep istnieje → create jeśli nie"""
#     rep = uow.reps.get(ref)
#     if not rep:
#         rep = model.SalesRep(reference=ref, name=cmd.rep_name, email=mapper.rep_data[cmd.rep_name][1])
#         uow.reps.add(rep)
#
#     with uow:
#         uow.commit()
#
# # AssignRepCmd:
# def assign_rep(cmd: AssignRepCmd, uow):
#     with uow:
#         company = uow.companies.get_by_nip(cmd.nip)
#         mapper = ZKMapper(REPS_DATA)  # Reference już istnieje!
#         ref = mapper.get_reference(cmd.rep_name)  # Tylko lookup!
#         rep = uow.reps.get(ref)  # Gwarantowany!
#
#         if company.current_rep != rep:
#             if company.current_rep:
#                 company.release_from_rep()
#             company.assign_to_rep(rep)
#         uow.commit()
#
# # handlers/get_company.py
# def get_company(cmd: GetCompanyCmd, uow):
#     company = uow.companies.get(cmd.nip, cmd.address)
#     return company  # None lub Company!
#
# # handlers/create_company.py
# def create_company(cmd: CreateCompanyCmd, uow):
#     company = model.Company(...)
#     uow.companies.add(company)
#     return company  # Zawsze sukces!
#
# # handlers/get_rep.py
# def get_rep(cmd: GetRepCmd, uow):
#     mapper = ZKMapper(REPS_DATA)
#     if cmd.rep_name in mapper.rep_
#         ref = mapper.rep_data[cmd.rep_name][0]
#         rep = uow.reps.get(ref)
#         return ref if rep else None
#     return None  # Nie istnieje w REPS_DATA lub DB
#
# # handlers/create_rep.py
# def create_rep(cmd: CreateRepCmd, uow):
#     mapper = ZKMapper(REPS_DATA)
#     ref = mapper.get_reference(cmd.rep_name)  # Mutuje REPS_DATA!
#     rep = model.SalesRep(reference=ref, name=cmd.rep_name, email=mapper.rep_data[cmd.rep_name][1])
#     uow.reps.add(rep)
#     return ref  # Nowy reference!
