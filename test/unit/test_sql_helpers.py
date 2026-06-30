from types import SimpleNamespace
from datetime import date
from domain import model
from infrastructure import sql_helpers, cqrs

class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

class FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.executed_query = None

    def execute(self, query):
        self.executed_query = query
        return FakeResult(self._rows)

class FakeConnection:
    def __init__(self, rows):
        self._rows = rows
        self.last_query = None

    def execute(self, query):
        self.last_query = query
        return FakeResult(self._rows)

def test_zk_24h_raw_maps_rows_to_dto():
    fake_rows = [
        SimpleNamespace(
            nip="1234567890",
            name="Company A",
            street="Main",
            building_nr="1",
            postal_code="00-000",
            city="Warsaw",
            rep_group_name="Group A",
            zk_date=date(2026, 5, 20),
        )
    ]
    conn = FakeConnection(fake_rows)

    result = sql_helpers.zk_24h_raw(conn)

    assert len(result) == 1
    assert result[0] == model.ZKRow(
        nip="1234567890",
        name="Company A",
        street="Main",
        building_nr="1",
        postal_code="00-000",
        city="Warsaw",
        rep_group_name="Group A",
        zk_date=date(2026, 5, 20),
    )

def test_recent_zk_companies_maps_rows_to_candidates():
    """
    Covers the common mapping behavior shared by recent_zk_companies(),
    warning_5m_candidates(), and stale_candidates().
    The only difference between them is the SQL query constant.
    """
    fake_rows = [
        SimpleNamespace(
            nip="1111111111",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        ),
        SimpleNamespace(
            nip="2222222222",
            street="Side",
            building_nr="2",
            postal_code="00-002",
            city="Krakow",
        ),
    ]
    session = FakeSession(fake_rows)

    result = sql_helpers.recent_zk_companies(session)

    assert result == [
        model.CompanyCandidate(
            nip="1111111111",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        ),
        model.CompanyCandidate(
            nip="2222222222",
            street="Side",
            building_nr="2",
            postal_code="00-002",
            city="Krakow",
        ),
    ]
    assert session.executed_query.text == cqrs.QUERY_RECENT_ZK_COMPANIES



