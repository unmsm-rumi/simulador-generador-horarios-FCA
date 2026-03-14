import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from itertools import product as iterproduct

BASE_DIR = Path(__file__).parent
EXCEL_PATH = BASE_DIR / "cursos_simulador.xlsx"

st.set_page_config(layout="wide")

# ------------------------------------------------
# ESTILOS GLOBALES
# ------------------------------------------------

st.markdown("""
<style>
[data-testid="stSidebar"] {
    background-color: #c85c72 !important;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background-color: rgba(255,255,255,0.15) !important;
    border-color: rgba(255,255,255,0.3) !important;
    color: white !important;
}
[data-testid="stSidebar"] button {
    background-color: rgba(255,255,255,0.2) !important;
    border-color: rgba(255,255,255,0.4) !important;
    color: white !important;
}

/* Botón modo generador */
.modo-btn {
    display: inline-block;
    background: linear-gradient(135deg, #c85c72, #a33a52);
    color: white !important;
    border-radius: 8px;
    padding: 0.4rem 1rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 6px;
}

/* Tarjetas de opciones generadas */
.opcion-card {
    border: 2px solid #c85c72;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    background: rgba(200, 92, 114, 0.05);
}
.opcion-card.principal {
    border-color: #c85c72;
    background: rgba(200, 92, 114, 0.1);
}
.opcion-card h4 {
    color: #c85c72;
    margin-bottom: 0.5rem;
}

/* Bloqueo card */
.bloqueo-row {
    background: rgba(200,92,114,0.07);
    border-left: 4px solid #c85c72;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.6rem;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# LOGO
# ------------------------------------------------
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

# ------------------------------------------------
# MODO: SIMULADOR / GENERADOR
# ------------------------------------------------
if "modo" not in st.session_state:
    st.session_state.modo = "simulador"

modo_label = "⚡ Cambiar a Generador" if st.session_state.modo == "simulador" else "🗓️ Cambiar a Simulador"
if st.sidebar.button(modo_label):
    nuevo_modo = "generador" if st.session_state.modo == "simulador" else "simulador"
    st.session_state.modo = nuevo_modo
    # Limpiar estado previo del otro modo
    for k in list(st.session_state.keys()):
        if k not in ["modo"]:
            del st.session_state[k]
    st.rerun()

modo_actual = st.session_state.modo

if st.sidebar.button("Reiniciar"):
    modo_guardado = st.session_state.modo
    st.cache_data.clear()
    st.session_state.clear()
    st.session_state.modo = modo_guardado
    st.rerun()

palette = ["#c85c72"] * 10

# ------------------------------------------------
# CARGAR DATA
# ------------------------------------------------

def normalizar_texto(serie):
    return (
        serie.astype(str).str.strip().str.upper()
        .str.replace("Á","A",regex=False).str.replace("É","E",regex=False)
        .str.replace("Í","I",regex=False).str.replace("Ó","O",regex=False)
        .str.replace("Ú","U",regex=False)
        .str.replace("á","a",regex=False).str.replace("é","e",regex=False)
        .str.replace("í","i",regex=False).str.replace("ó","o",regex=False)
        .str.replace("ú","u",regex=False)
    )

def _es_numero(val):
    try:
        float(val); return True
    except: return False

@st.cache_data(ttl=0)
def cargar_data(file_mtime):
    if not EXCEL_PATH.exists():
        st.error(f"No se encontró el archivo Excel. Ruta: {EXCEL_PATH}")
        st.stop()
    df = pd.read_excel(EXCEL_PATH)
    df.columns = (
        df.columns.str.strip().str.lower()
        .str.replace("á","a",regex=False).str.replace("é","e",regex=False)
        .str.replace("í","i",regex=False).str.replace("ó","o",regex=False)
        .str.replace("ú","u",regex=False)
    )
    for col in ["carrera","ciclo","sede","plan de estudios"]:
        if col in df.columns:
            df[col] = normalizar_texto(df[col])
    if "plan de estudios" in df.columns:
        df["plan de estudios"] = df["plan de estudios"].apply(
            lambda x: str(int(float(x))) if x not in ["NAN","NONE",""] and _es_numero(x) else x
        )
    return df

import os
file_mtime = os.path.getmtime(EXCEL_PATH) if EXCEL_PATH.exists() else 0
df = cargar_data(file_mtime)

COL_DIA2 = "dia 2 (partido)"
for col in ["carrera","ciclo","sede","plan de estudios"]:
    if col in df.columns:
        df[col] = df[col].astype(str)

tiene_sesion2_global = all(c in df.columns for c in [COL_DIA2,"hora inicio 2","hora fin 2"])
if tiene_sesion2_global:
    df[COL_DIA2] = df[COL_DIA2].fillna("").astype(str).str.strip()
    df["hora inicio 2"] = df["hora inicio 2"].astype(str).fillna("")
    df["hora fin 2"]    = df["hora fin 2"].astype(str).fillna("")

# ------------------------------------------------
# FUNCIONES AUXILIARES
# ------------------------------------------------

def fmt_seccion(val):
    try: return str(int(float(val)))
    except: return str(val) if pd.notna(val) else "Sin sección"

def parsear_hora(val):
    import datetime
    if val is None or (isinstance(val,float) and pd.isna(val)): return pd.NaT
    if isinstance(val,datetime.time):
        return pd.Timestamp(f"2000-01-01 {val.hour:02d}:{val.minute:02d}")
    s = str(val).strip()
    if not s or s in ["nan","None",""]: return pd.NaT
    parts = s.split(":")
    if len(parts) >= 2:
        try: return pd.Timestamp(f"2000-01-01 {int(parts[0]):02d}:{int(parts[1]):02d}")
        except: pass
    return pd.to_datetime(val, errors="coerce")

def obtener_sesiones(row):
    sesiones = []
    dia1 = str(row.get("dia 1","")).strip()
    if dia1 not in ["","nan","None"]:
        ini = parsear_hora(row["hora inicio 1"])
        fin = parsear_hora(row["hora fin 1"])
        if pd.notna(ini) and pd.notna(fin):
            sesiones.append({"curso":row["nombre del curso"],"dia":dia1,"inicio":ini,"fin":fin})
    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2,"")).strip()
        if dia2 not in ["","nan","None"]:
            ini2 = parsear_hora(row["hora inicio 2"])
            fin2 = parsear_hora(row["hora fin 2"])
            if pd.notna(ini2) and pd.notna(fin2):
                sesiones.append({"curso":row["nombre del curso"],"dia":dia2,"inicio":ini2,"fin":fin2})
    return sesiones

def detectar_cruces(df_horario):
    sesiones = []
    for _, row in df_horario.iterrows():
        sesiones.extend(obtener_sesiones(row))
    conflictos = []
    for i in range(len(sesiones)):
        for j in range(i+1,len(sesiones)):
            s1,s2 = sesiones[i],sesiones[j]
            if s1["curso"]==s2["curso"]: continue
            if s1["dia"]==s2["dia"] and s1["inicio"]<s2["fin"] and s2["inicio"]<s1["fin"]:
                c = f"{s1['curso']} se cruza con {s2['curso']} el {s1['dia']}"
                if c not in conflictos: conflictos.append(c)
    return conflictos

def construir_opcion(row):
    docente = str(row.get("docente","")).strip()
    if not docente or docente in ["nan","None",""]: docente = "Sin docente"
    seccion = fmt_seccion(row.get("seccion",""))
    sede    = str(row.get("sede","")).strip()
    dia1 = str(row.get("dia 1","")).strip()
    ses1 = None
    if dia1 not in ["","nan","None"]:
        ini = parsear_hora(row.get("hora inicio 1",""))
        fin = parsear_hora(row.get("hora fin 1",""))
        if pd.notna(ini) and pd.notna(fin):
            ses1 = f"{dia1} {ini.strftime('%H:%M')}-{fin.strftime('%H:%M')}"
    ses2 = None
    if tiene_sesion2_global:
        dia2 = str(row.get(COL_DIA2,"")).strip()
        if dia2 not in ["","nan","None"]:
            ini2 = parsear_hora(row.get("hora inicio 2",""))
            fin2 = parsear_hora(row.get("hora fin 2",""))
            if pd.notna(ini2) and pd.notna(fin2):
                ses2 = f"{dia2} {ini2.strftime('%H:%M')}-{fin2.strftime('%H:%M')}"
    if ses1 and ses2: horario_txt = f"{ses1}  /  {ses2}"
    elif ses1:        horario_txt = ses1
    elif ses2:        horario_txt = ses2
    else:             horario_txt = "Sin horario asignado"
    return f"[{sede}] Sec.{seccion} - {docente} | {horario_txt}"

def dibujar_horario(horario_df, bloqueos=None, titulo="Horario semanal"):
    """Dibuja el gráfico Plotly del horario. Si hay bloqueos, los pinta en gris."""
    dias     = ["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES","SABADO"]
    dias_con = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]
    dia_x    = {d:i for i,d in enumerate(dias_con)}
    dia_x.update({d:i for i,d in enumerate(dias)})
    ancho_col = 0.42

    fig       = go.Figure()
    color_map = {}
    color_idx = 0

    # Pintar bloqueos de horario primero (fondo gris)
    if bloqueos:
        for b in bloqueos:
            dia_b = b["dia"].upper().replace("É","E").replace("Á","A").replace("Ó","O")
            if dia_b not in dia_x: continue
            cx = dia_x[dia_b]
            y0_blk = b["inicio_h"]
            y1_blk = b["fin_h"]
            t_antes_h   = b.get("traslado_antes",  b.get("traslado", 0)) / 60.0
            t_despues_h = b.get("traslado_despues", b.get("traslado", 0)) / 60.0

            # Zona de traslado antes (más tenue)
            if t_antes_h > 0:
                fig.add_shape(
                    type="rect",
                    x0=cx-ancho_col, x1=cx+ancho_col,
                    y0=y0_blk - t_antes_h, y1=y0_blk,
                    fillcolor="rgba(150,150,150,0.18)",
                    line=dict(color="rgba(120,120,120,0.3)", width=1, dash="dot"),
                    layer="below",
                )
                fig.add_annotation(
                    x=cx, y=y0_blk - t_antes_h/2,
                    text=f"traslado<br>{b.get('traslado_antes',0)} min",
                    showarrow=False,
                    font=dict(size=7, color="rgba(80,80,80,0.7)"),
                    align="center", xanchor="center", yanchor="middle",
                )

            # Bloque principal OCUPADO
            fig.add_shape(
                type="rect",
                x0=cx-ancho_col, x1=cx+ancho_col,
                y0=y0_blk, y1=y1_blk,
                fillcolor="rgba(100,100,100,0.40)",
                line=dict(color="rgba(80,80,80,0.6)", width=1),
                layer="below",
            )
            cy = (y0_blk + y1_blk) / 2
            fig.add_annotation(
                x=cx, y=cy,
                text="<b>OCUPADO</b>",
                showarrow=False,
                font=dict(size=8, color="rgba(50,50,50,0.9)"),
                align="center", xanchor="center", yanchor="middle",
            )

            # Zona de traslado después (más tenue)
            if t_despues_h > 0:
                fig.add_shape(
                    type="rect",
                    x0=cx-ancho_col, x1=cx+ancho_col,
                    y0=y1_blk, y1=y1_blk + t_despues_h,
                    fillcolor="rgba(150,150,150,0.18)",
                    line=dict(color="rgba(120,120,120,0.3)", width=1, dash="dot"),
                    layer="below",
                )
                fig.add_annotation(
                    x=cx, y=y1_blk + t_despues_h/2,
                    text=f"traslado<br>{b.get('traslado_despues',0)} min",
                    showarrow=False,
                    font=dict(size=7, color="rgba(80,80,80,0.7)"),
                    align="center", xanchor="center", yanchor="middle",
                )

    for _, row in horario_df.iterrows():
        sesiones = obtener_sesiones(row)
        if not sesiones: continue
        nombre = row["nombre del curso"]
        if nombre not in color_map:
            color_map[nombre] = palette[color_idx % len(palette)]
            color_idx += 1
        color = color_map[nombre]
        docente = str(row.get("docente","Sin docente")).strip()
        if not docente or docente in ["nan","None",""]: docente = "Sin docente"

        for ses in sesiones:
            ini,fin,dia = ses["inicio"],ses["fin"],ses["dia"]
            if dia not in dia_x: continue
            cx = dia_x[dia]
            y0 = ini.hour + ini.minute/60
            y1 = fin.hour + fin.minute/60
            cy = (y0+y1)/2
            dur_h = y1-y0
            hora_txt = f"{ini.strftime('%H:%M')}-{fin.strftime('%H:%M')}"
            if dur_h < 0.75:
                label,font_size = hora_txt, 8
            elif dur_h < 1.25:
                n = nombre[:12]+"…" if len(nombre)>12 else nombre
                label,font_size = f"<b>{n}</b><br>{hora_txt}", 8
            elif dur_h < 2.0:
                n = nombre[:16]+"…" if len(nombre)>16 else nombre
                label,font_size = f"<b>{n}</b><br>{hora_txt}", 9
            else:
                n = nombre[:18]+"…" if len(nombre)>18 else nombre
                d = docente[:18]+"…" if len(docente)>18 else docente
                label = f"<b>{n}</b><br>Sec.{fmt_seccion(row['seccion'])} | {hora_txt}<br>{d}"
                font_size = 9
            fig.add_shape(
                type="rect",
                x0=cx-ancho_col, x1=cx+ancho_col,
                y0=y0, y1=y1,
                fillcolor=color,
                line=dict(color="white",width=2),
                layer="below",
            )
            fig.add_annotation(
                x=cx, y=cy, text=label, showarrow=False,
                font=dict(size=font_size, color="white"),
                align="center", xanchor="center", yanchor="middle",
                bgcolor="rgba(0,0,0,0)", borderpad=1,
            )

    hora_min,hora_max = 6,23
    n_dias = len(dias_con)
    fig.update_layout(
        height=720,
        xaxis=dict(
            tickvals=list(range(n_dias)), ticktext=dias_con,
            range=[-0.5,n_dias-0.5], showgrid=True,
            gridcolor="rgba(128,128,128,0.3)", side="top", fixedrange=True,
        ),
        yaxis=dict(
            tickvals=list(range(hora_min,hora_max+1)),
            ticktext=[f"{h:02d}:00" for h in range(hora_min,hora_max+1)],
            range=[hora_max,hora_min], showgrid=True,
            gridcolor="rgba(128,128,128,0.3)", fixedrange=True,
        ),
        template="none",
        margin=dict(t=60,l=70,r=20,b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.subheader(titulo)
    st.plotly_chart(fig, use_container_width=True)

# ================================================
# FILTROS COMUNES (sidebar)
# ================================================
st.sidebar.header("Filtros")

ORDEN_CICLOS = ["TERCER CICLO","QUINTO CICLO","SEPTIMO CICLO","NOVENO CICLO"]
ciclos_disponibles = df["ciclo"].dropna().unique()
ciclos_ordenados   = [c for c in ORDEN_CICLOS if c in ciclos_disponibles] + \
                     [c for c in sorted(ciclos_disponibles) if c not in ORDEN_CICLOS]

carrera = st.sidebar.selectbox("Carrera",          sorted(df["carrera"].dropna().unique()))
ciclo   = st.sidebar.selectbox("Ciclo",            ciclos_ordenados)
plan    = st.sidebar.selectbox("Plan de estudios", sorted(df["plan de estudios"].dropna().unique()))

filtrado_base = df[
    (df["carrera"]==carrera) & (df["ciclo"]==ciclo) & (df["plan de estudios"]==plan)
]
sedes_disponibles = sorted(filtrado_base["sede"].dropna().unique())
sede = st.sidebar.selectbox("Sede", ["Todas"]+sedes_disponibles)

filtrado = filtrado_base if sede=="Todas" else filtrado_base[filtrado_base["sede"]==sede]

if filtrado_base.empty:
    st.warning(f"No hay cursos para {carrera} — {ciclo} — Plan {plan}.")
    st.stop()
if filtrado.empty:
    st.warning(f"No hay cursos en la sede **{sede}** para {carrera} — {ciclo} — Plan {plan}.")
    st.stop()

# ================================================
# MODO SIMULADOR
# ================================================
if modo_actual == "simulador":
    st.title("🗓️ Simulador de Horarios")

    st.header("Paso 1: Selecciona los cursos")
    cursos = sorted(filtrado["nombre del curso"].unique())
    st.caption(f"Se encontraron **{len(cursos)} cursos** para {carrera} — {ciclo} — Plan {plan}.")

    cursos_seleccionados = []
    cols = st.columns(2)
    for idx, curso in enumerate(cursos):
        if cols[idx%2].checkbox(curso, key=f"chk_{curso}"):
            cursos_seleccionados.append(curso)

    if st.button("Continuar a horarios"):
        if not cursos_seleccionados:
            st.warning("Selecciona al menos un curso.")
        else:
            st.session_state.cursos_elegidos = cursos_seleccionados

    if "cursos_elegidos" in st.session_state:
        st.header("Paso 2: Escoge sección y horario")
        st.caption("Las opciones muestran las secciones disponibles para la sede seleccionada.")
        seleccionados = []

        for curso in st.session_state.cursos_elegidos:
            curso_df = filtrado[filtrado["nombre del curso"]==curso].copy()
            curso_df["docente"] = (
                curso_df["docente"].fillna("Sin docente").astype(str).str.strip()
                .replace({"":"Sin docente","nan":"Sin docente","None":"Sin docente"})
            )
            curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)
            curso_df["opcion"]  = curso_df.apply(construir_opcion, axis=1)
            curso_df = curso_df.sort_values("seccion")
            opciones = curso_df["opcion"].tolist()
            if all("Sin horario asignado" in op for op in opciones):
                st.warning(f"**{curso}**: ninguna sección tiene horario asignado aún.")
            NO_LLEVAR = "— No llevar este curso —"
            seleccion = st.selectbox(f"**{curso}**", [NO_LLEVAR]+opciones, key=f"sel_{curso}")
            if seleccion==NO_LLEVAR: continue
            fila = curso_df[curso_df["opcion"]==seleccion].iloc[0]
            seleccionados.append(fila)

        horario = pd.DataFrame(seleccionados)

        if st.button("Generar horario"):
            if horario.empty:
                st.warning("No has seleccionado ningún curso.")
                st.stop()
            conflictos = detectar_cruces(horario)
            if conflictos:
                st.error("Hay cruces de horario:")
                for c in conflictos: st.write(f"- {c}")
            else:
                st.success("✅ Horario generado correctamente.")
                dibujar_horario(horario)
                st.subheader("Resumen de cursos")
                cols_r = ["nombre del curso","docente","seccion","sede","dia 1","hora inicio 1","hora fin 1"]
                resumen = horario[[c for c in cols_r if c in horario.columns]].copy()
                resumen.columns = ["Curso","Docente","Sección","Sede","Día","Inicio","Fin"][:len(resumen.columns)]
                st.dataframe(resumen, use_container_width=True)

# ================================================
# MODO GENERADOR
# ================================================
else:
    st.title("⚡ Generador de Horarios")
    st.markdown(
        "Dinos cuándo **no puedes** asistir y generaremos las mejores combinaciones "
        "de horario para ti, respetando tus tiempos."
    )

    # ---------- PASO 1: Cursos ----------
    st.header("Paso 1: Selecciona los cursos que quieres llevar")
    cursos = sorted(filtrado["nombre del curso"].unique())
    st.caption(f"Se encontraron **{len(cursos)} cursos** para {carrera} — {ciclo} — Plan {plan}.")

    cursos_gen = []
    cols2 = st.columns(2)
    for idx, curso in enumerate(cursos):
        if cols2[idx%2].checkbox(curso, key=f"gen_chk_{curso}"):
            cursos_gen.append(curso)

    if st.button("Continuar →", key="gen_paso1"):
        if not cursos_gen:
            st.warning("Selecciona al menos un curso.")
        else:
            st.session_state.gen_cursos = cursos_gen
            st.session_state.gen_paso = 2

    # ---------- PASO 2: Bloqueos ----------
    if st.session_state.get("gen_paso",1) >= 2 and "gen_cursos" in st.session_state:

        st.header("Paso 2: Define los horarios en que NO puedes asistir")
        st.info(
            "➕ **Puedes agregar tantos bloqueos como necesites**, incluso varios en el mismo día. "
            "Ejemplo: Lunes 08:00-12:00 (trabajo mañana) y Lunes 19:00-22:00 (trabajo noche) "
            "→ así el generador sabe que solo tienes libre el lunes en la tarde."
        )

        DIAS_SEMANA = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"]
        MEDIAS = [f"{h:02d}:{m:02d}" for h in range(5,24) for m in [0,30]]
        TRASLADOS = list(range(15, 181, 15))  # 15, 30, 45, ... 180

        if "gen_bloqueos" not in st.session_state:
            st.session_state.gen_bloqueos = []

        # Formulario para agregar bloqueo
        with st.expander("➕ Agregar bloqueo de horario", expanded=True):
            c1,c2,c3 = st.columns([2,2,2])
            dia_blk  = c1.selectbox("Día",         DIAS_SEMANA, key="blk_dia")
            hora_ini = c2.selectbox("Hora inicio", MEDIAS,      key="blk_ini")
            hora_fin = c3.selectbox("Hora fin",    MEDIAS,      key="blk_fin")

            st.markdown("**🚌 Tiempos de traslado**")
            ct1, ct2 = st.columns(2)
            traslado_antes = ct1.selectbox(
                "Antes del bloqueo (min)",
                [0] + TRASLADOS,
                index=0,
                key="blk_traslado_antes",
                help="¿Cuánto tiempo necesitas para llegar desde la universidad a tu actividad ANTES de que empiece? "
                     "Ejemplo: si trabajas a las 14:00 y tardas 1h, el sistema bloqueará clases que terminen después de las 13:00."
            )
            traslado_despues = ct2.selectbox(
                "Después del bloqueo (min)",
                [0] + TRASLADOS,
                index=2,
                key="blk_traslado_despues",
                help="¿Cuánto tiempo necesitas para llegar desde tu actividad de vuelta a la universidad DESPUÉS de que termine? "
                     "Ejemplo: si tu trabajo termina a las 18:00 y tardas 1.5h, el sistema bloqueará clases que empiecen antes de las 19:30."
            )
            st.caption(
                "💡 **Antes**: tiempo univ → tu actividad &nbsp;|&nbsp; "
                "**Después**: tiempo tu actividad → univ. Pon 0 si no aplica."
            )
            if st.button("➕ Agregar este bloqueo"):
                ini_h = int(hora_ini.split(":")[0]) + int(hora_ini.split(":")[1])/60
                fin_h = int(hora_fin.split(":")[0]) + int(hora_fin.split(":")[1])/60
                if fin_h <= ini_h:
                    st.error("⚠️ La hora de fin debe ser mayor a la de inicio.")
                else:
                    resumen_traslado = []
                    if traslado_antes > 0:  resumen_traslado.append(f"antes: {traslado_antes} min")
                    if traslado_despues > 0: resumen_traslado.append(f"después: {traslado_despues} min")
                    traslado_txt = " | ".join(resumen_traslado) if resumen_traslado else "sin traslado"
                    st.session_state.gen_bloqueos.append({
                        "dia":              dia_blk,
                        "inicio":           hora_ini,
                        "fin":              hora_fin,
                        "inicio_h":         ini_h,
                        "fin_h":            fin_h,
                        "traslado_antes":   traslado_antes,
                        "traslado_despues": traslado_despues,
                    })
                    st.success(f"✅ Agregado: {dia_blk} {hora_ini}–{hora_fin} | {traslado_txt}")
                    st.rerun()

        # Mostrar bloqueos actuales agrupados por día
        if st.session_state.gen_bloqueos:
            st.markdown(f"**Bloqueos actuales ({len(st.session_state.gen_bloqueos)} en total):**")
            st.caption("Puedes seguir agregando más bloqueos arriba o eliminar alguno con ❌")

            # Agrupar por día para mostrar más ordenado
            dias_con_bloqueo = []
            for b in st.session_state.gen_bloqueos:
                if b["dia"] not in dias_con_bloqueo:
                    dias_con_bloqueo.append(b["dia"])

            for dia_g in dias_con_bloqueo:
                bloqueos_dia = [(i,b) for i,b in enumerate(st.session_state.gen_bloqueos) if b["dia"]==dia_g]
                st.markdown(f"**📅 {dia_g}**")
                for i, b in bloqueos_dia:
                    col_b1, col_b2 = st.columns([5,1])
                    partes_traslado = []
                    if b.get("traslado_antes", 0) > 0:
                        partes_traslado.append(f"antes: <b>{b['traslado_antes']} min</b>")
                    if b.get("traslado_despues", 0) > 0:
                        partes_traslado.append(f"después: <b>{b['traslado_despues']} min</b>")
                    traslado_txt_display = " | ".join(partes_traslado) if partes_traslado else "sin traslado"
                    col_b1.markdown(
                        f"<div class='bloqueo-row'>🚫 &nbsp;"
                        f"{b['inicio']} – {b['fin']} &nbsp;|&nbsp; "
                        f"🚌 {traslado_txt_display}</div>",
                        unsafe_allow_html=True
                    )
                    if col_b2.button("❌", key=f"del_blk_{i}"):
                        st.session_state.gen_bloqueos.pop(i)
                        st.rerun()

        st.markdown("---")
        col_gen1, col_gen2 = st.columns([1,3])
        with col_gen1:
            if st.button("⚡ Generar combinaciones", type="primary"):
                st.session_state.gen_paso = 3
                st.rerun()

    # ---------- PASO 3: Resultados ----------
    if st.session_state.get("gen_paso",1) >= 3:

        st.header("Paso 3: Combinaciones recomendadas")

        bloqueos  = st.session_state.get("gen_bloqueos",[])
        cursos_ok = st.session_state.get("gen_cursos",[])

        # Construir mapa dia→bloqueos para verificación rápida
        bloqueos_por_dia = {}
        for b in bloqueos:
            dia_norm = b["dia"].upper().replace("É","E").replace("Á","A").replace("Ó","O")
            if dia_norm not in bloqueos_por_dia:
                bloqueos_por_dia[dia_norm] = []
            bloqueos_por_dia[dia_norm].append(b)

        def sesion_tiene_conflicto(dia, ini_h, fin_h):
            """True si la sesión se solapa o viola los márgenes de traslado con algún bloqueo."""
            dia_norm = dia.upper().replace("É","E").replace("Á","A").replace("Ó","O")
            for b in bloqueos_por_dia.get(dia_norm,[]):
                blk_ini        = b["inicio_h"]
                blk_fin        = b["fin_h"]
                t_antes_h      = b.get("traslado_antes",  b.get("traslado", 0)) / 60.0
                t_despues_h    = b.get("traslado_despues", b.get("traslado", 0)) / 60.0

                # Zona bloqueada efectiva = (blk_ini - t_antes) hasta (blk_fin + t_despues)
                zona_ini = blk_ini - t_antes_h
                zona_fin = blk_fin + t_despues_h

                # Solapamiento con zona bloqueada ampliada
                if ini_h < zona_fin and fin_h > zona_ini:
                    return True
            return False

        def combinacion_valida(filas):
            """Verifica que ninguna sesión de las filas tenga conflicto con bloqueos."""
            for row in filas:
                sesiones = obtener_sesiones(row)
                for ses in sesiones:
                    ini_h = ses["inicio"].hour + ses["inicio"].minute/60
                    fin_h = ses["fin"].hour   + ses["fin"].minute/60
                    if sesion_tiene_conflicto(ses["dia"], ini_h, fin_h):
                        return False
            return True

        def sin_cruces_internos(filas):
            df_tmp = pd.DataFrame(list(filas))
            return len(detectar_cruces(df_tmp)) == 0

        def score_combinacion(filas):
            """
            Puntaje: penaliza horas muy tempranas y muy tardías,
            premia distribución equilibrada. Menor es mejor.
            """
            score = 0
            for row in filas:
                for ses in obtener_sesiones(row):
                    ini_h = ses["inicio"].hour + ses["inicio"].minute/60
                    fin_h = ses["fin"].hour   + ses["fin"].minute/60
                    # Penalizar clases antes de las 8 o después de las 20
                    if ini_h < 8:  score += (8 - ini_h) * 2
                    if fin_h > 20: score += (fin_h - 20) * 1.5
            return score

        # Obtener secciones de cada curso
        opciones_por_curso = {}
        for curso in cursos_ok:
            curso_df = filtrado[filtrado["nombre del curso"]==curso].copy()
            curso_df["docente"] = (
                curso_df["docente"].fillna("Sin docente").astype(str).str.strip()
                .replace({"":"Sin docente","nan":"Sin docente","None":"Sin docente"})
            )
            curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)
            filas = [row for _,row in curso_df.iterrows()]
            opciones_por_curso[curso] = filas

        # Generar todas las combinaciones (máximo razonable)
        MAX_COMBIS = 500
        lista_opciones = [opciones_por_curso[c] for c in cursos_ok]

        combinaciones_validas = []
        count = 0
        for combo in iterproduct(*lista_opciones):
            count += 1
            if count > MAX_COMBIS: break
            filas = list(combo)
            if combinacion_valida(filas) and sin_cruces_internos(filas):
                s = score_combinacion(filas)
                combinaciones_validas.append((s, filas))

        combinaciones_validas.sort(key=lambda x: x[0])

        MAX_MOSTRAR = 4   # 1 principal + 3 alternativas

        # Guardar combinaciones en session_state para paginación
        if "comb_validas" not in st.session_state or st.session_state.get("comb_hash") != len(combinaciones_validas):
            st.session_state.comb_validas = combinaciones_validas
            st.session_state.comb_hash    = len(combinaciones_validas)
            st.session_state.comb_pagina  = 0

        if not combinaciones_validas:
            st.error("😔 No se encontraron combinaciones disponibles con los bloqueos definidos.")

            # ─── Recopilar diagnóstico completo ───
            # Por curso: {curso -> {sec -> [(dia, ini, fin, razon_corta)]}}
            diag_cursos = {}
            # Por día: {dia -> [(curso, sec, ini, fin, razon_corta)]}
            diag_dias   = {}

            def razon_conflicto(dia, ses, b):
                ini_h = ses["inicio"].hour + ses["inicio"].minute/60
                fin_h = ses["fin"].hour   + ses["fin"].minute/60
                blk_ini     = b["inicio_h"]
                blk_fin     = b["fin_h"]
                t_antes_h   = b.get("traslado_antes",  0) / 60.0
                t_despues_h = b.get("traslado_despues", 0) / 60.0
                zona_ini    = blk_ini - t_antes_h
                zona_fin    = blk_fin + t_despues_h
                ini_str = ses["inicio"].strftime("%H:%M")
                fin_str = ses["fin"].strftime("%H:%M")

                if ini_h < blk_fin and fin_h > blk_ini:
                    return (
                        f"clase {ini_str}–{fin_str} se superpone con bloqueo {b['inicio']}–{b['fin']}"
                    )
                elif fin_h > zona_ini and ini_h < blk_ini:
                    salida = f"{int(zona_ini):02d}:{int((zona_ini%1)*60):02d}"
                    return (
                        f"clase {ini_str}–{fin_str} termina tarde: necesitas salir a las {salida} "
                        f"para llegar al bloqueo {b['inicio']} ({b.get('traslado_antes',0)} min traslado)"
                    )
                else:
                    zona_fin_str = f"{int(zona_fin):02d}:{int((zona_fin%1)*60):02d}"
                    return (
                        f"clase {ini_str}–{fin_str} empieza muy pronto: bloqueo termina {b['fin']} "
                        f"+ {b.get('traslado_despues',0)} min traslado → libre recién a las {zona_fin_str}"
                    )

            for curso in cursos_ok:
                filas_curso = opciones_por_curso.get(curso, [])
                diag_cursos[curso] = {"bloqueadas": [], "libres": []}

                for row in filas_curso:
                    sec = fmt_seccion(row["seccion"])
                    sesiones = obtener_sesiones(row)
                    conflicto_encontrado = False
                    for ses in sesiones:
                        ini_h    = ses["inicio"].hour + ses["inicio"].minute/60
                        fin_h    = ses["fin"].hour   + ses["fin"].minute/60
                        dia      = ses["dia"]
                        dia_norm = dia.upper().replace("É","E").replace("Á","A").replace("Ó","O")

                        for b in bloqueos_por_dia.get(dia_norm, []):
                            blk_ini     = b["inicio_h"]
                            blk_fin     = b["fin_h"]
                            t_antes_h   = b.get("traslado_antes",  0) / 60.0
                            t_despues_h = b.get("traslado_despues", 0) / 60.0
                            zona_ini    = blk_ini - t_antes_h
                            zona_fin    = blk_fin + t_despues_h

                            if ini_h < zona_fin and fin_h > zona_ini:
                                razon = razon_conflicto(dia, ses, b)
                                diag_cursos[curso]["bloqueadas"].append((sec, dia, ses["inicio"].strftime("%H:%M"), ses["fin"].strftime("%H:%M"), razon))
                                # Registrar también por día
                                if dia not in diag_dias:
                                    diag_dias[dia] = []
                                diag_dias[dia].append((curso, sec, ses["inicio"].strftime("%H:%M"), ses["fin"].strftime("%H:%M"), razon))
                                conflicto_encontrado = True
                                break
                        if conflicto_encontrado:
                            break

                    if not conflicto_encontrado:
                        diag_cursos[curso]["libres"].append(sec)

            # ─── VISTA 1: Por curso ───
            st.markdown("### 📚 Diagnóstico por curso")
            for curso in cursos_ok:
                info  = diag_cursos[curso]
                libres     = info["libres"]
                bloqueadas = info["bloqueadas"]

                if not bloqueadas:
                    st.success(f"✅ **{curso}** — todas sus secciones son compatibles.")
                elif libres:
                    with st.expander(f"⚠️ {curso} — secciones {', '.join(libres)} disponibles, otras con conflicto"):
                        st.markdown(f"Las secciones **{', '.join(libres)}** no tienen conflicto con tus bloqueos, "
                                    f"pero no combinan bien con otro curso seleccionado.")
                        st.markdown("**Secciones con conflicto:**")
                        for sec, dia, ini, fin, razon in bloqueadas:
                            st.markdown(f"- Sec. **{sec}** — {razon}")
                else:
                    with st.expander(f"❌ {curso} — ninguna sección disponible"):
                        st.markdown("**Todas las secciones tienen conflicto:**")
                        for sec, dia, ini, fin, razon in bloqueadas:
                            st.markdown(f"- Sec. **{sec}** — {razon}")

            # ─── VISTA 2: Por día ───
            if diag_dias:
                st.markdown("### 📅 Diagnóstico por día")
                ORDEN_DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado"]
                dias_ordenados = [d for d in ORDEN_DIAS if d in diag_dias] +                                  [d for d in diag_dias if d not in ORDEN_DIAS]
                for dia in dias_ordenados:
                    conflictos_dia = diag_dias[dia]
                    cursos_afectados = list(dict.fromkeys([c[0] for c in conflictos_dia]))
                    with st.expander(f"📅 {dia} — {len(conflictos_dia)} conflicto(s) en {len(cursos_afectados)} curso(s)"):
                        # Mostrar los bloqueos de ese día
                        dia_norm = dia.upper().replace("É","E").replace("Á","A").replace("Ó","O")
                        blqs = bloqueos_por_dia.get(dia_norm, [])
                        if blqs:
                            st.markdown("**Tus bloqueos ese día:**")
                            for b in blqs:
                                partes = []
                                if b.get("traslado_antes",  0) > 0: partes.append(f"traslado antes: {b['traslado_antes']} min")
                                if b.get("traslado_despues",0) > 0: partes.append(f"traslado después: {b['traslado_despues']} min")
                                extras = f" ({', '.join(partes)})" if partes else ""
                                st.markdown(f"- 🚫 {b['inicio']}–{b['fin']}{extras}")
                        st.markdown("**Secciones que no pueden ir ese día:**")
                        for curso, sec, ini, fin, razon in conflictos_dia:
                            st.markdown(f"- **{curso}** Sec.{sec} ({ini}–{fin}): {razon}")

            st.markdown("---")
            st.info(
                "💡 **Sugerencias para encontrar combinaciones:**\n"
                "- Reduce el tiempo de traslado en el día con más conflictos\n"
                "- Elimina un bloqueo que no sea estrictamente necesario\n"
                "- Vuelve al Paso 1 y deselecciona algún curso conflictivo"
            )
        else:
            pagina       = st.session_state.get("comb_pagina", 0)
            total        = len(combinaciones_validas)
            inicio       = pagina * MAX_MOSTRAR
            fin_pag      = min(inicio + MAX_MOSTRAR, total)
            pagina_combis = combinaciones_validas[inicio:fin_pag]
            total_paginas = (total + MAX_MOSTRAR - 1) // MAX_MOSTRAR

            st.success(
                f"✅ Se encontraron **{total}** combinación(es) válida(s). "
                f"Mostrando **{inicio+1}–{fin_pag}** de {total} "
                f"(página {pagina+1} de {total_paginas})."
            )

            for i, (score, filas) in enumerate(pagina_combis):
                num_global = inicio + i
                if num_global == 0:
                    etiqueta = "⭐ Opción Principal"
                else:
                    etiqueta = f"Alternativa {num_global}"
                with st.expander(etiqueta, expanded=(i==0)):
                    horario_df = pd.DataFrame(list(filas))

                    # Resumen rápido
                    resumen_lines = []
                    for row in filas:
                        secs = obtener_sesiones(row)
                        docente_r = str(row.get("docente","")).strip()
                        if not docente_r or docente_r in ["nan","None",""]:
                            docente_r = "Sin docente"
                        for ses in secs:
                            ini_str = ses["inicio"].strftime("%H:%M")
                            fin_str = ses["fin"].strftime("%H:%M")
                            resumen_lines.append(
                                f"📚 **{row['nombre del curso']}** — "
                                f"{ses['dia']} {ini_str}-{fin_str} | "
                                f"Sec. {fmt_seccion(row['seccion'])} | "
                                f"👤 {docente_r}"
                            )
                    for line in resumen_lines:
                        st.markdown(line)

                    st.markdown("---")
                    dibujar_horario(horario_df, bloqueos=bloqueos, titulo=f"Horario — {etiqueta}")

            # ── Navegación de páginas ──
            st.markdown("---")
            nav1, nav2, nav3 = st.columns([1, 2, 1])
            with nav1:
                if pagina > 0:
                    if st.button("← Opciones anteriores"):
                        st.session_state.comb_pagina -= 1
                        st.rerun()
            with nav2:
                st.markdown(
                    f"<div style='text-align:center; color:gray; padding-top:6px;'>"
                    f"Página {pagina+1} de {total_paginas} &nbsp;|&nbsp; "
                    f"{total} combinaciones en total</div>",
                    unsafe_allow_html=True
                )
            with nav3:
                if fin_pag < total:
                    if st.button("Ver otras opciones →"):
                        st.session_state.comb_pagina += 1
                        st.rerun()

        if st.button("🔄 Volver a ajustar bloqueos"):
            st.session_state.comb_pagina = 0
            st.session_state.gen_paso = 2
            st.rerun()
