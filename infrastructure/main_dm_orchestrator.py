import smtplib
from . import dm_orchestrators, subiekt_gateway
from datetime import date
import logging

logger = logging.getLogger(__name__)

def final_daily_maintenance(report_writer, mailer):
    report_writer.start_new_report()

    subiekt_conn = subiekt_gateway.get_subiekt_connection()
    try:
        dm_orchestrators.ingest_recent_zk_rows(
            subiekt_conn=subiekt_conn,
            report_writer=report_writer,
        )
        dm_orchestrators.synchronize_recent_companies()
        dm_orchestrators.process_warning_candidates()
        dm_orchestrators.process_stale_candidates()
    finally:
        subiekt_conn.close()

    if report_writer.has_content():
        try:
            mailer.send_attachment(
                file_path=report_writer.path,
                subject=f"Daily maintenance report {report_writer.path.name}",
                body="Please find the attached report",
                recipient="miloszpiskor97@gmail.com", # docelowo config.recipient
            )
            logger.info(f"Daily maintenance report sent, date: {date.today().isoformat()}.")
        except (smtplib.SMTPException, OSError) as e:
            report_writer.write_line(f"Failed to send report email: {repr(e)}")
            logger.exception(f"Failed to send report email from {date.today().isoformat()}!")
