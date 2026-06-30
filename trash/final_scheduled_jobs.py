# from typing import List
# from domain import model as model
#
# # WSZEDZIE WOITH UOW
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
#
# def stale_companies(uow) -> List[str]:  # Tylko NIPy!
#     return list(uow.session.execute("""
#         SELECT nip FROM companies
#         WHERE last_transaction_date < date('now', '-6 months')
#         OR last_transaction_date IS NULL
#     """))
# def release_stale_companies(uow):
#
#     # Scheduled Job
#
#     for nip in stale_companies(uow):  # 100 nips, nie 10k!
#         company = uow.companies.get(nip)  # Ładuj po 1
#         if company:  # release_from_rep
#             company.release_from_rep()
#             uow.commit()  # Event + save
#
# def sql_query_5_months_candidates(uow) -> List[str]:
#     return [row[0] for row in uow.session.execute("""
#         SELECT nip FROM companies
#         WHERE last_transaction_date <= DATEADD(day, -140, GETDATE())
#         AND warned_5m = 0
#     """).fetchall()]
# def warn_reps_5_months(uow):
#     """
#     Scheduled Job everynight: SQL queries candidates from within around 5 months (now - ltd)
#     and then checks in domain if they need a warning
#     """
#     for nip_str in sql_query_5_months_candidates(uow):
#         company = uow.companies.get(model.NIP(nip_str))  # → repo.seen.add()
#         company.needs_precise_5month_warning()     # → self.events.append()
#     uow.commit()  # → publish_events() dla WSZYSTKICH seen!
#
# def detect_new_companies(uow):
#     """Scheduled Job searchiung through SFaktury for new NIPs"""
#     pass
# def create_new_companies_if_detected(uow):
#     """Scheduled Job creating new companies if sich were detected from Subiekt SFaktury"""
#     pass
#
# """
# 1. CODZIENNIE W NOCY APLIKACJA MUSI SYNCHRONIZOWAC SIE Z BAZA SUBIEKTA (FAKTURY Z 24H) : AKTUALIZUJE .LTD KAZDEJ COMPANY,
# KTORA TAM SIE ZNAJDZIE, CELEM ZŁAPANIA OSTATNIEJ DATY TRANSACKJI
# 2. SCHEDULED JOB (SQL READ ZBIERAJACY NIPy) KTORY ZBIERA WSZYSTKIE COMPANIES Z LTD STARSZYM NIZ 6 MSC I RELEASUJE REPA!
#
# 3.OSTRZEZENIE DO REPA JESLI MINELO 5 MIESIECY OD LTD: SQL QUERY Z PARAMETREM OKOLO 5 MSC,
# NASTEPNIE FUNKCJA DOMENY SPRAWDZA, CZY OSTRZEZENIE SIE NALEZY
#
# 4? DO USTALENIA Z ZARZADEM, CZY NOWE COMPANIES POWSTAJA PO DETEKCJI NOWYCH NIPow Z OSTATNICH
# SFAKTUR Z SUBIEKTA
# """


# EVENT W 5 MIESIACU: PRZYPOMNIENIE DO REPA ZE ZBLIZA SIE DEADLINE NA RELEASE???? MOZLIWE?