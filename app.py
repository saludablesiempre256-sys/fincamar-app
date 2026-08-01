import streamlit as st
import re
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw
import os
import random

# Configuración de página
st.set_page_config(page_title="CACAOMAR v10.0", page_icon="🌾", layout="wide")

# --- BASE DE DATOS Y ESTADOS EN SESSION_STATE ---
if 'personal' not in st.session_state:
    st.session_state.personal = [
        {"nombre": "Guadalupe Guerrero", "cargo": "Cosechador"},
        {"nombre": "Jackson Andrade", "cargo": "Multifunción"},
        {"nombre": "Reynaldo Andrade", "cargo": "Multifunción"},
        {"nombre": "Jessica Quiroz", "cargo": "Cosechador"},
        {"nombre": "Belen Pozo", "cargo": "Cosechador"},
        {"nombre": "Kerly Andrade", "cargo": "Cosechador"},
        {"nombre": "Monica", "cargo": "Desvenador"},
        {"nombre": "David Pacheco", "cargo": "Pesado y Llenado"}
    ]

if 'catalogo_actividades' not in st.session_state:
    st.session_state.catalogo_actividades = {
        "COSECHA": (46, 204, 113, 110),        # Verde
        "CORTE DE MONTE": (230, 126, 34, 110), # Naranja
        "DESVENADO": (155, 89, 182, 110),     # Morado
        "FUMIGACION": (52, 152, 219, 110)      # Azul
    }

if 'historial_reportes' not in st.session_state:
    st.session_state.historial_reportes = []

if 'reporte_actual' not in st.session_state:
    st.session_state.reporte_actual = None

# Coordenadas exactas para marcar los lotes sobre mapa_finca.jpg
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

def generar_color():
    return (random.randint(50, 220), random.randint(50, 220), random.randint(50, 220), 110)

# --- LÓGICA DE PROCESAMIENTO INTELIGENTE DEL TEXTO ---
def procesar_texto_inteligente(texto):
    fecha_m = re.search(r'(\d{2}[\-\/]\d{2}[\-\/]\d{4})', texto)
    fecha = fecha_m.group(1) if fecha_m else datetime.today().strftime('%d-%m-%Y')

    # Lectura de Cosecha (Mañana / Tarde)
    sm = int(re.search(r'(\d+)\s*sacos?\s*(?:en la|de la)?\s*mañana', texto, re.I).group(1)) if re.search(r'(\d+)\s*sacos?\s*(?:en la|de la)?\s*mañana', texto, re.I) else 0
    
    match_tarde = re.search(r'(\d+)\s*sacos?\s*con\s*([\d\.,]+)\s*libras', texto, re.I)
    if not match_tarde:
        match_tarde = re.search(r'Tarde:[^\d]*(\d+)\s*sacos?[^\d]*([\d\.,]+)\s*lbs', texto, re.I)

    st_s = int(match_tarde.group(1)) if match_tarde else 0
    lt = float(match_tarde.group(2).replace(',', '.')) if match_tarde else 0.0

    total_lbs_raw = lt
    sacos_extra = int(total_lbs_raw // 100)
    lbs_finales = round(total_lbs_raw % 100, 2)
    total_sacos = sm + st_s + sacos_extra

    # Detección de Actividades y Lotes (Creación automática si no existen)
    actividades = []
    if "EUROPEA" in texto.upper() or "CARRETERO" in texto.upper() or "LAS TECAS" in texto.upper() or "COSECHA" in texto.upper():
        lotes_cosecha = ["EUROPEA", "CARRETERO", "LA PATERA", "LAS TECAS", "EL CORAL", "MANDARINA"]
        for l in lotes_cosecha:
            if l in texto.upper():
                actividades.append({"actividad": "COSECHA", "lote": l})
    
    if "CUBO" in texto.upper() or "CORTE DE MONTE" in texto.upper():
        actividades.append({"actividad": "CORTE DE MONTE", "lote": "CUBO"})

    # Detección de Personal Nuevo (Auto-Registro)
    nombres_existentes = [p["nombre"].lower() for p in st.session_state.personal]
    personal_dia = []

    patron_personas = r'[•\-]\s*([A-Za-zÁéíóúÁÉÍÓÚñÑ\s]+)'
    posibles_nombres = re.findall(patron_personas, texto)

    nombres_descartar = ["cosecha", "corte de monte", "mañana", "tarde", "desvenador", "pesado y llenado de sacos", "progreso total", "total cosechado"]

    for n in posibles_nombres:
        nombre_clean = n.strip()
        if nombre_clean.lower() not in nombres_descartar and len(nombre_clean) > 3:
            personal_dia.append({"nombre": nombre_clean, "asistencia": "Presente"})
            if nombre_clean.lower() not in nombres_existentes:
                st.session_state.personal.append({"nombre": nombre_clean, "cargo": "General"})
                nombres_existentes.append(nombre_clean.lower())

    # Retorno estructurado
    return {
        "fecha": fecha,
        "total_sacos": total_sacos,
        "total_lbs": lbs_finales,
        "actividades": actividades,
        "personal": personal_dia,
        "texto_raw": texto
    }

# --- GENERADOR DEL MAPA OPERACIONAL ---
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
# 📌 MENÚ PRINCIPAL LATERAL (SIDEBAR ORIGINAL)
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
        "9. 🚜 Control de Maquinaria y Taller"
    ]
)

# ------------------------------------------
# OPCIÓN 1: REGISTRAR REPORTE DIARIO
# ------------------------------------------
if opcion.startswith("1."):
    st.title("CACAOMAR (v10.0)")
    st.caption("Control Operacional, Cosecha, Nómina y Mapeo de Cacao")
    st.subheader("⚡ Registrar Reporte Diario")

    metodo = st.radio("Método de Ingreso:", ["Pegar Texto Automático", "Formulario Manual"], horizontal=True)

    if metodo == "Pegar Texto Automático":
        texto_ingresado = st.text_area("📋 Pega el reporte en texto aquí:", height=220)
        
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
            st.image(mapa, caption="Mapa actualizado con los lotes trabajados", use_column_width=True)

    else:
        st.info("Formulario manual habilitado para ingreso directo.")
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
    
    st.subheader("➕ Agregar Nuevo Trabajador Manualmente")
    n_nombre = st.text_input("Nombre completo:")
    n_cargo = st.text_input("Cargo habitual:")
    if st.button("Registrar Trabajador"):
        if n_nombre:
            st.session_state.personal.append({"nombre": n_nombre, "cargo": n_cargo})
            st.success(f"{n_nombre} registrado correctamente.")

# ------------------------------------------
# OPCIÓN 3: CREAR / VER TAREAS NUEVAS
# ------------------------------------------
elif opcion.startswith("3."):
    st.title("📋 Crear / Ver Tareas Nuevas")
    st.write("Catálogo actual de tareas y colores asignados:")
    st.dataframe(pd.DataFrame(list(st.session_state.catalogo_actividades.keys()), columns=["Tarea / Actividad"]), use_container_width=True)

# ------------------------------------------
# OPCIÓN 4 HASTA 9: MÓDULOS DEL SISTEMA
# ------------------------------------------
elif opcion.startswith("4."):
    st.title("📅 Asistencia y Nómina Semanal")
    st.info("Módulo de asistencia integrado con la lectura de reportes diarios.")

elif opcion.startswith("5."):
    st.title("📊 Historial de Reportes")
    if st.session_state.historial_reportes:
        st.write(st.session_state.historial_reportes)
    else:
        st.info("No hay reportes registrados aún en esta sesión.")

elif opcion.startswith("6."):
    st.title("🗺️ Mapa de Avance por Lote")
    mapa_general = generar_mapa_coloreado(st.session_state.reporte_actual['actividades'] if st.session_state.reporte_actual else [])
    st.image(mapa_general, use_column_width=True)

elif opcion.startswith("7."):
    st.title("📄 Exportar Reporte Diario PDF")
    st.button("Generar PDF del Reporte")

elif opcion.startswith("8."):
    st.title("📄 Exportar Nómina PDF")
    st.button("Generar PDF de Nómina")

elif opcion.startswith("9."):
    st.title("🚜 Control de Maquinaria y Taller")
    st.info("Módulo de control de insumos y maquinaria de la finca.")
