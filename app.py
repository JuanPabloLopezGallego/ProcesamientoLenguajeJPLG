# =============================================================================
# Trovador · Atelier de poesía: de PDF a poema
# Stack: Streamlit + OpenAI (RAG escrito a mano, sin LangChain).
#   - app.py            -> este archivo
#   - requirements.txt  -> dependencias
#   - .streamlit/secrets.toml (local) o sección Secrets (cloud) -> OPENAI_API_KEY
# =============================================================================

import os
import json
import time
import re
import secrets as _secrets
from datetime import datetime
from pathlib import Path

import streamlit as st
import pdfplumber

# OpenAI es opcional: si no hay clave, generamos un poema demo.
try:
    from openai import OpenAI
    _OPENAI_OK = True
except Exception:
    _OPENAI_OK = False


# -----------------------------------------------------------------------------
# Configuración de página + secretos
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Trovador · De PDF a Poema",
    page_icon="🪶",
    layout="wide",
    initial_sidebar_state="expanded",
)

try:
    API_KEY = st.secrets["OPENAI_API_KEY"]
except Exception:
    API_KEY = None


# -----------------------------------------------------------------------------
# Estilo (paleta papel cálido)
# -----------------------------------------------------------------------------
PALETTE = {
    "paper":    "#faf6ee",
    "paper_deep": "#f3ecdd",
    "card":     "#fffdf8",
    "ink":      "#201a15",
    "ink_soft": "#575046",
    "muted":    "#8a8177",
    "line":     "#e7dcc8",
    "line_strong": "#d8c9ae",
    "clay":     "#bc4b26",
    "clay_deep":  "#933613",
    "clay_soft":  "#fbe9dd",
    "moss":     "#44523f",
    "moss_deep":  "#2f3a2c",
    "moss_soft":  "#e8ecdf",
    "gold":     "#b98a1f",
    "gold_soft":  "#f8efce",
}

CSS = f"""
<style>
    .stApp {{
        background:
          radial-gradient(ellipse at 20% 10%, rgba(185,138,31,0.10), transparent 55%),
          radial-gradient(ellipse at 90% 20%, rgba(188,75,38,0.08), transparent 50%),
          radial-gradient(ellipse at 50% 100%, rgba(68,82,63,0.08), transparent 60%),
          repeating-linear-gradient(0deg, transparent 0 3px, rgba(32,26,21,0.012) 3px 4px),
          {PALETTE['paper']};
        color: {PALETTE['ink']};
        font-family: 'Inter', system-ui, sans-serif;
    }}
    h1, h2, h3, h4 {{
        font-family: 'Fraunces', 'Georgia', serif !important;
        color: {PALETTE['ink']} !important;
        letter-spacing: -0.01em;
    }}
    p, label, span, li, small {{ color: {PALETTE['ink_soft']}; }}
    a {{ color: {PALETTE['clay']} !important; }}

    .stButton>button {{
        background: {PALETTE['ink']};
        color: white;
        border: none;
        border-radius: 999px;
        padding: 0.65rem 1.25rem;
        font-weight: 700;
        transition: all .15s;
    }}
    .stButton>button:hover {{ background: {PALETTE['clay']}; color: white; }}
    .stButton>button:disabled {{ opacity: .5; }}

    .card {{
        background: {PALETTE['card']};
        border: 1px solid {PALETTE['line']};
        border-radius: 22px;
        padding: 26px;
        box-shadow: 0 12px 32px -12px rgba(32,26,21,0.14);
    }}
    .card-tinted {{
        background: linear-gradient(180deg, {PALETTE['paper_deep']} 0%, {PALETTE['card']} 100%);
    }}
    .stamp {{
        border: 1.5px dashed {PALETTE['line_strong']};
        border-radius: 16px;
        padding: 12px;
    }}

    .badge {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
        background: {PALETTE['paper_deep']};
        color: {PALETTE['ink_soft']};
    }}
    .badge.clay {{ background: {PALETTE['clay_soft']}; color: {PALETTE['clay_deep']}; }}
    .badge.moss {{ background: {PALETTE['moss_soft']}; color: {PALETTE['moss_deep']}; }}
    .badge.gold {{ background: {PALETTE['gold_soft']}; color: #7a5c0a; }}
    .badge.ink  {{ background: {PALETTE['ink']};  color: white; }}

    .step {{
        display: inline-flex; gap: 8px; align-items: center;
        padding: 8px 14px; border-radius: 999px;
        background: {PALETTE['paper_deep']};
        color: {PALETTE['ink_soft']};
        font-weight: 600; font-size: 13px;
    }}
    .step.done {{ background: {PALETTE['moss']}; color: white; }}

    .progress-track {{ background: {PALETTE['line']}; border-radius: 999px; height: 10px; overflow: hidden; }}
    .progress-bar  {{ background: {PALETTE['clay']}; height: 10px; border-radius: 999px; transition: width .4s; }}

    .poem {{
        background: {PALETTE['paper']};
        border: 1px solid {PALETTE['line']};
        border-radius: 22px;
        padding: 32px;
        font-family: 'Fraunces', 'Georgia', serif;
        font-style: italic;
        line-height: 1.95;
        font-size: 1.08rem;
        background-image: repeating-linear-gradient(180deg, transparent 0 30px, rgba(68,82,63,0.10) 30px 31px);
        color: {PALETTE['ink']};
    }}
    .poem::first-line {{ font-weight: 600; }}

    textarea, input[type=text], input[type=password] {{
        background: {PALETTE['paper']} !important;
        border: 1px solid {PALETTE['line']} !important;
        border-radius: 14px !important;
    }}
    textarea:focus, input:focus {{ border-color: {PALETTE['clay']} !important; box-shadow: 0 0 0 3px rgba(188,75,38,0.15); }}

    .file-drop {{
        background: {PALETTE['paper']};
        border: 2px dashed {PALETTE['line_strong']};
        border-radius: 22px;
        padding: 40px 20px;
        text-align: center;
    }}
    .file-drop.drag {{ border-color: {PALETTE['clay']}; background: {PALETTE['clay_soft']}; }}

    .stProgress > div > div > div > div {{ background: {PALETTE['clay']}; }}

    [data-testid="stFileUploaderDropzone"] {{
        background: transparent !important;
        border: none !important;
    }}

    #MainMenu, header {{ visibility: visible; }}
    footer {{ visibility: hidden; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Utilidades RAG (escritas a mano, sin LangChain)
# -----------------------------------------------------------------------------
STOPWORDS = set(
    "el la los las de del en y o que con por para un una unos unas se su sus al "
    "como mas pero este esta estos estas ese esa hay son es fue han the and of "
    "to in a is it for on".split()
)


def split_text(text: str, chunk_size: int = 600, overlap: int = 50) -> list[str]:
    clean = text.replace("\r", "").strip()
    if not clean:
        return []
    paras = [p.strip() for p in clean.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush_part(s: str):
        s = " ".join(s.split())
        i = 0
        while i < len(s):
            end = min(i + chunk_size, len(s))
            chunks.append(s[i:end].strip())
            if end >= len(s):
                break
            i = end - overlap

    for p in paras:
        candidate = (buf + "\n" + p).strip() if buf else p
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            if buf:
                (flush_part(buf) if len(buf) > chunk_size else chunks.append(buf.strip()))
            if len(p) > chunk_size:
                flush_part(p)
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf.strip())
    return [c for c in chunks if len(c) > 20]


def tokenize(s: str) -> list[str]:
    s = (s.lower().replace("á", "a").replace("é", "e").replace("í", "i")
           .replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
    toks = re.findall(r"[a-z0-9]{3,}", s)
    return [t for t in toks if t not in STOPWORDS]


def score_chunk(query: str, chunk: str) -> float:
    q = set(tokenize(query))
    if not q:
        return 0.0
    ct = tokenize(chunk)
    cs = set(ct)
    hits = 0.0
    for t in q:
        if t in cs:
            hits += 2
        else:
            for x in cs:
                if x.startswith(t[:5]) or t.startswith(x[:5]):
                    hits += 0.6
                    break
    bonus = min(len(chunk) / 600, 1) * 0.4
    return hits + bonus


def retrieve(query: str, chunks: list[str], k: int = 4) -> list[str]:
    scored = [(score_chunk(query, c), c) for c in chunks]
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [c for _, c in scored[:k]]
    if not top or max(s for s, _ in scored) == 0:
        return chunks[:k]
    return top


TONE_HINT = {
    "Contemplativo": "pausado y reflexivo, como mirar por la ventana",
    "Melancólico": "nostálgico, con niebla y atardeceres",
    "Alegre": "luminoso, con ritmo juguetón",
    "Romántico": "tierno e íntimo, de latidos y jazmines",
    "Épico": "grande y heroico, de horizontes en llamas",
    "Oscuro": "nocturno, de sombras y ecos",
    "Esperanzado": "abierto al mañana, de semillas y albas",
}

TONE_IMAGERY = {
    "Melancólico":  ["la tarde que se dobla", "una niebla delgada", "el eco de lo perdido", "ceniza tibia del recuerdo"],
    "Alegre":       ["la luz que se derrama", "un júbilo de pájaros", "la fiesta de la mañana", "risas sobre el papel"],
    "Épico":        ["el fragor de los tiempos", "estandartes del alba", "la marcha de los siglos", "un horizonte en llamas"],
    "Romántico":    ["el temblor de tu nombre", "jazmines en la penumbra", "un latido compartido", "la luna entre los versos"],
    "Oscuro":       ["la sombra que respira", "un sótano de ecos", "la noche sin orillas", "cuervos sobre el tejado"],
    "Contemplativo":["el silencio que observa", "agua quieta del estanque", "la hora suspendida", "polvo de luz inmóvil"],
    "Esperanzado":  ["una puerta entreabierta", "la semilla que despierta", "el alba que regresa", "manos que siembran luz"],
}


def build_prompt(context: str, topic: str, tone: str, form: str) -> str:
    return f"""Eres un poeta talentoso y lírico, un trovador contemporáneo que escribe en español con imágenes vívidas y musicalidad.

Utiliza ÚNICAMENTE la información del siguiente texto extraído de un documento para inspirar el poema. No inventes datos fácticos que contradigan el texto, pero sí puedes usar metáforas y lenguaje poético.

— INFORMACIÓN DEL DOCUMENTO —
{context}

— PETICIÓN DEL LECTOR —
Tema o enfoque: {topic}
Tono deseado: {tone or 'Contemplativo'} ({TONE_HINT.get(tone, '')})
Forma poética: {form or 'Verso libre'}

Instrucciones de estilo:
- Escribe directamente el poema, sin explicaciones previas ni posteriores.
- Si la forma es soneto, respeta 14 versos; si es haiku, 3 versos breves; si es décima, 10 versos; si es romance, versos octosílabos con asonancia.
- Incluye un título evocador en la primera línea (entre comillas o como título).
- Cierra con una imagen memorable que dialogue con el documento.
Poema:"""


def generate_demo_poem(relevant: list[str], topic: str, tone: str, form: str, filename: str) -> str:
    src = " ".join(relevant)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", src) if len(s.strip()) > 25][:12]
    keywords = list(dict.fromkeys(tokenize(src)))[:14]
    images = TONE_IMAGERY.get(tone, TONE_IMAGERY["Contemplativo"])
    clean_name = re.sub(r"\.pdf$", "", filename, flags=re.I)
    clean_name = re.sub(r"[-_]+", " ", clean_name)[:42] or "el documento"
    title = topic if len(topic) > 6 else f"Canto inspirado en {clean_name}"

    def pick(arr, i):
        if not arr:
            return ""
        return arr[i % len(arr)]

    verses: list[str] = []

    if form == "Haiku":
        k1 = keywords[0] if len(keywords) > 0 else "memoria"
        k2 = keywords[1] if len(keywords) > 1 else "papel"
        k3 = keywords[2] if len(keywords) > 2 else "tiempo"
        return f"“{title}”\n\n{k1} sobre el papel —\n{images[0]};\n{k2} y {k3} en calma."

    target = 14 if form == "Soneto" else (10 if form == "Décima" else 16)

    for i in range(target):
        sent = pick(sentences or [" ".join(keywords)], i)
        frag = sent.split(",")[0][:72].strip().rstrip(".")
        img = pick(images, i + 1)
        kw_a = keywords[i % max(len(keywords), 1)] or "el sentido"
        kw_b = keywords[(i * 2) % max(len(keywords), 1)] or "la palabra"
        lc_topic = topic.lower()[:48] or "memoria"

        if i % 4 == 0:
            verses.append(f'Yo leí en “{clean_name}” que {frag.lower()},')
        elif i % 4 == 1:
            verses.append(f'y en {img} descubrí {kw_a}.')
        elif i % 4 == 2:
            verses.append(f'{frag.capitalize()} — {lc_topic}.')
        else:
            verses.append(f'Que {img} guarde {kw_b}.')

        if (form == "Soneto" or target > 12) and i in (3, 7, 11):
            verses.append("")

    body = "\n".join(verses).strip()
    return f"“{title}”\n\n{body}\n\n— Compuesto en modo atelier (demo) a partir de {len(relevant)} fragmentos de “{clean_name}”."


def call_openai(api_key: str, prompt: str) -> str:
    if not _OPENAI_OK:
        raise RuntimeError("La librería openai no está instalada.")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.75,
        max_tokens=1200,
        messages=[
            {"role": "system", "content": "Eres un poeta lírico que escribe en español. Respondes solo con el poema."},
            {"role": "user", "content": prompt},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


# -----------------------------------------------------------------------------
# Estado: biblioteca persistente en disco (.trovador/)
# -----------------------------------------------------------------------------
DATA_DIR = Path.home() / ".trovador"
DATA_DIR.mkdir(exist_ok=True)
LIBRARY_FILE = DATA_DIR / "library.json"


def _load_library() -> list[dict]:
    if not LIBRARY_FILE.exists():
        return []
    try:
        return json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_library(items: list[dict]) -> None:
    LIBRARY_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add_poem(item: dict) -> None:
    items = _load_library()
    items.insert(0, item)
    _save_library(items[:60])


def delete_poem(pid: str) -> None:
    items = [p for p in _load_library() if p.get("id") != pid]
    _save_library(items)


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
          <span style="background:{PALETTE['clay']};color:white;border-radius:14px;width:42px;height:42px;
                       display:inline-flex;align-items:center;justify-content:center;font-size:22px">🪶</span>
          <span style="font-family:'Fraunces',serif;font-size:19px;font-weight:600">Trovador</span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption("Atelier de poesía · de PDF a poema.")
    st.divider()

    mode = st.radio(
        "Modo de generación",
        options=["Atelier (demo, sin clave)", "OpenAI · gpt-4o-mini"],
        index=0 if not API_KEY else 1,
        help="El modo demo no usa API. El modo OpenAI usa la clave definida en Secrets.",
    )
    use_api = mode.startswith("OpenAI")

    if use_api and not API_KEY:
        st.error("No hay clave OPENAI_API_KEY en Secrets. Añádela en la configuración de la app.")
        client_key = st.text_input("O pega aquí una clave (solo esta sesión)", type="password")
        if client_key:
            API_KEY = client_key

    st.divider()
    st.caption(f"Streamlit · Trovador v2.0 · {datetime.now().strftime('%Y/%m')}")


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;
                padding:14px 18px;background:{PALETTE['moss_deep']};color:#f3ecdd;border-radius:18px;">
      <div>✨ <strong style="color:#e7c873">Nuevo atelier</strong> ·
           Funciona sin clave en modo demo, o conecta OpenAI para versos con <em>gpt-4o-mini</em>.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")  # spacer


# -----------------------------------------------------------------------------
# Estado de sesión
# -----------------------------------------------------------------------------
for k, v in {
    "doc": None,
    "chunks": [],
    "topic": "",
    "tone": "Contemplativo",
    "form": "Verso libre",
    "result": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# -----------------------------------------------------------------------------
# HERO
# -----------------------------------------------------------------------------
c1, c2 = st.columns([1.05, 0.95], gap="large")
with c1:
    st.markdown(
        f'<span class="badge moss">📖 RAG poético · Lectura que se vuelve canto</span>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <h1 style="font-size:clamp(2.4rem,5.2vw,3.9rem);line-height:1.04;margin:14px 0 10px">
            Tus documentos,<br>convertidos en
            <span style="color:{PALETTE['clay']};position:relative">
                poesía
                <svg viewBox="0 0 220 14" style="position:absolute;left:0;bottom:-4px;width:100%" fill="none">
                  <path d="M3 10C60 3 140 3 217 9" stroke="{PALETTE['gold']}" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
                </svg>
            </span> viva.
        </h1>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='font-size:16.5px;line-height:1.6'>Sube un PDF, elige un tono y una forma literaria. "
        "El atelier lee los fragmentos más relevantes y compone un poema fiel a tus ideas — claro, "
        "estético y listo para compartir.</p>",
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    a.link_button("Empezar en el taller", "#taller", use_container_width=True)
    b.link_button("Ver cómo funciona", "#como-funciona", use_container_width=True)
    st.markdown(
        "<small>✓ Sin registro &nbsp; · &nbsp; ✓ Tu clave nunca se guarda &nbsp; · &nbsp; ✓ Copia y descarga tus versos</small>",
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="card" style="position:relative">
            <div style="position:absolute;top:-12px;right:24px;background:{PALETTE['gold']};color:white;
                        padding:6px 14px;border-radius:999px;font-size:11px;font-weight:800;letter-spacing:.14em;
                        text-transform:uppercase;box-shadow:0 8px 20px rgba(0,0,0,0.15);transform:rotate(3deg)">
                ✦ Edición del día
            </div>
            <p class="badge clay" style="margin:0 0 6px 0">POEMA · Verso libre</p>
            <h3 style="font-size:26px;margin:6px 0 12px">“Donde el papel respira”</h3>
            <div class="poem">
                Leí tu documento al caer la tarde,<br>
                y cada idea encendió una lámpara;<br>
                lo que era informe se hizo jardín,<br>
                lo que era dato, golondrina.
            </div>
            <div style="margin-top:14px;display:flex;gap:6px;flex-wrap:wrap">
                <span class="badge moss">4 fragmentos leídos</span>
                <span class="badge clay">Tono contemplativo</span>
                <span class="badge gold">RAG fiel al texto</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")


# -----------------------------------------------------------------------------
# Barra de progreso
# -----------------------------------------------------------------------------
steps_done = {
    "Conexión":  (not use_api) or bool(API_KEY),
    "Documento": st.session_state.doc is not None,
    "Poema":     st.session_state.result is not None,
}
done = sum(steps_done.values())
progress = done / 3

st.markdown(
    f"""
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap">
        <div style="font-weight:700">
            Tu progreso en el taller
            <div style="font-size:12.5px;color:{PALETTE['muted']};font-weight:500">
                Completa los tres pasos para estrenar tu poema.
            </div>
        </div>
        <div style="flex:1;min-width:200px">
            <div class="progress-track"><div class="progress-bar" style="width:{int(progress*100)}%"></div></div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
            {''.join(f'<span class="step {"done" if v else ""}">{("✓" if v else str(i+1))} · {name}</span>'
                     for i, (name, v) in enumerate(steps_done.items()))}
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")


# -----------------------------------------------------------------------------
# TALLER · 3 pasos
# -----------------------------------------------------------------------------
st.markdown('<a id="taller"></a>', unsafe_allow_html=True)
st.markdown('<span class="badge clay">El taller</span>', unsafe_allow_html=True)
st.markdown("## Tres pasos, cero complicaciones")

left, right = st.columns([1.7, 1], gap="large")

# -------------- COLUMNA PRINCIPAL --------------
with left:
    # ---- PASO 1: MODO / CONEXIÓN ----
    st.markdown(
        f"""<div class="card" style="margin-bottom:22px">
            <div style="display:flex;gap:14px;align-items:flex-start">
              <span style="background:{PALETTE['ink']};color:white;width:46px;height:46px;border-radius:14px;
                           display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:18px">1</span>
              <div style="flex:1">
                <h3 style="margin:0 0 4px;font-size:21px">Conecta tu inspiración</h3>
                <p style="margin:0;color:{PALETTE['ink_soft']};font-size:14px">
                    Puedes crear al instante <strong>sin clave</strong>, o pegar tu API key de OpenAI
                    para versos más ricos con <em>gpt-4o-mini</em>.
                </p>
                <p style="margin-top:10px"><span class="badge {'gold' if not use_api else 'moss'}">
                    Modo actual: {"Atelier (demo)" if not use_api else "OpenAI"}
                </span></p>
              </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- PASO 2: SUBIR PDF ----
    st.markdown(
        f"""<div class="card" style="margin-bottom:22px">
            <div style="display:flex;gap:14px;align-items:flex-start">
              <span style="background:{PALETTE['clay']};color:white;width:46px;height:46px;border-radius:14px;
                           display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:18px">2</span>
              <div>
                <h3 style="margin:0 0 4px;font-size:21px">Sube tu documento</h3>
                <p style="margin:0;color:{PALETTE['ink_soft']};font-size:14px">
                    Hasta 15 MB · texto seleccionable. Lo leeremos y fragmentaremos al instante.
                </p>
              </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="file-drop">', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Suelta tu PDF aquí o haz clic para elegirlo",
        type=["pdf"],
        accept_multiple_files=False,
        label_visibility="visible",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded is not None and st.session_state.doc is None:
        with st.spinner("Leyendo tu PDF…"):
            try:
                with pdfplumber.open(uploaded) as pdf:
                    pages = []
                    for p in pdf.pages:
                        t = p.extract_text() or ""
                        pages.append(t)
                full_text = "\n".join(pages).strip()
                if len(full_text) < 40:
                    st.error("No se pudo extraer texto. Asegúrate de que el PDF no esté escaneado.")
                else:
                    chunks = split_text(full_text, 600, 50)
                    st.session_state.doc = {
                        "name": uploaded.name,
                        "pages": len(pages),
                        "chars": len(full_text),
                        "chunks": len(chunks),
                        "excerpt": full_text[:600],
                    }
                    st.session_state.chunks = chunks
                    st.session_state.result = None
                    st.success("✓ Documento listo para poetizar")
            except Exception as e:
                st.error(f"Error procesando el PDF: {e}")

    if st.session_state.doc is not None:
        d = st.session_state.doc
        st.markdown(
            f"""<div class="card card-tinted" style="margin-top:12px">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap">
                    <div style="display:flex;gap:12px;align-items:center">
                        <span style="background:{PALETTE['clay_soft']};color:{PALETTE['clay_deep']};
                                     width:46px;height:46px;border-radius:14px;display:inline-flex;
                                     align-items:center;justify-content:center;font-size:22px">📄</span>
                        <div>
                            <div style="font-weight:800;font-size:15px">{d['name']}</div>
                            <div style="font-size:12.5px;color:{PALETTE['moss_deep']};font-weight:600">
                                ✓ Listo para poetizar
                            </div>
                        </div>
                    </div>
                </div>
                <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px">
                    <div style="background:{PALETTE['card']};border:1px solid {PALETTE['line']};border-radius:14px;padding:14px;text-align:center">
                        <div style="font-family:'Fraunces',serif;font-size:22px;font-weight:700">{d['pages']}</div>
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{PALETTE['muted']}">Páginas</div>
                    </div>
                    <div style="background:{PALETTE['card']};border:1px solid {PALETTE['line']};border-radius:14px;padding:14px;text-align:center">
                        <div style="font-family:'Fraunces',serif;font-size:22px;font-weight:700">{d['chars']:,}</div>
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{PALETTE['muted']}">Caracteres</div>
                    </div>
                    <div style="background:{PALETTE['card']};border:1px solid {PALETTE['line']};border-radius:14px;padding:14px;text-align:center">
                        <div style="font-family:'Fraunces',serif;font-size:22px;font-weight:700">{d['chunks']}</div>
                        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:{PALETTE['muted']}">Fragmentos</div>
                    </div>
                </div>
                <details style="margin-top:14px">
                    <summary style="cursor:pointer;font-weight:600">Vista previa del texto</summary>
                    <div style="margin-top:8px;font-size:13px;color:{PALETTE['ink_soft']};line-height:1.6">
                        {d['excerpt']}
                    </div>
                </details>
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Cambiar de archivo", use_container_width=False):
            st.session_state.doc = None
            st.session_state.chunks = []
            st.session_state.result = None
            st.rerun()

    # ---- PASO 3: PEDIR POEMA ----
    st.markdown(
        f"""<div class="card" style="margin-top:22px">
            <div style="display:flex;gap:14px;align-items:flex-start">
              <span style="background:{PALETTE['moss']};color:white;width:46px;height:46px;border-radius:14px;
                           display:inline-flex;align-items:center;justify-content:center;font-weight:800;font-size:18px">3</span>
              <div>
                <h3 style="margin:0 0 4px;font-size:21px">Pide tu poema</h3>
                <p style="margin:0;color:{PALETTE['ink_soft']};font-size:14px">
                    Describe el tema, elige el tono y la forma. El atelier busca los fragmentos más afines.
                </p>
              </div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.session_state.topic = st.text_area(
        "Tema o enfoque del poema",
        value=st.session_state.topic,
        placeholder="Ejemplo: un poema melancólico que resuma las conclusiones clave del documento…",
        height=100,
    )

    tones = ["Contemplativo", "Melancólico", "Alegre", "Romántico", "Épico", "Oscuro", "Esperanzado"]
    forms = ["Verso libre", "Soneto", "Haiku", "Décima", "Romance", "Oda"]
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        try:
            idx_t = tones.index(st.session_state.tone)
        except ValueError:
            idx_t = 0
        st.session_state.tone = st.selectbox("Tono", tones, index=idx_t,
                                              help=TONE_HINT.get(st.session_state.tone, ""))
    with tcol2:
        try:
            idx_f = forms.index(st.session_state.form)
        except ValueError:
            idx_f = 0
        st.session_state.form = st.selectbox("Forma", forms, index=idx_f)

    gen = st.button(
        "✨ Generar poema",
        type="primary",
        use_container_width=True,
        disabled=(st.session_state.doc is None),
    )

    if gen:
        if st.session_state.doc is None:
            st.warning("Sube un PDF para activar la composición.")
        elif len(st.session_state.topic.strip()) < 4:
            st.warning("Cuéntanos el tema en una frase (mín. 4 caracteres).")
        else:
            with st.spinner("El trovador está componiendo…"):
                try:
                    rel = retrieve(st.session_state.topic, st.session_state.chunks, k=4)
                    context = "\n\n".join(f"[Fragmento {i+1}]\n{c}" for i, c in enumerate(rel))[:6000]
                    content: str
                    model = "atelier-demo"
                    if use_api and API_KEY:
                        content = call_openai(API_KEY, build_prompt(
                            context, st.session_state.topic.strip(),
                            st.session_state.tone, st.session_state.form))
                        model = "gpt-4o-mini"
                    else:
                        content = generate_demo_poem(
                            rel, st.session_state.topic.strip(),
                            st.session_state.tone, st.session_state.form,
                            st.session_state.doc["name"])
                    st.session_state.result = {
                        "id": _secrets.token_hex(6),
                        "content": content,
                        "topic": st.session_state.topic.strip(),
                        "tone": st.session_state.tone,
                        "form": st.session_state.form,
                        "model": model,
                        "document": st.session_state.doc["name"],
                        "fragments": len(rel),
                        "ts": datetime.now().isoformat(timespec="seconds"),
                    }
                    add_poem(st.session_state.result)
                except Exception as e:
                    st.error(str(e))

# -------------- COLUMNA LATERAL --------------
with right:
    st.markdown(
        f"""<div class="card" style="background:{PALETTE['moss_deep']};color:#f3ecdd">
            <span class="badge" style="background:rgba(255,255,255,0.1);color:white">🔎 CÓMO LEE EL ATELIER</span>
            <ol style="margin-top:14px;padding-left:18px;font-size:13.5px;line-height:1.7">
              <li><strong style="color:white">Fragmenta</strong> tu PDF en porciones de ~600 caracteres.</li>
              <li><strong style="color:white">Recupera</strong> los 4 fragmentos más afines a tu tema.</li>
              <li><strong style="color:white">Compone</strong> un poema fiel, con tu tono y forma.</li>
            </ol>
            <div class="stamp" style="margin-top:14px;color:#e7dcc8;font-size:12.5px">
                A esto se le llama <strong style="color:white">RAG</strong>: el poema nace de tu texto, no de la nada.
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""<div class="card" style="margin-top:14px">
            <h4 style="margin:0 0 10px;font-size:17px">Consejos de trovador</h4>
            <ul style="font-size:13.5px;line-height:1.6;padding-left:18px">
              <li>Sé específico: <em>"las conclusiones sobre el clima"</em> vence a <em>"algo bonito"</em>.</li>
              <li>Prueba el mismo tema con dos tonos distintos.</li>
              <li>El haiku ama lo breve; el romance, las historias.</li>
            </ul>
            <div style="margin-top:12px;background:{PALETTE['gold_soft']};padding:12px;border-radius:14px;font-size:12.5px;line-height:1.5;color:#6b530a">
                Cada poema se guarda automáticamente en tu biblioteca.
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------------
# RESULTADO
# -----------------------------------------------------------------------------
if st.session_state.result:
    r = st.session_state.result
    st.write("")
    st.markdown(
        f"""<div class="card" style="margin-top:12px">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;
                        border-bottom:1px solid {PALETTE['line']};padding-bottom:14px">
                <span class="badge moss">🪶 POEMA RESULTANTE</span>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                    <span class="badge">{r['form']}</span>
                    <span class="badge">{r['tone']}</span>
                    <span class="badge {'moss' if r['model']=='gpt-4o-mini' else 'gold'}">
                        GPT-4o-mini if r['model']=='gpt-4o-mini' else Atelier demo
                    </span>
                </div>
            </div>
            <div style="font-size:12px;color:{PALETTE['muted']};margin-top:14px">
                Inspirado en <strong>{r['document']}</strong> · {r['fragments']} fragmentos
            </div>
            <div style="font-size:13px;font-style:italic;color:{PALETTE['ink_soft']}">Tema: "{r['topic']}"</div>
            <div class="poem" style="margin-top:18px">{r['content'].replace(chr(10), '<br>')}</div>
        </div>""",
        unsafe_allow_html=True,
    )
    cA, cB, cC = st.columns([1, 1, 1])
    with cA:
        st.download_button(
            "⬇ Descargar .txt",
            data=r["content"] + f"\n\n— Tema: {r['topic']}\n— Fuente: {r['document']}\n— Tono: {r['tone']} · Forma: {r['form']}",
            file_name=f"poema-{r['id']}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with cB:
        st.code(r["content"], language=None)
    with cC:
        if st.button("🗑 Nueva composición", use_container_width=True):
            st.session_state.result = None
            st.rerun()


# -----------------------------------------------------------------------------
# BIBLIOTECA
# -----------------------------------------------------------------------------
st.write("")
st.markdown("---")
st.markdown(
    f'<span class="badge clay">📚 Biblioteca</span>',
    unsafe_allow_html=True,
)
st.markdown("## Tus versos guardados")
st.caption("Todo lo que compongas queda archivado aquí.")

items = _load_library()
if not items:
    st.info("Aún no hay poemas. Cuando generes uno, vivirá aquí con su ficha de tono, forma y documento de origen.")
else:
    cols = st.columns(3, gap="medium")
    for i, p in enumerate(items[:30]):
        with cols[i % 3]:
            preview = p["content"][:240].replace("\n", " ")
            st.markdown(
                f"""<div class="card" style="margin-bottom:14px">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span class="badge {'moss' if p.get('model')=='gpt-4o-mini' else 'gold'}">
                            {p['form']} · {p['tone']}
                        </span>
                        <small style="color:{PALETTE['muted']}">{p['ts'][:10]}</small>
                    </div>
                    <h4 style="margin:10px 0 6px;font-size:16px">"{p['topic']}"</h4>
                    <div style="font-family:'Fraunces',serif;font-size:13.5px;line-height:1.5;color:{PALETTE['ink_soft']};
                                display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden">
                        {preview}
                    </div>
                    <div style="border-top:1px solid {PALETTE['line']};padding-top:8px;margin-top:10px;display:flex;
                                justify-content:space-between;align-items:center;font-size:12px;color:{PALETTE['muted']}">
                        <span>{p['document']}</span>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )
            with st.expander("Leer entero · acciones"):
                st.code(p["content"], language=None)
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "⬇ .txt",
                        data=p["content"],
                        file_name=f"poema-{p['id']}.txt",
                        mime="text/plain",
                        key=f"dl_{p['id']}",
                        use_container_width=True,
                    )
                with col2:
                    if st.button("🗑 Eliminar", key=f"del_{p['id']}", use_container_width=True):
                        delete_poem(p["id"])
                        st.rerun()


# -----------------------------------------------------------------------------
# CÓMO FUNCIONA
# -----------------------------------------------------------------------------
st.write("")
st.markdown('<a id="como-funciona"></a>', unsafe_allow_html=True)
st.markdown(
    f'<span class="badge clay">Comprender sin tecnicismos</span>',
    unsafe_allow_html=True,
)
st.markdown("## ¿Qué es esto del RAG?")
st.markdown(
    "Piensa en un investigador que primero <strong>lee y subraya</strong> tu PDF, "
    "luego <strong>elige las páginas exactas</strong> que hablan de tu tema "
    "y finalmente <strong>se las dicta al poeta</strong>. El poema nunca inventa desde cero: canta desde tu texto.",
    unsafe_allow_html=True,
)

cA, cB, cC = st.columns(3, gap="medium")
for col, (icon, title, body) in zip(
    [cA, cB, cC],
    [
        ("📖", "1 · Lee con calma",      "Extraemos el texto del PDF y lo cortamos en fragmentos de lectura cómoda, como fichas de biblioteca."),
        ("🔎", "2 · Subraya lo esencial", "Comparamos tu tema con cada ficha y rescatamos las 4 que más resuenan. Sin humo, con criterio."),
        ("🪶", "3 · Canta tu tema",       "El poeta —demo o GPT-4o-mini— compone con tu tono y forma, mirando siempre a los fragmentos."),
    ],
):
    with col:
        st.markdown(
            f"""<div class="card" style="height:100%">
                <span class="badge ink" style="font-size:18px">{icon}</span>
                <h4 style="margin:10px 0 6px">{title}</h4>
                <p style="font-size:13.5px;color:{PALETTE['ink_soft']}">{body}</p>
            </div>""",
            unsafe_allow_html=True,
        )


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.write("")
st.markdown("---")
st.markdown(
    f"<small style='color:{PALETTE['muted']};display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px'>"
    f"<span>🪶 Trovador · Atelier de poesía</span>"
    f"<span>RAG fiel al texto · Tu clave nunca se guarda</span></small>",
    unsafe_allow_html=True,
)
