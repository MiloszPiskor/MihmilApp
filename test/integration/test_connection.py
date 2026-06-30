from infrastructure import subiekt_gateway
from logging_config import get_logger
import pyodbc

logger = get_logger(__name__)

# def get_subiekt_connection():
#     """
#     Połączenie z lokalnym kontenerem Docker MSSQL z restauracją .bak Subiekta.
#     """
#     try:
#         conn = pyodbc.connect(
#             "DRIVER={ODBC Driver 18 for SQL Server};"
#             "SERVER=localhost,1433;"
#             "DATABASE=PREXPOL_Test;"  # ← Twoja baza z backupem
#             "UID=sa;"
#             "PWD=Ussworp7raiker!;"
#             "Encrypt=no;"
#             "TrustServerCertificate=yes;"
#         )
#         logger.info("✅ Połączenie z Subiekt GT nawiązane (localhost,1433)")
#         return conn
#     except pyodbc.Error as e:
#         logger.error(f"❌ Błąd połączenia z Subiekt GT: {e}")
#         raise


def test_subiekt_connection():
    """Test połączenia z bazą Subiekt GT."""
    logger.info("Testowanie połączenia z Subiekt GT...")

    conn = subiekt_gateway.get_subiekt_connection()
    assert conn is not None

    cursor = conn.cursor()
    cursor.execute("SELECT TOP 10 name FROM sys.databases")
    databases = cursor.fetchall()

    logger.info(f"✅ Połączenie udane. Dostępne bazy: {[d.name for d in databases[:5]]}")

    conn.close()
    logger.info("Połączenie zamknięte")
