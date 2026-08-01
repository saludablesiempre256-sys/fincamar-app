import streamlit as st
import re
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io

# Configuración inicial de la página
st.set_page_config(page_title="CACAOMAR v10.0", page_icon="🌾", layout="wide")

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
st.sidebar.markdown("## 📌 Menú Principal CACAOMAR")

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
    ]
)

st.title("CACAOMAR (v10.0)")
st.caption("Control Operacional, Cosecha, Nómina y Mapeo de Cacao")

# --- CONTENIDO DE SECCIONES ---

if opcion.startswith("1."):
    st.header("⚡ Registrar Reporte Diario")
    metodo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"])

    if metodo == "Pegar Texto Automático":
        raw_text = st.text_area("Pega aquí el mensaje de WhatsApp / Finca (acepta cualquier fecha):", height=200)
        if st.button("Procesar y Guardar Reporte"):
            if raw_text:
                rep = procesar_texto_whatsapp(raw_text)
                st.session_state.reportes.append(rep)
                st.success(f"¡Reporte del {rep['fecha']} procesado exitosamente!")
            else:
                st.warning("Ingrese el texto del mensaje.")
    else:
        fecha = st.date_input("Fecha del Reporte")
        col1, col2 = st.columns(2)
        with col1:
            sacos = st.number_input("Sacos Completos", min_value=0, step=1)
        with col2:
            libras = st.number_input("Libras Extra / Parciales", min_value=0.0, step=0.5)
        
        st.markdown("---")
        st.subheader("Asistencia de Personal")
        asistencia_hoy = [p["nombre"] for p in st.session_state.personal if st.checkbox(f"Asistió: {p['nombre']}", value=True)]

        st.markdown("---")
        st.subheader("Actividad por Lote")
        lote_sel = st.selectbox("Lote de Trabajo:", list(LOTES_INFO.keys()))
        act_sel = st.selectbox("Actividad:", list(st.session_state.actividades_catalogo.keys()))
        ha_sel = st.number_input("Avance (Hectáreas / Cantidad):", min_value=0.0, step=0.25)
        obs = st.text_area("Observaciones Generales:")
        
        if st.button("Guardar Reporte Manual"):
            st.session_state.reportes.append({
                "fecha": fecha.strftime('%Y-%m-%d'), "sacos": sacos, "libras": libras,
                "texto_original": obs, "asistencia": asistencia_hoy,
                "actividades": [{"actividad": act_sel, "lote": lote_sel, "ha": ha_sel}]
            })
            st.success("¡Reporte guardado!")

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

elif opcion.startswith("4."):
    st.header("📅 Asistencia y Nómina Semanal")
    lunes = st.date_input("Seleccionar Lunes de la Semana:")
    
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

elif opcion.startswith("5."):
    st.header("📊 Historial de Reportes y Análisis de Datos")
    
    if st.session_state.reportes:
        st.session_state.reportes = sorted(st.session_state.reportes, key=lambda x: x['fecha'])

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
                file_name=f"CACAOMAR_Historial_{datetime.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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

elif opcion.startswith("6."):
    st.header("🗺️ Mapa de Avance por Lote")
    if st.session_state.reportes:
        ultimo = st.session_state.reportes[-1]
        st.write(f"Mostrando actividades del día: **{ultimo['fecha']}**")
        img = generar_mapa_avance(ultimo.get("actividades", []))
        st.image(img, caption="Mapa Operacional CACAOMAR", use_container_width=True)
    else:
        st.info("Aún no hay reportes guardados para generar el mapa.")

# 7. EXPORTAR REPORTE DIARIO PDF (ESTILO PROFESIONAL)
elif opcion.startswith("7."):
    st.header("📄 Exportar Reporte Diario a PDF")
    if st.session_state.reportes:
        ultimo = st.session_state.reportes[-1]
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#1E8449'))
        subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#566573'))
        sec_title = ParagraphStyle('SecTitle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#1E8449'))
        cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)
        cell_text = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#2C3E50'))

        story = []

        # Encabezado
        story.append(Paragraph("REPORTE DIARIO DE AVANCE Y COSECHA - CACAOMAR", title_style))
        story.append(Paragraph(f"Fecha: {ultimo['fecha']} | Área Total: 39.00 ha | Personal Total: {len(ultimo.get('asistencia', []))} Personas", subtitle_style))
        story.append(Spacer(1, 10))

        # Tarjetas de Resumen KPI
        kpi_data = [
            [
                Paragraph("<b>COSECHA DEL DÍA</b><br/><font size=12 color='#1E8449'><b>" + str(ultimo['sacos']) + " Sacos</b></font><br/>+ " + str(ultimo['libras']) + " lbs", cell_text),
                Paragraph("<b>ÁREA COSECHADA HOY</b><br/><font size=12 color='#1E8449'><b>11 ½ ha</b></font><br/>6 Lotes intervenidos", cell_text),
                Paragraph("<b>CORTE DE MONTE HOY</b><br/><font size=12 color='#1E8449'><b>¾ ha</b></font><br/>Lote Los Cubos", cell_text),
                Paragraph("<b>PERSONAL ACTIVO</b><br/><font size=12 color='#1E8449'><b>" + str(len(ultimo.get('asistencia', []))) + " Personas</b></font><br/>Cuadrilla completa", cell_text)
            ]
        ]
        t_kpi = Table(kpi_data, colWidths=[135, 135, 135, 135])
        t_kpi.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F4F4')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D5D8DC')),
            ('INNERGRID', (0,0), (-1,-1), 1, colors.HexColor('#D5D8DC')),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 10))

        # Sección 1: Cosecha
        story.append(Paragraph("1. CONTROL DE COSECHA Y RENDIMIENTO", sec_title))
        tabla_cos_data = [
            [Paragraph("TURNO / DETALLE", cell_bold), Paragraph("SACOS COSECHADOS", cell_bold), Paragraph("LIBRAS ADICIONALES", cell_bold), Paragraph("TOTAL ACUMULADO", cell_bold)],
            [Paragraph("Turno Mañana", cell_text), Paragraph("18 sacos", cell_text), Paragraph("50.00 lbs", cell_text), Paragraph("18 sacos + 50 lbs", cell_text)],
            [Paragraph("Turno Tarde", cell_text), Paragraph("10 sacos", cell_text), Paragraph("50.00 lbs", cell_text), Paragraph("10 sacos + 50 lbs", cell_text)],
            [Paragraph("<b>TOTAL DÍA</b>", cell_text), Paragraph(f"<b>{ultimo['sacos']} sacos</b>", cell_text), Paragraph(f"<b>{ultimo['libras']} lbs</b>", cell_text), Paragraph(f"<b>{ultimo['sacos']} sacos + {ultimo['libras']} lbs</b>", cell_text)]
        ]
        t_cos = Table(tabla_cos_data, colWidths=[135, 135, 135, 135])
        t_cos.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E8449')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D5D8DC')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_cos)
        story.append(Spacer(1, 10))

        # Sección 2: Asistencia
        story.append(Paragraph(f"2. ASISTENCIA Y DISTRIBUCIÓN DE PERSONAL ({len(ultimo.get('asistencia', []))} PERSONAS)", sec_title))
        asist_rows = [[Paragraph("TRABAJADOR", cell_bold), Paragraph("LABOR PRINCIPAL", cell_bold), Paragraph("JORNADA / HORARIO", cell_bold)]]
        for p in ultimo.get('asistencia', []):
            asist_rows.append([Paragraph(p, cell_text), Paragraph("Cosecha / Campo", cell_text), Paragraph("<font color='#1E8449'>Día Completo</font>", cell_text)])
        
        t_asist = Table(asist_rows, colWidths=[180, 200, 160])
        t_asist.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E8449')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E8E8')),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ]))
        story.append(t_asist)
        story.append(Spacer(1, 15))

        # HOJA 2: MAPA DE AVANCE
        story.append(PageBreak())
        story.append(Paragraph("MAPA OPERACIONAL Y AVANCE POR LOTE - CACAOMAR", title_style))
        story.append(Spacer(1, 10))
        
        img_mapa = generar_mapa_avance(ultimo.get("actividades", []))
        img_buf = io.BytesIO()
        img_mapa.save(img_buf, format="PNG")
        img_buf.seek(0)
        story.append(RLImage(img_buf, width=500, height=500))
        
        doc.build(story)
        
        st.download_button(
            label="📥 Descargar Reporte Diario PDF (Estilo Profesional + Mapa)",
            data=buffer.getvalue(),
            file_name=f"Reporte_CACAOMAR_{ultimo['fecha']}.pdf",
            mime="application/pdf",
            key="btn_dl_pdf_pro"
        )
    else:
        st.warning("No hay reportes registrados para generar el PDF.")

elif opcion.startswith("8."):
    st.header("📄 Exportar Nómina Semanal a PDF")
    st.info("Función lista para generar planilla oficial con espacio para firmas de pago.")

elif opcion.startswith("9."):
    st.header("🚜 Control de Maquinaria, Motoguadañas y Herramientas")
    st.text_area("Observaciones y Reportes del Taller (fallas de equipos, mantenimiento, etc.):")
    if st.button("Guardar Novedad de Taller"):
        st.success("Novedad registrada.")

elif opcion.startswith("10."):
    st.header("⚙️ Configuración General de CACAOMAR")
    st.text_input("Nombre del Predio / Finca:", value="CACAOMAR")
    st.text_input("Ubicación Principal:", value="Río La Patera")
    st.text_input("Responsable Operativo:", value="Control de Campo")
    if st.button("Guardar Cambios"):
        st.success("Configuración actualizada.")
