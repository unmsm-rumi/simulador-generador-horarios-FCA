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

df = pd.read_excel("data/cursos_simulador.xlsx")

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
    df[col] = df[col].astype(str)

df = df[df["plan de estudios"].str.contains(r"\d", na=False)]

# ------------------------------------------------
# FILTROS
# ------------------------------------------------

st.sidebar.header("Filtros")

carrera = st.sidebar.selectbox("Carrera",sorted(df["carrera"].dropna().unique()))
ciclo = st.sidebar.selectbox("Ciclo",sorted(df["ciclo"].dropna().unique()))
sede = st.sidebar.selectbox("Sede",sorted(df["sede"].dropna().unique()))
plan = st.sidebar.selectbox("Plan de estudios",sorted(df["plan de estudios"].dropna().unique()))

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

cursos = filtrado["nombre del curso"].unique()

cursos_seleccionados = []

for curso in cursos:
    if st.checkbox(curso):
        cursos_seleccionados.append(curso)

if st.button("Continuar a horarios"):

    if len(cursos_seleccionados) == 0:
        st.warning("Selecciona al menos un curso")
        st.stop()

    st.session_state["cursos_elegidos"] = cursos_seleccionados

# ------------------------------------------------
# PASO 2 — SELECCIONAR HORARIOS
# ------------------------------------------------

if "cursos_elegidos" in st.session_state:

    st.header("Paso 2: Escoge profesor y horario")

    cursos_elegidos = st.session_state["cursos_elegidos"]

    seleccionados = []

    for curso in cursos_elegidos:

        curso_df = filtrado[filtrado["nombre del curso"] == curso].copy()

        curso_df["docente"] = curso_df["docente"].fillna("Sin docente")
        curso_df["seccion"] = curso_df.get("seccion","").fillna("Sin sección")

        curso_df["hora inicio 1"] = curso_df["hora inicio 1"].astype(str)
        curso_df["hora fin 1"] = curso_df["hora fin 1"].astype(str)

        curso_df["opcion"] = (
            curso_df["docente"]
            + " - Sección "
            + curso_df["seccion"].astype(str)
            + " ("
            + curso_df["hora inicio 1"]
            + "-"
            + curso_df["hora fin 1"]
            + ")"
        )

        opciones = curso_df["opcion"].tolist()

        seleccion = st.selectbox(curso, opciones)

        fila = curso_df[curso_df["opcion"] == seleccion].iloc[0]

        seleccionados.append(fila)

    horario = pd.DataFrame(seleccionados)

# ------------------------------------------------
# DETECTAR CRUCES
# ------------------------------------------------

    def detectar_cruces(df_horario):

        conflictos = []

        for i in range(len(df_horario)):
            for j in range(i+1,len(df_horario)):

                c1 = df_horario.iloc[i]
                c2 = df_horario.iloc[j]

                if c1["dia 1"] == c2["dia 1"]:

                    if (
                        c1["hora inicio 1"] < c2["hora fin 1"]
                        and
                        c2["hora inicio 1"] < c1["hora fin 1"]
                    ):

                        conflictos.append(
                            f"{c1['nombre del curso']} se cruza con {c2['nombre del curso']}"
                        )

        return conflictos

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

            horario["inicio"] = pd.to_datetime(horario["hora inicio 1"])
            horario["fin"] = pd.to_datetime(horario["hora fin 1"])

            dias = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"]

            fig = go.Figure()

            for i,row in horario.iterrows():

                color = palette[i % len(palette)]

                # dividir texto del curso en múltiples líneas
                curso_texto = "<br>".join(textwrap.wrap(row["nombre del curso"], width=14))

                texto = (
                    curso_texto
                    + "<br>Sección "
                    + str(row["seccion"])
                    + "<br>"
                    + str(row["hora inicio 1"])
                    + " - "
                    + str(row["hora fin 1"])
                )

                # color de texto según fondo
                text_color = "black" if color == "#fff7e4" else "white"

                fig.add_trace(go.Bar(

                    x=[row["dia 1"]],
                    y=[(row["fin"]-row["inicio"]).seconds/3600],
                    base=row["inicio"].hour + row["inicio"].minute/60,

                    marker_color=color,
                    width=0.6,

                    text=texto,
                    textposition="inside",
                    textangle=0,
                    insidetextanchor="middle",

                    textfont=dict(
                        size=14,
                        color=text_color
                    ),

                    hoverinfo="skip",
                    showlegend=False

                ))

            fig.update_layout(

                height=700,

                xaxis=dict(
                    title="Día",
                    categoryorder="array",
                    categoryarray=dias
                ),

                yaxis=dict(
                    title="Hora",
                    autorange="reversed"
                ),

                template="plotly_white",
                showlegend=False

            )

            st.subheader("Horario semanal")
            st.plotly_chart(fig,use_container_width=True)

            st.subheader("Resumen de cursos")
            st.dataframe(horario)