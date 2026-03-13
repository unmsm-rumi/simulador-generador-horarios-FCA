import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import textwrap

st.set_page_config(layout="wide")

st.title("Simulador de Horarios Universitarios")

# ------------------------------------------------
# PALETA DE COLORES
# ------------------------------------------------

palette = ["#c13850","#d86d80","#d55a68","#ef94a4","#fff7e4"]

# ------------------------------------------------
# CARGAR DATA
# ------------------------------------------------

@st.cache_data
def cargar_data():

    df = pd.read_excel("cursos_simulador.xlsx")

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

df = cargar_data()

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


def tiene_horario_valido(row):
    """Retorna True si la fila tiene al menos una sesión con día y horas válidas."""
    dia1 = str(row.get("dia 1", "")).strip()
    if dia1 not in ["", "nan", "None"]:
        inicio = pd.to_datetime(row.get("hora inicio 1", ""), errors="coerce")
        fin = pd.to_datetime(row.get("hora fin 1", ""), errors="coerce")
        if pd.notna(inicio) and pd.notna(fin):
            return True

    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2, "")).strip()
        if dia2 not in ["", "nan", "None"]:
            inicio = pd.to_datetime(row.get("hora inicio 2", ""), errors="coerce")
            fin = pd.to_datetime(row.get("hora fin 2", ""), errors="coerce")
            if pd.notna(inicio) and pd.notna(fin):
                return True

    return False


def obtener_sesiones(row):

    sesiones = []

    dia1 = str(row.get("dia 1","")).strip()
    if dia1 not in ["","nan","None"]:

        inicio = pd.to_datetime(row["hora inicio 1"], errors="coerce")
        fin = pd.to_datetime(row["hora fin 1"], errors="coerce")

        if pd.notna(inicio) and pd.notna(fin):

            sesiones.append({
                "curso": row["nombre del curso"],
                "dia": dia1,
                "inicio": inicio,
                "fin": fin
            })

    if tiene_sesion2_global:

        dia2 = str(row.get(COL_DIA2,"")).strip()

        if dia2 not in ["","nan","None"]:

            inicio = pd.to_datetime(row["hora inicio 2"], errors="coerce")
            fin = pd.to_datetime(row["hora fin 2"], errors="coerce")

            if pd.notna(inicio) and pd.notna(fin):

                sesiones.append({
                    "curso": row["nombre del curso"],
                    "dia": dia2,
                    "inicio": inicio,
                    "fin": fin
                })

    return sesiones


def detectar_cruces(df_horario):

    sesiones = []

    for _, row in df_horario.iterrows():
        sesiones.extend(obtener_sesiones(row))

    conflictos = []

    for i in range(len(sesiones)):
        for j in range(i+1,len(sesiones)):

            s1 = sesiones[i]
            s2 = sesiones[j]

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
    Construye el texto de la opción para el selectbox de secciones.
    Si no hay horario válido, indica claramente 'Sin horario asignado'.
    """
    docente = str(row.get("docente", "")).strip()
    if not docente or docente in ["nan", "None", ""]:
        docente = "Sin docente"

    seccion = fmt_seccion(row.get("seccion", ""))

    # Intenta construir sesión 1
    dia1 = str(row.get("dia 1", "")).strip()
    sesion1_texto = None
    if dia1 not in ["", "nan", "None"]:
        inicio = pd.to_datetime(row.get("hora inicio 1", ""), errors="coerce")
        fin = pd.to_datetime(row.get("hora fin 1", ""), errors="coerce")
        if pd.notna(inicio) and pd.notna(fin):
            sesion1_texto = f"{dia1} ({inicio.strftime('%H:%M')}-{fin.strftime('%H:%M')})"

    # Intenta construir sesión 2
    sesion2_texto = None
    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2, "")).strip()
        if dia2 not in ["", "nan", "None"]:
            inicio2 = pd.to_datetime(row.get("hora inicio 2", ""), errors="coerce")
            fin2 = pd.to_datetime(row.get("hora fin 2", ""), errors="coerce")
            if pd.notna(inicio2) and pd.notna(fin2):
                sesion2_texto = f"{dia2} ({inicio2.strftime('%H:%M')}-{fin2.strftime('%H:%M')})"

    # Armar texto final
    if sesion1_texto and sesion2_texto:
        horario_texto = f"{sesion1_texto} y {sesion2_texto}"
    elif sesion1_texto:
        horario_texto = sesion1_texto
    elif sesion2_texto:
        horario_texto = sesion2_texto
    else:
        horario_texto = "⚠️ Sin horario asignado"

    return f"{docente} - Sección {seccion} | {horario_texto}"

# ------------------------------------------------
# BOTÓN REINICIAR
# ------------------------------------------------

if st.sidebar.button("Reiniciar simulador"):
    st.session_state.clear()

# ------------------------------------------------
# FILTROS
# ------------------------------------------------

st.sidebar.header("Filtros")

carrera = st.sidebar.selectbox("Carrera", sorted(df["carrera"].dropna().unique()))
ciclo = st.sidebar.selectbox("Ciclo", sorted(df["ciclo"].dropna().unique()))
sede = st.sidebar.selectbox("Sede", sorted(df["sede"].dropna().unique()))
plan = st.sidebar.selectbox("Plan de estudios", sorted(df["plan de estudios"].dropna().unique()))

filtrado = df[
    (df["carrera"] == carrera) &
    (df["ciclo"] == ciclo) &
    (df["sede"] == sede) &
    (df["plan de estudios"] == plan)
]

if filtrado.empty:
    st.warning("No existen cursos con esos filtros")
    st.stop()

# ------------------------------------------------
# PASO 1 — SELECCIONAR CURSOS
# ------------------------------------------------

st.header("Paso 1: Selecciona los cursos")

cursos = sorted(filtrado["nombre del curso"].unique())

cursos_seleccionados = []

for curso in cursos:
    if st.checkbox(curso):
        cursos_seleccionados.append(curso)

if st.button("Continuar a horarios"):

    if len(cursos_seleccionados) == 0:
        st.warning("Selecciona al menos un curso")
    else:
        st.session_state.cursos_elegidos = cursos_seleccionados

# ------------------------------------------------
# PASO 2 — SELECCIONAR HORARIOS
# ------------------------------------------------

if "cursos_elegidos" in st.session_state:

    st.header("Paso 2: Escoge profesor y horario")

    cursos_elegidos = st.session_state.cursos_elegidos

    seleccionados = []

    for curso in cursos_elegidos:

        curso_df = filtrado[filtrado["nombre del curso"] == curso].copy()

        curso_df["docente"] = curso_df["docente"].fillna("Sin docente").astype(str).str.strip()
        curso_df["docente"] = curso_df["docente"].replace({"": "Sin docente", "nan": "Sin docente", "None": "Sin docente"})
        curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)

        curso_df["opcion"] = curso_df.apply(construir_opcion, axis=1)

        opciones = curso_df["opcion"].tolist()

        # Si todas las opciones son sin horario, mostrar aviso pero igual dejarlas seleccionables
        todas_sin_horario = all("Sin horario asignado" in op for op in opciones)
        if todas_sin_horario:
            st.warning(f"⚠️ **{curso}**: ninguna sección tiene horario asignado aún. Se incluirá en el resumen pero no aparecerá en el gráfico.")

        seleccion = st.selectbox(curso, opciones, key=f"select_{curso}")

        fila = curso_df[curso_df["opcion"] == seleccion].iloc[0]

        seleccionados.append(fila)

    horario = pd.DataFrame(seleccionados)

# ------------------------------------------------
# GENERAR HORARIO
# ------------------------------------------------

    if st.button("Generar horario"):

        conflictos = detectar_cruces(horario)

        if conflictos:

            st.error("Hay cruces de horario")

            for c in conflictos:
                st.write(c)

        else:

            st.success("Horario generado correctamente")

            dias = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]

            fig = go.Figure()

            cursos_con_horario = 0

            for i, row in horario.iterrows():

                sesiones = obtener_sesiones(row)

                if not sesiones:
                    # Curso sin horario: no se grafica pero sí aparece en el resumen
                    continue

                cursos_con_horario += 1
                color = palette[i % len(palette)]
                text_color = "black" if color == "#fff7e4" else "white"

                curso_texto = "<br>".join(textwrap.wrap(row["nombre del curso"], width=14))

                docente = str(row.get("docente", "Sin docente")).strip()
                if not docente or docente in ["nan", "None", ""]:
                    docente = "Sin docente"

                for ses in sesiones:

                    inicio = ses["inicio"]
                    fin = ses["fin"]

                    texto = (
                        curso_texto
                        + "<br>" + docente
                        + "<br>Sección " + fmt_seccion(row["seccion"])
                        + "<br>" + inicio.strftime("%H:%M") + " - " + fin.strftime("%H:%M")
                    )

                    fig.add_trace(go.Bar(
                        x=[ses["dia"]],
                        y=[(fin - inicio).seconds/3600],
                        base=inicio.hour + inicio.minute/60,
                        marker_color=color,
                        width=0.6,
                        text=texto,
                        textposition="inside",
                        insidetextanchor="middle",
                        textfont=dict(size=12,color=text_color),
                        hoverinfo="skip",
                        showlegend=False
                    ))

            if cursos_con_horario == 0:
                st.warning("Ninguno de los cursos seleccionados tiene horario asignado. No se puede generar el gráfico.")
            else:
                fig.update_layout(
                    height=700,
                    barmode="overlay",
                    xaxis=dict(
                        title="Día",
                        categoryorder="array",
                        categoryarray=dias
                    ),
                    yaxis=dict(
                        title="Hora",
                        autorange="reversed"
                    ),
                    template="plotly_white"
                )

                st.subheader("Horario semanal")
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("Resumen de cursos")
            st.dataframe(horario)
