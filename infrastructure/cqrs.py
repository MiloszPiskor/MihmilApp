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
#     -- BRAK FILTRA CZASU — wszystkie ZK z snapshotu
QUERY_ZK_ALL = """
SELECT TOP 50
    ah.adrh_NIP as nip, k.kh_Symbol as name,
    ah.adrh_Ulica as street, ah.adrh_NrDomu as building_nr,
    ah.adrh_Kod as postal_code, ah.adrh_Miejscowosc as city,
    g.grk_Nazwa as rep_group_name,
    MAX(d.dok_DataWyst) as zk_date
FROM dok__Dokument d 
JOIN kh__Kontrahent k ON k.kh_Id = d.dok_OdbiorcaId
JOIN adr_Historia ah ON ah.adrh_Id = d.dok_OdbiorcaAdreshId
LEFT JOIN sl_GrupaKh g ON g.grk_Id = k.kh_IdGrupa
WHERE d.dok_Typ = 16 AND k.kh_Rodzaj = 2 
GROUP BY ah.adrh_NIP, k.kh_Symbol, ah.adrh_Ulica, ah.adrh_NrDomu,
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
WHERE c.last_zk_transaction_date >= CURRENT_DATE - INTERVAL '1 day'
"""
# Dla testu — wszystkie companies z last_zk_transaction_date (bez filtra czasu)
QUERY_ALL_ZK_COMPANIES = """
SELECT DISTINCT
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_transaction_date IS NOT NULL
"""
QUERY_WARNING_5M = """
SELECT DISTINCT
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_transaction_date <= CURRENT_DATE - INTERVAL '5 months'
  AND c.last_zk_transaction_date >= CURRENT_DATE - INTERVAL '6 months'
  AND EXISTS (
      SELECT 1
      FROM company_assignments ca
      WHERE ca.company_id = c.id
  )
"""
QUERY_STALE = """
SELECT DISTINCT  
    c.nip as nip,
    c.street as street,
    c.building_nr as building_nr,
    c.postal_code as postal_code,
    c.city as city
FROM companies c
WHERE c.last_zk_transaction_date < CURRENT_DATE - INTERVAL '6 months'
  AND EXISTS (
      SELECT 1
      FROM company_assignments ca
      WHERE ca.company_id = c.id
  )
"""