# main.py

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Connection
from typing import Dict, Any
from decouple import config, Csv

# Importa el motor, no la clase
from conexion import engine

app = FastAPI(
    title=config('APP_TITLE', default='GERESAPI'),
    description=config('APP_DESCRIPTION', default='API para consultas a la base de datos de GERESA.'),
    version=config('APP_VERSION', default='1.0.0')
)

# Configuración de CORS
origins = config('CORS_ORIGINS', default='http://localhost:5173', cast=Csv())

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependencia para la Conexión a la BD ---
def get_db_connection():
  
    if engine is None:
        raise HTTPException(status_code=503, detail="La conexión con la base de datos no está disponible.")
    
    try:
        conn = engine.connect()
        yield conn
    finally:
        if conn:
            conn.close()

# --- Endpoints Optimizados ---

@app.get("/paciente", summary="Obtener datos básicos del paciente")
def get_paciente(ndoc: str, db: Connection = Depends(get_db_connection)):
  
    query = text("""
        SELECT DISTINCT TOP 10  
            T.Abrev_Tipo_Doc,
            P.Numero_Documento, 
            P.Fecha_Nacimiento, 
            P.Genero, 
            DATEDIFF(YEAR, P.Fecha_Nacimiento, GETDATE()) AS EDAD 
        FROM MAESTRO_PACIENTE AS P
        INNER JOIN MAESTRO_HIS_TIPO_DOC AS T ON T.Id_Tipo_Documento = P.Id_Tipo_Documento
        WHERE P.Numero_Documento = :ndoc
    """)
    try:
        result = db.execute(query, {"ndoc": ndoc}).fetchall()
        return {"result": [dict(row._mapping) for row in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {e}")
    
    

@app.get("/atenciones", summary="Obtener atenciones por año y documento")
def get_atenciones(anio: int, ndoc: str, db: Connection = Depends(get_db_connection), offset: int = 0, per_page: int = 500):
    try:
        query = text("""
        SELECT
            ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS N,
            h.Id_Cita, FORMAT(h.Fecha_Atencion, 'dd-MM-yyyy') AS F_ATENCION,
            CONCAT(h.Tipo_Diagnostico,' | ',h.Codigo_Item) AS Codigo_Item,
            c.Descripcion_Item,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 1 THEN h.Valor_Lab END), '') AS LAB1,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 2 THEN h.Valor_Lab END), '') AS LAB2,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 3 THEN h.Valor_Lab END), '') AS LAB3,
            FORMAT(h.Fecha_Registro, 'dd-MM-yyyy HH:mm:ss') AS F_REGISTRO, FORMAT(h.Fecha_Modificacion, 'dd-MM-yyyy HH:mm:ss') AS F_MODIFICACION,            
            r.est_nombre AS ESTABLECIMIENTO,
            CONCAT(r.DESC_DIST,' | ', r.DESC_PROV) AS [DISTRITO | PROVINCIA],
            S.Descripcion_Sistema AS SISTEMA,
            LTRIM(RTRIM(
                COALESCE(re.Nombres_Registrador,'') + ' ' +
                COALESCE(re.Apellido_Paterno_Registrador,'') + ' ' +
                COALESCE(re.Apellido_Materno_Registrador,'')
            )) AS REGISTRADOR
        FROM DBGERESA.dbo.HISMINSA h
        INNER JOIN DBGERESA.dbo.MAESTRO_PACIENTE p ON p.Id_Paciente = h.Id_Paciente
        INNER JOIN DBGERESA.dbo.RENIPRESS r ON r.COD_ESTAB = h.renipress
        LEFT JOIN DBGERESA.dbo.MAESTRO_HIS_CIE_CPMS c ON c.Codigo_Item = h.Codigo_Item
        LEFT JOIN DBGERESA.dbo.MAESTRO_HIS_SISTEMA S ON S.Id_Sistema = H.Id_AplicacionOrigen
        LEFT JOIN DBGERESA.dbo.MAESTRO_REGISTRADOR re ON re.Id_Registrador = h.Id_Registrador
        WHERE p.Numero_Documento = :ndoc AND h.Anio = :anio
        GROUP BY
            h.Id_Cita, h.Fecha_Atencion, h.Tipo_Diagnostico, h.Codigo_Item, c.Descripcion_Item,
            h.Fecha_Registro, h.Fecha_Modificacion, S.Descripcion_Sistema, r.est_nombre,
            r.DESC_DIST, r.DESC_PROV, re.Nombres_Registrador,
            re.Apellido_Paterno_Registrador, re.Apellido_Materno_Registrador
        ORDER BY h.Fecha_Atencion DESC
        OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY;
        """)
        params = {"ndoc": ndoc, "anio": anio, "offset": offset, "per_page": per_page}
        resultado = db.execute(query, params).fetchall()       
        return {"result": [dict(row._mapping) for row in resultado]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
       


