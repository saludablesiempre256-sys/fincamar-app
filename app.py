import streamlit as st
import sqlite3
import re
from datetime import datetime
from io import BytesIO

# Importaciones de PDF y Excel
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import openpyxl

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
    
    # Carga Inicial por defecto
    lotes_def = [("Lote 1", 2.0), ("Palacio Grande", 3.0), ("Palacio Chico", 2.0), ("Eduardo", 2.5), ("Cable Bomba", 3.0), ("El Coral", 2.5), ("Mandarina", 2.0), ("La Patera", 2.5), ("Cambursillo", 2.0), ("Carretero", 2.5), ("Las Tecas", 1.0), ("Los Cubos", 3.5), ("El Mango", 2.5), ("Manuel", 2.0), ("La Isla", 3.0), ("Europea", 12.0)]
    c.executemany("INSERT OR IGNORE INTO lotes (nombre, ha) VALUES (?, ?)", lotes_def)
    
    act_def = [("Deshierbe / Corte de Monte",), ("Cosecha de Cacao",), ("Poda",), ("Fumigación / Aplicación de Insumos",), ("Mantenimiento de Riego",)]
    c.executemany("INSERT OR IGNORE INTO actividades (nombre) VALUES (?)", act_def)
    
    conn.commit()
    conn.close()

iniciar_db()

st.title("🌾 SISTEMA INTEGRAL FINCAMAR (v10.0)")
st.caption("Control Operacional, Cosecha y Nómina de Cacao")

# NAVEGACIÓN COMPLETA (Menú Pydroid 3)
opcion = st.sidebar.selectbox("Selecciona una opción del menú", [
    "1. ⚡ Carga Automática / Registro Manual",
    "2. 📋 Ver Historial de Reportes",
    "3. 📦 Control e Inventario de Insumos",
    "4. 👥 Gestionar Personal",
    "5. ⚙️ Gestionar Actividades",
    "6. 🗺️ Gestionar Lotes",
    "7. 📄 Generar Reporte Diario en PDF",
    "8. 📝 Generar Nómina de Asistencia en PDF",
    "9. 📊 Exportar Respaldo a Excel"
])

# 1. REGISTRO Y CARGA AUTOMÁTICA (Acepta desde marzo a la fecha)
if opcion == "1. ⚡ Carga Automática / Registro Manual":
    st.header("⚡ Registrar Reporte Diario")
    
    modo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"])
    
    if modo == "Pegar Texto Automático":
        texto_reporte = st.text_area("Pega aquí el mensaje de WhatsApp / Finca (acepta cualquier fecha):", height=150)
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
                st.success(f"✅ Reporte guardado exitosamente para la fecha: {fecha}")
            else:
                st.warning("Por favor ingresa un texto.")
                
    else:
        with st.form("form_manual"):
            fecha_manual = st.date_input("Fecha del Reporte", datetime.now())
            cosecha_ha = st.number_input("Hectáreas Cosechadas", min_value=0.0, step=0.5)
            sacos = st.number_input("Sacos Completos", min_value=0, step=1)
            libras = st.number_input("Libras Extra", min_value=0.0, step=0.5)
            corte_ha = st.number_input("Corte de Monte (ha)", min_value=0.0, step=0.5)
            personal = st.number_input("Personal Activo", min_value=0, step=1)
            obs = st.text_area("Observaciones")
            
            if st.form_submit_button("Guardar Registro Manual"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("""INSERT OR REPLACE INTO reportes_diarios 
                             (fecha, cosecha_ha, sacos_completos, libras_extra, corte_monte_ha, personal_activo, observaciones)
                             VALUES (?, ?, ?, ?, ?, ?, ?)""", 
                          (str(fecha_manual), cosecha_ha, sacos, libras, corte_ha, personal, obs))
                conn.commit()
                conn.close()
                st.success(f"✅ Reporte guardado para la fecha {fecha_manual}")

# 2. HISTORIAL
elif opcion == "2. 📋 Ver Historial de Reportes":
    st.header("📋 Historial Completo de Reportes")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT fecha, cosecha_ha, sacos_completos, libras_extra, corte_monte_ha, personal_activo, observaciones FROM reportes_diarios ORDER BY fecha DESC")
    datos = c.fetchall()
    conn.close()
    
    if datos:
        for d in datos:
            with st.expander(f"📅 Fecha: {d[0]} — Cosecha: {d[2]} Sacos + {d[3]} lbs"):
                st.write(f"**Hectáreas Cosechadas:** {d[1]} ha")
                st.write(f"**Corte de Monte:** {d[4]} ha")
                st.write(f"**Personal Activo:** {d[5]} trabajadores")
                st.write(f"**Detalle / Novedades:** {d[6]}")
    else:
        st.info("No hay reportes registrados aún.")

# 5. GESTIONAR ACTIVIDADES (NUEVO)
elif opcion == "5. ⚙️ Gestionar Actividades":
    st.header("⚙️ Gestión de Actividades")
    
    nueva_act = st.text_input("Nombre de la nueva actividad:")
    if st.button("Agregar Actividad"):
        if nueva_act:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO actividades (nombre) VALUES (?)", (nueva_act.strip(),))
                conn.commit()
                st.success(f"Actividad '{nueva_act}' agregada con éxito.")
            except:
                st.error("Esta actividad ya existe.")
            conn.close()
            
    st.subheader("Lista de Actividades Registradas:")
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM actividades")
    acts = c.fetchall()
    conn.close()
    for a in acts:
        st.write(f"• {a[1]}")

# 7. GENERAR REPORTE DIARIO EN PDF (NUEVO)
elif opcion == "7. 📄 Generar Reporte Diario en PDF":
    st.header("📄 Exportar Reporte Diario a PDF")
    fecha_pdf = st.date_input("Selecciona la fecha a exportar:", datetime.now())
    
    if st.button("Generar PDF"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM reportes_diarios WHERE fecha=?", (str(fecha_pdf),))
        rep = c.fetchone()
        conn.close()
        
        if rep:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []
            
            elements.append(Paragraph(f"<b>FINCAMAR - Reporte Diario del {fecha_pdf}</b>", styles['Title']))
            elements.append(Spacer(1, 12))
            
            data = [
                ["Concepto", "Valor"],
                ["Hectáreas Cosechadas", f"{rep[2]} ha"],
                ["Sacos Completos", f"{rep[3]}"],
                ["Libras Extra", f"{rep[4]} lbs"],
                ["Corte de Monte", f"{rep[5]} ha"],
                ["Personal Activo", f"{rep[6]} personas"]
            ]
            t = Table(data)
            t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.green),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                   ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            elements.append(t)
            elements.append(Spacer(1, 12))
            elements.append(Paragraph(f"<b>Observaciones:</b> {rep[7]}", styles['Normal']))
            
            doc.build(elements)
            st.download_button(label="📥 Descargar PDF", data=buffer.getvalue(), file_name=f"Reporte_FINCAMAR_{fecha_pdf}.pdf", mime="application/pdf")
        else:
            st.error("No existen registros para esa fecha.")

# 8. GENERAR NÓMINA EN PDF (NUEVO)
elif opcion == "8. 📝 Generar Nómina de Asistencia en PDF":
    st.header("📝 Reporte de Nómina de Asistencia")
    st.info("Genera el reporte consolidado de asistencia de trabajadores.")
    
    if st.button("Generar Documento de Nómina PDF"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        elements.append(Paragraph("<b>FINCAMAR - Control de Nómina y Asistencia</b>", styles['Title']))
        elements.append(Spacer(1, 15))
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT nombre, cargo FROM personal")
        personal_list = c.fetchall()
        conn.close()
        
        data = [["Trabajador", "Cargo", "Estado"]]
        for p in personal_list:
            data.append([p[0], p[1], "Activo"])
            
        t = Table(data)
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.darkblue),
                               ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                               ('GRID', (0,0), (-1,-1), 1, colors.black)]))
        elements.append(t)
        doc.build(elements)
        
        st.download_button(label="📥 Descargar Nómina PDF", data=buffer.getvalue(), file_name="Nomina_Asistencia_FINCAMAR.pdf", mime="application/pdf")            
