import streamlit as st
import sqlite3
import os
import shutil
import re
from datetime import datetime
from PIL import Image

# Importaciones de PDF y Excel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing, Rect, String
import openpyxl

# Configuración de la página Web
st.set_page_config(page_title="FINCAMAR", page_icon="🌾", layout="centered")

DB_NAME = "fincamar_control.db"

def iniciar_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, ha REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS personal (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, cargo TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS actividades (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS insumos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, unidad TEXT, stock REAL DEFAULT 0.0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS mov_insumos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, insumo_id INTEGER, tipo TEXT, cantidad REAL, observacion TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS reportes_diarios (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT UNIQUE, cosecha_ha REAL, sacos_completos INTEGER, libras_extra REAL, corte_monte_ha REAL, personal_activo INTEGER, observaciones TEXT)""")
    
    # Carga Inicial de Lotes
    lotes_def = [("Lote 1", 2.0), ("Palacio Grande", 3.0), ("Palacio Chico", 2.0), ("Eduardo", 2.5), ("Cable Bomba", 3.0), ("El Coral", 2.5), ("Mandarina", 2.0), ("La Patera", 2.5), ("Cambursillo", 2.0), ("Carretero", 2.5), ("Las Tecas", 1.0), ("Los Cubos", 3.5), ("El Mango", 2.5), ("Manuel", 2.0), ("La Isla", 3.0), ("Europea", 12.0)]
    c.executemany("INSERT OR IGNORE INTO lotes (nombre, ha) VALUES (?, ?)", lotes_def)
    conn.commit()
    conn.close()

iniciar_db()

# TÍTULO E ICONO PRINCIPAL
st.title("🌾 SISTEMA INTEGRAL FINCAMAR")
st.caption("Control Operacional y Cosecha de Cacao")

# NAVEGACIÓN TIPO MENÚ
opcion = st.sidebar.selectbox("Selecciona una opción", [
    "⚡ Carga Automática (Pegar Texto)",
    "📝 Registrar Reporte Manual",
    "📋 Ver Historial de Reportes",
    "📦 Control e Inventario de Insumos",
    "👥 Gestionar Personal",
    "🗺️ Gestionar Lotes",
    "📊 Exportar a Excel"
])

# 1. CARGA AUTOMÁTICA
if opcion == "⚡ Carga Automática (Pegar Texto)":
    st.header("⚡ Cargar Reporte Pegando Texto")
    texto_reporte = st.text_area("Pega aquí el mensaje del reporte diario:", height=150)
    
    if st.button("Procesar y Guardar Reporte"):
        if texto_reporte:
            fecha_match = re.search(r'(\d{2}[-/\.]\d{2}[-/\.]\d{4})', texto_reporte)
            fecha = datetime.strptime(fecha_match.group(1).replace("/", "-"), "%d-%m-%Y").strftime("%Y-%m-%d") if fecha_match else datetime.now().strftime("%Y-%m-%d")
            
            sacos_match = re.search(r'Total de sacos completos\s+(\d+)', texto_reporte, re.I)
            sacos = int(sacos_match.group(1)) if sacos_match else 0
            
            lbs_match = re.search(r'total\s+(\d+[\.,]?\d*)\s*libras', texto_reporte, re.I)
            lbs = float(lbs_match.group(1).replace(",", ".")) if lbs_match else 0.0

            pers_match = re.search(r'Se trabaj[oó] con\s+(\d+)\s+personas', texto_reporte, re.I)
            personal = int(pers_match.group(1)) if pers_match else 0

            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("""INSERT OR REPLACE INTO reportes_diarios 
                         (fecha, cosecha_ha, sacos_completos, libras_extra, corte_monte_ha, personal_activo, observaciones)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                      (fecha, 2.5, sacos, lbs, 1.5, personal, texto_reporte))
            conn.commit()
            conn.close()
            st.success(f"✅ ¡Reporte del {fecha} guardado exitosamente!")
        else:
            st.warning("Por favor pega un texto antes de procesar.")

# 2. VER HISTORIAL
elif opcion == "📋 Ver Historial de Reportes":
    st.header("📋 Historial de Cosecha")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT fecha, cosecha_ha, sacos_completos, libras_extra, corte_monte_ha, personal_activo, observaciones FROM reportes_diarios ORDER BY fecha DESC")
    datos = c.fetchall()
    conn.close()
    
    for d in datos:
        with st.expander(f"📅 Fecha: {d[0]} - {d[2]} Sacos + {d[3]} lbs"):
            st.write(f"**Hectáreas Cosechadas:** {d[1]} ha")
            st.write(f"**Corte de Monte:** {d[4]} ha")
            st.write(f"**Personal Activo:** {d[5]} trabajadores")
            st.write(f"**Novedades:** {d[6]}")
