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

COL_DIA2 = "dia 2 (partido)"

for col in ["carrera","ciclo","sede","plan de estudios"]:
    df[col] = df[col].astype(str)

df = df[df["plan de estudios"].str.contains(r"\d", na=False)]

tiene_sesion2_global = all(c in df.columns for c in [COL_DIA2, "hora inicio 2", "hora fin 2"])

if tiene_sesion2_global:
    df[COL_DIA2] = df[COL_DIA2].fillna("").astype(str).str.strip()
    df["hora inicio 2"] = df["hora inicio 2"].astype(str).fillna("")
    df["hora fin 2"] = df["hora fin 2"].astype(str).fillna("")

# Función para mostrar sección sin decimales
def fmt_seccion(val):
    try:
        return str(int(float(val)))
    except:
        return str(val) if pd.notna(val) else "Sin sección"

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
        curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)
        curso_df["hora inicio 1"] = curso_df["hora inicio 1"].astype(str)
        curso_df["hora fin 1"] = curso_df["hora fin 1"].astype(str)

        def construir_opcion(row):
            sesion1 = f"{row['dia 1']} ({row['hora inicio 1']}-{row['hora fin 1']})"
            if tiene_sesion2_global:
                dia2 = str(row.get(COL_DIA2, "")).strip()
                tiene_s2 = dia2 not in ["", "nan", "None"]
            else:
                tiene_s2 = False

            if tiene_s2:
                sesion2 = f"{row[COL_DIA2]} ({row['hora inicio 2']}-{row['hora fin 2']})"
                return f"{row['docente']} - Sección {row['seccion']} | {sesion1} y {sesion2}"
            else:
                return f"{row['docente']} - Sección {row['seccion']} | {sesion1}"

        curso_df["opcion"] = curso_df.apply(construir_opcion, axis=1)

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

        sesiones = []
        for _, row in df_horario.iterrows():
            dia1 = str(row.get("dia 1","")).strip()
            if dia1 not in ["", "nan", "None"]:
                sesiones.append({
                    "curso": row["nombre del curso"],
                    "dia": dia1,
                    "inicio": row["hora inicio 1"],
                    "fin": row["hora fin 1"]
                })
            if tiene_sesion2_global:
                dia2 = str(row.get(COL_DIA2, "")).strip()
                if dia2 not in ["", "nan", "None"]:
                    sesiones.append({
                        "curso": row["nombre del curso"],
                        "dia": dia2,
                        "inicio": row["hora inicio 2"],
                        "fin": row["hora fin 2"]
                    })

        for i in range(len(sesiones)):
            for j in range(i+1, len(sesiones)):
                s1 = sesiones[i]
                s2 = sesiones[j]

                if s1["curso"] == s2["curso"]:
                    continue

                if s1["dia"] == s2["dia"]:
                    if (
                        s1["inicio"] < s2["fin"]
                        and s2["inicio"] < s1["fin"]
                    ):
                        conflicto = f"{s1['curso']} se cruza con {s2['curso']} el {s1['dia']}"
                        if conflicto not in conflictos:
                            conflictos.append(conflicto)

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

            dias = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]

            fig = go.Figure()

            # Trazas invisibles para forzar el orden de los días
            for dia in dias:
                fig.add_trace(go.Bar(
                    x=[dia],
                    y=[0],
                    base=0,
                    marker_color="rgba(0,0,0,0)",
                    showlegend=False,
                    hoverinfo="skip"
                ))

            for i, row in horario.iterrows():

                color = palette[i % len(palette)]
                text_color = "black" if color == "#fff7e4" else "white"
                curso_texto = "<br>".join(textwrap.wrap(row["nombre del curso"], width=14))
                seccion_txt = fmt_seccion(row["seccion"])
                docente_txt = row["docente"] if str(row["docente"]) not in ["", "nan", "None"] else "Sin docente"

                # Sesión 1 — solo si tiene día y hora válidos
                dia1 = str(row.get("dia 1","")).strip()
                hora_ini1 = str(row.get("hora inicio 1","")).strip()
                hora_fin1 = str(row.get("hora fin 1","")).strip()

                if dia1 not in ["", "nan", "None"] and hora_ini1 not in ["", "nan", "None"] and hora_fin1 not in ["", "nan", "None"]:
                    inicio1 = pd.to_datetime(hora_ini1)
                    fin1 = pd.to_datetime(hora_fin1)

                    texto1 = (
                        curso_texto
                        + "<br>" + docente_txt
                        + "<br>Sección " + seccion_txt
                        + "<br>" + hora_ini1 + " - " + hora_fin1
                    )

                    fig.add_trace(go.Bar(
                        x=[dia1],
                        y=[(fin1 - inicio1).seconds / 3600],
                        base=inicio1.hour + inicio1.minute / 60,
                        marker_color=color,
                        width=0.6,
                        text=texto1,
                        textposition="inside",
                        textangle=0,
                        insidetextanchor="middle",
                        textfont=dict(size=12, color=text_color),
                        hoverinfo="skip",
                        showlegend=False
                    ))

                # Sesión 2 — solo si tiene día y hora válidos
                if tiene_sesion2_global:
                    dia2 = str(row.get(COL_DIA2, "")).strip()
                    hora_ini2 = str(row.get("hora inicio 2","")).strip()
                    hora_fin2 = str(row.get("hora fin 2","")).strip()

                    if dia2 not in ["", "nan", "None"] and hora_ini2 not in ["", "nan", "None"] and hora_fin2 not in ["", "nan", "None"]:
                        inicio2 = pd.to_datetime(hora_ini2)
                        fin2 = pd.to_datetime(hora_fin2)

                        texto2 = (
                            curso_texto
                            + "<br>" + docente_txt
                            + "<br>Sección " + seccion_txt
                            + "<br>" + hora_ini2 + " - " + hora_fin2
                        )

                        fig.add_trace(go.Bar(
                            x=[dia2],
                            y=[(fin2 - inicio2).seconds / 3600],
                            base=inicio2.hour + inicio2.minute / 60,
                            marker_color=color,
                            width=0.6,
                            text=texto2,
                            textposition="inside",
                            textangle=0,
                            insidetextanchor="middle",
                            textfont=dict(size=12, color=text_color),
                            hoverinfo="skip",
                            showlegend=False
                        ))

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
                template="plotly_white",
                showlegend=False
            )

            st.subheader("Horario semanal")
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Resumen de cursos")
            st.dataframe(horario)
