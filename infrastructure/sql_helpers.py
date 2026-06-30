from sqlalchemy import text
from domain import model
from . import cqrs

# TODO : Najlepsza zmiana to przenieść odpowiedzialność za źródło danych do funkcji typu  zk_24h_raw(...) , ale zrobić z niej wersję „CSV source”, np.  zk_24h_raw_from_csv(path) -> listmodel.ZKRow . Wtedy orchestrator zostaje prawie identyczny, a zmieniasz tylko to, skąd biorą się wiersze.
def zk_24h_raw(subiekt_conn) -> list[model.ZKRow]:
    rows = subiekt_conn.execute(cqrs.QUERY_ZK_24H).fetchall()
    return [
        model.ZKRow(
            nip=row.nip,
            name=row.name,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
            rep_group_name=row.rep_group_name,
            zk_date=row.zk_date,
        )
        for row in rows
    ]

# def zk_24h_raw_from_csv(csv_path: str | Path) -> list[model.ZKRow]:
#     csv_path = Path(csv_path)
#
#     with csv_path.open("r", encoding="utf-8", newline="") as f:
#         reader = csv.DictReader(f)
#         rows = []
#         for row in reader:
#             rows.append(
#                 model.ZKRow(
#                     nip=row["nip"],
#                     name=row["name"],
#                     street=row["street"],
#                     building_nr=row["building_nr"],
#                     postal_code=row["postal_code"],
#                     city=row["city"],
#                     rep_group_name=row["rep_group_name"],
#                     zk_date=row["zk_date"],
#                 )
#             )
#     return rows

def recent_zk_companies(session) -> list[model.CompanyCandidate]:
    rows = session.execute(text(cqrs.QUERY_RECENT_ZK_COMPANIES)).fetchall()
    return [
        model.CompanyCandidate(
            nip=row.nip,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
        )
        for row in rows
    ]

def warning_5m_candidates(session) -> list[model.CompanyCandidate]:
    rows = session.execute(text(cqrs.QUERY_WARNING_5M)).fetchall()
    return [
        model.CompanyCandidate(
            nip=row.nip,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
        )
        for row in rows
    ]

def stale_candidates(session) -> list[model.CompanyCandidate]:
    rows = session.execute(text(cqrs.QUERY_STALE)).fetchall()
    return [
        model.CompanyCandidate(
            nip=row.nip,
            street=row.street,
            building_nr=row.building_nr,
            postal_code=row.postal_code,
            city=row.city,
        )
        for row in rows
    ]
