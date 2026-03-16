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

/* Secciones disponibles pill */
.secciones-ok {
    display: inline-block;
    background: rgba(40,167,69,0.12);
    border: 1px solid rgba(40,167,69,0.4);
    color: #1a6e2e;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-left: 8px;
}
.secciones-warn {
    display: inline-block;
    background: rgba(255,193,7,0.15);
    border: 1px solid rgba(255,193,7,0.5);
    color: #856404;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-left: 8px;
}
.secciones-error {
    display: inline-block;
    background: rgba(220,53,69,0.12);
    border: 1px solid rgba(220,53,69,0.4);
    color: #842029;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-left: 8px;
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
    dias     = ["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES","SABADO"]
    dias_con = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES","SÁBADO"]
    dia_x    = {d:i for i,d in enumerate(dias_con)}
    dia_x.update({d:i for i,d in enumerate(dias)})
    ancho_col = 0.42

    fig       = go.Figure()
    color_map = {}
    color_idx = 0

    if bloqueos:
        for b in bloqueos:
            dia_b = b["dia"].upper().replace("É","E").replace("Á","A").replace("Ó","O")
            if dia_b not in dia_x: continue
            cx = dia_x[dia_b]
            y0_blk = b["inicio_h"]
            y1_blk = b["fin_h"]
            t_antes_h   = b.get("traslado_antes",  b.get("traslado", 0)) / 60.0
            t_despues_h = b.get("traslado_despues", b.get("traslado", 0)) / 60.0

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
    import hashlib, time
    chart_key = hashlib.md5(f"{titulo}{time.time_ns()}".encode()).hexdigest()[:12]
    st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_key}")

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
        TRASLADOS = list(range(15, 181, 15))

        if "gen_bloqueos" not in st.session_state:
            st.session_state.gen_bloqueos = []

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
                help="¿Cuánto tiempo necesitas para llegar desde la universidad a tu actividad ANTES de que empiece?"
            )
            traslado_despues = ct2.selectbox(
                "Después del bloqueo (min)",
                [0] + TRASLADOS,
                index=2,
                key="blk_traslado_despues",
                help="¿Cuánto tiempo necesitas para llegar desde tu actividad de vuelta a la universidad DESPUÉS de que termine?"
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
                    if traslado_antes > 0:   resumen_traslado.append(f"antes: {traslado_antes} min")
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

        if st.session_state.gen_bloqueos:
            st.markdown(f"**Bloqueos actuales ({len(st.session_state.gen_bloqueos)} en total):**")
            st.caption("Puedes seguir agregando más bloqueos arriba o eliminar alguno con ❌")

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
                blk_ini     = b["inicio_h"]
                blk_fin     = b["fin_h"]
                t_antes_h   = b.get("traslado_antes",  b.get("traslado", 0)) / 60.0
                t_despues_h = b.get("traslado_despues", b.get("traslado", 0)) / 60.0
                zona_ini = blk_ini - t_antes_h
                zona_fin = blk_fin + t_despues_h
                if ini_h < zona_fin and fin_h > zona_ini:
                    return True
            return False

        def fila_es_libre(row):
            """True si NINGUNA sesión de la fila tiene conflicto con bloqueos."""
            for ses in obtener_sesiones(row):
                ini_h = ses["inicio"].hour + ses["inicio"].minute/60
                fin_h = ses["fin"].hour   + ses["fin"].minute/60
                if sesion_tiene_conflicto(ses["dia"], ini_h, fin_h):
                    return False
            return True

        def combinacion_valida(filas):
            return all(fila_es_libre(row) for row in filas)

        def sin_cruces_internos(filas):
            df_tmp = pd.DataFrame(list(filas))
            return len(detectar_cruces(df_tmp)) == 0

        def score_combinacion(filas):
            score = 0
            for row in filas:
                for ses in obtener_sesiones(row):
                    ini_h = ses["inicio"].hour + ses["inicio"].minute/60
                    fin_h = ses["fin"].hour   + ses["fin"].minute/60
                    if ini_h < 8:  score += (8 - ini_h) * 2
                    if fin_h > 20: score += (fin_h - 20) * 1.5
            return score

        # ── FILTRAR SECCIONES POR BLOQUEOS (sin fallback) ──────────────────────
        # Cada curso solo conserva las secciones cuyas sesiones NO chocan con bloqueos.
        # Si no queda ninguna sección libre, el curso queda con lista vacía → sin combinaciones.

        opciones_por_curso = {}
        for curso in cursos_ok:
            curso_df = filtrado[filtrado["nombre del curso"]==curso].copy()
            curso_df["docente"] = (
                curso_df["docente"].fillna("Sin docente").astype(str).str.strip()
                .replace({"":"Sin docente","nan":"Sin docente","None":"Sin docente"})
            )
            curso_df["seccion"] = curso_df["seccion"].apply(fmt_seccion)
            opciones_por_curso[curso] = [row for _,row in curso_df.iterrows()]

        opciones_filtradas = {}
        cursos_sin_seccion = []   # cursos que quedaron sin ninguna sección disponible

        for curso in cursos_ok:
            libres = [row for row in opciones_por_curso[curso] if fila_es_libre(row)]
            if libres:
                opciones_filtradas[curso] = libres
            else:
                # No hay ninguna sección compatible → marcar y dejar lista vacía
                opciones_filtradas[curso] = []
                cursos_sin_seccion.append(curso)

        # ── MOSTRAR RESUMEN DE SECCIONES DISPONIBLES POR CURSO ─────────────────
        st.markdown("#### 📋 Secciones compatibles con tus bloqueos")
        total_secs_por_curso = {c: len(opciones_por_curso[c]) for c in cursos_ok}
        libres_por_curso     = {c: len(opciones_filtradas[c]) for c in cursos_ok}

        cols_preview = st.columns(min(len(cursos_ok), 3))
        for i, curso in enumerate(cursos_ok):
            total = total_secs_por_curso[curso]
            libres = libres_por_curso[curso]
            col = cols_preview[i % len(cols_preview)]
            with col:
                if libres == 0:
                    badge = f"<span class='secciones-error'>0 / {total} secciones</span>"
                    col.markdown(
                        f"❌ **{curso}**<br>{badge}<br>"
                        f"<small style='color:#842029'>Ninguna sección es compatible con tus bloqueos</small>",
                        unsafe_allow_html=True
                    )
                elif libres < total:
                    badge = f"<span class='secciones-warn'>{libres} / {total} secciones</span>"
                    secs_libres = [fmt_seccion(r.get("seccion","")) for r in opciones_filtradas[curso]]
                    col.markdown(
                        f"⚠️ **{curso}**<br>{badge}<br>"
                        f"<small>Secciones disponibles: {', '.join(secs_libres)}</small>",
                        unsafe_allow_html=True
                    )
                else:
                    badge = f"<span class='secciones-ok'>{libres} / {total} secciones</span>"
                    col.markdown(
                        f"✅ **{curso}**<br>{badge}",
                        unsafe_allow_html=True
                    )

        st.markdown("---")

        # Si algún curso quedó sin secciones, no tiene sentido combinar → mostrar error directo
        if cursos_sin_seccion:
            st.error(
                f"😔 Los siguientes cursos **no tienen ninguna sección compatible** con tus bloqueos: "
                f"**{', '.join(cursos_sin_seccion)}**.\n\n"
                "No es posible generar combinaciones. Ajusta tus bloqueos o deselecciona estos cursos."
            )

            # Diagnóstico detallado de los cursos bloqueados
            st.markdown("### 📚 ¿Por qué no hay secciones disponibles?")
            for curso in cursos_sin_seccion:
                with st.expander(f"❌ {curso} — detalle de conflictos"):
                    for row in opciones_por_curso[curso]:
                        sec = fmt_seccion(row.get("seccion",""))
                        sesiones = obtener_sesiones(row)
                        conflictos_sec = []
                        for ses in sesiones:
                            ini_h    = ses["inicio"].hour + ses["inicio"].minute/60
                            fin_h    = ses["fin"].hour   + ses["fin"].minute/60
                            dia_norm = ses["dia"].upper().replace("É","E").replace("Á","A").replace("Ó","O")
                            for b in bloqueos_por_dia.get(dia_norm, []):
                                t_antes_h   = b.get("traslado_antes",  0) / 60.0
                                t_despues_h = b.get("traslado_despues", 0) / 60.0
                                zona_ini    = b["inicio_h"] - t_antes_h
                                zona_fin    = b["fin_h"]    + t_despues_h
                                if ini_h < zona_fin and fin_h > zona_ini:
                                    ini_str = ses["inicio"].strftime("%H:%M")
                                    fin_str = ses["fin"].strftime("%H:%M")
                                    zona_ini_str = f"{int(zona_ini):02d}:{int((zona_ini%1)*60):02d}"
                                    zona_fin_str = f"{int(zona_fin):02d}:{int((zona_fin%1)*60):02d}"
                                    conflictos_sec.append(
                                        f"Sec. **{sec}** — {ses['dia']} {ini_str}–{fin_str} "
                                        f"choca con bloqueo {b['inicio']}–{b['fin']} "
                                        f"(zona bloqueada efectiva: {zona_ini_str}–{zona_fin_str})"
                                    )
                                    break
                        for msg in conflictos_sec:
                            st.markdown(f"- {msg}")

            st.markdown("---")
            st.info(
                "💡 **Sugerencias:**\n"
                "- Reduce el tiempo de traslado en alguno de tus bloqueos\n"
                "- Elimina un bloqueo que no sea estrictamente necesario\n"
                "- Vuelve al Paso 1 y deselecciona el curso problemático"
            )

        else:
            # ── GENERAR COMBINACIONES con las secciones ya filtradas ─────────────
            MAX_COMBIS_VALIDAS = 200
            lista_opciones = [opciones_filtradas[c] for c in cursos_ok]

            total_tras_filtro = 1
            for opts in lista_opciones:
                total_tras_filtro *= len(opts)

            MAX_ITER = max(5000, total_tras_filtro)

            combinaciones_validas = []
            count = 0
            for combo in iterproduct(*lista_opciones):
                count += 1
                if count > MAX_ITER: break
                filas = list(combo)
                # combinacion_valida ya es redundante porque filtramos antes,
                # pero lo dejamos como doble chequeo de seguridad
                if combinacion_valida(filas) and sin_cruces_internos(filas):
                    s = score_combinacion(filas)
                    combinaciones_validas.append((s, filas))
                    if len(combinaciones_validas) >= MAX_COMBIS_VALIDAS:
                        break

            combinaciones_validas.sort(key=lambda x: x[0])

            MAX_MOSTRAR = 4

            if "comb_validas" not in st.session_state or st.session_state.get("comb_hash") != len(combinaciones_validas):
                st.session_state.comb_validas = combinaciones_validas
                st.session_state.comb_hash    = len(combinaciones_validas)
                st.session_state.comb_pagina  = 0

            if not combinaciones_validas:
                st.error(
                    "😔 Las secciones compatibles con tus bloqueos se cruzan entre sí. "
                    "No hay ninguna combinación sin conflictos internos."
                )

                # Diagnóstico: mostrar qué secciones quedaron y por qué se cruzan
                st.markdown("### 📚 Secciones disponibles (pero con cruces entre cursos)")
                for curso in cursos_ok:
                    filas = opciones_filtradas[curso]
                    secs  = [fmt_seccion(r.get("seccion","")) for r in filas]
                    ops   = [construir_opcion(r) for r in filas]
                    with st.expander(f"📖 {curso} — {len(secs)} sección(es) libre(s)"):
                        for op in ops:
                            st.markdown(f"- {op}")

                st.info(
                    "💡 **Sugerencias:**\n"
                    "- Amplía algún bloqueo (más horas libres = más secciones disponibles = más combinaciones)\n"
                    "- Elimina un bloqueo secundario\n"
                    "- Deselecciona algún curso para reducir conflictos entre asignaturas"
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
                    etiqueta = "⭐ Opción Principal" if num_global == 0 else f"Alternativa {num_global}"
                    with st.expander(etiqueta, expanded=(i==0)):
                        horario_df = pd.DataFrame(list(filas))

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
