from unittest import mock
from pathlib import Path

from entrypoints import dm_entrypoint

def test_run_daily_maintenance():
    fake_writer = mock.Mock()
    fake_mailer = mock.Mock()

    with mock.patch("entrypoints.dm_entrypoint.error_writer.ErrorReportWriter", return_value=fake_writer) as mock_writer_cls, \
         mock.patch("entrypoints.dm_entrypoint.SmtpMailer", return_value=fake_mailer) as mock_mailer_cls, \
         mock.patch("entrypoints.dm_entrypoint.main_dm_orchestrator.final_daily_maintenance") as mock_final, \
         mock.patch("entrypoints.dm_entrypoint.logger") as mock_logger, \
         mock.patch("entrypoints.dm_entrypoint.config") as mock_config:

        mock_config.username = "user@example.com"
        mock_config.password = "secret"

        dm_entrypoint.run_daily_maintenance()

    mock_writer_cls.assert_called_once_with(Path("reports"))
    mock_mailer_cls.assert_called_once_with(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username="user@example.com",
        password="secret",
    )
    mock_final.assert_called_once_with(
        report_writer=fake_writer,
        mailer=fake_mailer,
    )
    assert mock_logger.info.call_count == 2
