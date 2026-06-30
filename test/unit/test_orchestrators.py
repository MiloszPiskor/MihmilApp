from types import SimpleNamespace
from unittest import mock

from domain import commands
from infrastructure import dm_orchestrators, main_dm_orchestrator

"""
Architecture note:

This module intentionally avoids introducing a full dependency-injection/bootstrap
layer for the message bus and related orchestration dependencies (emailing etc.).

Rationale:
- The main daily maintenance process and notification flow are still simple.
- A lightweight messagebus module keeps the code easy to follow and quick to change.
- Test isolation is handled with `mock.patch(...)` inside test functions for now,
  which keeps the current design pragmatic and low-overhead.

If the number of mocks, patches, or orchestration dependencies grows to the point
where tests become hard to read or maintain, this decision should be revisited and
a proper DI/bootstrap mechanism should be introduced, with explicit dependencies of 
orchestrators on messagebus, and mailing system on its' implementation. 
"""

def test_ingest_recent_zk_rows():
    fake_subiekt_conn = object()
    fake_rows = [
        SimpleNamespace(
            rep_group_name="Rep A",
            nip="1234567890",
            name="Company A",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
            zk_date="2026-05-26",
        )
    ]
    fake_report_writer = mock.Mock()
    fake_uow = mock.Mock()

    with mock.patch("infrastructure.dm_orchestrators.sql_helpers.zk_24h_raw", return_value=fake_rows) as mock_zk_raw, \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle") as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow) as mock_uow_cls, \
         mock.patch("infrastructure.dm_orchestrators.logger") as mock_logger:

        dm_orchestrators.ingest_recent_zk_rows(fake_subiekt_conn, fake_report_writer)

    mock_zk_raw.assert_called_once_with(fake_subiekt_conn)
    assert mock_handle.call_count == 3
    assert mock_uow_cls.call_count == 3
    assert fake_report_writer.write_line.call_count == 0
    assert mock_logger.info.call_count >= 1

    first_call = mock_handle.call_args_list[0]
    second_call = mock_handle.call_args_list[1]
    third_call = mock_handle.call_args_list[2]

    assert isinstance(first_call.kwargs["message"], commands.EnsureRepExists)
    assert first_call.kwargs["message"].rep_name == "Rep A"
    assert first_call.kwargs["uow"] is fake_uow

    assert isinstance(second_call.kwargs["message"], commands.EnsureCompanyExists)
    assert second_call.kwargs["message"].nip == "1234567890"
    assert second_call.kwargs["message"].name == "Company A"
    assert second_call.kwargs["message"].street == "Main"
    assert second_call.kwargs["message"].building_nr == "1"
    assert second_call.kwargs["message"].postal_code == "00-001"
    assert second_call.kwargs["message"].city == "Warsaw"
    assert second_call.kwargs["uow"] is fake_uow

    assert isinstance(third_call.kwargs["message"], commands.UpdateLastZK)
    assert third_call.kwargs["message"].nip == "1234567890"
    assert third_call.kwargs["message"].name == "Company A"
    assert third_call.kwargs["message"].street == "Main"
    assert third_call.kwargs["message"].building_nr == "1"
    assert third_call.kwargs["message"].postal_code == "00-001"
    assert third_call.kwargs["message"].city == "Warsaw"
    assert third_call.kwargs["message"].zk_date == "2026-05-26"
    assert third_call.kwargs["message"].rep_name == "Rep A"
    assert third_call.kwargs["uow"] is fake_uow

def test_ingest_recent_zk_rows_writes_report_on_failure():
    fake_subiekt_conn = object()
    fake_rows = [
        SimpleNamespace(
            rep_group_name="Rep A",
            nip="1234567890",
            name="Company A",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
            zk_date="2026-05-26",
        )
    ]
    fake_report_writer = mock.Mock()
    fake_uow = mock.Mock()

    def handle_side_effect(*, message, uow):
        if isinstance(message, commands.EnsureCompanyExists):
            raise RuntimeError("boom")

    with mock.patch("infrastructure.dm_orchestrators.sql_helpers.zk_24h_raw", return_value=fake_rows), \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle", side_effect=handle_side_effect) as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow), \
         mock.patch("infrastructure.dm_orchestrators.logger") as mock_logger:

        dm_orchestrators.ingest_recent_zk_rows(fake_subiekt_conn, fake_report_writer)

    fake_report_writer.write_line.assert_called_once()
    assert "ingest_recent_zk_rows failed" in fake_report_writer.write_line.call_args.args[0]
    mock_logger.exception.assert_called_once()
    assert mock_handle.call_count == 2

def test_ingest_recent_zk_rows_continues_after_row_failure():
    fake_subiekt_conn = object()
    fake_rows = [
        SimpleNamespace(
            rep_group_name="Rep A",
            nip="1234567890",
            name="Company A",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
            zk_date="2026-05-26",
        ),
        SimpleNamespace(
            rep_group_name="Rep B",
            nip="9999999999",
            name="Company B",
            street="Second",
            building_nr="2",
            postal_code="00-002",
            city="Krakow",
            zk_date="2026-05-27",
        ),
    ]
    fake_report_writer = mock.Mock()
    fake_uow = mock.Mock()

    def handle_side_effect(*, message, uow):
        if isinstance(message, commands.EnsureRepExists) and message.rep_name == "Rep A":
            raise RuntimeError("boom")

    with mock.patch("infrastructure.dm_orchestrators.sql_helpers.zk_24h_raw", return_value=fake_rows), \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle", side_effect=handle_side_effect) as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow), \
         mock.patch("infrastructure.dm_orchestrators.logger"):

        dm_orchestrators.ingest_recent_zk_rows(fake_subiekt_conn, fake_report_writer)

    assert fake_report_writer.write_line.call_count == 1

    assert mock_handle.call_count == 4

    first_call = mock_handle.call_args_list[0]
    second_call = mock_handle.call_args_list[1]
    third_call = mock_handle.call_args_list[2]
    fourth_call = mock_handle.call_args_list[3]

    assert isinstance(first_call.kwargs["message"], commands.EnsureRepExists)
    assert first_call.kwargs["message"].rep_name == "Rep A"

    assert isinstance(second_call.kwargs["message"], commands.EnsureRepExists)
    assert second_call.kwargs["message"].rep_name == "Rep B"
    assert second_call.kwargs["uow"] is fake_uow

    assert isinstance(third_call.kwargs["message"], commands.EnsureCompanyExists)
    assert third_call.kwargs["message"].nip == "9999999999"
    assert third_call.kwargs["uow"] is fake_uow

    assert isinstance(fourth_call.kwargs["message"], commands.UpdateLastZK)
    assert fourth_call.kwargs["message"].nip == "9999999999"
    assert fourth_call.kwargs["message"].zk_date == "2026-05-27"
    assert fourth_call.kwargs["uow"] is fake_uow

def test_synchronize_recent_companies():
    fake_session = object()
    fake_rows = [
        SimpleNamespace(
            nip="1234567890",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        )
    ]

    with mock.patch("infrastructure.dm_orchestrators.unit_of_work.DEFAULT_SESSION_FACTORY", return_value=fake_session) as mock_session_factory, \
         mock.patch("infrastructure.dm_orchestrators.sql_helpers.recent_zk_companies", return_value=fake_rows) as mock_recent, \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle") as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value="fake-uow") as mock_uow_cls:

        dm_orchestrators.synchronize_recent_companies()

    mock_session_factory.assert_called_once()
    mock_recent.assert_called_once_with(session=fake_session)

    assert mock_handle.call_count == 2

    first_call = mock_handle.call_args_list[0]
    second_call = mock_handle.call_args_list[1]

    assert isinstance(first_call.kwargs["message"], commands.SynchronizeRep)
    assert isinstance(second_call.kwargs["message"], commands.SynchronizeLTD)
    assert first_call.kwargs["uow"] == "fake-uow"
    assert second_call.kwargs["uow"] == "fake-uow"

    assert first_call.kwargs["message"].nip == "1234567890"
    assert second_call.kwargs["message"].city == "Warsaw"

    assert mock_uow_cls.call_count == 2

def test_synchronize_recent_companies_continues_after_failure():
    """
    Representative failure/continue test for the shared orchestrator pattern.
    The other row-processing orchestrators use the same try/except + continue mechanism,
    so we verify the behavior once here instead of duplicating the same deep test in every function.
    """
    fake_session = object()
    fake_rows = [
        SimpleNamespace(
            nip="1234567890",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        ),
        SimpleNamespace(
            nip="9999999999",
            street="Second",
            building_nr="2",
            postal_code="00-002",
            city="Krakow",
        ),
    ]
    fake_uow = mock.Mock()

    def handle_side_effect(*, message, uow):
        if isinstance(message, commands.SynchronizeRep) and message.nip == "1234567890":
            raise RuntimeError("boom")

    with mock.patch("infrastructure.dm_orchestrators.unit_of_work.DEFAULT_SESSION_FACTORY", return_value=fake_session), \
         mock.patch("infrastructure.dm_orchestrators.sql_helpers.recent_zk_companies", return_value=fake_rows), \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle", side_effect=handle_side_effect) as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow), \
         mock.patch("infrastructure.dm_orchestrators.logger"):

        dm_orchestrators.synchronize_recent_companies()

    assert mock_handle.call_count == 3

    first_call = mock_handle.call_args_list[0]
    second_call = mock_handle.call_args_list[1]
    third_call = mock_handle.call_args_list[2]

    assert isinstance(first_call.kwargs["message"], commands.SynchronizeRep)
    assert first_call.kwargs["message"].nip == "1234567890"

    assert isinstance(second_call.kwargs["message"], commands.SynchronizeRep)
    assert second_call.kwargs["message"].nip == "9999999999"

    assert isinstance(third_call.kwargs["message"], commands.SynchronizeLTD)
    assert third_call.kwargs["message"].nip == "9999999999"


def test_process_warning_candidates():
    fake_rows = [
        SimpleNamespace(
            nip="1234567890",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        ),
        SimpleNamespace(
            nip="0987654321",
            street="Other",
            building_nr="2",
            postal_code="00-002",
            city="Gdansk",
        )
    ]
    fake_uow = mock.Mock()
    fake_session = object()

    with mock.patch("infrastructure.dm_orchestrators.unit_of_work.DEFAULT_SESSION_FACTORY", return_value=fake_session) as mock_session_factory, \
         mock.patch("infrastructure.dm_orchestrators.sql_helpers.warning_5m_candidates", return_value=fake_rows) as mock_candidates, \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle") as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow) as mock_uow_cls:

        dm_orchestrators.process_warning_candidates()

    mock_session_factory.assert_called_once()
    mock_candidates.assert_called_once_with(session=fake_session)
    assert mock_handle.call_count == 2
    assert mock_uow_cls.call_count == 2

    first_call = mock_handle.call_args_list[0]
    second_call = mock_handle.call_args_list[1]

    assert (isinstance(first_call.kwargs["message"], commands.WarnRepAfter5Months)
            and isinstance(second_call.kwargs["message"], commands.WarnRepAfter5Months))
    assert first_call.kwargs["message"].nip == "1234567890"
    assert second_call.kwargs["message"].nip == "0987654321"
    assert first_call.kwargs["message"].street == "Main"
    assert second_call.kwargs["message"].street == "Other"
    assert first_call.kwargs["message"].building_nr == "1"
    assert second_call.kwargs["message"].building_nr == "2"
    assert first_call.kwargs["message"].postal_code == "00-001"
    assert second_call.kwargs["message"].postal_code == "00-002"
    assert first_call.kwargs["message"].city == "Warsaw"
    assert second_call.kwargs["message"].city == "Gdansk"
    assert first_call.kwargs["uow"] is fake_uow and second_call.kwargs["uow"] is fake_uow

def test_process_stale_candidates():
    fake_rows = [
        SimpleNamespace(
            nip="1234567890",
            street="Main",
            building_nr="1",
            postal_code="00-001",
            city="Warsaw",
        )
    ]
    fake_uow = mock.Mock()
    fake_session = object()

    with mock.patch("infrastructure.dm_orchestrators.unit_of_work.DEFAULT_SESSION_FACTORY", return_value=fake_session) as mock_session_factory, \
         mock.patch("infrastructure.dm_orchestrators.sql_helpers.stale_candidates", return_value=fake_rows) as mock_candidates, \
         mock.patch("infrastructure.dm_orchestrators.messagebus.handle") as mock_handle, \
         mock.patch("infrastructure.dm_orchestrators.unit_of_work.SqlAlchemyUnitOfWork", return_value=fake_uow) as mock_uow_cls:

        dm_orchestrators.process_stale_candidates()

    mock_session_factory.assert_called_once()
    mock_candidates.assert_called_once_with(session=fake_session)
    assert mock_handle.call_count == 1
    mock_uow_cls.assert_called_once()

    call = mock_handle.call_args
    assert isinstance(call.kwargs["message"], commands.ReleaseStale)
    assert call.kwargs["message"].nip == "1234567890"
    assert call.kwargs["message"].street == "Main"
    assert call.kwargs["message"].building_nr == "1"
    assert call.kwargs["message"].postal_code == "00-001"
    assert call.kwargs["message"].city == "Warsaw"
    assert call.kwargs["uow"] is fake_uow

def test_final_daily_maintenance_happy_path():
    fake_conn = mock.Mock()
    report_writer = mock.Mock()
    report_writer.path.name = "daily_maintenance_2026-06-16.txt"
    report_writer.has_content.return_value = True
    mailer = mock.Mock()

    with mock.patch("infrastructure.main_dm_orchestrator.subiekt_gateway.get_subiekt_connection", return_value=fake_conn) as mock_get_conn, \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.ingest_recent_zk_rows") as mock_ingest, \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.synchronize_recent_companies") as mock_sync, \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_warning_candidates") as mock_warn, \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_stale_candidates") as mock_stale, \
         mock.patch("infrastructure.main_dm_orchestrator.logger") as mock_logger:

        main_dm_orchestrator.final_daily_maintenance(report_writer=report_writer, mailer=mailer)

    report_writer.start_new_report.assert_called_once()
    mock_get_conn.assert_called_once()
    mock_ingest.assert_called_once_with(subiekt_conn=fake_conn, report_writer=report_writer)
    mock_sync.assert_called_once()
    mock_warn.assert_called_once()
    mock_stale.assert_called_once()
    fake_conn.close.assert_called_once()

    mailer.send_attachment.assert_called_once_with(
        file_path=report_writer.path,
        subject="Daily maintenance report daily_maintenance_2026-06-16.txt",
        body="Please find the attached report",
        recipient="miloszpiskor97@gmail.com",
    )
    mock_logger.info.assert_called_once()

def test_final_daily_maintenance_skips_mail_when_report_empty():
    fake_conn = mock.Mock()
    report_writer = mock.Mock()
    report_writer.path.name = "daily_maintenance_2026-06-16.txt"
    report_writer.has_content.return_value = False
    mailer = mock.Mock()

    with mock.patch("infrastructure.main_dm_orchestrator.subiekt_gateway.get_subiekt_connection", return_value=fake_conn), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.ingest_recent_zk_rows"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.synchronize_recent_companies"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_warning_candidates"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_stale_candidates"):

        main_dm_orchestrator.final_daily_maintenance(report_writer=report_writer, mailer=mailer)

    mailer.send_attachment.assert_not_called()
    fake_conn.close.assert_called_once()

import smtplib

def test_final_daily_maintenance_logs_mail_failure_and_continues():
    fake_conn = mock.Mock()
    report_writer = mock.Mock()
    report_writer.path.name = "daily_maintenance_2026-06-16.txt"
    report_writer.has_content.return_value = True
    mailer = mock.Mock()
    mailer.send_attachment.side_effect = smtplib.SMTPException("boom")

    with mock.patch("infrastructure.main_dm_orchestrator.subiekt_gateway.get_subiekt_connection", return_value=fake_conn), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.ingest_recent_zk_rows"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.synchronize_recent_companies"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_warning_candidates"), \
         mock.patch("infrastructure.main_dm_orchestrator.dm_orchestrators.process_stale_candidates"), \
         mock.patch("infrastructure.main_dm_orchestrator.logger") as mock_logger:

        main_dm_orchestrator.final_daily_maintenance(report_writer=report_writer, mailer=mailer)

    report_writer.write_line.assert_called_once()
    mock_logger.exception.assert_called_once()
    fake_conn.close.assert_called_once()




