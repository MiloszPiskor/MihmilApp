from unittest import mock
from infrastructure.mailer import SmtpMailer
import pytest
import smtplib

def test_smtp_mailer_sends_attachment(tmp_path):
    report_file = tmp_path / "report.txt"
    report_file.write_text("hello", encoding="utf-8")

    with mock.patch("infrastructure.mailer.smtplib.SMTP") as smtp_cls:
        smtp_conn = smtp_cls.return_value.__enter__.return_value
        mailer = SmtpMailer("smtp.gmail.com", 587, "user@example.com", "secret")

        mailer.send_email_with_attachment(
            recipient="ops@example.com",
            subject="Daily report",
            body="Attached.",
            file_path=report_file,
        )

    smtp_cls.assert_called_once_with("smtp.gmail.com", 587)
    smtp_conn.starttls.assert_called_once()
    smtp_conn.login.assert_called_once_with(user="user@example.com", password="secret")
    smtp_conn.send_message.assert_called_once()

    msg = smtp_conn.send_message.call_args.args[0]
    assert msg["From"] == "user@example.com"
    assert msg["To"] == "ops@example.com"
    assert msg["Subject"] == "Daily report"

    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.txt"

def test_smtp_mailer_raises_when_send_fails(tmp_path):
    report_file = tmp_path / "report.txt"
    report_file.write_text("hello", encoding="utf-8")

    with mock.patch("infrastructure.mailer.smtplib.SMTP") as smtp_cls:
        smtp_conn = smtp_cls.return_value.__enter__.return_value
        smtp_conn.send_message.side_effect = smtplib.SMTPException("boom")
        mailer = SmtpMailer("smtp.gmail.com", 587, "user@example.com", "secret")

        with pytest.raises(smtplib.SMTPException, match="boom"):
            mailer.send_email_with_attachment(
                recipient="ops@example.com",
                subject="Daily report",
                body="Attached.",
                file_path=report_file,
            )
