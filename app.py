import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import random

# Configuración de la app
st.set_page_config(page_title="CACAOMAR - Control Agrícola", page_icon="🌾", layout="wide")

# --- BASE DE DATOS DINÁMICA (Personal y Actividades) ---
if 'personal_registrado' not in st.session_state:
    st.session_state.personal_registrado = []

if 'catalogo_actividades' not in st.session_state:
    # Catálogo inicial de actividades con sus colores para el mapa (RGBA)
    st.session_state.catalogo_actividades = {
        "COSECHA": (46, 204, 113, 110),        # Verde
        "CORTE DE MONTE": (230, 126, 34, 110), # Naranja
        "DESVENADO": (155, 89, 182, 110),     # Morado
        "FUMIGACION": (52, 152, 219, 110)      # Azul
    }

if 'reporte_actual' not in st.session_state:
    st.session_state.reporte_actual = None

# --- COORDENADAS DE LOS LOTES SOBRE EL MAPA REAL ---
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

# Generador de colores aleatorios para actividades totalmente nuevas
def generar_color_nuevo():
    return (random.randint(50, 220), random.randint(50, 220), random.randint(50, 220), 110)

# --- PROCESADOR INTELIGENTE DE TEXTO ---
def procesar_texto_inteligente(texto):
    # 1. Fecha
    fecha_m = re.search(r'Fecha:\s*([\d\-\.\/]+)', texto, re.IGNORECASE)
    fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%Y-%m-%d')
    
    # 2. Cosecha del día
    sm = int(re.search(r'Mañana:\s*(\d+)\s*sacos', texto, re.IGNORECASE).group(1)) if re.search(r'Mañana:\s*(\d+)\s*sacos', texto, re.IGNORECASE) else 0
    lm = float(re.search(r'Mañana:[^,]+,\s*([\d\.]+)\s*lbs', texto, re.IGNORECASE).group(1)) if re.search(r'Mañana:[^,]+,\s*([\d\.]+)\s*lbs', texto, re.IGNORECASE) else 0.0
    st_s = int(re.search(r'Tarde:\s*(\d+)\s*sacos', texto, re.IGNORECASE).group(1)) if re.search(r'Tarde:\s*(\d+)\s*sacos', texto, re.IGNORECASE) else 0
    lt = float(re.search(r'Tarde:[^,]+,\s*([\d\.]+)\s*lbs', texto, re.IGNORECASE).group(1)) if re.search(r'Tarde:[^,]+,\s*([\d\.]+)\s*lbs', texto, re.IGNORECASE) else 0.0

    total_lbs_raw = lm + lt
    sacos_extra = int(total_lbs_raw // 100)
    lbs_finales = total_lbs_raw % 100
    total_sacos = sm + st_s + sacos_extra

    # 3. ACTIVIDADES (DETECCIÓN Y AUTO-REGISTRO DE LABORES NUEVAS)
    actividades = []
    bloque_a = re.search(r'ACTIVIDADES DEL DÍA:(.*?)(?=PERSONAL Y ROLES|$)', texto, re.DOTALL | re.IGNORECASE)
    if bloque_a:
        for linea in bloque_a.group(1).strip().split('\n'):
            match = re.search(r'-\s*([^:]+):\s*(.+)', linea)
            if match:
                act_nombre = match.group(1).strip().upper()
                lote_nombre = match.group(2).strip().upper()

                # Si es una actividad NUEVA que no teníamos registrada, ¡la creamos con su propio color!
                if act_nombre not in st.session_state.catalogo_actividades:
                    st.session_state.catalogo_actividades[act_nombre] = generar_color_nuevo()

                actividades.append({"actividad": act_nombre, "lote": lote_nombre})

    # 4. PERSONAL (MULTIFUNCIÓN Y AUTO-REGISTRO DE NOMBRES)
    personal_del_dia = []
    bloque_p = re.search(r'PERSONAL Y ROLES:(.*?)(?=COSECHA DEL DÍA|DESPACHO|$)', texto, re.DOTALL | re.IGNORECASE)
    
    if bloque_p:
        nombres_registrados = [p["nombre"].lower() for p in st.session_state.personal_registrado]
        
        for linea in bloque_p.group(1).strip().split('\n'):
            match = re.search(r'-\s*([^:]+):\s*(.+)', linea)
            if match:
                nombre = match.group(1).strip()
                labor_hoy = match.group(2).strip() # Rol multifunción del día
                
                # Registramos a la persona en la BD general si es nueva
                if nombre.lower() not in nombres_registrados:
                    st.session_state.personal_registrado.append({
                        "nombre": nombre,
                        "fecha_ingreso": fecha
                    })
                    nombres_registrados.append(nombre.lower())
                
                # Guardamos la función específica que hizo HOY
                personal_del_dia.append({"nombre": nombre, "labor_hoy": labor_hoy})

    # 5. Despacho enviado
    despachos = []
    bloque_d = re.search(r'DESPACHO ENVIADO HOY:(.*?)(?=Total Despacho|$)', texto, re.DOTALL | re.IGNORECASE)
    if bloque_d:
        for linea in bloque_d.group(1).strip().split('\n'):
            match = re.search(r'-\s*([\d\-\.\/]+):\s*(\d+)\s*sacos?,\s*([\d\.]+)\s*lbs', linea)
            if match:
                despachos.append({
                    "fecha": match.group(1).strip(),
                    "sacos": int(match.group(2)),
                    "libras": float(match.group(3))
                })

    return {
        "fecha": fecha,
        "sacos_m": sm, "lbs_m": lm,
        "sacos_t": st_s, "lbs_t": lt,
        "total_sacos": total_sacos, "total_lbs": lbs_finales,
        "personal": personal_del_dia,
        "actividades": actividades,
        "despacho": despachos
    }

# --- GENERADOR DEL MAPA RESALTADO MULTI-COLOR ---
def resaltar_mapa_real(actividades):
    ruta_mapa = "mapa_finca.jpg"
    
    if os.path.exists(ruta_mapa):
        base_img = Image.open(ruta_mapa).convert("RGBA")
    else:
        base_img = Image.new("RGBA", (1000, 1000), (240, 240, 240, 255))

    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    for act in actividades:
        lote_nombre = act["lote"]
        act_nombre = act["actividad"]

        if lote_nombre in COORDENADAS_LOTES:
            box = COORDENADAS_LOTES[lote_nombre]
            # Obtiene el color correspondiente del catálogo dinámico
            color = st.session_state.catalogo_actividades.get(act_nombre, (128, 128, 128, 110))
            draw.rectangle(box, fill=color, outline=(0, 0, 0, 255), width=3)

    resultado = Image.alpha_composite(base_img, overlay)
    return resultado.convert("RGB")

# --- INTERFAZ PRINCIPAL ---
st.title("🌾 CACAOMAR - Control Agrícola Multifunción")

texto_input = st.text_area("📋 Pega aquí el reporte del día:", height=220)

if st.button("🔄 Procesar Reporte"):
    if texto_input.strip():
        reporte = procesar_texto_inteligente(texto_input)
        st.session_state.reporte_actual = reporte
        st.success("¡Reporte procesado! Se actualizaron trabajadores, actividades y el mapa.")
    else:
        st.warning("Por favor pega el texto antes de procesar.")

if st.session_state.reporte_actual:
    rep = st.session_state.reporte_actual

    st.markdown("---")
    st.header(f"📊 Reporte del Día: {rep['fecha']}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Cosecha Total", f"{rep['total_sacos']} Sacos", f"{rep['total_lbs']} lbs")
    col2.metric("Personal en Campo", f"{len(rep['personal'])} Personas")
    col3.metric("Lotes Trabajados", f"{len(rep['actividades'])} Lotes")

    st.subheader("🗺️ Mapa Operacional Real")
    mapa_final = resaltar_mapa_real(rep['actividades'])
    st.image(mapa_final, caption="Lotes resaltados según la labor realizada hoy", use_column_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("👥 Personal y Labor Realizada Hoy")
        st.dataframe(pd.DataFrame(rep['personal']), use_container_width=True)
    
    with col_b:
        st.subheader("🛠️ Actividades Detectadas en el Sistema")
        # Muestra el catálogo dinámico de actividades que el sistema va aprendiendo
        df_act = pd.DataFrame([{"Actividad Registrada": k} for k in st.session_state.catalogo_actividades.keys()])
        st.dataframe(df_act, use_container_width=True)
