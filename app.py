import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import io
import base64
import sqlite3
import hashlib

# ==========================================
# 🌾 1. CONFIGURACIÓN Y BASE DE DATOS
# ==========================================
st.set_page_config(page_title="CACAOMAR v15.0 - Motor Dinámico", page_icon="🌾", layout="wide")

DB_NAME = "cacaomar.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS personal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    cargo TEXT,
                    tarifa_diaria REAL DEFAULT 0.0
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS reportes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    actividad_principal TEXT,
                    sacos_total INTEGER,
                    lbs_total REAL,
                    tanques INTEGER,
                    pomas INTEGER,
                    ha_trabajadas REAL,
                    personal_json TEXT,
                    actividades_json TEXT,
                    observaciones TEXT,
                    texto_raw TEXT
                )''')
    
    c.execute("SELECT COUNT(*) FROM personal")
    if c.fetchone()[0] == 0:
        personal_inicial = [
            ("Jackson Andrade", "Multifunción", 15.0),
            ("Reynaldo Andrade", "Multifunción", 15.0),
            ("David Pacheco", "Aplicador / Campo", 15.0),
            ("Jacqueline Quiroz", "Aplicador / Fumigación", 15.0)
        ]
        c.executemany("INSERT INTO personal (nombre, cargo, tarifa_diaria) VALUES (?, ?, ?)", personal_inicial)
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 🎨 2. GENERADOR AUTÓNOMO DE COLORES (HASH)
# ==========================================
def obtener_color_actividad(nombre_actividad):
    """
    Genera un color RGB único y consistente a partir del texto de la actividad.
    Permite que Cualquier Actividad Nueva reciba su propio color automáticamente.
    """
    act_clean = nombre_actividad.strip().upper()
    
    colores_fijos = {
        "COSECHA": (39, 174, 96, 150),              # Verde
        "FUMIGACION DE MONTE": (52, 152, 219, 150),  # Azul
        "CORTE DE MONTE": (230, 126, 34, 150)       # Naranja
    }
    if act_clean in colores_fijos:
        return colores_fijos[act_clean]
    
    hash_val = int(hashlib.md5(act_clean.encode('utf-8')).hexdigest(), 16)
    r = (hash_val & 0xFF0000) >> 16
    g = (hash_val & 0x00FF00) >> 8
    b = (hash_val & 0x0000FF)
    
    r = int((r + 100) / 2)
    g = int((g + 100) / 2)
    b = int((b + 100) / 2)
    
    return (r, g, b, 150)

# ==========================================
# 🗺️ 3. COORDENADAS Y ALIAS DE LOTES
# ==========================================
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
    "CUBO": ["CUBO", "LAS CUBO", "EL CUBO"],
    "EUROPEA": ["EUROPEA", "LA EUROPEA"],
    "CARRETERO": ["CARRETERO", "EL CARRETERO"],
    "LAS TECAS": ["LAS TECAS", "TECAS"],
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
# 🧠 4. PARSER INTELIGENTE Y AUTÓNOMO
# ==========================================
def procesar_texto_inteligente(texto):
    try:
        # 1. Extraer Fecha
        fecha_m = re.search(r'(\d{2}[\-\/]\d{2}[\-\/]\d{4})', texto)
        fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%d-%m-%Y')

        # 2. Extraer Actividad Principal Dinámicamente
        act_nombre = "MANTENIMIENTO GENERAL"
        match_act = re.search(r'(?:actividades de:|actividad:)\s*([^\n\•\*\.]+)', texto, re.I)
        if match_act:
            act_nombre = match_act.group(1).strip().upper()
            act_nombre = re.sub(r'^[🌿🌾🍂🍇🧹✂️\s]+', '', act_nombre)
        else:
            for line in texto.split('\n'):
                if any(k in line.lower() for k in ["fumigacion", "fumigación", "cosecha", "corte", "poda", "desvenado", "resiembra"]):
                    act_nombre = line.replace('•', '').replace('🌿', '').strip().upper()
                    break

        # 3. Datos Cuantitativos
        sacos_m = re.search(r'(\d+)\s*sacos', texto, re.I)
        sacos_total = int(sacos_m.group(1)) if sacos_m else 0
        
        lbs_m = re.search(r'([\d\.,]+)\s*lbs', texto, re.I)
        lbs_total = float(lbs_m.group(1).replace(',', '.')) if lbs_m else 0.0

        tanques_m = re.search(r'(\d+)\s*tanques', texto, re.I)
        tanques = int(tanques_m.group(1)) if tanques_m else 0
        
        pomas_m = re.search(r'(\d+)\s*pomas', texto, re.I)
        pomas = int(pomas_m.group(1)) if pomas_m else (tanques * 10 if tanques > 0 else 0)

        ha_m = re.search(r'(\d+)\s*Hectarias?\s*(y\s*½|1\/2)?', texto, re.I)
        ha_trabajadas = float(ha_m.group(1)) if ha_m else 0.0
        if ha_m and ha_m.group(2): ha_trabajadas += 0.5

        # 4. Lotes Intervenidos
        texto_upper = texto.upper()
        actividades = []
        for lote_real, aliases in ALIASES_LOTES.items():
            for alias in aliases:
                if alias in texto_upper:
                    if {"actividad": act_nombre, "lote": lote_real} not in actividades:
                        actividades.append({"actividad": act_nombre, "lote": lote_real})
                    break

        # 5. Personal Activo
        personal_dia = []
        palabras_ignorar = ["cosecha", "fumigacion", "fumigación", "monte", "rendimiento", "sacos", "pomas", "tanques", "hectarias", "realizado", "pendiente"]
        for line in texto.split('\n'):
            line_clean = line.strip()
            if line_clean.startswith(('•', '-', '*', '.')):
                cand = re.sub(r'^[•\-\*\.]\s*', '', line_clean).strip()
                cand = re.sub(r'\(.*?\)', '', cand).strip()
                if len(cand) > 3 and not any(p in cand.lower() for p in palabras_ignorar):
                    personal_dia.append({"nombre": cand, "asistencia": "Presente", "jornada": "Día Completo"})

        # 6. Observaciones de Campo
        obs = ""
        if "Cabe destacar" in texto:
            obs = "Cabe destacar " + texto.split("Cabe destacar")[-1].strip()
        elif "Observación" in texto or "Observacion" in texto:
            obs = texto.split("Observación")[-1].strip()

        return {
            "fecha": fecha,
            "actividad_principal": act_nombre,
            "sacos_total": sacos_total,
            "lbs_total": lbs_total,
            "tanques": tanques,
            "pomas": pomas,
            "ha_trabajadas": ha_trabajadas,
            "actividades": actividades,
            "personal": personal_dia,
            "observaciones": obs,
            "texto_raw": texto
        }
    except Exception as e:
        return {"fecha": datetime.today().strftime('%d-%m-%Y'), "actividad_principal": "MANTENIMIENTO", "personal": [], "actividades": [], "texto_raw": texto}

# ==========================================
# 🗺️ 5. MOTOR DE MAPA AUTÓNOMO
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
            color = obtener_color_actividad(act_nombre)
            draw.rectangle(box, fill=color, outline=(20, 80, 150, 255), width=3)

    resultado = Image.alpha_composite(base_img, overlay)
    return resultado.convert("RGB")

# ==========================================
# 📌 6. INTERFAZ Y NAVEGACIÓN
# ==========================================
st.sidebar.title("📌 CACAOMAR v15.0")
opcion = st.sidebar.radio(
    "Seleccione Módulo:",
    [
        "1. ⚡ Registrar Reporte Diario",
        "2. 👥 Gestionar Personal",
        "3. 📊 Historial de Registros",
        "4. 🗺️ Mapa Operacional",
        "5. 📄 Exportar PDF Dinámico"
    ]
)

# ------------------------------------------
# OPCIÓN 1: REGISTRAR REPORTE
# ------------------------------------------
if opcion.startswith("1."):
    st.markdown("<h1>CACAOMAR <span style='font-size: 18px; color: #2e7d32;'>(Sistema Autónomo)</span></h1>", unsafe_allow_html=True)
    st.caption("Ingresa cualquier reporte. El sistema detecta labores, insumos y asigna colores de forma automática.")
    
    texto_ingresado = st.text_area("📋 Pega la información del día aquí:", height=220)
    
    if st.button("🔄 Procesar y Guardar Reporte"):
        if texto_ingresado.strip():
            rep = procesar_texto_inteligente(texto_ingresado)
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute('''INSERT INTO reportes 
                        (fecha, actividad_principal, sacos_total, lbs_total, tanques, pomas, ha_trabajadas, personal_json, actividades_json, observaciones, texto_raw)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (rep['fecha'], rep['actividad_principal'], rep['sacos_total'], rep['lbs_total'], 
                      rep['tanques'], rep['pomas'], rep['ha_trabajadas'],
                      str(rep['personal']), str(rep['actividades']), rep['observaciones'], rep['texto_raw']))
            conn.commit()
            conn.close()

            st.session_state.reporte_actual = rep
            st.success(f"✅ ¡Reporte procesado! Actividad detectada: **{rep['actividad_principal']}**")
        else:
            st.warning("Ingresa un texto para procesar.")

    if 'reporte_actual' in st.session_state and st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        st.markdown("---")
        st.markdown(f"### 📊 Resumen Procesado Automáticamente - {rep['fecha']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Actividad Detectada", rep['actividad_principal'])
        c2.metric("Superficie", f"{rep['ha_trabajadas']} ha")
        
        if rep['sacos_total'] > 0:
            c3.metric("Cosecha", f"{rep['sacos_total']} Sacos / {rep['lbs_total']} lbs")
        elif rep['pomas'] > 0 or rep['tanques'] > 0:
            c3.metric("Insumos", f"{rep['pomas']} Pomas ({rep['tanques']} Tanques)")
        else:
            c3.metric("Avance", "Jornada Completa")
            
        c4.metric("Personal", f"{len(rep['personal'])} Personas")

        st.subheader("🗺️ Capa Visual Generada Auto-Adaptativamente")
        st.image(generar_mapa_coloreado(rep['actividades']), use_column_width=True)

# ------------------------------------------
# OPCIÓN 2: PERSONAL
# ------------------------------------------
elif opcion.startswith("2."):
    st.title("👥 Personal Registrado")
    conn = sqlite3.connect(DB_NAME)
    df_p = pd.read_sql_query("SELECT * FROM personal", conn)
    conn.close()
    st.dataframe(df_p, use_container_width=True)

# ------------------------------------------
# OPCIÓN 3: HISTORIAL
# ------------------------------------------
elif opcion.startswith("3."):
    st.title("📊 Historial de Reportes")
    conn = sqlite3.connect(DB_NAME)
    df_rep = pd.read_sql_query("SELECT id, fecha, actividad_principal, ha_trabajadas, pomas, sacos_total FROM reportes ORDER BY id DESC", conn)
    conn.close()
    st.dataframe(df_rep, use_container_width=True)

# ------------------------------------------
# OPCIÓN 4: MAPA
# ------------------------------------------
elif opcion.startswith("4."):
    st.title("🗺️ Mapa Operacional de Finca")
    actividades_act = st.session_state.reporte_actual['actividades'] if 'reporte_actual' in st.session_state and st.session_state.reporte_actual else []
    st.image(generar_mapa_coloreado(actividades_act), use_column_width=True)

# ------------------------------------------
# OPCIÓN 5: PDF DINÁMICO AUTO-ADAPTATIVO
# ------------------------------------------
elif opcion.startswith("5."):
    st.title("📄 Generación de Reporte PDF Dinámico")
    
    if 'reporte_actual' in st.session_state and st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        mapa_img = generar_mapa_coloreado(rep['actividades'])

        buffered = io.BytesIO()
        mapa_img.save(buffered, format="JPEG")
        mapa_b64 = base64.b64encode(buffered.getvalue()).decode()

        filas_p = "".join([f"<tr><td><b>{p['nombre']}</b></td><td>{rep['actividad_principal']}</td><td><span class='badge badge-green'>Día Completo</span></td></tr>" for p in rep['personal']])
        lotes_str = ", ".join([a['lote'].title() for a in rep['actividades']]) if rep['actividades'] else "Ninguno"

        if rep['sacos_total'] > 0:
            titulo_sec1 = "1. REGISTRO DE COSECHA Y PRODUCCIÓN"
            tabla_sec1 = f"""
            <table>
                <tr><th>CONCEPTO</th><th>CANTIDAD</th><th>DETALLE</th></tr>
                <tr><td>Sacos Cosechados</td><td><b>{rep['sacos_total']} Sacos</b></td><td>Jornada Completa</td></tr>
                <tr><td>Libras Adicionales</td><td><b>{rep['lbs_total']} lbs</b></td><td>Sueltas</td></tr>
            </table>
            """
        elif rep['pomas'] > 0 or rep['tanques'] > 0:
            titulo_sec1 = f"1. CONTROL DE APLICACIÓN E INSUMOS ({rep['actividad_principal']})"
            prom_ha = (rep['pomas']/rep['ha_trabajadas']) if rep['ha_trabajadas'] > 0 else 0
            tabla_sec1 = f"""
            <table>
                <tr><th>CONCEPTO / INSUMO</th><th>CANTIDAD DETECTADA</th><th>PROMEDIO POR HECTÁREA</th></tr>
                <tr><td>Tanques Preparados/Usados</td><td><b>{rep['tanques']} Tanques</b></td><td>Aplicación en Campo</td></tr>
                <tr><td>Pomas Consumidas</td><td><b>{rep['pomas']} Pomas</b></td><td><b>{prom_ha:.1f} pomas/ha</b></td></tr>
            </table>
            """
        else:
            titulo_sec1 = f"1. RESUMEN DE AVANCE DE TRABAJO ({rep['actividad_principal']})"
            tabla_sec1 = f"""
            <table>
                <tr><th>LABOR EJECUTADA</th><th>SUPERFICIE CUBIERTA</th><th>ESTADO</th></tr>
                <tr><td><b>{rep['actividad_principal']}</b></td><td><b>{rep['ha_trabajadas']} ha</b></td><td>Completado en la jornada</td></tr>
            </table>
            """

        obs_box = f"""
        <div class="progress-box" style="margin-top:8px; background:#fffde7; border-color:#fff59d;">
            <b>📌 Observaciones de Campo:</b><br>{rep['observaciones']}
        </div>
        """ if rep['observaciones'] else ""

        html_pdf = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 15px; color: #222; background: #fff; }}
        .title {{ color: #1b5e20; font-size: 18px; font-weight: bold; border-bottom: 2px solid #1b5e20; padding-bottom: 4px; }}
        .subtitle {{ font-size: 11px; color: #555; margin-bottom: 12px; margin-top: 4px; }}
        .cards {{ display: flex; justify-content: space-between; margin-bottom: 12px; }}
        .card {{ background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px; width: 23%; text-align: center; }}
        .card-title {{ font-size: 9px; color: #666; font-weight: bold; text-transform: uppercase; }}
        .card-val {{ font-size: 13px; font-weight: bold; color: #2e7d32; margin: 3px 0; }}
        .sec-header {{ background: #2e7d32; color: white; font-weight: bold; padding: 5px 8px; font-size: 11px; margin-top: 12px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 4px; font-size: 10px; }}
        th {{ background: #43a047; color: white; text-align: left; padding: 5px; }}
        td {{ border-bottom: 1px solid #eee; padding: 5px; }}
        .badge {{ padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: bold; }}
        .badge-green {{ background: #e8f5e9; color: #1b5e20; border: 1px solid #c8e6c9; }}
        .progress-box {{ background: #f9f9f9; border: 1px solid #e0e0e0; padding: 6px; font-size: 9.5px; border-radius: 3px; }}
        .map-container {{ text-align: center; margin-top: 10px; border: 1px solid #ddd; padding: 8px; background: #fafafa; }}
        .map-container img {{ width: 100%; max-width: 600px; }}
    </style>
</head>
<body>
    <div class="title">REPORTE DIARIO DE OPERACIONES - CACAOMAR</div>
    <div class="subtitle">Fecha: {rep['fecha']} | Superficie Total: 39.00 ha | Personal: {len(rep['personal'])} Personas</div>

    <div class="cards">
        <div class="card">
            <div class="card-title">Actividad Principal</div>
            <div class="card-val">{rep['actividad_principal']}</div>
        </div>
        <div class="card">
            <div class="card-title">Área Intervenida</div>
            <div class="card-val">{rep['ha_trabajadas']} ha</div>
        </div>
        <div class="card">
            <div class="card-title">Insumos / Producción</div>
            <div class="card-val">{'Cosecha: ' + str(rep['sacos_total']) + ' sacos' if rep['sacos_total']>0 else str(rep['pomas']) + ' Pomas'}</div>
        </div>
        <div class="card">
            <div class="card-title">Personal Activo</div>
            <div class="card-val">{len(rep['personal'])} Personas</div>
        </div>
    </div>

    <div class="sec-header">{titulo_sec1}</div>
    {tabla_sec1}

    <div class="progress-box">
        <b>Lotes Intervenidos Hoy ({rep['ha_trabajadas']} ha):</b> {lotes_str}.
    </div>

    {obs_box}

    <div class="sec-header">2. ASISTENCIA DE PERSONAL ({len(rep['personal'])} PERSONAS)</div>
    <table>
        <tr><th>TRABAJADOR</th><th>LABOR</th><th>JORNADA</th></tr>
        {filas_p}
    </table>

    <div class="sec-header">3. MAPA OPERACIONAL Y AVANCE GENERADO</div>
    <div class="map-container">
        <img src="data:image/jpeg;base64,{mapa_b64}" />
    </div>
</body>
</html>"""

        st.components.v1.html(html_pdf, height=800, scrolling=True)

        st.download_button(
            label="📥 Descargar Reporte PDF Oficial",
            data=html_pdf,
            file_name=f"Reporte_CACAOMAR_{rep['fecha']}.html",
            mime="text/html"
        )
    else:
        st.warning("⚠️ Primero procesa un reporte en la Opción 1.")
