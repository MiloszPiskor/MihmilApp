# from functools import partial
# from typing import Dict, Type, List, Callable
# from mailer import SmtpMailer
# from domain import events
# from service_layer import handlers
# import config
#
# def make_event_handlers():
#     mailer = SmtpMailer(
#         smtp_host="smtp.gmail.com",
#         smtp_port=587,
#         username=config.username,
#         password=config.password,
#     )
#     return {
#         events.CompanyReleased: [partial(handlers.send_company_released_notification, mailer=mailer)],
#         events.CompanyAssigned: [partial(handlers.send_company_assigned_notification, mailer=mailer)],
#         events.RepWarned5Months: [partial(handlers.send_stale_warning_notification, mailer=mailer)],
#     } # type: Dict[Type[events.Event], List[Callable]]


#     smtp_host="smtp.gmail.com",
#     smtp_port=587,
#     username="miloszpiskor97@gmail.com",
#     password="vsew diek xqsm habi"