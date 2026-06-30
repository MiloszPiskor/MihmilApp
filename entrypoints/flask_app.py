from datetime import date
from flask import request, jsonify, Flask
from adapters.orm import start_mappers
from service_layer import unit_of_work, views, messagebus
from logging_config import get_logger
from domain import commands, model
from flask_cors import CORS

# Initialize Flask
app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
)
# Initialize logger
logger = get_logger(__name__)

start_mappers()

def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)

def serialize_date(value):
    return value.isoformat() if value is not None else None

# @app.route("/assign", methods=["POST"])
# def assign_endpoint():
#
#     data = request.get_json()
#
#     nip_value, rep_ref = data["nip_value"], data["rep_ref"]
#     uow = unit_of_work.SqlAlchemyUnitOfWork()
#
#     try:
#         repref = services.assign_company(uow, nip_value, rep_ref)
#
#     except model.CompanyAlreadyAssigned as e:
#         return jsonify({"error": str(e)}), 400
#
#     return jsonify(repref = repref), 201 # [] -> ?

@app.route("/api/reps/<rep_reference>/dashboard", methods=["GET"])
def rep_dashboard(rep_reference):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    rows = views.rep_dashboard(rep_reference, uow)
    for row in rows:
        if row.get("last_transaction_date") is not None:
            row["last_transaction_date"] = serialize_date(row["last_transaction_date"])

    return jsonify(rows), 200

@app.route("/api/managers/reps/search", methods=["GET"])
def search_reps():
    query = request.args.get("query", "", type=str).strip()
    if not query:
        return jsonify([]), 200

    uow = unit_of_work.SqlAlchemyUnitOfWork()
    rows = views.manager_search_reps(query, uow)
    return jsonify(rows), 200

@app.route("/api/managers/reps/<rep_reference>/dashboard", methods=["GET"])
def manager_rep_dashboard(rep_reference):
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    rows = views.manager_dashboard(rep_reference, uow)
    for row in rows:
        if row.get("last_transaction_date") is not None:
            row["last_transaction_date"] = serialize_date(row["last_transaction_date"])

    return jsonify(rows), 200

@app.route("/api/office/fix-zk-row", methods=["POST"])
def fix_zk_row():
    """
        Manually repair a ZK row and synchronize company state.

        Expected JSON payload:
        {
          "rep_name": "str",
          "nip": "str",
          "name": "str",
          "street": "str",
          "building_nr": "str",
          "postal_code": "str",
          "city": "str",
          "zk_date": "YYYY-MM-DD"
        }

        Frontend instructions:
        - Send POST with Content-Type: application/json.
        - Send all fields as strings.
        - zk_date must be an ISO date string in the form YYYY-MM-DD.
        - If the backend returns 400, show the error message to the user.

        Office instructions:
        - Fill in the exact rep name from Subiekt/ZK group.
        - Fill in the company identity and address exactly as it appears in the source.
        - Enter zk_date as a calendar date in YYYY-MM-DD format.
        - Use this endpoint only for manual correction of rows that failed the daily ingestion.

        Types:
        - rep_name: str
        - nip: str
        - name: str
        - street: str
        - building_nr: str
        - postal_code: str
        - city: str
        - zk_date: str in request, parsed to datetime.date in backend
    """

    data = request.get_json()

    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    required = [
        "rep_name",
        "nip",
        "name",
        "street",
        "building_nr",
        "postal_code",
        "city",
        "zk_date",
    ]
    missing = [key for key in required if key not in data or data[key] in (None, "")]
    if missing:
        return jsonify({"error": "missing fields", "missing": missing}), 400

    try:
        zk_date = _parse_iso_date(data["zk_date"])
    except ValueError:
        return jsonify({"error": "zk_date must be in YYYY-MM-DD format"}), 400
    try:
        messagebus.handle(
            message=commands.EnsureRepExists(rep_name=data["rep_name"]),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )

        messagebus.handle(
            message=commands.EnsureCompanyExists(
                nip=data["nip"],
                name=data["name"],
                street=data["street"],
                building_nr=data["building_nr"],
                postal_code=data["postal_code"],
                city=data["city"],
            ),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )

        messagebus.handle(
            message=commands.UpdateLastZK(
                nip=data["nip"],
                name=data["name"],
                street=data["street"],
                building_nr=data["building_nr"],
                postal_code=data["postal_code"],
                city=data["city"],
                zk_date=zk_date,
                rep_name=data["rep_name"],
            ),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )

        messagebus.handle(
            message=commands.SynchronizeRep(
                nip=data["nip"],
                street=data["street"],
                building_nr=data["building_nr"],
                postal_code=data["postal_code"],
                city=data["city"],
            ),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )

        messagebus.handle(
            message=commands.SynchronizeLTD(
                nip=data["nip"],
                street=data["street"],
                building_nr=data["building_nr"],
                postal_code=data["postal_code"],
                city=data["city"],
            ),
            uow=unit_of_work.SqlAlchemyUnitOfWork(),
        )

        return "", 204

    except Exception as e:
        logger.exception("fix_zk_row failed")
        return jsonify({"error": repr(e)}), 400

@app.route("/api/reps/company-lookup", methods=["POST"])
def company_lookup():

    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    required = ["nip", "street", "building_nr", "postal_code", "city"]
    missing = [key for key in required if key not in data or data[key] in (None, "")]
    if missing:
        return jsonify({"error": "missing fields", "missing": missing}), 400

    address = model.Address(
        data["street"],
        data["building_nr"],
        data["postal_code"],
        data["city"],
    )

    uow = unit_of_work.SqlAlchemyUnitOfWork()
    rows = views.lookup_company_by_nip_and_address(data["nip"], address, uow)
    return jsonify(rows), 200

@app.route("/api/managers/company-lookup", methods=["POST"])
def manager_company_lookup():
    data = request.get_json(silent=True)

    if data is None:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    required = ["nip", "street", "building_nr", "postal_code", "city"]
    missing = [key for key in required if key not in data or data[key] in (None, "")]
    if missing:
        return jsonify({"error": "missing fields", "missing": missing}), 400

    address = model.Address(
        data["street"],
        data["building_nr"],
        data["postal_code"],
        data["city"],
    )

    uow = unit_of_work.SqlAlchemyUnitOfWork()
    rows = views.manager_lookup_company_by_nip_and_address(
        data["nip"],
        address,
        uow,
    )
    for row in rows:
        company = row.get("company")
        if company and company.get("last_transaction_date") is not None:
            company["last_transaction_date"] = serialize_date(company["last_transaction_date"])

    return jsonify(rows), 200


