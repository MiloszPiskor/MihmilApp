from datetime import date
from pathlib import Path
from infrastructure import error_writer, main_dm_orchestrator
from infrastructure.mailer import SmtpMailer
import config
import logging_config

logger = logging_config.get_logger(__name__)

def run_daily_maintenance():
    logger.info("Daily maintenance job started", extra={"date": date.today().isoformat()})

    report_writer = error_writer.ErrorReportWriter(Path("reports"))
    mailer = SmtpMailer(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        username=config.username,
        password=config.password,
    )

    main_dm_orchestrator.final_daily_maintenance(
        report_writer=report_writer,
        mailer=mailer,
    )

    logger.info("Daily maintenance job finished", extra={"date": date.today().isoformat()})

# report_writer = error_writer.ErrorReportWriter(Path("reports"))
# mailer = SmtpMailer(
#     smtp_host="smtp.gmail.com",
#     smtp_port=587,
#     username="miloszpiskor97@gmail.com",
#     password="vsew diek xqsm habi"
# )
# report_writer.start_new_report()
# report_writer.write_line("błąd 2")
# mailer.send_email_with_attachment(
#     recipient="miloszpiskor97@gmail.com",
#     subject="Daily maintenance report",
#     body="Please find the attached report.",
#     file_path=report_writer.path,
# )