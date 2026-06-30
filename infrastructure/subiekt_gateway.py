import pyodbc  # pip install pyodbc
from logging_config import get_logger

"""
External DB connector
"""
logger = get_logger(__name__)

def get_subiekt_connection():
    """
    Połączenie z lokalnym kontenerem Docker MSSQL z restauracją .bak Subiekta.
    """
    try:
        conn = pyodbc.connect(
            "DRIVER={ODBC Driver 18 for SQL Server};"
            "SERVER=127.0.0.1,1433;"
            "DATABASE=PREXPOL_Test;"  # ← Twoja baza z backupem
            "UID=sa;"
            "PWD=Ussworp7raiker!;"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )
        logger.info("✅ Połączenie z Subiekt GT nawiązane (localhost,1433)")
        return conn
    except pyodbc.Error as e:
        logger.error(f"❌ Błąd połączenia z Subiekt GT: {e}")
        raise
