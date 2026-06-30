#
# """
# Events = messagebus version:
# """
# def process_zk_24h_row(cmd: ProcessZk24hRowCmd, uow):
#     # 1. Szukaj po adresie (unikalny key)
#     company = uow.companies.get_by_address(cmd.nip, cmd.street, cmd.building_nr, cmd.postal_code, cmd.city)
#
#     # 2. NEW? → create
#     if not company:
#         create_event = events.CompanyCreated(
#             nip=cmd.nip, name=cmd.name, street=cmd.street,
#             building_nr=cmd.building_nr, postal_code=cmd.postal_code,
#             city=cmd.city, ltd=cmd.last_zk_date
#         )
#         messagebus.handle(create_event, uow)
#         is_new = True
#     else:
#         is_new = False
#
#     # 3. LTD update?
#     if cmd.last_zk_date > company.ltd:
#         company.ltd = cmd.last_zk_date
#
#     # 4. Rep logic
#     mapper = ZKMapper(uow, REPS_DATA)
#     rep = mapper.get_or_create(cmd.rep_group_name)
#     if is_new or company.current_rep != rep:
#         rep_event = events.AssignmentRequired(
#             nip=cmd.nip, street=cmd.street, building_nr=cmd.building_nr,
#             postal_code=cmd.postal_code, city=cmd.city, rep_ref=rep.reference
#         )
#         messagebus.handle(rep_event, uow)
#     uow.commit()
#
# """
# Pure domain inside handler version:
# """
#
#
# def process_zk_24h_row(cmd: ProcessZk24hRowCmd, uow: unit_of_work.AbstractUnitOfWork):
#     # 1. Szukaj po nip i adresie (unikalny key)
#     with uow:
#         address, nip = model.Address(
#             street=cmd.street,
#             building_nr=cmd.building_nr,
#             postal_code=cmd.postal_code,
#             city=cmd.city
#         ), model.NIP(cmd.nip)
#
#         company = uow.companies.get(nip, address)
#
#         # 2. NEW? → create
#         if not company:
#
#             company = model.Company(nip=nip, name=cmd.name,
#                                     address=address)  # InvalidNip -> catch this error later (endpoint or cron)
#             uow.companies.add(company)
#
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
#         if is_new or company.current_rep != rep:
#             company.assign_to_rep(rep)
#
#         uow.commit()
# """
# PROCESS + ORCHESTRATORS (PURE CMD + HANDLERS, EASY TESTING)
# """
#
# # service_layer/orchestrators/zk_orchestrator.py
# def process_zk_row(cmd: ProcessZk24hRowCmd, uow):
#     """ZK Document → 4 atomic domain actions"""
#     with uow:
#         # 1. Company
#         company = orchestrator_company(cmd, uow)
#
#         # 2. LTD
#         orchestrator_ltd(cmd, company, uow)
#
#         # 3. Rep
#         orchestrator_rep(cmd, company, uow)
#
#         uow.commit()
#
#
# def orchestrator_company(cmd, uow):
#     """Get or create company"""
#     company = uow.companies.get(cmd.nip, cmd.address)
#     if not company:
#         # Event → handler
#         messagebus.handle(events.CompanyCreated(cmd), uow)
#         company = uow.companies.get(cmd.nip, cmd.address)
#     return company
#
#
# def orchestrator_ltd(cmd, company, uow):
#     """Update LTD if newer"""
#     if cmd.last_zk_date > company.ltd:
#         cmd_update = commands.UpdateCompanyLTD(cmd.nip, cmd.last_zk_date)
#         messagebus.handle(cmd_update, uow)
#
#
# def orchestrator_rep(cmd, company, uow):
#     """Rep change detection + actions"""
#     rep = ZKMapper(uow, REPS_DATA).get_or_create(cmd.rep_group_name)
#     if company.current_rep != rep:
#         if company.current_rep:
#             messagebus.handle(commands.ReleaseCompany(cmd.nip), uow)
#         messagebus.handle(commands.AssignCompany(cmd.nip, rep.reference), uow)
#
# """
# 4 handlers instead of one big process, no nested uow and handlers
# 1. messagebus.handle(CreateCompanyCmd.from_row(row), uow)
# 2. messagebus.handle(UpdateLTDCmd.from_row(row), uow)
# 3. messagebus.handle(AssignRepCmd.from_row(row), uow)
# 4. messagebus.handle(DiscoverRepCmd.from_row(row), uow)
# """
# # 1. handlers/create_company.py
# def create_company(cmd: CreateCompanyCmd, uow):
#     with uow:
#         company = model.Company(nip=cmd.nip, name=cmd.name, address=cmd.address)
#         uow.companies.add(company)
#         uow.commit()
#
# # 2. handlers/update_ltd.py
# def update_ltd(cmd: UpdateLTDCmd, uow):
#     with uow:
#         company = uow.companies.get(cmd.nip, cmd.address)
#         if cmd.last_zk_date > company.ltd:
#             company.update_ltd(cmd.last_zk_date)
#         uow.commit()
#
# # 3. handlers/assign_rep.py
# def assign_rep(cmd: AssignRepCmd, uow):
#     with uow:
#         company = uow.companies.get_by_nip(cmd.nip)
#         rep = uow.reps.get(cmd.rep_reference)
#         if company.current_rep:
#             company.release_from_rep()
#         company.assign_to_rep(rep)
#         uow.commit()
#
# # 4. handlers/discover_rep.py
# def discover_rep(cmd: DiscoverRepCmd, uow):
#     with uow:
#         mapper = ZKMapper(uow, REPS_DATA)
#         mapper.get_or_create(cmd.rep_name)  # Mutuje REPS_DATA + tworzy SalesRep
#         uow.commit()
#
# # 5-6. warn_rep_5m + release_stale (masz już)
# # WTEDY:
# def daily_maintenance(uow):
#     """Thin coordinator → PLASKIE handlery"""
#     with uow:
#         # 1-4. ZK24h → 4 OSOBNE handlery (dla każdego row!)
#         subiekt_conn = subiekt_gateway.get_subiekt_connection()
#         for row in zk_24h_raw(subiekt_conn):
#             messagebus.handle(CreateCompanyCmd.from_row(row), uow)
#             messagebus.handle(UpdateLTDCmd.from_row(row), uow)
#             messagebus.handle(DiscoverRepCmd.from_row(row), uow)
#             messagebus.handle(AssignRepCmd.from_row(row), uow)
#
#         # 5-6. Warnings + Stale
#         for nip in warning_5m_candidates(uow):
#             messagebus.handle(WarnRep5mCmd(nip), uow)
#         for nip in stale_candidates(uow):
#             messagebus.handle(ReleaseStaleCmd(nip), uow)
#
#         uow.commit()


















# # Atomic handlers:
# def handle_company_created(event: events.CompanyCreated, uow):
#     """10 linii max!"""
#     company = model.Company(...)
#     uow.companies.add(company)
#
# def handle_update_company_ltd(cmd: commands.UpdateCompanyLTD, uow):
#     """Pure domain!"""
#     company = uow.companies.get(cmd.nip)
#     company.ltd = cmd.date
#
# def handle_release_company(cmd: commands.ReleaseCompany, uow):
#     """Domain method!"""
#     company = uow.companies.get(cmd.nip)
#     company.release_from_rep()
#
# # TESTY:
# # 1. Atomic handlers (mock uow)
# def test_handle_company_created():
#     handle_company_created(event, mock_uow)
#     assert mock_uow.companies.add.called
#
# # 2. Orchestrators (mock handlers)
# def test_orchestrator_company_new():
#     mock_handle = MockHandler()
#     orchestrator_company(cmd, uow)
#     assert mock_handle.company_created.called
#
# # 3. Full orchestrator (mock sub-orchestrators)
# def test_process_zk_document():
#     mock_orch = MockOrchestrator()
#     process_zk_document(cmd, uow)
#     assert mock_orch.company.called
#     assert mock_orch.ltd.called
#     assert mock_orch.rep.called
#
# # 4. Integration (real uow)
# def test_end_to_end():
#     process_zk_document(cmd, real_uow)