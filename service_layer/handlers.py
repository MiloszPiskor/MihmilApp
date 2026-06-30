import smtplib
from infrastructure.mailer import SmtpMailer # no bootstrap
from domain import model, events, commands
from service_layer import unit_of_work
from adapters import email
from infrastructure import rep_mapper
import logging_config
import config

logger = logging_config.get_logger(__name__)

# def assign_company(event: commands.Assign, uow: unit_of_work.AbstractUnitOfWork) -> str:
#     nip, address = model.NIP(event.nip), model.Address(event.street, event.building_nr, event.postal_code, event.city)
#     # rep_ref from endpoint:get_jwt_claims()['reference'] from JWT? User context
#     rep = uow.reps.get(event.rep_ref)
#     with uow:
#         company = uow.companies.get(nip=nip, address=address)
#         if not company:
#             raise ValueError("Company not found") # custom error here needed
#
#         rep_ref = company.assign_to_rep(rep) # INVARIANT FULLY ENFORCED
#         uow.commit() # company triggers
#
#     return rep_ref # [] if idempotent
#
# def add_company(event:events.CompanyCreated, uow: unit_of_work.AbstractUnitOfWork):
#     """
#     After calling external API for information and confirming it, or scheduled job finding new
#     NIP in Subiekt recent ZK, it will have to create a new entity to tie it with the SalesRep
#     """
#     with uow:
#         address, nip = model.Address(
#             street=event.street,
#             building_nr=event.building_nr,
#             postal_code=event.postal_code,
#             city=event.city
#         ), model.NIP(event.nip)
#
#         new_company = model.Company(nip=nip, name=event.name, address=address) # InvalidNip -> catch this error later (endpoint or cron)
#         uow.companies.add(new_company)
#         uow.commit()
#
# def add_sales_rep(event:events.SalesRepCreated, uow: unit_of_work.AbstractUnitOfWork):
#     """
#     Scheduled Job searches for Grupa (sales rep) in new ZK's: after discovering one
#     not found in the DB, it creates new one automatically.
#     """
#     with uow:
#
#         new_rep = (model.SalesRep(reference=event.reference, name=event.name, email=event.email))
#         uow.reps.add(new_rep)
#         uow.commit()

# Subiekt SQL related CMD's
def ensure_rep(command: commands.EnsureRepExists, uow: unit_of_work.AbstractUnitOfWork):
    """
    The command takes the data from Subiekt SQL query (ZK, Dok Typ 16) and makes sure the sales rep
    responsible for the order exists in the system.
    """
    with uow:
        mapper = rep_mapper.ZKMapper()
        name, reference, email = mapper.get_rep_data(command.rep_name)

        sales_rep = uow.reps.get(reference)
        if sales_rep is None:
            sales_rep = (model.SalesRep(reference=reference, name=name, email=email))
            uow.reps.add(sales_rep)

        uow.commit()

def ensure_company(command: commands.EnsureCompanyExists, uow: unit_of_work.AbstractUnitOfWork):
    """
    The command takes the data from Subiekt SQL query (ZK, Dok Typ 16) and makes sure the company
    that made the order exists in the system.
    """
    with uow:
        address, nip = model.Address(
            street=command.street,
            building_nr=command.building_nr,
            postal_code=command.postal_code,
            city=command.city
        ), model.NIP(command.nip)
        company = uow.companies.get(nip= nip, address=address)

        if company is None:
            new_company = model.Company(nip=nip, name=command.name,
                                        address=address)  # InvalidNip -> catch this error later (endpoint or cron)
            uow.companies.add(new_company)

        uow.commit()

def update_last_zk(command: commands.UpdateLastZK, uow: unit_of_work.AbstractUnitOfWork):
    nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code, command.city)

    with uow:

        zk = model.ZK(command.nip, command.name, command.street, command.building_nr, command.postal_code, command.city,
                 command.zk_date, command.rep_name)

        company = uow.companies.get(nip, address)

        # company.last_zk = zk
        company.update_last_zk(zk)
        uow.commit()

# Synchronizers:
def synchronize_rep(command: commands.SynchronizeRep, uow: unit_of_work.AbstractUnitOfWork):
    nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code,
                                                         command.city)

    with uow:
        company = uow.companies.get(nip, address)

        company.check_for_zk()
        rep_name = company.last_zk.rep_name
        mapper = rep_mapper.ZKMapper()
        reference = mapper.get_rep_data(rep_name)[1]
        logger.info(f"before reps.get({reference})")
        sales_rep = uow.reps.get(reference)
        logger.info(f"after reps.get({reference}) -> {sales_rep}")
        company.synchronize_rep_from_zk(sales_rep)

        uow.commit()

def synchronize_ltd(command: commands.SynchronizeLTD, uow: unit_of_work.AbstractUnitOfWork):
    nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code,
                                                         command.city)

    with uow:
        company = uow.companies.get(nip, address)
        company.check_for_zk()
        company.synchronize_ltd_from_zk()
        uow.commit()

# Warning and releasing:
def warn_rep_after_5_months(command: commands.WarnRepAfter5Months, uow: unit_of_work.AbstractUnitOfWork):
    nip, address = model.NIP(command.nip), model.Address(command.street, command.building_nr, command.postal_code,
                                                         command.city)

    with uow:
        company = uow.companies.get(nip, address)
        company.needs_precise_5month_warning()
        uow.commit()

def release_stale(command: commands.ReleaseStale, uow: unit_of_work.AbstractUnitOfWork):
    nip = model.NIP(command.nip)
    address = model.Address(command.street, command.building_nr, command.postal_code, command.city)

    with uow:
        company = uow.companies.get(nip, address)
        company.stale_rep_release()
        uow.commit()



def company_lookup(nip: model.NIP, name: str, address: model.Address, uow: unit_of_work.AbstractUnitOfWork):
    """
    User makes a lookup, using external API, to find out whether a given company is in our DB:
    - answer with information about occupation?
    - information in arguments given by API?
    """
    with uow:
        company = uow.companies.get(nip)

# Added from messagebus.py
# def send_company_released_notification(event: events.CompanyReleased, uow: unit_of_work.AbstractUnitOfWork):
#     email.send_mail(
#         'buiro@prexpol.eu',
#         f'{event.email}'
#         f'Company (NIP: {event.nip}) released from "{event.rep_name}".',
#     )
def send_company_released_notification(event: events.CompanyReleased, uow: unit_of_work.AbstractUnitOfWork):
    mailer = SmtpMailer(
        smtp_host=config.host,
        smtp_port=config.port,
        username=config.username,
        password=config.password
    )
    subject = f'Company (NIP: {event.nip}) released from "{event.rep_name}"'
    body = f"Company {event.nip} was released from {event.rep_name}."

    try:
        mailer.send_email(event.email, subject, body)
    except (smtplib.SMTPException, OSError) as e:
        logger.exception(f"Failed to send released notification for %s, error: {e}", event.nip)
        raise

def send_company_assigned_notification(event: events.CompanyAssigned, uow: unit_of_work.AbstractUnitOfWork):
    mailer = SmtpMailer(
        smtp_host=config.host,
        smtp_port=config.port,
        username=config.username,
        password=config.password
    )
    subject = f'Company (NIP: {event.nip}) assigned to "{event.rep_name}").'
    body = f'Company (NIP: {event.nip}) was assigned to "{event.rep_name}").'

    try:
        mailer.send_email(event.email, subject, body)
    except (smtplib.SMTPException, OSError) as e:
        logger.exception(f"Failed to send released notification for %s, error: {e}", event.nip)
        raise

def send_stale_warning_notification(event: events.RepWarned5Months, uow: unit_of_work.AbstractUnitOfWork):
    mailer = SmtpMailer(
        smtp_host=config.host,
        smtp_port=config.port,
        username=config.username,
        password=config.password
    )
    subject = f'Company (NIP: {event.nip}) assigned to {event.rep_name} becomes stale in a month.'
    body = f'Company (NIP: {event.nip}) assigned to {event.rep_name} becomes stale in a month.'

    try:
        mailer.send_email(event.email, subject, body)
    except (smtplib.SMTPException, OSError) as e:
        logger.exception(f"Failed to send released notification for %s, error: {e}", event.nip)
        raise

#TODO: ALL THE MAINTENANCE HANDLERS


