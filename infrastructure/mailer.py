import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path

class SmtpMailer:
    def __init__(self, smtp_host, smtp_port, username, password):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send_email_with_attachment(self, recipient, subject, body, file_path: str | Path):
        file_path = Path(file_path)

        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        ctype, _ = mimetypes.guess_type(file_path.name)
        if ctype is None:
            ctype = "application/octet-stream"
        maintype, subtype = ctype.split("/", 1)

        msg.add_attachment(
            file_path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=file_path.name,
        )

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as connection:
            connection.starttls()
            connection.login(user=self.username, password=self.password)
            connection.send_message(msg)

    def send_email(self, recipient, subject, body):
        msg = EmailMessage()
        msg["From"] = self.username
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as connection:
            connection.starttls()
            connection.login(user=self.username, password=self.password)
            connection.send_message(msg)
    #
    # def send_company_released_notification(self, event, mailer):
    #     subject = f'Company (NIP: {event.nip}) released from "{event.rep_name}"'
    #     body = f"Company {event.nip} was released from {event.rep_name}."
    #     mailer.send_email(
    #         recipient=event.email,
    #         subject=subject,
    #         body=body,
    #     )