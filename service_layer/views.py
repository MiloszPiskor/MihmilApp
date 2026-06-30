from . import unit_of_work
from sqlalchemy import text
from domain import model

def rep_dashboard(rep_reference: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = list(uow.session.execute(
            text("""
            SELECT DISTINCT
                c.nip AS nip,
                c.name AS company_name,
                c.street AS street,
                c.building_nr AS building_nr,
                c.postal_code AS postal_code,
                c.city AS city,
                c.ltd AS last_transaction_date,
                CASE
                    WHEN c.ltd IS NULL THEN 'UNKNOWN'
                    WHEN c.ltd <= CURRENT_DATE - INTERVAL '6 months' THEN 'STALE'
                    WHEN c.ltd <= CURRENT_DATE - INTERVAL '5 months' THEN 'WARNING'
                    ELSE 'ACTIVE'
                END AS status
            FROM companies c
            JOIN company_assignments ca ON ca.company_id = c.id
            JOIN sales_reps sr ON sr.id = ca.rep_id
            WHERE sr.reference = :rep_reference
            ORDER BY c.name
            """),
            {"rep_reference": rep_reference},
        ).mappings().all())
    return [dict(row) for row in results]

def manager_search_reps(query: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = list(uow.session.execute(
            text("""
            SELECT DISTINCT
                sr.reference AS rep_reference,
                sr.name AS rep_name
            FROM sales_reps sr
            JOIN company_assignments ca ON ca.rep_id = sr.id
            JOIN companies c ON c.id = ca.company_id
            WHERE sr.name ILIKE :pattern
                OR sr.reference ILIKE :pattern
            ORDER BY sr.name
            """),
            {"pattern": f"%{query}%"},
        ).mappings().all())
    return [dict(row) for row in results]

def manager_dashboard(rep_reference: str, uow: unit_of_work.SqlAlchemyUnitOfWork):
    with uow:
        results = list(uow.session.execute(
            text("""
            SELECT DISTINCT
                sr.name AS rep_name,
                c.name AS company_name,
                c.nip AS nip,
                c.street AS street,
                c.building_nr AS building_nr,
                c.postal_code AS postal_code,
                c.city AS city,
                c.ltd AS last_transaction_date,
                CASE
                    WHEN c.ltd IS NULL THEN 'UNKNOWN'
                    WHEN c.ltd <= CURRENT_DATE - INTERVAL '6 months' THEN 'STALE'
                    WHEN c.ltd <= CURRENT_DATE - INTERVAL '5 months' THEN 'WARNING'
                    ELSE 'ACTIVE'
                END AS status
            FROM companies c
            JOIN company_assignments ca ON ca.company_id = c.id
            JOIN sales_reps sr ON sr.id = ca.rep_id
            WHERE sr.reference = :rep_reference
            ORDER BY c.name
            """),
            {"rep_reference": rep_reference},
        ).mappings().all())
    return [dict(row) for row in results]

def lookup_company_by_nip_and_address(
    nip: str,
    address: model.Address,
    uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        results = list(uow.session.execute(
            text("""
                SELECT
                    c.nip AS nip,
                    c.name AS company_name,
                    c.street AS street,
                    c.building_nr AS building_nr,
                    c.postal_code AS postal_code,
                    c.city AS city,
                    sr.reference AS assigned_rep_reference,
                    sr.name AS assigned_rep_name
                FROM companies c
                LEFT JOIN company_assignments ca ON ca.company_id = c.id
                LEFT JOIN sales_reps sr ON sr.id = ca.rep_id
                WHERE c.nip = :nip
                  AND c.street = :street
                  AND c.building_nr = :building_nr
                  AND c.postal_code = :postal_code
                  AND c.city = :city
                LIMIT 1
            """),
            {
                "nip": nip,
                "street": address.street,
                "building_nr": address.building_nr,
                "postal_code": address.postal_code,
                "city": address.city,
            },
        ).mappings().all())

        if results:
            row = dict(results[0])
            if row["assigned_rep_reference"] is not None:
                row["status"] = "OCCUPIED"
                row["message"] = "This company is already assigned to another rep."
            # else:
            #     row["status"] = "AVAILABLE"
            #     row["message"] = "This company is available."
                return [row]

        occupied_rows = list(uow.session.execute(
            text("""
                       SELECT
                           c.nip AS nip,
                           c.name AS company_name,
                           c.street AS street,
                           c.building_nr AS building_nr,
                           c.postal_code AS postal_code,
                           c.city AS city
                       FROM companies c
                       JOIN company_assignments ca ON ca.company_id = c.id
                       JOIN sales_reps sr ON sr.id = ca.rep_id
                       WHERE c.nip = :nip
                       ORDER BY c.street, c.building_nr, c.city
                   """),
            {"nip": nip},
        ).mappings().all())

        if occupied_rows:
            return [{
                "nip": nip,
                "status": "OCCUPIED_OTHER_ADDRESS",
                "message": (
                    "This NIP exists in the system and is assigned to another rep, "
                    "but this exact address was not found."
                ),
                "occupied_addresses": [dict(row) for row in occupied_rows],
            }]

        return [{
            "nip": nip,
            "status": "AVAILABLE",
            "message": "No matching company found in the system.",
        }]

def manager_lookup_company_by_nip_and_address(
    nip: str,
    address,
    uow: unit_of_work.SqlAlchemyUnitOfWork,
):
    with uow:
        exact = list(uow.session.execute(
            text("""
                SELECT
                    c.nip AS nip,
                    c.name AS company_name,
                    c.street AS street,
                    c.building_nr AS building_nr,
                    c.postal_code AS postal_code,
                    c.city AS city,
                    c.ltd AS last_transaction_date,
                    sr.reference AS assigned_rep_reference,
                    sr.name AS assigned_rep_name,
                    CASE
                        WHEN ca.rep_id IS NULL THEN 'UNASSIGNED'
                        WHEN c.ltd IS NULL THEN 'UNKNOWN'
                        WHEN c.ltd <= CURRENT_DATE - INTERVAL '6 months' THEN 'STALE'
                        WHEN c.ltd <= CURRENT_DATE - INTERVAL '5 months' THEN 'WARNING'
                        ELSE 'ACTIVE'
                    END AS status
                FROM companies c
                LEFT JOIN company_assignments ca ON ca.company_id = c.id
                LEFT JOIN sales_reps sr ON sr.id = ca.rep_id
                WHERE c.nip = :nip
                  AND c.street = :street
                  AND c.building_nr = :building_nr
                  AND c.postal_code = :postal_code
                  AND c.city = :city
                LIMIT 1
            """),
            {
                "nip": nip,
                "street": address.street,
                "building_nr": address.building_nr,
                "postal_code": address.postal_code,
                "city": address.city,
            },
        ).mappings().all())

        other_addresses = list(uow.session.execute(
            text("""
                SELECT
                    c.nip AS nip,
                    c.name AS company_name,
                    c.street AS street,
                    c.building_nr AS building_nr,
                    c.postal_code AS postal_code,
                    c.city AS city,
                    c.ltd AS last_transaction_date,
                    sr.reference AS assigned_rep_reference,
                    sr.name AS assigned_rep_name,
                    CASE
                        WHEN ca.rep_id IS NULL THEN 'UNASSIGNED'
                        WHEN c.ltd IS NULL THEN 'UNKNOWN'
                        WHEN c.ltd <= CURRENT_DATE - INTERVAL '6 months' THEN 'STALE'
                        WHEN c.ltd <= CURRENT_DATE - INTERVAL '5 months' THEN 'WARNING'
                        ELSE 'ACTIVE'
                    END AS status
                FROM companies c
                LEFT JOIN company_assignments ca ON ca.company_id = c.id
                LEFT JOIN sales_reps sr ON sr.id = ca.rep_id
                WHERE c.nip = :nip
                  AND NOT (
                    c.street = :street
                    AND c.building_nr = :building_nr
                    AND c.postal_code = :postal_code
                    AND c.city = :city
                  )
                ORDER BY c.street, c.building_nr, c.city
            """),
            {
                "nip": nip,
                "street": address.street,
                "building_nr": address.building_nr,
                "postal_code": address.postal_code,
                "city": address.city,
            },
        ).mappings().all())

        if not exact:
            if other_addresses:
                return [{
                    "status": "NOT_FOUND",
                    "message": "No exact company found for this NIP and address.",
                    "other_addresses": [dict(r) for r in other_addresses],
                }]
            return [{
                "status": "NOT_FOUND",
                "message": "No matching company found.",
                "other_addresses": [],
            }]

        row = dict(exact[0])
        response = {
            "status": row["status"],
            "message": "Company found.",
            "company": {
                "nip": row["nip"],
                "company_name": row["company_name"],
                "street": row["street"],
                "building_nr": row["building_nr"],
                "postal_code": row["postal_code"],
                "city": row["city"],
                "last_transaction_date": row["last_transaction_date"],
                "assigned_rep_reference": row["assigned_rep_reference"],
                "assigned_rep_name": row["assigned_rep_name"],
            },
            "other_addresses": [dict(r) for r in other_addresses],
        }
        return [response]



