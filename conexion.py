# conexion.py

from decouple import config
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import urllib

def create_db_engine():
   
    try:
        server = config('DB_HOST')
        username = config('DB_USER')
        password = config('DB_PASSWORD')
        database = config('DB_DATABASE')
        port = config('DB_PORT')
        driver = 'ODBC Driver 17 for SQL Server'

        params = urllib.parse.quote_plus(
            f"DRIVER={{{driver}}};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes"
        )

        conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
        engine = create_engine(conn_str, fast_executemany=True)

        # Probar la conexión una vez al inicio
        with engine.connect() as conn:
            print(f"✅ Conexión inicial exitosa a la base de datos '{database}'")
        
        return engine

    except SQLAlchemyError as e:
        print("❌ Error fatal al crear el motor de base de datos:")
        print(e)
        return None

# Se crea una única instancia del motor cuando la aplicación se inicia
engine = create_db_engine()