from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.cron import CronTrigger
from infrastructure.scheduler_logging import (
    scheduler_listener,
    log_scheduler_startup,
    log_scheduler_shutdown,
    log_heartbeat,
)
from entrypoints.dm_entrypoint import run_daily_maintenance
import time

def start_scheduler():
    log_scheduler_startup()
    scheduler = BackgroundScheduler(
        jobstores={"default": MemoryJobStore()},
        executors={"default": ThreadPoolExecutor(max_workers=1)},
        timezone="Europe/Warsaw",
    )
    scheduler.add_listener(scheduler_listener)
    scheduler.add_job(
        run_daily_maintenance,
        trigger=CronTrigger(hour=2, minute=0),
        id="daily_maintenance",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()
    try:
        while True:
            log_heartbeat()
            time.sleep(20 * 60)
    except KeyboardInterrupt:
        log_scheduler_shutdown()
    finally:
        scheduler.shutdown(wait=True)