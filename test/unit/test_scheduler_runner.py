# from unittest import mock
# from entrypoints import schedule_runner
#
#
# def test_start_scheduler_registers_job_and_starts():
#     with mock.patch("entrypoints.scheduler_runner.BackgroundScheduler") as mock_scheduler_cls, \
#          mock.patch("entrypoints.scheduler_runner.CronTrigger") as mock_cron_trigger, \
#          mock.patch("entrypoints.scheduler_runner.run_daily_maintenance") as mock_job, \
#          mock.patch("entrypoints.scheduler_runner.log_scheduler_startup") as mock_startup:
#
#         scheduler_instance = mock_scheduler_cls.return_value
#         schedule_runner.start_scheduler()
#
#     mock_startup.assert_called_once()
#     mock_scheduler_cls.assert_called_once_with(
#         jobstores={"default": mock.ANY},
#         executors={"default": mock.ANY},
#         timezone="Europe/Warsaw",
#     )
#     mock_cron_trigger.assert_called_once_with(hour=2, minute=0)
#     scheduler_instance.add_listener.assert_called_once()
#     scheduler_instance.add_job.assert_called_once_with(
#         mock_job,
#         trigger=mock_cron_trigger.return_value,
#         id="daily_maintenance",
#         replace_existing=True,
#         max_instances=1,
#         coalesce=True,
#     )
#     scheduler_instance.start.assert_called_once()


