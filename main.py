from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
from conexion import SQLServerConnector  # tu clase actual
import pandas as pd

app = FastAPI()
db = SQLServerConnector()
# 2. Define los orígenes permitidos (la dirección de tu frontend)
origins = [
    "http://localhost:5173",
]

# 3. Añade el middleware a tu aplicación FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permite todos los encabezados
)

@app.get("/paciente")
def ejecutar_consulta(ndoc: str):
    try:
        query = f"""
            SELECT DISTINCT TOP 10  
                T.Abrev_Tipo_Doc,
                P.Numero_Documento, 
                Fecha_Nacimiento, 
                P.Genero, 
                DATEDIFF(YEAR, Fecha_Nacimiento, GETDATE()) AS EDAD 
            FROM MAESTRO_PACIENTE P
            INNER JOIN MAESTRO_HIS_TIPO_DOC T 
                ON T.Id_Tipo_Documento = P.Id_Tipo_Documento
            WHERE P.Numero_Documento = '{ndoc}'
        """
        resultado = db.ejecutar_sql(query)
        return {"result": [dict(row._mapping) for row in resultado]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/atenciones")
def ejecutar_comando(anio: int, ndoc: str):
    try:
        query = f"""
        SELECT TOP 100
            h.Id_Cita,
            h.Fecha_Atencion AS FECHA_ATENCION,
            h.Tipo_Diagnostico AS T_DIAG,
            h.Codigo_Item,
            c.Descripcion_Item,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 1 THEN h.Valor_Lab END), '') AS LAB1,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 2 THEN h.Valor_Lab END), '') AS LAB2,
            ISNULL(MAX(CASE WHEN h.Id_Correlativo_Lab = 3 THEN h.Valor_Lab END), '') AS LAB3,
            h.Fecha_Registro AS F_REGISTRO,
            h.Fecha_Modificacion AS F_MODIFICACION,
            r.est_nombre AS ESTABLECIMIENTO,
            r.DESC_DIST AS DISTRITO,
            r.DESC_PROV AS POVINCIA
        FROM DBGERESA.dbo.HISMINSA h
        INNER JOIN DBGERESA.dbo.MAESTRO_PACIENTE p
            ON p.Id_Paciente = h.Id_Paciente
        INNER JOIN DBGERESA.dbo.RENIPRESS r
            ON r.COD_ESTAB = h.renipress
        INNER JOIN DBGERESA.dbo.MAESTRO_HIS_CIE_CPMS c
            ON c.Codigo_Item = h.Codigo_Item
        WHERE p.Numero_Documento = '{ndoc}'
          AND h.Anio = {anio}
        GROUP BY
            h.Id_Cita,
            h.Fecha_Atencion,
            h.Tipo_Diagnostico,
            h.Codigo_Item,
            c.Descripcion_Item,
            h.Fecha_Registro,
            h.Fecha_Modificacion,
            r.est_nombre,
            r.DESC_DIST,
            r.DESC_PROV
        ORDER BY h.Fecha_Atencion DESC
        """
        resultado = db.ejecutar_sql(query)
        return {"result": [dict(row._mapping) for row in resultado]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



