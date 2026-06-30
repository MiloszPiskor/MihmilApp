# # infrastructure: Read Model query (SQL) OUR APP OWN DATABASE
# def stale_companies() -> List[str]:  # Tylko NIPy!
#     return db.execute("""
#         SELECT nip FROM companies
#         WHERE last_transaction_date < date('now', '-6 months')
#         OR last_transaction_date IS NULL
#     """).fetchall()
#
# # Scheduled Job
#
# for nip in stale_companies():  # 100 nips, nie 10k!
#     company = uow.companies.get(nip)  # Ładuj po 1
#     if company.release_due_to_inactivity(): #release_from_rep
#         uow.commit()  # Event + save

