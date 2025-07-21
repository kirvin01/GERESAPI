# %%
from decouple import config
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import urllib
import pandas as pd


class SQLServerConnector:
    def __init__(self):
        
        self.server = config('DB_HOST')
        self.username = config('DB_USER')
        self.password = config('DB_PASSWORD')
        self.database = config('DB_DATABASE')
        self.port = config('DB_PORT')
        self.driver = 'ODBC Driver 17 for SQL Server'
        self.engine = None
        
        

        self.connect()

    def connect(self):
        try:
            params = urllib.parse.quote_plus(
                f"DRIVER={self.driver};"
                f"SERVER={self.server},{self.port};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"TrustServerCertificate=yes"
            )

            conn_str = f"mssql+pyodbc:///?odbc_connect={params}"
            self.engine = create_engine(conn_str, fast_executemany=True)

            with self.engine.connect() as conn:
                print("✅ Conexión exitosa a SQL Server " + config('DB_DATABASE'))

        except SQLAlchemyError as e:
            print("❌ Error al conectar a SQL Server:")
            print(e)

    def insertar_dataframe(self, df: pd.DataFrame, nombre_tabla: str, if_exists='append', dtype=None):
        try:
            df.to_sql(nombre_tabla, self.engine, if_exists=if_exists, index=False, dtype=dtype)
            print(f"✅ DataFrame insertado correctamente en '{nombre_tabla}'")
        except Exception as e:
            print(f"❌ Error al insertar el DataFrame: {e}")
  
    def ejecutar_sql(self, query, retornar_datos=True):
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                if retornar_datos:
                    try:
                        return result.fetchall()
                    except Exception:
                        return []
                else:
                    return result.rowcount  # útil para INSERT, UPDATE, DELETE
        except Exception as e:
            print(f"❌ Error al ejecutar la consulta: {e}")
            return None



