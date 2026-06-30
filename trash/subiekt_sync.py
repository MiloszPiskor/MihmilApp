# # def sync_transactions_from_subiekt():
# #     invoices = subiekt_gt_api.get_invoices_last_7_days()
# #     for invoice in invoices:
# #         company = uow.companies.get(invoice.nip)
# #         if company:
# #             company.update_last_transaction(invoice.date)  # Domenowa metoda!
# #             uow.commit()
# #
#
# def sync_last_transaction_from_subiekt(uow):  # Codziennie nocą
#     conn = get_subiekt_connection()
#     cursor = conn.cursor()
#
#     # Ostatnie 7 dni faktur (wydajne!) PRZECIEZ MUSI BYC OSTATNIE 24H, filtruj po aktywnych !!!!!!!!
#     cursor.execute("""
#         SELECT TOP 10000 Kontrahent.NIP, MAX(SFaktury.DataWystawienia) as last_date
#         FROM SFaktury
#         JOIN Kontrahenci ON SFaktury.KontrahentId = Kontrahenci.Id
#         WHERE SFaktury.DataWystawienia >= DATEADD(day, -7, GETDATE())
#         GROUP BY Kontrahent.NIP
#     """)
#
#     for nip, last_date in cursor.fetchall():
#         company = uow.companies.get(NIP(nip))
#         if company:
#             company.update_last_transaction(last_date.date())  # Domenowa metoda
#             uow.commit()  # Zapis + events jeśli zmieniono


"""
1. CODZIENNIE W NOCY APLIKACJA MUSI SYNCHRONIZOWAC SIE Z BAZA SUBIEKTA (FAKTURY Z 24H) : AKTUALIZUJE .LTD KAZDEJ COMPANY, 
KTORA TAM SIE ZNAJDZIE, CELEM ZŁAPANIA OSTATNIEJ DATY TRANSACKJI
2. SCHEDULED JOB (SQL READ ZBIERAJACY NIPy) KTORY ZBIERA WSZYSTKIE COMPANIES Z LTD STARSZYM NIZ 6 MSC I RELEASUJE REPA!
"""


# EVENT W 5 MIESIACU: PRZYPOMNIENIE DO REPA ZE ZBLIZA SIE DEADLINE NA RELEASE???? MOZLIWE?