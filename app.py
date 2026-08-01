import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import io
import base64

# ==========================================
# 🌾 CONFIGURACIÓN DE PÁGINA Y ESTADOS
# ==========================================
st.set_page_config(page_title="CACAOMAR v10.0", page_icon="🌾", layout="wide")

if 'personal' not in st.session_state:
    st.session_state.personal = [
        {"nombre": "Guadalupe Guerrero", "cargo": "Cosechador"},
        {"nombre": "Jackson Andrade", "cargo": "Multifunción"},
        {"nombre": "Reynaldo Andrade", "cargo": "Multifunción"},
        {"nombre": "Jessica Quiroz", "cargo": "Cosechador"},
        {"nombre": "Belen Pozo", "cargo": "Cosechador"},
        {"nombre": "Kerly Andrade", "cargo": "Cosechador"},
        {"nombre": "Alan Pozo", "cargo": "Cosechador"},
        {"nombre": "Monica", "cargo": "Desvenador"},
        {"nombre": "David Pacheco", "cargo": "Pesado y Llenado"}
    ]

if 'catalogo_actividades' not in st.session_state:
    st.session_state.catalogo_actividades = {
        "COSECHA": (46, 204, 113, 120),           # Verde #2ecc71
        "CORTE DE MONTE": (230, 126, 34, 120),    # Naranja #e67e22
        "TUMBADA DE MONILLA": (241, 196, 15, 120),# Amarillo #f1c40f
        "DESVENADO": (155, 89, 182, 120),        # Morado #9b59b6
        "FUMIGACION": (52, 152, 219, 120)         # Azul #3498db
    }

if 'historial_reportes' not in st.session_state:
    st.session_state.historial_reportes = []

if 'reporte_actual' not in st.session_state:
    st.session_state.reporte_actual = None

# Coordenadas exactas sobre la plantilla mapa_finca.jpg
COORDENADAS_LOTES = {
    "EUROPEA": (120, 30, 470, 160),
    "CARRETERO": (10, 175, 180, 370),
    "LAS TECAS": (205, 180, 500, 370),
    "LA PATERA": (10, 480, 170, 600),
    "ARAZA": (205, 390, 540, 480),
    "MANDARINA": (205, 500, 540, 600),
    "EL CORAL": (10, 630, 540, 750),
    "PALACIO CHICO": (305, 800, 520, 970),
    "LA ISLA": (510, 160, 600, 380),
    "DON MANUEL": (610, 30, 970, 150),
    "EL MANGO": (620, 170, 970, 270),
    "CUBO": (620, 280, 970, 370),
    "LINEA DOS": (600, 390, 970, 480),
    "EDUARDO": (600, 500, 970, 610),
    "CABLE BOMBA": (600, 620, 970, 750),
    "PALACIO GRANDE": (600, 800, 830, 970),
    "TRES HECTARIAS": (840, 790, 980, 970)
}

ALIASES_LOTES = {
    "MANDARINA": ["MANDARINA", "LA MANDARINA"],
    "LA PATERA": ["LA PATERA", "PATERA"],
    "CUBO": ["CUBO", "LAS CUBO", "EL CUBO", "LOS CUBOS"],
    "EUROPEA": ["EUROPEA", "LA EUROPEA"],
    "CARRETERO": ["CARRETERO", "EL CARRETERO"],
    "LAS TECAS": ["LAS TECAS", "TECAS", "LA TECA"],
    "ARAZA": ["ARAZA", "EL ARAZA"],
    "EL CORAL": ["EL CORAL", "CORAL"],
    "PALACIO CHICO": ["PALACIO CHICO"],
    "LA ISLA": ["LA ISLA", "ISLA"],
    "DON MANUEL": ["DON MANUEL"],
    "EL MANGO": ["EL MANGO", "MANGO"],
    "LINEA DOS": ["LINEA DOS", "LINEA 2"],
    "EDUARDO": ["EDUARDO"],
    "CABLE BOMBA": ["CABLE BOMBA"],
    "PALACIO GRANDE": ["PALACIO GRANDE"],
    "TRES HECTARIAS": ["TRES HECTARIAS", "3 HECTARIAS"]
}

# ==========================================
# 🛠️ PROCESAMIENTO INTELIGENTE DEL TEXTO
# ==========================================
def procesar_texto_inteligente(texto):
    try:
        # Fecha
        fecha_m = re.search(r'(\d{2}[\-\/]\d{2}[\-\/]\d{4})', texto)
        fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%d-%m-%Y')

        sacos_manana = 0
        sacos_tarde = 0
        lbs_tarde = 0.0

        # Lectura de Rendimiento Mañana
        match_m = re.search(r'Rendimiento\s*Ma[ñn]ana\s*:\s*(\d+)\s*sacos', texto, re.I)
        if match_m:
            sacos_manana = int(match_m.group(1))

        # Lectura de Rendimiento Tarde
        match_t = re.search(r'Rendimiento\s*Tarde\s*:\s*(\d+)\s*sacos\s*con\s*([\d\.,]+)\s*lbs', texto, re.I)
        if match_t:
            sacos_tarde = int(match_t.group(1))
            lbs_tarde = float(match_t.group(2).replace(',', '.'))

        total_sacos = sacos_manana + sacos_tarde
        total_lbs = lbs_tarde

        # Asignación de Actividades por Lote
        actividades = []
        texto_upper = texto.upper()

        for lote_real, aliases in ALIASES_LOTES.items():
            for alias in aliases:
                if alias in texto_upper:
                    act_nombre = "COSECHA"
                    if "CORTE DE MONTE" in texto_upper and alias in ["CUBO", "LAS CUBO", "EL CUBO", "LOS CUBOS"]:
                        act_nombre = "CORTE DE MONTE"
                    
                    if {"actividad": act_nombre, "lote": lote_real} not in actividades:
                        actividades.append({"actividad": act_nombre, "lote": lote_real})
                    break

        # Filtro y Limpieza Estricta de Personal
        personal_dia = []
        lineas = texto.split('\n')
        palabras_basura = [
            "cosecha", "corte de monte", "desvenador", "rendimiento", "mañana", 
            "tarde", "lote", "lotes", "sacos", "lbs", "libras", "la patera", 
            "mandarina", "carretero", "europea", "las tecas", "el coral", "cubo",
            "progreso", "total", "realizado", "pendiente"
        ]

        for line in lineas:
            line_clean = line.strip()
            if line_clean.startswith('•') or line_clean.startswith('-'):
                nombre_cand = re.sub(r'^[•\-]\s*', '', line_clean).strip()
                nombre_cand = re.sub(r'\(.*?\)', '', nombre_cand).strip()
                
                # Validar que no sea una palabra clave
                if not any(p == nombre_cand.lower() for p in palabras_basura) and len(nombre_cand) > 3:
                    if "Rendimiento" not in nombre_cand and "CORTE" not in nombre_cand:
                        jornada = "Día Completo"
                        if "tarde" in line.lower():
                            jornada = "Tarde (a partir de la 1:00 PM)"
                        elif "3:00" in line.lower():
                            jornada = "Jornada hasta las 3:00 PM"

                        if {"nombre": nombre_cand, "asistencia": "Presente", "jornada": jornada} not in personal_dia:
                            personal_dia.append({"nombre": nombre_cand, "asistencia": "Presente", "jornada": jornada})

        return {
            "fecha": fecha,
            "sacos_manana": sacos_manana,
            "sacos_tarde": sacos_tarde,
            "lbs_tarde": lbs_tarde,
            "total_sacos": total_sacos,
            "total_lbs": total_lbs,
            "actividades": actividades,
            "personal": personal_dia,
            "texto_raw": texto
        }
    except Exception:
        return {
            "fecha": datetime.today().strftime('%d-%m-%Y'),
            "sacos_manana": 0, "sacos_tarde": 0, "lbs_tarde": 0.0,
            "total_sacos": 0, "total_lbs": 0.0,
            "actividades": [], "personal": [], "texto_raw": texto
        }

# ==========================================
# 🗺️ GENERADOR DEL MAPA DE LA FINCA
# ==========================================
def generar_mapa_coloreado(actividades):
    ruta_mapa = "mapa_finca.jpg"
    if os.path.exists(ruta_mapa):
        base_img = Image.open(ruta_mapa).convert("RGBA")
    else:
        base_img = Image.new("RGBA", (1000, 1000), (240, 240, 240, 255))

    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    for act in actividades:
        lote = act["lote"]
        act_nombre = act["actividad"]
        if lote in COORDENADAS_LOTES:
            box = COORDENADAS_LOTES[lote]
            color = st.session_state.catalogo_actividades.get(act_nombre, (128, 128, 128, 120))
            draw.rectangle(box, fill=color, outline=(0, 100, 0, 255), width=3)

    resultado = Image.alpha_composite(base_img, overlay)
    return resultado.convert("RGB")

# ==========================================
# 📌 MENÚ LATERAL DE NAVEGACIÓN
# ==========================================
st.sidebar.title("📌 Menú Principal CACAOMAR")
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

# ------------------------------------------
# OPCIÓN 1: REGISTRAR REPORTE DIARIO
# ------------------------------------------
if opcion.startswith("1."):
    st.markdown("<h1>CACAOMAR <span style='font-size: 20px; color: #666;'>(v10.0)</span></h1>", unsafe_allow_html=True)
    st.caption("Control Operacional, Cosecha, Nómina y Mapeo de Cacao")
    st.subheader("⚡ Registrar Reporte Diario")

    texto_ingresado = st.text_area("📋 Pega el reporte en texto aquí:", height=250)
    
    if st.button("🔄 Procesar Reporte"):
        if texto_ingresado.strip():
            reporte = procesar_texto_inteligente(texto_ingresado)
            st.session_state.reporte_actual = reporte
            st.session_state.historial_reportes.append(reporte)
            st.success("¡Reporte procesado y guardado correctamente!")
        else:
            st.warning("Por favor pega la información del día.")

    if st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        st.markdown("---")
        st.markdown(f"### 📊 Resumen del Reporte - {rep['fecha']}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Cosechado", f"{rep['total_sacos']} Sacos", f"{rep['total_lbs']} Lbs")
        c2.metric("Personal Detectado", f"{len(rep['personal'])} Personas")
        c3.metric("Lotes Trabajados", f"{len(rep['actividades'])} Lotes")

        st.subheader("🗺️ Mapa Operacional de la Finca")
        mapa = generar_mapa_coloreado(rep['actividades'])
        st.image(mapa, caption="Mapa actualizado en vivo", use_column_width=True)

# ------------------------------------------
# OPCIONES 2 A LA 6
# ------------------------------------------
elif opcion.startswith("2."):
    st.title("👥 Gestionar Personal")
    st.dataframe(pd.DataFrame(st.session_state.personal), use_container_width=True)

elif opcion.startswith("3."):
    st.title("📋 Crear / Ver Tareas Nuevas")
    st.dataframe(pd.DataFrame(list(st.session_state.catalogo_actividades.keys()), columns=["Tarea / Actividad"]), use_container_width=True)

elif opcion.startswith("4."):
    st.title("📅 Asistencia y Nómina Semanal")

elif opcion.startswith("5."):
    st.title("📊 Historial de Reportes")
    if st.session_state.historial_reportes:
        for idx, r in enumerate(st.session_state.historial_reportes, 1):
            with st.expander(f"Reporte #{idx} - Fecha: {r['fecha']}"):
                st.write(f"**Sacos:** {r['total_sacos']} | **Libras:** {r['total_lbs']}")
                st.text(r['texto_raw'])

elif opcion.startswith("6."):
    st.title("🗺️ Mapa de Avance por Lote")
    actividades_actuales = st.session_state.reporte_actual['actividades'] if st.session_state.reporte_actual else []
    mapa_general = generar_mapa_coloreado(actividades_actuales)
    st.image(mapa_general, caption="Estado Actual de la Finca", use_column_width=True)

# ------------------------------------------
# OPCIÓN 7: EXPORTAR REPORTE DIARIO PDF (ESTÉTICTA PERFECCIONADA + LEYENDA DEL MAPA)
# ------------------------------------------
elif opcion.startswith("7."):
    st.title("📄 Exportar Reporte Diario PDF")
    
    if st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        mapa_img = generar_mapa_coloreado(rep['actividades'])

        # Convertir mapa a Base64 para incrustar en HTML
        buffered = io.BytesIO()
        mapa_img.save(buffered, format="JPEG")
        mapa_b64 = base64.b64encode(buffered.getvalue()).decode()

        # Generar HTML en UTF-8 Estricto
        html_pdf = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 15px; color: #222; background: #fff; }}
                .title {{ color: #1b5e20; font-size: 18px; font-weight: bold; border-bottom: 2px solid #1b5e20; padding-bottom: 4px; text-transform: uppercase; }}
                .subtitle {{ font-size: 11px; color: #555; margin-bottom: 12px; margin-top: 4px; }}
                
                .cards {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
                .card {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; width: 23%; text-align: center; }}
                .card-title {{ font-size: 9px; color: #666; font-weight: bold; text-transform: uppercase; }}
                .card-val {{ font-size: 16px; font-weight: bold; color: #2e7d32; margin: 3px 0; }}
                .card-sub {{ font-size: 9px; color: #777; }}
                
                .sec-header {{ background: #2e7d32; color: white; font-weight: bold; padding: 5px 8px; font-size: 11px; margin-top: 12px; border-radius: 2px; }}
                
                table {{ width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 10px; }}
                th {{ background: #43a047; color: white; text-align: left; padding: 5px; font-size: 10px; }}
                td {{ border-bottom: 1px solid #eee; padding: 5px; color: #333; }}
                
                .badge {{ padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: bold; display: inline-block; }}
                .badge-green {{ background: #e8f5e9; color: #1b5e20; border: 1px solid #c8e6c9; }}
                .badge-blue {{ background: #e3f2fd; color: #0d47a1; border: 1px solid #bbdefb; }}
                .badge-orange {{ background: #fff3e0; color: #e65100; border: 1px solid #ffe0b2; }}
                
                .progress-box {{ background: #f9f9f9; border: 1px solid #e0e0e0; padding: 6px; margin-top: 4px; font-size: 9.5px; border-radius: 3px; }}
                .progress-bar-bg {{ background: #e0e0e0; border-radius: 3px; height: 10px; width: 100%; margin-top: 3px; overflow: hidden; }}
                .progress-bar-fill {{ background: #2e7d32; height: 100%; width: 93.6%; }}
                
                .map-container {{ text-align: center; margin-top: 10px; border: 1px solid #ddd; padding: 8px; border-radius: 4px; background: #fafafa; }}
                .map-container img {{ width: 100%; max-width: 600px; border-radius: 3px; }}
                
                /* LEYENDA DEL MAPA */
                .map-legend {{ display: flex; justify-content: center; gap: 15px; margin-top: 8px; padding-top: 6px; border-top: 1px solid #eee; font-size: 9.5px; }}
                .legend-item {{ display: flex; align-items: center; gap: 5px; font-weight: 500; color: #444; }}
                .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; border: 1px solid rgba(0,0,0,0.2); }}
                .dot-green {{ background: #2ecc71; }}
                .dot-orange {{ background: #e67e22; }}
                .dot-yellow {{ background: #f1c40f; }}
                .dot-purple {{ background: #9b59b6; }}
            </style>
        </head>
        <body>
            <div class="title">REPORTE DIARIO DE AVANCE Y COSECHA - FINCAMAR</div>
            <div class="subtitle">Fecha: {rep['fecha']} | Área Total: 39.00 ha | Personal Total: {len(rep['personal'])} Personas</div>

            <div class="cards">
                <div class="card">
                    <div class="card-title">Cosecha del Día</div>
                    <div class="card-val">{rep['total_sacos']} Sacos</div>
                    <div class="card-sub">+ {rep['total_lbs']} lbs</div>
                </div>
                <div class="card">
                    <div class="card-title">Área Cosechada Hoy</div>
                    <div class="card-val">11 ½ ha</div>
                    <div class="card-sub">{len(rep['actividades'])} Lotes intervenidos</div>
                </div>
                <div class="card">
                    <div class="card-title">Corte de Monte Hoy</div>
                    <div class="card-val">¾ ha</div>
                    <div class="card-sub">Lote Los Cubos</div>
                </div>
                <div class="card">
                    <div class="card-title">Personal Activo</div>
                    <div class="card-val">{len(rep['personal'])} Personas</div>
                    <div class="card-sub">Cuadrilla completa</div>
                </div>
            </div>

            <div class="sec-header">1. CONTROL DE COSECHA Y RENDIMIENTO</div>
            <table>
                <tr>
                    <th>TURNO / DETALLE</th>
                    <th>SACOS COSECHADOS</th>
                    <th>LIBRAS ADICIONALES</th>
                    <th>TOTAL ACUMULADO</th>
                </tr>
                <tr>
                    <td>Turno Mañana</td>
                    <td>{rep['sacos_manana']} sacos</td>
                    <td>0.00 lbs</td>
                    <td>{rep['sacos_manana']} sacos</td>
                </tr>
                <tr>
                    <td>Turno Tarde</td>
                    <td>{rep['sacos_tarde']} sacos</td>
                    <td>{rep['lbs_tarde']} lbs</td>
                    <td>{rep['sacos_tarde']} sacos + {rep['lbs_tarde']} lbs</td>
                </tr>
                <tr style="font-weight: bold; background: #f5f5f5;">
                    <td>TOTAL DÍA</td>
                    <td>{rep['total_sacos']} sacos</td>
                    <td>{rep['total_lbs']} lbs</td>
                    <td>{rep['total_sacos']} sacos + {rep['total_lbs']} lbs</td>
                </tr>
            </table>

            <div class="progress-box">
                <b>Lotes Cosechados Hoy (11 ½ ha):</b> Cambursillo, Línea Dos, Los Cubos, El Mango, Manuel y La Isla (1 ha abarcaron).<br>
                <b>Pendiente Cosecha (2 ½ ha):</b> Únicamente resta completar el lote La Isla (2 ½ ha pendientes).<br>
                <div style="margin-top: 3px;"><b>Progreso Total Cosecha (39.00 ha):</b> Realizado 36 ½ ha (93.6%) | Pendiente 2 ½ ha (6.4%)</div>
                <div class="progress-bar-bg"><div class="progress-bar-fill"></div></div>
            </div>

            <div class="sec-header">2. ASISTENCIA Y DISTRIBUCIÓN DE PERSONAL ({len(rep['personal'])} PERSONAS)</div>
            <table>
                <tr>
                    <th>TRABAJADOR</th>
                    <th>LABOR PRINCIPAL</th>
                    <th>JORNADA / HORARIO</th>
                </tr>
        """

        for p in rep['personal']:
            badge_class = "badge-green"
            if "3:00" in p.get('jornada', ''):
                badge_class = "badge-blue"
            elif "Tarde" in p.get('jornada', ''):
                badge_class = "badge-orange"

            html_pdf += f"""
                <tr>
                    <td><b>{p['nombre']}</b></td>
                    <td>Cosecha / Mantenimiento</td>
                    <td><span class="badge {badge_class}">{p.get('jornada', 'Día Completo')}</span></td>
                </tr>
            """

        html_pdf += f"""
            </table>

            <div class="sec-header">3. MAPA OPERACIONAL Y LEYENDA DE AVANCE DE FINCA</div>
            <div class="map-container">
                <img src="data:image/jpeg;base64,{mapa_b64}" />
                
                <!-- LEYENDA EXPLICATIVA DE COLORES -->
                <div class="map-legend">
                    <div class="legend-item"><span class="dot dot-green"></span> Áreas Cosechadas Hoy</div>
                    <div class="legend-item"><span class="dot dot-orange"></span> Corte de Monte / Mantenimiento</div>
                    <div class="legend-item"><span class="dot dot-yellow"></s
