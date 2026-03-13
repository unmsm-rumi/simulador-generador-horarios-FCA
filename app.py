import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import textwrap
from pathlib import Path

# Ruta al Excel: siempre relativa al directorio donde está este script
BASE_DIR = Path(__file__).parent
EXCEL_PATH = BASE_DIR / "cursos_simulador.xlsx"

st.set_page_config(layout="wide")

# Logo Rumi en la esquina superior izquierda del sidebar
LOGO_PATH = BASE_DIR / "logo.png"
if LOGO_PATH.exists():
    import base64
    with open(str(LOGO_PATH), "rb") as img_file:
        logo_b64 = base64.b64encode(img_file.read()).decode()
    st.sidebar.markdown(
        f'''<img src="data:image/png;base64,{logo_b64}"
             style="width:200px; image-rendering:-webkit-optimize-contrast;
                    image-rendering:crisp-edges; display:block; margin-bottom:8px;">''',
        unsafe_allow_html=True
    )

st.title("Simulador de Horarios Universitarios")

# ------------------------------------------------
# PALETA DE COLORES
# ------------------------------------------------

palette = ["#c13850","#d55a68","#d86d80","#ef94a4","#fff7e4"]

# ------------------------------------------------
# CARGAR DATA
# ------------------------------------------------

@st.cache_data(ttl=0)
def cargar_data(file_mtime):
    """file_mtime se pasa para invalidar cache cuando el Excel cambie."""
    if not EXCEL_PATH.exists():
        ruta = str(EXCEL_PATH)
        st.error(
            "No se encontro el archivo Excel. "
            "Ruta buscada: " + ruta + ". "
            "Asegurate de que cursos_simulador.xlsx este en la misma carpeta que app.py en tu repositorio de GitHub."
        )
        st.stop()
    df = pd.read_excel(EXCEL_PATH)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace("á","a")
        .str.replace("é","e")
        .str.replace("í","i")
        .str.replace("ó","o")
        .str.replace("ú","u")
    )
    for col in ["carrera","ciclo","sede","plan de estudios"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df

# Pasar el timestamp de modificacion del Excel como argumento
# Esto fuerza que el cache se invalide automaticamente cuando se suba un Excel nuevo
import os
file_mtime = os.path.getmtime(EXCEL_PATH) if EXCEL_PATH.exists() else 0
df = cargar_data(file_mtime)

COL_DIA2 = "dia 2 (partido)"

for col in ["carrera","ciclo","sede","plan de estudios"]:
    df[col] = df[col].astype(str)

tiene_sesion2_global = all(c in df.columns for c in [COL_DIA2, "hora inicio 2", "hora fin 2"])

if tiene_sesion2_global:
    df[COL_DIA2] = df[COL_DIA2].fillna("").astype(str).str.strip()
    df["hora inicio 2"] = df["hora inicio 2"].astype(str).fillna("")
    df["hora fin 2"] = df["hora fin 2"].astype(str).fillna("")

# ------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------

def fmt_seccion(val):
    try:
        return str(int(float(val)))
    except:
        return str(val) if pd.notna(val) else "Sin sección"


def parsear_hora(val):
    """Parsea un valor de hora en cualquier formato (string HH:MM, HH:MM:SS, datetime.time, etc.)"""
    import datetime
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return pd.NaT
    if isinstance(val, datetime.time):
        return pd.Timestamp(f"2000-01-01 {val.hour:02d}:{val.minute:02d}")
    s = str(val).strip()
    if not s or s in ["nan", "None", ""]:
        return pd.NaT
    # Remove seconds if present (HH:MM:SS → HH:MM)
    parts = s.split(":")
    if len(parts) >= 2:
        try:
            return pd.Timestamp(f"2000-01-01 {int(parts[0]):02d}:{int(parts[1]):02d}")
        except:
            pass
    return pd.to_datetime(val, errors="coerce")


def obtener_sesiones(row):
    sesiones = []

    dia1 = str(row.get("dia 1","")).strip()
    if dia1 not in ["","nan","None"]:
        inicio = parsear_hora(row["hora inicio 1"])
        fin    = parsear_hora(row["hora fin 1"])
        if pd.notna(inicio) and pd.notna(fin):
            sesiones.append({"curso": row["nombre del curso"], "dia": dia1, "inicio": inicio, "fin": fin})

    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2,"")).strip()
        if dia2 not in ["","nan","None"]:
            inicio = parsear_hora(row["hora inicio 2"])
            fin    = parsear_hora(row["hora fin 2"])
            if pd.notna(inicio) and pd.notna(fin):
                sesiones.append({"curso": row["nombre del curso"], "dia": dia2, "inicio": inicio, "fin": fin})

    return sesiones


def detectar_cruces(df_horario):
    sesiones = []
    for _, row in df_horario.iterrows():
        sesiones.extend(obtener_sesiones(row))

    conflictos = []
    for i in range(len(sesiones)):
        for j in range(i+1, len(sesiones)):
            s1, s2 = sesiones[i], sesiones[j]
            if s1["curso"] == s2["curso"]:
                continue
            if s1["dia"] == s2["dia"]:
                if s1["inicio"] < s2["fin"] and s2["inicio"] < s1["fin"]:
                    conflicto = f"{s1['curso']} se cruza con {s2['curso']} el {s1['dia']}"
                    if conflicto not in conflictos:
                        conflictos.append(conflicto)
    return conflictos


def construir_opcion(row):
    """
    Construye la etiqueta del selectbox.
    Incluye sede, docente, seccion y horario.
    Si no hay horario valido lo indica claramente.
    """
    docente = str(row.get("docente","")).strip()
    if not docente or docente in ["nan","None",""]:
        docente = "Sin docente"

    seccion = fmt_seccion(row.get("seccion",""))
    sede    = str(row.get("sede","")).strip()

    # Sesion 1
    dia1 = str(row.get("dia 1","")).strip()
    ses1 = None
    if dia1 not in ["","nan","None"]:
        ini = parsear_hora(row.get("hora inicio 1",""))
        fin = parsear_hora(row.get("hora fin 1",""))
        if pd.notna(ini) and pd.notna(fin):
            ses1 = f"{dia1} {ini.strftime('%H:%M')}-{fin.strftime('%H:%M')}"

    # Sesion 2
    ses2 = None
    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2,"")).strip()
        if dia2 not in ["","nan","None"]:
            ini2 = parsear_hora(row.get("hora inicio 2",""))
            fin2 = parsear_hora(row.get("hora fin 2",""))
            if pd.notna(ini2) and pd.notna(fin2):
                ses2 = f"{dia2} {ini2.strftime('%H:%M')}-{fin2.strftime('%H:%M')}"

    if ses1 and ses2:
        horario_txt = f"{ses1}  /  {ses2}"
    elif ses1:
        horario_txt = ses1
    elif ses2:
        horario_txt = ses2
    else:
        horario_txt = "Sin horario asignado"

    return f"[{sede}] Sec.{seccion} - {docente} | {horario_txt}"


# ------------------------------------------------
# BOTON REINICIAR
# ------------------------------------------------

if st.sidebar.button("Reiniciar simulador"):
    st.cache_data.clear()
    st.session_state.clear()
    st.rerun()

# ------------------------------------------------
# FILTROS
# Sede ya NO filtra que cursos aparecen.
# Solo se usa para preseleccionar secciones en paso 2.
# ------------------------------------------------

st.sidebar.header("Filtros")

# Orden correcto de ciclos (no alfabético)
ORDEN_CICLOS = ["TERCER CICLO", "QUINTO CICLO", "SÉPTIMO CICLO", "NOVENO CICLO"]
ciclos_disponibles = df["ciclo"].dropna().unique()
ciclos_ordenados = [c for c in ORDEN_CICLOS if c in ciclos_disponibles] + \
                   [c for c in sorted(ciclos_disponibles) if c not in ORDEN_CICLOS]

carrera = st.sidebar.selectbox("Carrera",          sorted(df["carrera"].dropna().unique()))
ciclo   = st.sidebar.selectbox("Ciclo",            ciclos_ordenados)
plan    = st.sidebar.selectbox("Plan de estudios", sorted(df["plan de estudios"].dropna().unique()))

# Base filtrada por carrera + ciclo + plan (sin sede aún)
filtrado_base = df[
    (df["carrera"] == carrera) &
    (df["ciclo"]   == ciclo)   &
    (df["plan de estudios"] == plan)
]

# Sedes disponibles para esta combinación
sedes_disponibles = sorted(filtrado_base["sede"].dropna().unique())

sede = st.sidebar.selectbox(
    "Sede",
    ["Todas"] + sedes_disponibles
)

# Aplicar filtro de sede
if sede == "Todas":
    filtrado = filtrado_base
else:
    filtrado = filtrado_base[filtrado_base["sede"] == sede]

if filtrado_base.empty:
    st.warning(f"No hay cursos para {carrera} — {ciclo} — Plan {plan}.")
    st.stop()

if filtrado.empty:
    st.warning(f"No hay cursos en la sede **{sede}** para {carrera} — {ciclo} — Plan {plan}.")
    st.stop()

# ------------------------------------------------
# PASO 1 - SELECCIONAR CURSOS
# ------------------------------------------------

st.header("Paso 1: Selecciona los cursos")

cursos = sorted(filtrado["nombre del curso"].unique())

st.caption(f"Se encontraron **{len(cursos)} cursos** para {carrera} — {ciclo} — Plan {plan}.")

cursos_seleccionados = []

cols = st.columns(2)
for idx, curso in enumerate(cursos):
    col = cols[idx % 2]
    if col.checkbox(curso, key=f"chk_{curso}"):
        cursos_seleccionados.append(curso)

if st.button("Continuar a horarios"):
    if len(cursos_seleccionados) == 0:
        st.warning("Selecciona al menos un curso.")
    else:
        st.session_state.cursos_elegidos = cursos_seleccionados

# ------------------------------------------------
# PASO 2 - SELECCIONAR SECCION / HORARIO
# ------------------------------------------------

if "cursos_elegidos" in st.session_state:

    st.header("Paso 2: Escoge seccion y horario")
    st.caption("Las opciones muestran las secciones disponibles para la sede seleccionada.")

    cursos_elegidos = st.session_state.cursos_elegidos
    seleccionados   = []

    for curso in cursos_elegidos:

        curso_df = filtrado[filtrado["nombre del curso"] == curso].copy()

        # Limpiar docente
        curso_df["docente"] = (
            curso_df["docente"]
            .fillna("Sin docente")
            .astype(str)
            .str.strip()
            .replace({"": "Sin docente", "nan": "Sin docente", "None": "Sin docente"})
        )
        curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)

        # Construir etiqueta de opcion
        curso_df["opcion"] = curso_df.apply(construir_opcion, axis=1)

        # Ordenar secciones por numero de seccion
        curso_df = curso_df.sort_values("seccion")

        opciones = curso_df["opcion"].tolist()

        # Avisar si todas sin horario
        todas_sin_horario = all("Sin horario asignado" in op for op in opciones)
        if todas_sin_horario:
            st.warning(f"**{curso}**: ninguna seccion tiene horario asignado aun.")

        NO_LLEVAR = "— No llevar este curso —"
        opciones_con_skip = [NO_LLEVAR] + opciones

        seleccion = st.selectbox(f"**{curso}**", opciones_con_skip, key=f"sel_{curso}")

        if seleccion == NO_LLEVAR:
            continue  # Omitir este curso del horario

        fila = curso_df[curso_df["opcion"] == seleccion].iloc[0]
        seleccionados.append(fila)

    horario = pd.DataFrame(seleccionados)

    # ------------------------------------------------
    # GENERAR HORARIO
    # ------------------------------------------------

    if st.button("Generar horario"):

        if horario.empty:
            st.warning("No has seleccionado ningún curso. Elige al menos uno para generar el horario.")
            st.stop()

        conflictos = detectar_cruces(horario)

        if conflictos:
            st.error("Hay cruces de horario:")
            for c in conflictos:
                st.write(f"- {c}")
        else:
            st.success("Horario generado correctamente.")

            dias = ["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES","SABADO"]
            # Incluir version con tilde para que el grafico los encuentre
            dias_con_tilde = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]

            fig       = go.Figure()
            color_map = {}
            color_idx = 0

            # Mapeo dia -> posicion X (columna)
            dia_x = {d: i for i, d in enumerate(dias_con_tilde)}
            ancho_col = 0.45  # ancho de cada bloque (de -0.45 a +0.45 del centro)

            for _, row in horario.iterrows():
                sesiones = obtener_sesiones(row)
                if not sesiones:
                    continue

                nombre = row["nombre del curso"]
                if nombre not in color_map:
                    color_map[nombre] = palette[color_idx % len(palette)]
                    color_idx += 1

                color      = color_map[nombre]
                text_color = "#3a1a20" if color == "#fff7e4" else "white"

                docente = str(row.get("docente","Sin docente")).strip()
                if not docente or docente in ["nan","None",""]:
                    docente = "Sin docente"

                for ses in sesiones:
                    ini = ses["inicio"]
                    fin = ses["fin"]
                    dia = ses["dia"]
                    if dia not in dia_x:
                        continue

                    cx     = dia_x[dia]
                    y0     = ini.hour + ini.minute / 60
                    y1     = fin.hour + fin.minute / 60
                    cy     = (y0 + y1) / 2
                    dur_h  = y1 - y0

                    # Nombre del curso cortado a 1 linea
                    nombre_corto = nombre if len(nombre) <= 22 else nombre[:20] + "…"

                    # Texto dentro del bloque: nombre + hora
                    label = (
                        f"<b>{nombre_corto}</b><br>"
                        f"Sec.{fmt_seccion(row['seccion'])} | "
                        f"{ini.strftime('%H:%M')}-{fin.strftime('%H:%M')}"
                    )
                    if dur_h >= 1.5:
                        label += f"<br>{docente}"

                    # Rectangulo de color
                    fig.add_shape(
                        type="rect",
                        x0=cx - ancho_col, x1=cx + ancho_col,
                        y0=y0, y1=y1,
                        fillcolor=color,
                        line=dict(color="white", width=2),
                        layer="below",
                    )

                    # Texto centrado horizontal dentro del bloque
                    fig.add_annotation(
                        x=cx,
                        y=cy,
                        text=label,
                        showarrow=False,
                        font=dict(size=10, color=text_color),
                        align="center",
                        xanchor="center",
                        yanchor="middle",
                        bgcolor="rgba(0,0,0,0)",
                        borderpad=2,
                    )

            if not color_map:
                st.warning("Ninguno de los cursos seleccionados tiene horario asignado.")
            else:
                hora_min = 6
                hora_max = 23
                tickvals_y = [h + m/60 for h in range(hora_min, hora_max+1) for m in [0]]
                ticktext_y = [f"{h:02d}:00" for h in range(hora_min, hora_max+1)]

                n_dias = len(dias_con_tilde)
                fig.update_layout(
                    height=750,
                    xaxis=dict(
                        tickvals=list(range(n_dias)),
                        ticktext=dias_con_tilde,
                        range=[-0.5, n_dias - 0.5],
                        showgrid=True,
                        gridcolor="rgba(128,128,128,0.3)",
                        side="top",
                        fixedrange=True,
                    ),
                    yaxis=dict(
                        tickvals=tickvals_y,
                        ticktext=ticktext_y,
                        range=[hora_max, hora_min],  # invertido: horas crecen hacia abajo
                        showgrid=True,
                        gridcolor="rgba(128,128,128,0.3)",
                        fixedrange=True,
                    ),
                    template="none",
                    margin=dict(t=60, l=70, r=20, b=20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color=None),
                )

                st.subheader("Horario semanal")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Resumen de cursos seleccionados")
            cols_resumen = ["nombre del curso","docente","seccion","sede","dia 1","hora inicio 1","hora fin 1"]
            resumen = horario[[c for c in cols_resumen if c in horario.columns]].copy()
            resumen.columns = ["Curso","Docente","Seccion","Sede","Dia","Inicio","Fin"][:len(resumen.columns)]
            st.dataframe(resumen, use_container_width=True)
