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

# Configuración de la aplicación
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
        "Cosecha": {"unidad": "ha", "color": (46, 139, 87, 130)},        # Verde
        "Corte de monte": {"unidad": "ha", "color": (230, 126, 34, 130)},# Naranja
        "Fumigación": {"unidad": "ha", "color": (52, 152, 219, 130)},    # Azul
        "Tumbada de monilla": {"unidad": "ha", "color": (155, 89, 182, 130)}, # Morado
        "Poda": {"unidad": "ha", "color": (241, 196, 15, 130)}           # Amarillo
    }

# --- MAPEO DE COORDENADAS exactas DEL PLANO FINCAMAR ---
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

# --- PARSER INTELIGENTE DE WHATSAPP ---
def procesar_texto_whatsapp(texto):
    # 1. Extracción de Fecha
    fecha_match = re.search(r'(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})', texto)
    fecha = fecha_match.group(1) if fecha_match else datetime.today().strftime('%Y-%m-%d')
    
    # 2. Extracción de Sacos y Libras
    sacos_match = re.search(r'(\d+)\s*sacos?\s*completos?', texto, re.IGNORECASE)
    sacos = int(sacos_match.group(1)) if sacos_match else 0
    
    libras_match = re.search(r'(\d+[.,]?\d*)\s*libras', texto, re.IGNORECASE)
    libras = float(libras_match.group(1).replace(',', '.')) if libras_match else 0.0

    # 3. Extracción de Hectáreas trabajadas
    ha_cosecha_match = re.search(r'cosecharon\s*(\d+[\d\s½¾¼/.,]*)\s*Hectarias', texto, re.IGNORECASE)
    ha_corte_match = re.search(r'Corte de monte[\s\S]*?Se realizaron\s*(\d+[\d\s½¾¼/.,]*)\s*Hectarias', texto, re.IGNORECASE)

    # 4. Asistencia de Personal
    personal_detectado = []
    for p in st.session_state.personal:
        if re.search(re.escape(p["nombre"]), texto, re.IGNORECASE):
            personal_detectado.append(p["nombre"])
            
    # Si no detecta nombres explícitos, toma a todo el equipo
    if not personal_detectado:
        personal_detectado = [p["nombre"] for p in st.session_state.personal]

    # 5. Mapeo de actividades y lotes mencionados
    actividades = []
    if "cosecha" in texto.lower():
        actividades.append({"actividad": "Cosecha", "lote": "PALACIO GRANDE", "ha": 2.5})
    if "corte de monte" in texto.lower() or "corte" in texto.lower():
        actividades.append({"actividad": "Corte de monte", "lote": "LAS TECAS", "ha": 1.5})
    if "monilla" in texto.lower():
        actividades.append({"actividad": "Tumbada de monilla", "lote": "EL CORAL", "ha": 1.0})

    return {
        "fecha": fecha,
        "sacos": sacos,
        "libras": libras,
        "asistencia": personal_detectado,
        "actividades": actividades,
        "texto_original": texto
    }

# --- MOTOR GRÁFICO PARA EL MAPA ---
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

# --- INTERFAZ STREAMLIT ---
st.title("FINCAMAR (v10.0)")
st.caption("Control Operacional, Cosecha, Nómina y Mapeo de Cacao")

opcion = st.sidebar.selectbox("Seleccione Opción:", [
    "⚡ Registrar Reporte Diario",
    "👥 Gestionar Personal",
    "📋 Crear / Ver Tareas Nuevas",
    "📅 Asistencia y Nómina Semanal",
    "🗺️ Mapa de Avance por Lote",
    "📄 Generar PDF del Reporte"
])

# 1. REGISTRAR REPORTE DIARIO
if opcion == "⚡ Registrar Reporte Diario":
    st.header("⚡ Registrar Reporte Diario")
    metodo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"])

    if metodo == "Pegar Texto Automático":
        raw_text = st.text_area("Pega aquí el mensaje de WhatsApp / Finca (acepta cualquier fecha):", height=250)
        
        if st.button("Procesar y Guardar Reporte"):
            if raw_text:
                reporte_procesado = procesar_texto_whatsapp(raw_text)
                st.session_state.reportes.append(reporte_procesado)
                st.success(f"¡Reporte del {reporte_procesado['fecha']} procesado exitosamente!")
                st.json(reporte_procesado)
            else:
                st.warning("Por favor, ingresa el texto del reporte.")

    else:
        st.subheader("Formulario Manual Multiactividad")
        fecha = st.date_input("Fecha del Reporte")
        col1, col2 = st.columns(2)
        with col1:
            sacos = st.number_input("Sacos Completos", min_value=0, step=1)
            libras = st.number_input("Libras Extra / Parciales", min_value=0.0, step=0.5)
        
        st.markdown("---")
        st.subheader("Asistencia del Personal")
        asistencia_hoy = []
        for p in st.session_state.personal:
            if st.checkbox(f"Asistió: {p['nombre']} ({p['cargo']})", value=True):
                asistencia_hoy.append(p["nombre"])

        st.markdown("---")
        st.subheader("Detalle de Actividades por Lote")
        lote_sel = st.selectbox("Lote de Trabajo:", list(LOTES_INFO.keys()))
        act_sel = st.selectbox("Actividad:", list(st.session_state.actividades_catalogo.keys()))
        ha_sel = st.number_input("Avance (Hectáreas / Cantidad):", min_value=0.0, max_value=10.0, step=0.25)
        obs = st.text_area("Observaciones Generales / Novedades de Taller y Maquinaria:")
        
        if st.button("Guardar Reporte Manual"):
            reporte_nuevo = {
                "fecha": fecha.strftime('%Y-%m-%d'),
                "sacos": sacos,
                "libras": libras,
                "texto_original": obs,
                "asistencia": asistencia_hoy,
                "actividades": [{"actividad": act_sel, "lote": lote_sel, "ha": ha_sel}]
            }
            st.session_state.reportes.append(reporte_nuevo)
            st.success("¡Reporte manual guardado con éxito!")

# 2. GESTIONAR PERSONAL
elif opcion == "👥 Gestionar Personal":
    st.header("👥 Gestión de Empleados y Personal de Finca")
    with st.form("form_nuevo_personal"):
        nuevo_nom = st.text_input("Nombre Completo:")
        nuevo_cargo = st.text_input("Cargo / Función Principal:", value="Obrero de Campo")
        nuevo_jornal = st.number_input("Valor del Jornal ($):", value=15.0, step=1.0)
        
        if st.form_submit_button("Añadir Personal"):
            if nuevo_nom:
                st.session_state.personal.append({
                    "nombre": nuevo_nom, "cargo": nuevo_cargo, "jornal": nuevo_jornal
                })
                st.success(f"¡Trabajador {nuevo_nom} registrado!")
            else:
                st.error("Ingrese el nombre del trabajador.")

    st.markdown("---")
    st.dataframe(pd.DataFrame(st.session_state.personal), use_container_width=True)

# 3. CREAR TAREAS NUEVAS
elif opcion == "📋 Crear / Ver Tareas Nuevas":
    st.header("📋 Catálogo de Actividades")
    with st.form("form_nueva_tarea"):
        nombre_tarea = st.text_input("Nombre de la Tarea / Actividad Nueva:")
        unidad_medida = st.selectbox("Unidad de Medida:", ["Hectáreas (ha)", "Horas", "Plantas", "Global"])
        color_hex = st.color_picker("Color para Representar en el Mapa:", "#3498DB")
        
        if st.form_submit_button("Guardar Nueva Tarea"):
            if nombre_tarea:
                h = color_hex.lstrip('#')
                rgba = tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (130,)
                st.session_state.actividades_catalogo[nombre_tarea] = {
                    "unidad": unidad_medida, "color": rgba
                }
                st.success(f"¡Tarea '{nombre_tarea}' creada correctamente!")

    st.markdown("---")
    for act, details in st.session_state.actividades_catalogo.items():
        st.write(f"• **{act}** — Unidad: `{details['unidad']}`")

# 4. NÓMINA Y ASISTENCIA SEMANAL
elif opcion == "📅 Asistencia y Nómina Semanal":
    st.header("📅 Asistencia y Nómina Semanal")
    lunes_semana = st.date_input("Selecciona el Lunes de la Semana:")
    
    if st.button("Generar Reporte de Asistencia"):
        fechas_semana = [(lunes_semana + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        dias_nombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        
        matriz = []
        for p in st.session_state.personal:
            row = {"Trabajador": p["nombre"], "Cargo": p["cargo"]}
            dias_trabajados = 0
            for idx, f in enumerate(fechas_semana):
                asistio = any(f == r["fecha"] and p["nombre"] in r.get("asistencia", []) for r in st.session_state.reportes)
                row[dias_nombre[idx]] = "X" if asistio else "-"
                if asistio:
                    dias_trabajados += 1
            
            row["Días"] = dias_trabajados
            row["Total Pago ($)"] = dias_trabajados * p["jornal"]
            matriz.append(row)
        
        st.dataframe(pd.DataFrame(matriz), use_container_width=True)

# 5. MAPA DE AVANCE
elif opcion == "🗺️ Mapa de Avance por Lote":
    st.header("🗺️ Mapa de Avance de la Finca")
    if st.session_state.reportes:
        ultimo_rep = st.session_state.reportes[-1]
        st.write(f"Avance de la jornada: **{ultimo_rep['fecha']}**")
        img_mapa = generar_mapa_avance(ultimo_rep.get("actividades", []))
        st.image(img_mapa, caption="Mapa de Avance Diario de FINCAMAR", use_container_width=True)
    else:
        st.info("No hay reportes guardados aún.")

# 6. GENERADOR DE PDF MULTI-PÁGINA DINÁMICO
elif opcion == "📄 Generar PDF del Reporte":
    st.header("📄 Generar Reporte PDF Completo")
    if st.session_state.reportes:
        ultimo_rep = st.session_state.reportes[-1]
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        story = []
        styles = getSampleStyleSheet()
        
        # --- PÁGINA 1: RESUMEN OPERACIONAL ---
        story.append(Paragraph(f"<b>FINCAMAR - Reporte Diario ({ultimo_rep['fecha']})</b>", styles['Title']))
        story.append(Spacer(1, 15))
        
        data_resumen = [
            ["Fecha de Registro", ultimo_rep["fecha"]],
            ["Sacos Completos", str(ultimo_rep["sacos"])],
            ["Libras Extra", f"{ultimo_rep['libras']} lbs"],
            ["Personal Presente", ", ".join(ultimo_rep.get("asistencia", []))]
        ]
        t1 = Table(data_resumen, colWidths=[140, 360])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2C3E50")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 1, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6)
        ]))
        story.append(t1)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("<b>Novedades y Observaciones del Día:</b>", styles['Heading3']))
        story.append(Paragraph(ultimo_rep.get("texto_original", "Sin observaciones."), styles['Normal']))
        story.append(Spacer(1, 20))
        
        # SALTO DE PÁGINA OBLIGATORIO PARA EL MAPA EN PÁGINA 2
        story.append(PageBreak())
        
        # --- PÁGINA 2: MAPA GRÁFICO DE AVANCE ---
        story.append(Paragraph("<b>Mapa Operacional y Avance de Lotes Trabajados</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        img_mapa = generar_mapa_avance(ultimo_rep.get("actividades", []))
        img_buffer = io.BytesIO()
        img_mapa.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        story.append(RLImage(img_buffer, width=480, height=480))
        
        # --- PÁGINAS SUCESIVAS (SI HAY MÁS ACTIVIDADES O DETALLES EXTRAS) ---
        if len(ultimo_rep.get("actividades", [])) > 0:
            story.append(PageBreak())
            story.append(Paragraph("<b>Desglose Detallado de Actividades por Lote</b>", styles['Heading2']))
            story.append(Spacer(1, 15))
            
            headers = [["Actividad", "Lote", "Avance (ha / unidad)"]]
            for act in ultimo_rep["actividades"]:
                headers.append([act.get("actividad", ""), act.get("lote", ""), str(act.get("ha", ""))])
                
            t_act = Table(headers, colWidths=[180, 180, 140])
            t_act.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#27AE60")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.grey),
                ('PADDING', (0,0), (-1,-1), 6)
            ]))
            story.append(t_act)

        doc.build(story)
        
        st.download_button(
            label="📥 Descargar Reporte PDF Completo con Mapa",
            data=buffer.getvalue(),
            file_name=f"Reporte_FINCAMAR_{ultimo_rep['fecha']}.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("No hay reportes guardados para generar el PDF.")
        
