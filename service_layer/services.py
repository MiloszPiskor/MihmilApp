# # Application Service - stateless, UoW-injected
# class AssignCompanyService:
#     def execute(self, uow: 'UnitOfWork', rep_id: UUID, nip_value: str) -> CompanyAssigned:
#         nip = NIP(nip_value)
#
#         with uow:  # Transaction boundary
#             # UoW provides repositories (no service_layer deps)
#             rep = uow.rep_repo.get_by_id(rep_id)
#             company = uow.company_repo.find_by_nip(nip)
#
#             if not rep or not company:
#                 raise ValueError("Entity not found")
#
#             # Fast read model query (UoW provides or separate read DB connection)
#             current_assignment = uow.read_model.get_assignment_for_company(nip.value)
#             current_rep_id = current_assignment.rep_id if current_assignment else None
#
#             # Pure domain validation
#             if not AssignmentRules.is_assignment_valid(
#                     rep._assigned_company_nips, current_rep_id, rep.id
#             ):
#                 raise ValueError(f"Company {nip.value} assigned to another rep")
#
#             # Domain behavior
#             event = rep.request_company_assignment(nip)
#
#             # UoW tracks changes automatically
#             uow.commit()  # Saves all dirty aggregates with versioning
#
#         # Event publishing happens outside transaction (async)
#         return event
