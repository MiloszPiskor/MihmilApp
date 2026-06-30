from sqlalchemy import (
    Table, Column, String, ForeignKey,
    Integer, Date, Index, UniqueConstraint, TypeDecorator, event
)
from sqlalchemy.orm import registry, relationship, composite
from domain import model
mapper_registry = registry()
metadata = mapper_registry.metadata

# model.NIP V.O. to SQLALchemy mapper
class NIPType(TypeDecorator):
    impl = String
    cache_ok = True # SQLAlchemy knows this type is safe for caching

    def process_bind_param(self, value, dialect):
        # Python → DB
        if value is None:
            return None
        return value.value  # convert NIP → str

    def process_result_value(self, value, dialect):
        # DB → Python
        if value is None:
            return None
        return model.NIP(value)  # convert str → NIP

# SalesRep - Simple reference table
sales_reps = Table(
    'sales_reps', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('reference', String(20), unique=True, index=True),
    Column('name', String(255)),
    Column('email', String(255)),

    UniqueConstraint("reference", name="uq_salesrep_reference")
)

# Company - Aggregate root table
companies = Table(
    'companies', metadata,
    # nip = PRIMARY KEY (matches Company.nip identity)
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column('nip', NIPType(), nullable=False),
    # name = direct from constructor
    Column('name', String(255), nullable=False),
    # ltd = from constructor
    Column('ltd', Date, nullable=True),
    # address = 4 separate columns (matches Address dataclass)
    Column('street', String(255), nullable=False),
    Column('building_nr', String(20), nullable=False),
    Column('postal_code', String(10), nullable=False),
    Column('city', String(100), nullable=False),
    # ZK embedded (7 columns)
    Column('last_zk_nip', String(20), nullable=True),
    Column('last_zk_name', String(255), nullable=True),
    Column('last_zk_street', String(255), nullable=True),
    Column('last_zk_building_nr', String(20), nullable=True),
    Column('last_zk_postal_code', String(10), nullable=True),
    Column('last_zk_city', String(100), nullable=True),
    Column('last_zk_transaction_date', Date, nullable=True),
    Column('last_zk_rep_name', String(255), nullable=True),
    # version = manual optimistic locking
    Column('version', Integer, nullable=False, default=0),
    # lookup index
    Index(
        "ix_company_lookup",
        "nip",
        "postal_code",
        "city",
        "street",
        "building_nr",
    ),
    # unique record guarantee    POD TO TEST???
    UniqueConstraint(
        "nip",
        "street",
        "building_nr",
        "postal_code",
        "city",
        name="uq_company_address",
    )
)
# MAGIC: session.commit() does this:
# UPDATE companies SET current_rep=?, version=version+1
# WHERE nip=? AND version=<expected>

company_assignments = Table(
    'company_assignments', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('company_id', ForeignKey('companies.id')),
    Column('rep_id', ForeignKey('sales_reps.id')),
)

def start_mappers():
    # 1. Map SalesRep
    rep_mapper = mapper_registry.map_imperatively(model.SalesRep, sales_reps)

    # 2. Map Company WITH relationship (minimal)
    mapper_registry.map_imperatively(
        model.Company,
         companies,
         properties={
                        '_current_rep': relationship(
                            rep_mapper,  # Target mapper
                            secondary=company_assignments, # Intermediary table
                            uselist=False, # 1:1
                            lazy='select' # Load on access
    ),
                         'address': composite(
                             model.Address,
                             companies.c.street,
                             companies.c.building_nr,
                             companies.c.postal_code,
                             companies.c.city,
    ),
                         'last_zk': composite(
                             model.ZK.as_composite,
                             companies.c.last_zk_nip,
                             companies.c.last_zk_name,
                             companies.c.last_zk_street,
                             companies.c.last_zk_building_nr,
                             companies.c.last_zk_postal_code,
                             companies.c.last_zk_city,
                             companies.c.last_zk_transaction_date,
                             companies.c.last_zk_rep_name,
                         )
    },
    )

@event.listens_for(model.Company, 'load')
def receive_load(company, _):
    company.events = []
