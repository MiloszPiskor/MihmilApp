import time
import pytest
from sqlalchemy import text
from domain.events import CompanyAssigned
from domain import model
from service_layer import unit_of_work

def insert_company(session, nip, name, street, building_nr, postal_code, city, version):
    session.execute(text("""
    INSERT INTO companies (nip, name, street, building_nr, postal_code, city, version) 
    VALUES (:nip, :name, :street, :building_nr, :postal_code, :city, :version)
    """),
    dict(nip=nip, name=name, street=street, building_nr=building_nr, postal_code=postal_code, city=city, version=version)
    )

def insert_sales_rep(session, ref, name, email):

    session.execute(text("""
        INSERT INTO sales_reps (reference, name, email) VALUES
        (:ref, :name, :email)
    """),
    dict(ref=ref, name=name, email=email)
    )

def get_assigned_company_nip(session, rep_ref):

    [[sales_rep_id]] = session.execute(text("""
    SELECT id FROM sales_reps WHERE reference=:rep_ref
    """),
    dict(rep_ref=rep_ref)
    )
    [[company_nip]] = session.execute(text("""
    SELECT c.nip
    FROM company_assignments JOIN companies AS c ON company_id = c.id
    WHERE rep_id=:sales_rep_id
    """),
    dict(sales_rep_id=sales_rep_id)
    )
    return company_nip

def test_uow_can_retrieve_a_sales_rep_and_a_company_and_assign_to_it(session_factory):

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory=session_factory)
    with uow:
        # Data Preparation
        insert_company(uow.session, "0000000000", "Company", "Street", "1", "00-000", "City1", 1)
        insert_sales_rep(uow.session, "namsur", "Name Surname", "email@gmail.com")

        company = uow.companies.get(nip=model.NIP("0000000000"),
                                    address=model.Address(street="Street",building_nr="1", postal_code="00-000", city="City1")
                                    )
        rep = uow.reps.get(reference="namsur")

        company.assign_to_rep(rep)
        uow.commit()

    # Data layer: fetching the company's' nip by SQL
    new_session = session_factory()
    company_nip = get_assigned_company_nip(new_session, rep.reference)

    assert company_nip == company.nip.value

# SAVING AND ROLLING BACK THE CHANGES
def test_commits_work(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)

    with uow:
        insert_company(uow.session, "123456789", "Company", "Street", "1", "00-000", "City", 1)
        uow.commit()

    new_session = session_factory()
    rows = list(new_session.execute(text('SELECT * FROM companies')))

    assert len(rows) == 1

def test_rolls_back_uncommitted_work_by_default(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)

    with uow:
        insert_company(uow.session, "0000000000", "Company", "Street", "1", "00-000", "City1", 1)

    new_session = session_factory()
    rows = list(new_session.execute(text('''
    SELECT * FROM "companies"''')))

    assert rows == []

def test_rolls_back_on_error(session_factory):
    class MyException(Exception):
        pass

    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)
    with pytest.raises(MyException):
        with uow:
            insert_company(uow.session, "0000000000", "Company", "Street", "1", "00-000", "City1", 1)
            raise MyException()

    new_session = session_factory()
    rows = list(new_session.execute(text('''
    SELECT * FROM "companies"''')))

    assert rows == []

def test_does_not_persist_without_commit(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)

    with uow:
        insert_company(uow.session, "0000000000", "Company", "Street", "1", "00-000", "City1", 1)
        insert_sales_rep(uow.session, "namsur", "Name Surname", "email@gmail.com")

        company = uow.companies.get(nip=model.NIP("0000000000"),
                                    address=model.Address(street="Street",building_nr="1", postal_code="00-000", city="City1")
                                    )
        rep = uow.reps.get(reference="namsur")

        company.assign_to_rep(rep)
        # no commit

    new_session = session_factory()
    rows = list(new_session.execute(text('SELECT * FROM company_assignments')))

    assert rows == []

# Events collection
def test_uow_collects_new_events(session_factory):
    uow = unit_of_work.SqlAlchemyUnitOfWork(session_factory)

    with uow:
        insert_company(uow.session, "0000000000", "Company", "Street", "1", "00-000", "City1", 1)
        insert_sales_rep(uow.session, "namsur", "Name Surname", "email@gmail.com")

        company = uow.companies.get(nip=model.NIP("0000000000"),
                                    address=model.Address(street="Street",building_nr="1", postal_code="00-000", city="City1")
                                    )
        rep = uow.reps.get(reference="namsur")

        company.assign_to_rep(rep)

        events_list = list(uow.collect_new_events())

        assert len(events_list) == 1
        assert events_list[0].__class__.__name__ == "CompanyAssigned"

# # def create_company() as insert batch
# # try_to_allocate as try_to_assign
# def try_to_assign(rep_id, nip, exceptions):
#     rep =
# def try_to_allocate(orderid, sku, exceptions):
#     line = model.OrderLine(orderid, sku, 10)
#     try:
#         with unit_of_work.SqlAlchemyUnitOfWork() as uow:
#             product = uow.products.get(sku=sku)
#             product.allocate(line)
#             time.sleep(0.2)
#             uow.commit()
#     except Exception as e:
#         print(traceback.format_exc())
#         exceptions.append(e)
#
#
# def test_concurrent_updates_to_version_are_not_allowed(postgres_session_factory):
#     sku, batch = random_sku(), random_batchref()
#     session = postgres_session_factory()
#     insert_batch(session, batch, sku, 100, eta=None, product_version=1)
#     session.commit()
#
#     order1, order2 = random_orderid(1), random_orderid(2)
#     exceptions = []  # type: List[Exception]
#     try_to_allocate_order1 = lambda: try_to_allocate(order1, sku, exceptions)
#     try_to_allocate_order2 = lambda: try_to_allocate(order2, sku, exceptions)
#     thread1 = threading.Thread(target=try_to_allocate_order1)
#     thread2 = threading.Thread(target=try_to_allocate_order2)
#     thread1.start()
#     thread2.start()
#     thread1.join()
#     thread2.join()
#
#     [[version]] = session.execute(
#         "SELECT version_number FROM products WHERE sku=:sku",
#         dict(sku=sku),
#     )
#     assert version == 2
#     [exception] = exceptions
#     assert 'could not serialize access due to concurrent update' in str(exception)
#
#     orders = list(session.execute(
#         "SELECT orderid FROM allocations"
#         " JOIN batches ON allocations.batch_id = batches.id"
#         " JOIN order_lines ON allocations.orderline_id = order_lines.id"
#         " WHERE order_lines.sku=:sku",
#         dict(sku=sku),
#     ))
#     assert len(orders) == 1
#     with unit_of_work.SqlAlchemyUnitOfWork() as uow:
