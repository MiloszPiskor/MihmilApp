from typing import List, Dict, Callable, Type, Union
from venv import logger
from domain import events, commands
from service_layer import handlers
from . import unit_of_work
from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

# After Cmd introduction:
Message = Union[commands.Command, events.Event]

def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")
    return results

# What can be sorted later (manual input or retrying):
def handle_event(
        event: Message,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            for attempt in Retrying(
                stop = stop_after_attempt(3),
                wait = wait_exponential()
            ):
                with attempt:
                    logger.debug('Handling event %s with handler %s', event, handler)
                    handler(event, uow)
                    queue.extend(uow.collect_new_events())
        except RetryError as retry_failure:
            logger.error('Error of event handler %s time. I give up!',
                         retry_failure.last_attempt.attempt_number
            )
            continue

# What has to be executed without errors (crucial business flows):
def handle_command(
        command: Message,
        queue: List[Message],
        uow: unit_of_work.AbstractUnitOfWork
):
    logger.debug('Handling command %s', command)
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow = uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception('Exception handling command %s', command)
        raise

EVENT_HANDLERS = {
    # Notification handlers (Domain Events → side effects)
    events.CompanyReleased: [handlers.send_company_released_notification],
    events.CompanyAssigned: [handlers.send_company_assigned_notification],
    events.RepWarned5Months: [handlers.send_stale_warning_notification]
}  # type: Dict[Type[events.Event], List[Callable]]

COMMAND_HANDLERS = {
    # Command handlers (job -> SQL candidates → Cmd -> handler):
    commands.EnsureRepExists: handlers.ensure_rep,
    commands.EnsureCompanyExists: handlers.ensure_company,
    commands.UpdateLastZK: handlers.update_last_zk,
    # Synchronizes:
    commands.SynchronizeRep: handlers.synchronize_rep,
    commands.SynchronizeLTD: handlers.synchronize_ltd,
    # Warnings and Releases:
    commands.WarnRepAfter5Months: handlers.warn_rep_after_5_months,
    commands.ReleaseStale: handlers.release_stale,
} # type: Dict[Type[commands.Command], Callable]

