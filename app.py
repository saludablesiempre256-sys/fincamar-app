import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import random

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="CACAOMAR v10.0", page_icon="🌾", layout="wide")

# --- ESTADOS DE SESIÓN ---
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
        "COSECHA": (46, 204, 113, 110),           # Verde
        "CORTE DE MONTE": (230, 126, 34, 110),    # Naranja
        "TUMBADA DE MONILLA": (241, 196, 15, 110),# Amarillo
        "DESVENADO": (155, 89, 182, 110),        # Morado
        "FUMIGACION": (52, 152, 219, 110)         # Azul
    }

if 'historial_reportes' not in st.session_state:
    st.session_state.historial_reportes = []

if 'reporte_actual' not in st.session_state:
    st.session_state.reporte_actual = None

# Coordenadas ajustadas sobre la imagen real (mapa_finca.jpg)
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

# Aliases flexible para el lenguaje diario de los reportes
ALIASES_LOTES = {
    "MANDARINA": ["MANDARINA", "LA MANDARINA"],
    "LA PATERA": ["LA PATERA", "PATERA"],
    "CUBO": ["CUBO", "LAS CUBO", "EL CUBO"],
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

# --- PROCESAMIENTO ROBUSTO DE REPORTES ---
def procesar_texto_inteligente(texto):
    try:
        fecha_m = re.search(r'(\d{2}[\-\/]\d{2}[\-\/]\d{4})', texto)
        fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%d-%m-%Y')

        total_sacos = 0
        total_lbs = 0.0

        match_sacos_m = re.search(r'(\d+)\s*sacos?\s*(?:en la|de la)?\s*mañana', texto, re.I)
        if match_sacos_m:
            total_sacos += int(match_sacos_m.group(1))

        match_sacos_t = re.search(r'(\d+)\s*sacos?\s*con\s*([\d\.,]+)\s*libras', texto, re.I)
        if match_sacos_t:
            total_sacos += int(match_sacos_t.group(1))
            total_lbs += float(match_sacos_t.group(2).replace(',', '.'))
        else:
            match_global = re.search(r'total cosechado\s*:\?\s*(\d+)\s*sacos?\s*(?:con)?\s*([\d\.,]+)?\s*libras', texto, re.I)
            if match_global:
                total_sacos = int(match_global.group(1)) if match_global.group(1) else total_sacos
                if match_global.group(2):
                    total_lbs = float(match_global.group(2).replace(',', '.'))

        actividades = []
        texto_upper = texto.upper()

        for lote_real, aliases in ALIASES_LOTES.items():
            for alias in aliases:
                if alias in texto_upper:
                    act_nombre = "COSECHA"
                    if "MONTE" in texto_upper and alias in ["CUBO", "LAS CUBO", "EL CUBO"]:
                        act_nombre = "CORTE DE MONTE"
                    
                    if {"actividad": act_nombre, "lote": lote_real} not in actividades:
                        actividades.append({"actividad": act_nombre, "lote": lote_real})
                    break

        nombres_existentes = [p["nombre"].lower() for p in st.session_state.personal]
        personal_dia = []

        patron_personas = r'[•\-]\s*([A-Za-zÁéíóúÁÉÍÓÚñÑ\s]+)'
        posibles_nombres = re.findall(patron_personas, texto)
        palabras_filtro = ["cosecha", "corte de monte", "tumbada de monilla", "mañana", "tarde", "desvenador", "pesado y llenado de sacos", "progreso total", "total cosechado", "realizado", "pendiente"]

        for n in posibles_nombres:
            nombre_clean = re.sub(r'\(.*?\)', '', n).strip()
            if nombre_clean.lower() not in palabras_filtro and len(nombre_clean) > 3:
                if {"nombre": nombre_clean, "asistencia": "Presente"} not in personal_dia:
                    personal_dia.append({"nombre": nombre_clean, "asistencia": "Presente"})
                if nombre_clean.lower() not in nombres_existentes:
                    st.session_state.personal.append({"nombre": nombre_clean, "cargo": "General"})
                    nombres_existentes.append(nombre_clean.lower())

        return {
            "fecha": fecha,
            "total_sacos": total_sacos,
            "total_lbs": total_lbs,
            "actividades": actividades,
            "personal": personal_dia,
            "texto_raw": texto
        }
    except Exception:
        return {
            "fecha": datetime.today().strftime('%d-%m-%Y'),
            "total_sacos": 0,
            "total_lbs": 0.0,
            "actividades": [],
            "personal": [],
            "texto_raw": texto
        }

# --- GENERADOR DEL MAPA EN VIVO ---
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
            color = st.session_state.catalogo_actividades.get(act_nombre, (128, 128, 128, 110))
            draw.rectangle(box, fill=color, outline=(0, 0, 0, 255), width=3)

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

    metodo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"], horizontal=True)

    if metodo == "Pegar Texto Automático":
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

    else:
        st.info("Formulario manual habilitado.")
        fecha_manual = st.date_input("Fecha:", datetime.today())
        sacos_manual = st.number_input("Sacos cosechados:", min_value=0, step=1)
        lbs_manual = st.number_input("Libras sueltas:", min_value=0.0, step=0.5)
        if st.button("Guardar Reporte Manual"):
            st.success("Reporte manual guardado.")

# ------------------------------------------
# OPCIÓN 2: GESTIONAR PERSONAL
# ------------------------------------------
elif opcion.startswith("2."):
    st.title("👥 Gestionar Personal")
    st.dataframe(pd.DataFrame(st.session_state.personal), use_container_width=True)

# ------------------------------------------
# OPCIÓN 3: CREAR / VER TAREAS NUEVAS
# ------------------------------------------
elif opcion.startswith("3."):
    st.title("📋 Crear / Ver Tareas Nuevas")
    st.dataframe(pd.DataFrame(list(st.session_state.catalogo_actividades.keys()), columns=["Tarea / Actividad"]), use_container_width=True)

# ------------------------------------------
# OPCIÓN 5: HISTORIAL DE REPORTES
# ------------------------------------------
elif opcion.startswith("5."):
    st.title("📊 Historial de Reportes")
    if st.session_state.historial_reportes:
        for idx, r in enumerate(st.session_state.historial_reportes, 1):
            with st.expander(f"Reporte #{idx} - Fecha: {r['fecha']}"):
                st.write(f"**Sacos:** {r['total_sacos']} | **Libras:** {r['total_lbs']}")
                st.text(r['texto_raw'])
    else:
        st.info("No hay reportes registrados aún en esta sesión.")

# ------------------------------------------
# OPCIÓN 6: MAPA DE AVANCE POR LOTE
# ------------------------------------------
elif opcion.startswith("6."):
    st.title("🗺️ Mapa de Avance por Lote")
    actividades_actuales = st.session_state.reporte_actual['actividades'] if st.session_state.reporte_actual else []
    mapa_general = generar_mapa_coloreado(actividades_actuales)
    st.image(mapa_general, caption="Estado Actual de la Finca", use_column_width=True)

# ------------------------------------------
# OPCIÓN 7: EXPORTAR REPORTE DIARIO PDF / DOCUMENTO (DESCARGA REAL CORREGIDA)
# ------------------------------------------
elif opcion.startswith("7."):
    st.title("📄 Exportar Reporte Diario PDF")
    
    if st.session_state.reporte_actual:
        rep = st.session_state.reporte_actual
        st.subheader(f"Vista previa de descarga - Fecha: {rep['fecha']}")
        
        # Generar contenido del documento imprimible/descargable
        contenido_reporte = f"""==================================================
              FINCA CACAOMAR
       REPORTE DIARIO DE OPERACIONES
==================================================
Fecha: {rep['fecha']}

[RESUMEN DE PRODUCCIÓN]
- Total Sacos Cosechados: {rep['total_sacos']}
- Libras Fracción: {rep['total_lbs']} lbs
- Lotes Trabajados: {len(rep['actividades'])}
- Personal Presente: {len(rep['personal'])} personas

[DETALLE DE ACTIVIDADES Y LOTES]
"""
        for act in rep['actividades']:
            contenido_reporte += f"• Actividad: {act['actividad']} | Lote: {act['lote']}\n"

        contenido_reporte += "\n[PERSONAL DETECTADO]\n"
        for p in rep['personal']:
            contenido_reporte += f"• {p['nombre']} ({p['asistencia']})\n"

        contenido_reporte += f"\n[TEXTO ORIGINAL DEL INFORME]\n{rep['texto_raw']}\n"
        contenido_reporte += "=================================================="

        st.text_area("Contenido del Reporte:", value=contenido_reporte, height=250)

        # BOTÓN OFICIAL DE DESCARGA EN EL CELULAR/SISTEMA
        st.download_button(
            label="📥 Descargar Reporte Diario (.txt / .pdf)",
            data=contenido_reporte,
            file_name=f"Reporte_CACAOMAR_{rep['fecha']}.txt",
            mime="text/plain"
        )
    else:
        st.warning("⚠️ Primero debes ingresar y procesar un reporte en la Opción 1 para poder descargarlo.")

# ------------------------------------------
# RESTO DE MÓDULOS (4, 8, 9, 10)
# ------------------------------------------
elif opcion.startswith("4."):
    st.title("📅 Asistencia y Nómina Semanal")

elif opcion.startswith("8."):
    st.title("📄 Exportar Nómina PDF")

elif opcion.startswith("9."):
    st.title("🚜 Control de Maquinaria y Taller")

elif opcion.startswith("10."):
    st.title("⚙️ Configuración de Finca")
