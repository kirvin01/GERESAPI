# main.py

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.engine import Connection
from typing import Dict, Any
from decouple import config, Csv
from fastapi.responses import StreamingResponse
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from datetime import datetime

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
       


@app.get("/certificado/", summary="Generar un certificado en PDF")
def generar_certificado(
    nombre: str = Query(..., description="Nombre completo de la persona"),
    calidad: str = Query(..., description="Calidad en la que se otorga el certificado (ej. Ponente, Asistente)"),
    fecha: str = Query(..., description="Fecha del evento o certificado"),
    folio: str = Query(..., description="Folio del certificado"),
    numero: str = Query(..., description="Número o código del certificado")
):
    try:
        template_path = "Plantillas/certificado.pdf"
        template_pdf_reader = PdfReader(template_path)

        if len(template_pdf_reader.pages) < 2:
            raise HTTPException(status_code=400, detail="La plantilla del certificado debe tener al menos 2 páginas.")

        output = PdfWriter()

        # --- PÁGINA 1: Nombre, Calidad, Fecha ---
        packet1 = io.BytesIO()
        page1_template = template_pdf_reader.pages[0]
        page1_width = float(page1_template.mediabox.width)
        page1_height = float(page1_template.mediabox.height)
        
        can1 = canvas.Canvas(packet1, pagesize=(page1_width, page1_height))
        
        # --- Ejemplo de personalización para el NOMBRE ---
        can1.setFont("Helvetica-Bold", 22)  # Fuente Negrita, Tamaño 24
        can1.setFillColor(colors.darkblue) # Color azul oscuro
        can1.drawString(250, 340, nombre)

        can1.setFont("Helvetica-Bold", 16)  # Fuente Negrita, Tamaño 24
        can1.setFillColor(colors.black) # Color azul oscuro        
        can1.drawString(130, 300,f"{calidad}:")

        # --- Restaurar a valores por defecto para los siguientes textos ---
        can1.setFont("Helvetica-Bold", 12) # Fuente normal, Tamaño 12
        can1.setFillColor(colors.black) # Color negro

        fecha_obj = datetime.strptime(fecha, "%d-%m-%Y")
        meses = {
            1: "enero",
            2: "febrero",
            3: "marzo",
            4: "abril",
            5: "mayo",
            6: "junio",
            7: "julio",
            8: "agosto",
            9: "septiembre",
            10: "octubre",
            11: "noviembre",
            12: "diciembre"
        }

        can1.drawString(600, 105, f"Cusco, {fecha_obj.day} de {meses[fecha_obj.month]} {fecha_obj.year}")
        
        can1.save()
        packet1.seek(0)
        
        overlay_pdf1 = PdfReader(packet1)
        page1_template.merge_page(overlay_pdf1.pages[0])
        output.add_page(page1_template)

        # --- PÁGINA 2: Folio, Numero ---
        packet2 = io.BytesIO()
        page2_template = template_pdf_reader.pages[1]
        page2_width = float(page2_template.mediabox.width)
        page2_height = float(page2_template.mediabox.height)

        can2 = canvas.Canvas(packet2, pagesize=(page2_width, page2_height))

        # --- Ejemplo de personalización para Folio y Número ---
        can2.setFont("Courier-Oblique", 10) # Fuente Cursiva, Tamaño 10
        can2.setFillColor(colors.black) # Color gris
        
        can2.drawString(290, 465, folio)
        can2.drawString(105, 465, numero)
        can2.drawString(120, 410, fecha)
        
        can2.save()
        packet2.seek(0)

        overlay_pdf2 = PdfReader(packet2)
        page2_template.merge_page(overlay_pdf2.pages[0])
        output.add_page(page2_template)

        # Añadir el resto de las páginas de la plantilla si existen
        for i in range(2, len(template_pdf_reader.pages)):
            output.add_page(template_pdf_reader.pages[i])

        # --- Guardar y devolver el PDF final ---
        output_stream = io.BytesIO()
        output.write(output_stream)
        output_stream.seek(0)
        
        return StreamingResponse(
            output_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=certificado_{calidad}_{numero}.pdf"}#inline attachment
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No se encontró la plantilla del certificado en '{template_path}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar el PDF: {e}")
    #http://127.0.0.1:8000/certificado/?nombre=Juan%20Perez&calidad=Asistente&fecha=13-10-2025&folio=A-001&numero=12345

