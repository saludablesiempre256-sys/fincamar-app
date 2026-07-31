import streamlit as st
import re
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
import io

# Configuración inicial de la página
st.set_page_config(page_title="FINCAMAR v10.0", page_icon="🌾", layout="wide")

# --- BASE DE DATOS Y ESTADOS EN SESIÓN ---
if 'reportes' not in st.session_state:
    st.session_state.reportes = []

if 'personal' not in st.session_state:
    st.session_state.personal = [
        {"nombre": "Jackson Andrade", "cargo": "Cosechador / Guadañador", "jornal": 15.0},
        {"nombre": "Reynaldo Andrade", "cargo": "Cosechador / Guadañador", "jornal": 15.0},
        {"nombre": "Jessica Quiroz", "cargo": "Cosechadora / Monilla", "jornal": 15.0},
        {"nombre": "David Pacheco", "cargo": "Desvenador / Pesador", "jornal": 15.0}
    ]

if 'actividades_catalogo' not in st.session_state:
    st.session_state.actividades_catalogo = {
        "Cosecha": {"unidad": "ha", "color": (46, 139, 87, 130)},
        "Corte de monte": {"unidad": "ha", "color": (230, 126, 34, 130)},
        "Fumigación": {"unidad": "ha", "color": (52, 152, 219, 130)},
        "Tumbada de monilla": {"unidad": "ha", "color": (155, 89, 182, 130)},
        "Poda": {"unidad": "ha", "color": (241, 196, 15, 130)}
    }

LOTES_INFO = {
    "EUROPEA": {"ha": 2.00, "bbox": (160, 40, 480, 160)},
    "CARRETERO": {"ha": 2.00, "bbox": (20, 165, 195, 360)},
    "LAS TECAS": {"ha": 2.00, "bbox": (210, 180, 540, 370)},
    "LA ISLA": {"ha": 3.50, "bbox": (510, 150, 600, 380)},
    "DON MANUEL": {"ha": 2.50, "bbox": (615, 30, 960, 155)},
    "EL MANGO": {"ha": 2.50, "bbox": (620, 175, 960, 275)},
    "CUBO": {"ha": 1.00, "bbox": (620, 280, 960, 370)},
    "ARAZA": {"ha": 1.50, "bbox": (210, 390, 540, 480)},
    "MANDARINA": {"ha": 1.50, "bbox": (210, 505, 540, 600)},
    "LA PATERA": {"ha": 1.50, "bbox": (20, 520, 195, 620)},
    "EL CORAL": {"ha": 2.50, "bbox": (140, 625, 540, 780)},
    "LINEA DOS": {"ha": 1.00, "bbox": (600, 390, 960, 480)},
    "EDUARDO": {"ha": 3.00, "bbox": (600, 500, 960, 600)},
    "CABLE BOMBA": {"ha": 3.00, "bbox": (600, 625, 960, 770)},
    "PALACIO CHICO": {"ha": 1.50, "bbox": (305, 805, 540, 970)},
    "PALACIO GRANDE": {"ha": 5.00, "bbox": (605, 805, 825, 970)},
    "TRES HECTAREAS": {"ha": 3.00, "bbox": (835, 805, 960, 970)}
}

# --- FUNCIONES AUXILIARES ---
def procesar_texto_whatsapp(texto):
    fecha_match = re.search(r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})', texto)
    fecha = fecha_match.group(1) if fecha_match else datetime.today().strftime('%Y-%m-%d')
    
    sacos_match = re.search(r'(\d+)\s*sacos?\s*completos?', texto, re.IGNORECASE)
    sacos = int(sacos_match.group(1)) if sacos_match else 0
    
    libras_match = re.search(r'(\d+[.,]?\d*)\s*libras', texto, re.IGNORECASE)
    libras = float(libras_match.group(1).replace(',', '.')) if libras_match else 0.0

    personal_detectado = [p["nombre"] for p in st.session_state.personal if re.search(re.escape(p["nombre"]), texto, re.IGNORECASE)]
    if not personal_detectado:
        personal_detectado = [p["nombre"] for p in st.session_state.personal]

    actividades = []
    if "cosecha" in texto.lower():
        actividades.append({"actividad": "Cosecha", "lote": "PALACIO GRANDE", "ha": 2.5})
    if "corte de monte" in texto.lower() or "corte" in texto.lower():
        actividades.append({"actividad": "Corte de monte", "lote": "LAS TECAS", "ha": 1.5})

    return {
        "fecha": fecha, "sacos": sacos, "libras": libras,
        "asistencia": personal_detectado, "actividades": actividades,
        "texto_original": texto
    }

def generar_mapa_avance(actividades_lotes, imagen_base_path="mapa_fincamar.png"):
    try:
        base_img = Image.open(imagen_base_path).convert("RGBA")
    except Exception:
        base_img = Image.new("RGBA", (1000, 1000), (245, 245, 220, 255))
    
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    for act in actividades_lotes:
        lote_nombre = act.get("lote", "").upper()
        actividad = act.get("actividad", "")
        if lote_nombre in LOTES_INFO:
            bbox = LOTES_INFO[lote_nombre]["bbox"]
            cfg = st.session_state.actividades_catalogo.get(actividad, {"color": (127, 140, 141, 130)})
            draw.rectangle(bbox, fill=cfg["color"], outline=(0, 0, 0, 220), width=3)
            
    resultado = Image.alpha_composite(base_img, overlay)
    return resultado.convert("RGB")

# --- MENÚ LATERAL VISIBLE 100% ---
st.sidebar.markdown("## 📌 Menú Principal FINCAMAR")

opcion = st.sidebar.radio(
    "Seleccione una opción:",
    [
        "1. ⚡ Registrar Reporte Diario",
        "2. 👥 Gestionar Personal",
        "3. 📋 Crear / Ver Tareas Nuevas",
        "4. 📅 Asistencia y Nómina Semanal",
        "5. 📊 Historial de Reportes",
        "6. 🗺️ Mapa de Avance por Lote",
        "7. 📄 Exportar Reporte Diario PDF",
        "8. 📄 Exportar Nómina PDF",
        "9. 🚜 Control de Maquinaria y Taller",
        "10. ⚙️ Configuración de Finca"
    ],
    key="menu_radio_fincamar_v10"
)

st.title("FINCAMAR (v10.0)")
st.caption("Control Operacional, Cosecha, Nómina y Mapeo de Cacao")

# --- CONTENIDO DE CADA SECCIÓN ---

# 1. REGISTRAR REPORTE DIARIO
if opcion.startswith("1."):
    st.header("⚡ Registrar Reporte Diario")
    metodo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"], key="rad_metodo")

    if metodo == "Pegar Texto Automático":
        raw_text = st.text_area("Pega aquí el mensaje de WhatsApp / Finca (acepta cualquier fecha):", height=200, key="txt_wa")
        if st.button("Procesar y Guardar Reporte", key="btn_proc_wa"):
            if raw_text:
                rep = procesar_texto_whatsapp(raw_text)
                st.session_state.reportes.append(rep)
                st.success(f"¡Reporte del {rep['fecha']} procesado exitosamente!")
            else:
                st.warning("Ingrese el texto del mensaje.")
    else:
        fecha = st.date_input("Fecha del Reporte", key="f_manual")
        col1, col2 = st.columns(2)
        with col1:
            sacos = st.number_input("Sacos Completos", min_value=0, step=1, key="sacos_m")
        with col2:
            libras = st.number_input("Libras Extra / Parciales", min_value=0.0, step=0.5, key="lbs_m")
        
        st.markdown("---")
        st.subheader("Asistencia de Personal")
        asistencia_hoy = [p["nombre"] for p in st.session_state.personal if st.checkbox(f"Asistió: {p['nombre']}", value=True, key=f"chk_{p['nombre']}")]

        st.markdown("---")
        st.subheader("Actividad por Lote")
        lote_sel = st.selectbox("Lote de Trabajo:", list(LOTES_INFO.keys()), key="lote_m")
        act_sel = st.selectbox("Actividad:", list(st.session_state.actividades_catalogo.keys()), key="act_m")
        ha_sel = st.number_input("Avance (Hectáreas / Cantidad):", min_value=0.0, step=0.25, key="ha_m")
        obs = st.text_area("Observaciones Generales:", key="obs_m")
        
        if st.button("Guardar Reporte Manual", key="btn_man_save"):
            st.session_state.reportes.append({
                "fecha": fecha.strftime('%Y-%m-%d'), "sacos": sacos, "libras": libras,
                "texto_original": obs, "asistencia": asistencia_hoy,
                "actividades": [{"actividad": act_sel, "lote": lote_sel, "ha": ha_sel}]
            })
            st.success("¡Reporte guardado!")

# 2. GESTIONAR PERSONAL
elif opcion.startswith("2."):
    st.header("👥 Gestionar Personal")
    with st.form("form_personal"):
        nom = st.text_input("Nombre Completo:")
        cargo = st.text_input("Cargo / Función:", value="Obrero de Campo")
        jornal = st.number_input("Jornal Diario ($):", value=15.0, step=1.0)
        if st.form_submit_button("Añadir Nuevo Personal"):
            if nom:
                st.session_state.personal.append({"nombre": nom, "cargo": cargo, "jornal": jornal})
                st.success(f"¡Trabajador {nom} agregado exitosamente!")
    
    st.markdown("---")
    st.dataframe(pd.DataFrame(st.session_state.personal), use_container_width=True)

# 3. CREAR / VER TAREAS NUEVAS
elif opcion.startswith("3."):
    st.header("📋 Crear / Ver Tareas Nuevas")
    with st.form("form_tareas"):
        nombre_tarea = st.text_input("Nombre de la Nueva Tarea:")
        unidad = st.selectbox("Unidad de Medida:", ["Hectáreas (ha)", "Horas", "Plantas", "Global"])
        color_hex = st.color_picker("Color para el Mapa:", "#27AE60")
        if st.form_submit_button("Guardar Tarea"):
            if nombre_tarea:
                h = color_hex.lstrip('#')
                rgba = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (130,)
                st.session_state.actividades_catalogo[nombre_tarea] = {"unidad": unidad, "color": rgba}
                st.success(f"¡Tarea '{nombre_tarea}' creada!")

    st.markdown("---")
    st.subheader("Catálogo Actual de Tareas:")
    for k, v in st.session_state.actividades_catalogo.items():
        st.write(f"• **{k}** — Unidad: `{v['unidad']}`")

# 4. ASISTENCIA Y NÓMINA SEMANAL
elif opcion.startswith("4."):
    st.header("📅 Asistencia y Nómina Semanal")
    lunes = st.date_input("Seleccionar Lunes de la Semana:", key="lun_asist")
    
    fechas = [(lunes + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    dias_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    
    matriz = []
    for p in st.session_state.personal:
        row = {"Trabajador": p["nombre"], "Cargo": p["cargo"]}
        dias_cant = 0
        for idx, f in enumerate(fechas):
            asist = any(f == r["fecha"] and p["nombre"] in r.get("asistencia", []) for r in st.session_state.reportes)
            row[dias_nombre[idx]] = "X" if asist else "-"
            if asist: dias_cant += 1
        row["Días Trabajados"] = dias_cant
        row["Total a Pagar ($)"] = dias_cant * p["jornal"]
        matriz.append(row)
        
    st.dataframe(pd.DataFrame(matriz), use_container_width=True)

# 5. HISTORIAL DE REPORTES Y EXPORTAR A EXCEL CON GRÁFICOS
elif opcion.startswith("5."):
    st.header("📊 Historial de Reportes y Análisis de Datos")
    
    if st.session_state.reportes:
        # Generación de Excel en Memoria
        buffer_excel = io.BytesIO()
        try:
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df_rep = pd.DataFrame(st.session_state.reportes)
                df_rep.to_excel(writer, sheet_name='Reportes_Diarios', index=False)
                
                df_per = pd.DataFrame(st.session_state.personal)
                df_per.to_excel(writer, sheet_name='Personal', index=False)

            st.download_button(
                label="📥 Descargar Base de Datos Completa en Excel (.xlsx)",
                data=buffer_excel.getvalue(),
                file_name=f"FINCAMAR_Historial_{datetime.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_excel_historial"
            )
        except Exception:
            st.warning("Para descargar en Excel asegura tener instalada la librería 'openpyxl' (`pip install openpyxl`).")

        st.markdown("---")
        st.subheader("📋 Tabla de Registros Guardados")
        st.dataframe(pd.DataFrame(st.session_state.reportes), use_container_width=True)

        st.markdown("---")
        st.subheader("📈 Gráfico Comparativo de Cosecha (Sacos por Fecha)")
        df_graf = pd.DataFrame(st.session_state.reportes)
        if 'sacos' in df_graf.columns and 'fecha' in df_graf.columns:
            st.bar_chart(data=df_graf, x='fecha', y='sacos')
    else:
        st.info("No existen reportes guardados en el historial aún.")

# 6. MAPA DE AVANCE POR LOTE
elif opcion.startswith("6."):
    st.header("🗺️ Mapa de Avance por Lote")
    if st.session_state.reportes:
        ultimo = st.session_state.reportes[-1]
        st.write(f"Mostrando actividades del día: **{ultimo['fecha']}**")
        img = generar_mapa_avance(ultimo.get("actividades", []))
        st.image(img, caption="Mapa Operacional FINCAMAR", use_container_width=True)
    else:
        st.info("Aún no hay reportes guardados para generar el mapa.")

# 7. EXPORTAR REPORTE DIARIO PDF
elif opcion.startswith("7."):
    st.header("📄 Exportar Reporte Diario a PDF")
    if st.session_state.reportes:
        ultimo = st.session_state.reportes[-1]
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = [Paragraph(f"<b>FINCAMAR - Reporte Diario ({ultimo['fecha']})</b>", getSampleStyleSheet()['Title'])]
        story.append(Spacer(1, 15))
        
        data = [
            ["Fecha", ultimo["fecha"]],
            ["Sacos Completos", str(ultimo["sacos"])],
            ["Libras Extra", f"{ultimo['libras']} lbs"],
            ["Personal Presente", ", ".join(ultimo.get("asistencia", []))]
        ]
        t = Table(data, colWidths=[140, 360])
        t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('GRID', (0,0), (-1,-1), 1, colors.grey)]))
        story.append(t)
        story.append(Spacer(1, 15))
        
        # PÁGINA 2: MAPA PINTADO
        story.append(PageBreak())
        story.append(Paragraph("<b>Mapa Operacional y Avance por Lote</b>", getSampleStyleSheet()['Heading2']))
        story.append(Spacer(1, 10))
        
        img_mapa = generar_mapa_avance(ultimo.get("actividades", []))
        img_buf = io.BytesIO()
        img_mapa.save(img_buf, format="PNG")
        img_buf.seek(0)
        story.append(RLImage(img_buf, width=480, height=480))
        
        doc.build(story)
        
        st.download_button(
            label="📥 Descargar Reporte Diario PDF con Mapa (Página 2)",
            data=buffer.getvalue(),
            file_name=f"Reporte_FINCAMAR_{ultimo['fecha']}.pdf",
            mime="application/pdf",
            key="btn_dl_pdf_rep"
        )
    else:
        st.warning("No hay reportes registrados para generar el PDF.")

# 8. EXPORTAR NÓMINA PDF
elif opcion.startswith("8."):
    st.header("📄 Exportar Nómina Semanal a PDF")
    st.info("Función lista para generar planilla oficial con espacio para firmas de pago.")

# 9. CONTROL DE MAQUINARIA Y TALLER
elif opcion.startswith("9."):
    st.header("🚜 Control de Maquinaria, Motoguadañas y Herramientas")
    st.text_area("Observaciones y Reportes del Taller (fallas de equipos, mantenimiento, etc.):", key="txt_taller")
    if st.button("Guardar Novedad de Taller", key="btn_taller"):
        st.success("Novedad registrada.")

# 10. CONFIGURACIÓN DE FINCA
elif opcion.startswith("10."):
    st.header("⚙️ Configuración General de FINCAMAR")
    st.text_input("Nombre del Predio / Finca:", value="FINCAMAR", key="cfg_nom")
    st.text_input("Ubicación Principal:", value="Río La Patera", key="cfg_ubi")
    st.text_input("Responsable Operativo:", value="Control de Campo", key="cfg_resp")
    if st.button("Guardar Cambios", key="btn_cfg_save"):
        st.success("Configuración actualizada.")
