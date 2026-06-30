import os
import socket
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
import logging_config

logger = logging_config.get_logger(__name__)


def scheduler_listener(event):
    if event.code == EVENT_JOB_EXECUTED:
        logger.info(
            "Job executed successfully",
            extra={"job_id": event.job_id},
        )
    elif event.code == EVENT_JOB_ERROR:
        logger.error(
            "Job crashed",
            extra={
                "job_id": event.job_id,
                "exception": repr(event.exception),
                "traceback": event.traceback,
            },
        )
    elif event.code == EVENT_JOB_MISSED:
        logger.warning(
            "Job missed its scheduled run",
            extra={"job_id": event.job_id},
        )

def log_scheduler_startup():
    logger.info(
        "Scheduler started",
        extra={"pid": os.getpid(), "host": socket.gethostname()},
    )

def log_scheduler_shutdown():
    logger.info(
        "Scheduler stopped",
        extra={"pid": os.getpid(), "host": socket.gethostname()},
    )

def log_heartbeat():
    logger.info(
        "Scheduler heartbeat",
        extra={"pid": os.getpid(), "host": socket.gethostname()},
    )
