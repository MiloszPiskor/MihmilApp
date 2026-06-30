# from apscheduler.schedulers.background import BackgroundScheduler
# from apscheduler.jobstores.memory import MemoryJobStore
# from apscheduler.executors.pool import ThreadPoolExecutor
# from apscheduler.triggers.cron import CronTrigger
# from entrypoints import dm_entrypoint
#
# def start_scheduler():
#
#     scheduler = BackgroundScheduler(
#         jobstores={"default": MemoryJobStore()},
#         executors={"default": ThreadPoolExecutor(max_workers=1)},
#         timezone="Europe/Warsaw",
#     )
#
#     scheduler.add_job(
#         dm_entrypoint.run_daily_maintenance,
#         trigger=CronTrigger(hour=2, minute=0),
#         id="daily_maintenance",
#         replace_existing=True,
#         max_instances=1,
#         coalesce=True,
#     )
#
#     scheduler.start()
#     return scheduler
#
# if __name__ == "__main__":
#     start_scheduler()
#     import time
#     while True:
#         time.sleep(60)