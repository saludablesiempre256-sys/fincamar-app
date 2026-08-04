import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import io
import base64
import sqlite3

# ==========================================
# 🌾 1. CONFIGURACIÓN DE PÁGINA Y BASE DE DATOS
# ==========================================
st.set_page_config(page_title="CACAOMAR v15.0", page_icon="🌾", layout="wide")

DB_NAME = "cacaomar.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabla de Personal
    c.execute('''CREATE TABLE IF NOT EXISTS personal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    cargo TEXT,
                    tarifa_diaria REAL DEFAULT 0.0
                )''')
    # Tabla de Reportes Diarios
    c.execute('''CREATE TABLE IF NOT EXISTS reportes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    actividad_principal TEXT,
                    sacos_manana INTEGER,
                    sacos_tarde INTEGER,
                    lbs_tarde REAL,
                    total_sacos INTEGER,
                    total_lbs REAL,
                    ha_trabajadas REAL,
                    personal_json TEXT,
                    actividades_json TEXT,
                    texto_raw TEXT
                )''')
    
    # Cargar personal inicial si está vacía
    c.execute("SELECT COUNT(*) FROM personal")
    if c.fetchone()[0] == 0:
        personal_inicial = [
            ("Guadalupe Guerrero", "Cosechador", 15.0),
            ("Jackson Andrade", "Multifunción", 15.0),
            ("Reynaldo Andrade", "Multifunción", 15.0),
            ("Jessica Quiroz", "Cosechador", 15.0),
            ("Belen Pozo", "Cosechador", 15.0),
            ("Kerly Andrade", "Cosechador", 15.0),
            ("Alan Pozo", "Cosechador", 15.0),
            ("Monica", "Desvenador", 15.0),
            ("David Pacheco", "Pesado y Llenado", 15.0),
            ("Jacqueline Quiroz", "Aplicador / Fumigación", 15.0)
        ]
        c.executemany("INSERT INTO personal (nombre, cargo, tarifa_diaria) VALUES (?, ?, ?)", personal_inicial)
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🎨 2. CONFIGURACIÓN DE CATÁLOGOS Y MAPA
# ==========================================
if 'catalogo_actividades' not in st.session_state:
    st.session_state.catalogo_actividades = {
        "COSECHA": (46, 204, 113, 120),           # Verde #2ecc71
        "CORTE DE MONTE": (230, 126, 34, 120),    # Naranja #e67e22
        "TUMBADA DE MONILLA": (241, 196, 15, 120),# Amarillo #f1c40f
        "DESVENADO": (155, 89, 182, 120),        # Morado #9b59b6
        "FUMIGACION": (52, 152, 219, 120)         # Azul #3498db
    }

COORDENADAS_LOTES = {
    "EUROPEA": (120, 30, 470, 160),
    "CARRETERO": (10, 175, 180, 370),
    "LAS TECAS": (205, 180, 500, 370),
    "LA PATERA": (10, 480, 170, 600),
    "ARAZA": (205, 410, 520, 480),       
    "MANDARINA": (205, 500, 520, 575),   
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
# 🧠 3. PARSER INTELIGENTE ADAPTATIVO
# ==========================================
def procesar_texto_inteligente(texto):
    try:
        # 1. Fecha
        fecha_m = re.search(r'(\d{2}[\-\/]\d{2}[\-\/]\d{4})', texto)
        fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%d-%m-%Y')

        # 2. Cosecha
        sacos_manana, sacos_tarde, lbs_tarde = 0, 0, 0.0
        match_m = re.search(r'Rendimiento\s*Ma[ñn]ana\s*:\s*(\d+)\s*sacos', texto, re.I)
        if match_m: sacos_manana = int(match_m.group(1))

        match_t = re.search(r'Rendimiento\s*Tarde\s*:\s*(\d+)\s*sacos\s*con\s*([\d\.,]+)\s*lbs', texto, re.I)
        if match_t:
            sacos_tarde = int(match_t.group(1))
            lbs_tarde = float(match_t.group(2).replace(',', '.'))

        # 3. Hectáreas
        ha_m = re.search(r'(\d+)\s*Hectarias?\s*(y\s*½|1\/2)?', texto, re.I)
        ha_trabajadas = float(ha_m.group(1)) if ha_m else 0.0
        if ha_m and ha_m.group(2): ha_trabajadas += 0.5

        # 4. Actividad Principal
        texto_upper = texto.upper()
        act_nombre = "COSECHA"
        if "FUMIGACION" in texto_upper or "FUMIGACIÓN" in texto_upper:
            act_nombre = "FUMIGACION"
        elif "CORTE DE MONTE" in texto_upper or "DESBROCE" in texto_upper:
            act_nombre = "CORTE DE MONTE"
        elif "DESVENADO" in texto_upper:
            act_nombre = "DESVENADO"

        # 5. Mapear Lotes Mencionados
        actividades = []
        for lote_real, aliases in ALIASES_LOTES.items():
            for alias in aliases:
                if alias in texto_upper:
                    if {"actividad": act_nombre, "lote": lote_real} not in actividades:
                        actividades.append({"actividad": act_nombre, "lote": lote_real})
                    break

        # 6. Parser de Personal
        personal_dia = []
        lineas = texto.split('\n')
        palabras_ignorar = [
            "cosecha", "corte", "monte", "fumigacion", "fumigación", "rendimiento", 
            "mañana", "tarde", "lote", "lotes", "sacos", "lbs", "libras", "progreso", 
            "total", "realizado", "pendiente", "hectarias", "hectáreas", "actividades", 
            "reporte", "finca", "cacaomar", "efectuadas", "trabajó", "personas"
        ]

        for line in lineas:
            line_clean = line.strip()
            if line_clean.startswith(('•', '-', '*', '.')):
                cand = re.sub(r'^[•\-\*\.]\s*', '', line_clean).strip()
                cand = re.sub(r'\(.*?\)', '', cand).strip()
                
                if len(cand) > 3 and not any(p in cand.lower() for p in palabras_ignorar):
                    jornada = "Día Completo"
                    if "tarde" in line.lower(): jornada = "Tarde (a partir de 1:00 PM)"
                    elif "3:00" in line.lower(): jornada = "Hasta 3:00 PM"

                    if {"nombre": cand, "asistencia": "Presente", "jornada": jornada} not in personal_dia:
                        personal_dia.append({"nombre": cand, "asistencia": "Presente", "jornada": jornada})

        return {
            "fecha": fecha,
            "actividad_principal": act_nombre,
            "sacos_manana": sacos_manana,
            "sacos_tarde": sacos_tarde,
            "lbs_tarde": lbs_tarde,
            "total_sacos": sacos_manana + sacos_tarde,
            "total_lbs": lbs_tarde,
            "ha_trabajadas": ha_trabajadas if ha_trabajadas > 0 else (11.5 if act_nombre == "COSECHA" else 0.0),
            "actividades": actividades,
            "personal": personal_dia,
            "texto_raw": texto
        }
    except Exception:
        return {
            "fecha": datetime.today().strftime('%d-%m-%Y'),
            "actividad_principal": "COSECHA",
            "sacos_manana": 0, "sacos_tarde": 0, "lbs_tarde": 0.0,
            "total_sacos": 0, "total_lbs": 0.0, "ha_trabajadas": 0.0,
            "actividades": [], "personal": [], "texto_raw": texto
        }

# ==========================================
# 🗺️ 4. GENERADOR DEL MAPA INTERACTIVO
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
# 📌 5. NAVEGACIÓN Y MENÚ LATERAL
# ==========================================
st.sidebar.title("📌 Menú CACAOMAR v15.0")
opcion = st.sidebar.radio(
    "Seleccione Módulo:",
    [
        "1. ⚡ Registrar Reporte Diario",
        "2. 👥 Gestionar Personal & Nómina",
        "3. 📋 Catálogo de Actividades",
        "4. 📅 Control de Asistencia",
        "5. 📊 Historial y Exportar Excel",
        "6. 🗺️ Mapa Operacional de Finca",
        "7. 📄 Exportar Reporte Diario PDF",
        "8. 🚜 Maquinaria y Taller",
        "9. 📦 Inventario de Insumos",
        "10. ⚙️ Configuración & Base de Datos"
    ]
)

# ------------------------------------------
# OPCIÓN 1: REGISTRAR REPORTE DIARIO
# ------------------------------------------
if opcion.startswith("1."):
    st.markdown("<h1>CACAOMAR <span style='font-size: 18px; color: #2e7d32;'>(v15.0 - Sistema Integral)</span></h1>", unsafe_allow_html=True)
    st.caption("Gestión Agrícola, Procesamiento con IA Local y SQLite")
    st.subheader("⚡ Registrar Reporte Diario de Operaciones")

    texto_ingresado = st.text_area("📋 Pega el reporte en texto aquí:", height=220)
    
    if st.button("🔄 Procesar y Guardar Reporte"):
        if texto_ingresado.strip():
            rep = procesar_texto_inteligente(texto_ingresado)
            
            # Guardar en SQLite
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''INSERT INTO reportes 
                        (fecha, actividad_principal, sacos_manana, sacos_tarde, lbs_tarde, total_sacos, total_lbs, ha_trabajadas, personal_json, actividades_json, texto_raw)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (rep['fecha'], rep['actividad_principal'], rep['sacos_manana'], rep['sacos_tarde'], 
                      rep['lbs_tarde'], rep['total_sacos'], rep['total_lbs'], rep['ha_trabajadas'],
                      str(rep['personal']), str(rep['actividades']), rep['texto_raw']))
            conn.commit()
            conn.close()

            st.session_state.reporte_actual = rep
            st.success("✅ ¡Reporte procesado y almacenado permanentemente en la base de datos!")
        else:
            st.warning("Por favor ingresa el texto del reporte.")

    if 'reporte_actual' in st.session_state and st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        st.markdown("---")
        st.markdown(f"### 📊 Resumen Procesado - {rep['fecha']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Labor Principal", rep['actividad_principal'])
        c2.metric("Área Avance", f"{rep['ha_trabajadas']} ha")
        c3.metric("Personal Activo", f"{len(rep['personal'])} Personas")
        c4.metric("Lotes Intervenidos", f"{len(rep['actividades'])} Lotes")

        # Verificación de Trabajadores Nuevos
        conn = sqlite3.connect(DB_NAME)
        df_p = pd.read_sql_query("SELECT nombre FROM personal", conn)
        conn.close()
        
        nombres_registrados = df_p['nombre'].tolist() if not df_p.empty else []
        nuevos_det = [p['nombre'] for p in rep['personal'] if p['nombre'] not in nombres_registrados]

        if nuevos_det:
            st.warning(f"💡 **Detección Automática:** Se encontraron {len(nuevos_det)} personas nuevas no registradas: {', '.join(nuevos_det)}")
            if st.button("➕ Registrar personas nuevas en Base de Datos"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for nom in nuevos_det:
                    c.execute("INSERT OR IGNORE INTO personal (nombre, cargo, tarifa_diaria) VALUES (?, ?, ?)", (nom, "Cosechador/Campo", 15.0))
                conn.commit()
                conn.close()
                st.success("¡Personal registrado en la base de datos exitosamente!")

        st.subheader("🗺️ Mapa Operacional de Avance")
        mapa = generar_mapa_coloreado(rep['actividades'])
        st.image(mapa, caption="Vista general de la finca", use_column_width=True)

# ------------------------------------------
# OPCIÓN 2: GESTIONAR PERSONAL & NÓMINA
# ------------------------------------------
elif opcion.startswith("2."):
    st.title("👥 Personal y Estructura de Nómina")
    conn = sqlite3.connect(DB_NAME)
    df_p = pd.read_sql_query("SELECT * FROM personal", conn)
    conn.close()

    st.dataframe(df_p, use_container_width=True)

    with st.expander("➕ Agregar Nuevo Trabajador Manualmente"):
        with st.form("form_nuevo_p"):
            nom = st.text_input("Nombre Completo:")
            cargo = st.text_input("Cargo / Labor Principal:", "Cosechador")
            tarifa = st.number_input("Tarifa Diaria ($):", value=15.0)
            if st.form_submit_button("Guardar Trabajador"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO personal (nombre, cargo, tarifa_diaria) VALUES (?, ?, ?)", (nom, cargo, tarifa))
                conn.commit()
                conn.close()
                st.success("Trabajador registrado.")
                st.rerun()

# ------------------------------------------
# OPCIÓN 5: HISTORIAL Y EXPORTAR EXCEL
# ------------------------------------------
elif opcion.startswith("5."):
    st.title("📊 Historial General y Exportación a Excel")
    conn = sqlite3.connect(DB_NAME)
    df_rep = pd.read_sql_query("SELECT id, fecha, actividad_principal, total_sacos, total_lbs, ha_trabajadas FROM reportes ORDER BY id DESC", conn)
    conn.close()

    st.dataframe(df_rep, use_container_width=True)

    if not df_rep.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_rep.to_excel(writer, sheet_name='Reportes_Historicos', index=False)
        
        st.download_button(
            label="📥 Descargar Historial Completo en Excel (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"CACAOMAR_Historial_{datetime.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )

# ------------------------------------------
# OPCIÓN 6: MAPA OPERACIONAL
# ------------------------------------------
elif opcion.startswith("6."):
    st.title("🗺️ Mapa Operacional por Lote")
    actividades_act = st.session_state.reporte_actual['actividades'] if 'reporte_actual' in st.session_state and st.session_state.reporte_actual else []
    mapa_gen = generar_mapa_coloreado(actividades_act)
    st.image(mapa_gen, caption="Estado de lotes en la finca", use_column_width=True)

# ------------------------------------------
# OPCIÓN 7: EXPORTAR REPORTE PDF
# ------------------------------------------
elif opcion.startswith("7."):
    st.title("📄 Exportar Reporte Diario Oficial PDF")
    
    if 'reporte_actual' in st.session_state and st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        mapa_img = generar_mapa_coloreado(rep['actividades'])

        buffered = io.BytesIO()
        mapa_img.save(buffered, format="JPEG")
        mapa_b64 = base64.b64encode(buffered.getvalue()).decode()

        filas_personal = ""
        for p in rep['personal']:
            badge_class = "badge-green"
            jornada_txt = p.get('jornada', 'Día Completo')
            if "3:00" in jornada_txt: badge_class = "badge-blue"
            elif "Tarde" in jornada_txt: badge_class = "badge-orange"

            filas_personal += f"""
            <tr>
                <td><b>{p['nombre']}</b></td>
                <td>{rep['actividad_principal']} / Campo</td>
                <td><span class="badge {badge_class}">{jornada_txt}</span></td>
            </tr>
            """

        lotes_str = ", ".join([a['lote'].title() for a in rep['actividades']]) if rep['actividades'] else "Ninguno registrado"

        html_pdf = f"""<!DOCTYPE html>
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
        .card-val {{ font-size: 15px; font-weight: bold; color: #2e7d32; margin: 3px 0; }}
        .card-sub {{ font-size: 9px; color: #777; }}
        .sec-header {{ background: #2e7d32; color: white; font-weight: bold; padding: 5px 8px; font-size: 11px; margin-top: 12px; border-radius: 2px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 10px; }}
        th {{ background: #43a047; color: white; text-align: left; padding: 5px; font-size: 10px; }}
        td {{ border-bottom: 1px solid #eee; padding: 5px; color: #333; }}
        .badge {{ padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: bold; display: inline-block; }}
        .badge-green {{ background: #e8f5e9; color: #1b5e20; border: 1px solid #c8e6c9; }}
        .badge-blue {{ background: #e3f2fd; color: #0d47a1; border: 1px solid #bbdefb; }}
        .badge-orange {{ background: #fff3e0; color: #e65100; border: 1px solid #e65100; }}
        .progress-box {{ background: #f9f9f9; border: 1px solid #e0e0e0; padding: 6px; margin-top: 4px; font-size: 9.5px; border-radius: 3px; }}
        .map-container {{ text-align: center; margin-top: 10px; border: 1px solid #ddd; padding: 8px; border-radius: 4px; background: #fafafa; }}
        .map-container img {{ width: 100%; max-width: 600px; border-radius: 3px; }}
        .map-legend {{ display: flex; justify-content: center; gap: 15px; margin-top: 8px; padding-top: 6px; border-top: 1px solid #eee; font-size: 9.5px; }}
        .legend-item {{ display: flex; align-items: center; gap: 5px; font-weight: 500; color: #444; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
        .dot-green {{ background: #2ecc71; }}
        .dot-orange {{ background: #e67e22; }}
        .dot-yellow {{ background: #f1c40f; }}
        .dot-purple {{ background: #9b59b6; }}
        .dot-blue {{ background: #3498db; }}
    </style>
</head>
<body>
    <div class="title">REPORTE DIARIO DE AVANCE Y COSECHA - CACAOMAR</div>
    <div class="subtitle">Fecha: {rep['fecha']} | Área Total: 39.00 ha | Personal Total: {len(rep['personal'])} Personas</div>

    <div class="cards">
        <div class="card">
            <div class="card-title">Cosecha del Día</div>
            <div class="card-val">{rep['total_sacos']} Sacos</div>
            <div class="card-sub">+ {rep['total_lbs']} lbs</div>
        </div>
        <div class="card">
            <div class="card-title">Área Trabajada Hoy</div>
            <div class="card-val">{rep['ha_trabajadas']} ha</div>
            <div class="card-sub">{len(rep['actividades'])} Lotes intervenidos</div>
        </div>
        <div class="card">
            <div class="card-title">Labor Principal</div>
            <div class="card-val">{rep['actividad_principal']}</div>
            <div class="card-sub">Jornada de Campo</div>
        </div>
        <div class="card">
            <div class="card-title">Personal Activo</div>
            <div class="card-val">{len(rep['personal'])} Personas</div>
            <div class="card-sub">Cuadrilla en Finca</div>
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
        <b>Lotes Intervenidos Hoy ({rep['ha_trabajadas']} ha):</b> {lotes_str}.<br>
        <b>Labor Ejecutada:</b> {rep['actividad_principal']}.
    </div>

    <div class="sec-header">2. ASISTENCIA Y DISTRIBUCIÓN DE PERSONAL ({len(rep['personal'])} PERSONAS)</div>
    <table>
        <tr>
            <th>TRABAJADOR</th>
            <th>LABOR PRINCIPAL</th>
            <th>JORNADA / HORARIO</th>
        </tr>
        {filas_personal}
    </table>

    <div class="sec-header">3. MAPA OPERACIONAL Y LEYENDA DE AVANCE DE FINCA</div>
    <div class="map-container">
        <img src="data:image/jpeg;base64,{mapa_b64}" />
        <div class="map-legend">
            <div class="legend-item"><span class="dot dot-green"></span> Cosecha</div>
            <div class="legend-item"><span class="dot dot-blue"></span> Fumigación</div>
            <div class="legend-item"><span class="dot dot-orange"></span> Corte de Monte</div>
            <div class="legend-item"><span class="dot dot-yellow"></span> Monilla</div>
            <div class="legend-item"><span class="dot dot-purple"></span> Desvenado</div>
        </div>
    </div>
</body>
</html>"""

        st.components.v1.html(html_pdf, height=850, scrolling=True)

        st.download_button(
            label="📥 Descargar Reporte PDF Oficial Completo",
            data=html_pdf,
            file_name=f"Reporte_CACAOMAR_{rep['fecha']}.html",
            mime="text/html"
        )
    else:
        st.warning("⚠️ Primero procesa un reporte en la Opción 1.")

# ------------------------------------------
# OPCIONES RESTANTES (MÓDULOS EN DESARROLLO)
# ------------------------------------------
elif opcion.startswith("3."):
    st.title("📋 Catálogo de Actividades")
    st.write(st.session_state.catalogo_actividades)

elif opcion.startswith("4."):
    st.title("📅 Control de Asistencia Semanal")

elif opcion.startswith("8."):
    st.title("🚜 Maquinaria y Taller")

elif opcion.startswith("9."):
    st.title("📦 Inventario de Insumos")

elif opcion.startswith("10."):
    st.title("⚙️ Configuración & Base de Datos")
    st.success(f"Base de datos SQLite activa: `{DB_NAME}`")
