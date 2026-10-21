import os
import platform
import traceback
import streamlit as st
from PIL import Image
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains.question_answering import load_qa_chain

# -----------------------------------------------------------------------------
# 1. Configuración de la Página
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Trovador Digital · De PDF a Poema",
    page_icon="🖋️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Estilos Personalizados (CSS) — Dark Academia
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400&family=Inter:wght@300;400;500;600&display=swap');

    :root {
        --bg:            #0d0c10;
        --surface:       #16141a;
        --surface-hover: #1e1b24;
        --ink:           #e6e1d6; /* Blanco cálido */
        --ink-muted:     #8b858f;
        --border:        #2a2633;
        --accent:        #d4a373; /* Dorado viejo */
        --accent-glow:   rgba(212, 163, 115, 0.15);
    }

    /* ═══ BASE ═══ */
    html, body, [class*="css"], .stApp, button, input, textarea, select {
        font-family: 'Inter', sans-serif !important;
        color: var(--ink) !important;
    }

    h1, h2, h3, h4, h5 {
        font-family: 'Cormorant Garamond', serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
        color: var(--ink) !important;
    }

    /* ═══ FONDO OSCURO ═══ */
    .stApp {
        background-color: var(--bg) !important;
        background-image: 
            radial-gradient(circle at 50% 0%, rgba(212, 163, 115, 0.05), transparent 50%),
            radial-gradient(circle at 10% 90%, rgba(212, 163, 115, 0.03), transparent 40%);
        background-attachment: fixed;
    }

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header[data-testid="stHeader"] { background: transparent; }

    .block-container {
        padding-top: 3rem !important;
        padding-bottom: 4rem !important;
        max-width: 1100px !important;
    }

    /* ═══ SIDEBAR ═══ */
    [data-testid="stSidebar"] {
        background: var(--surface) !important;
        border-right: 1px solid var(--border) !important;
    }
    [data-testid="stSidebar"] * { color: var(--ink) !important; }

    .sb-brand {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
    .sb-brand-icon {
        font-size: 2.5rem;
        display: block;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 0 10px rgba(212, 163, 115, 0.3));
    }
    .sb-brand-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: var(--ink);
        margin: 0;
        line-height: 1.1;
    }
    .sb-brand-sub {
        font-size: 0.72rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--accent);
        margin-top: 0.35rem;
        font-weight: 500;
    }

    /* ═══ INPUTS ═══ */
    .stTextInput label,
    .stTextArea label,
    .stTextInput [data-testid="stWidgetLabel"] p,
    .stTextArea [data-testid="stWidgetLabel"] p {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.78rem !important;
        letter-spacing: 0.05em !important;
        text-transform: uppercase !important;
        color: var(--ink-muted) !important;
        font-weight: 600 !important;
    }
    
    .stTextInput div[data-baseweb="input"] > div,
    .stTextInput input,
    .stTextArea textarea {
        background-color: var(--bg) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--ink) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.92rem !important;
        padding: 0.7rem 1rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput div[data-baseweb="input"] > div:focus-within,
    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-glow) !important;
        outline: none !important;
    }

    /* ═══ FILE UPLOADER ═══ */
    [data-testid="stFileUploader"] {
        background-color: var(--surface);
        border: 1px dashed var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        transition: border-color 0.2s ease;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: var(--accent);
    }
    [data-testid="stFileUploader"] section {
        padding: 0 !important;
    }
    [data-testid="stFileUploader"] button {
        background-color: var(--surface-hover) !important;
        border: 1px solid var(--border) !important;
        color: var(--ink) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stFileUploader"] button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }

    /* ═══ BOTÓN PRINCIPAL ═══ */
    .stButton > button {
        width: 100%;
        background-color: var(--accent) !important;
        color: var(--bg) !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.85rem 1.4rem !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 15px rgba(212, 163, 115, 0.2) !important;
    }
    .stButton > button p { color: var(--bg) !important; font-weight: 600 !important; }
    .stButton > button:hover {
        background-color: #e6b88a !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(212, 163, 115, 0.35) !important;
    }

    /* ═══ HERO ═══ */
    .hero {
        text-align: center;
        padding: 1rem 0 2.5rem 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 2.5rem;
    }
    .hero-kicker {
        font-size: 0.75rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--accent);
        font-weight: 600;
        margin-bottom: 1rem;
        display: block;
    }
    .hero h1 {
        font-size: 4rem !important;
        line-height: 1.05 !important;
        margin: 0 0 1rem 0 !important;
        font-weight: 700 !important;
        color: var(--ink) !important;
        text-shadow: 0 0 30px rgba(230, 225, 214, 0.1);
    }
    .hero h1 em {
        font-style: italic;
        font-weight: 400;
        color: var(--accent);
        text-shadow: 0 0 40px var(--accent-glow);
    }
    .hero p {
        font-size: 1.1rem;
        color: var(--ink-muted);
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.6;
    }

    /* ═══ TARJETAS MÉTRICAS ═══ */
    .metric-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;
        margin-bottom: 2.5rem;
    }
    .metric-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 2px solid var(--accent);
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
    }
    .metric-value {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.8rem;
        font-weight: 700;
        color: var(--accent);
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 0.75rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        color: var(--ink-muted);
        font-weight: 600;
    }

    /* ═══ CAJA DEL POEMA ═══ */
    .poem-container {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 4px solid var(--accent);
        border-radius: 8px;
        padding: 3.5rem 3rem;
        margin-top: 2.5rem;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), inset 0 0 20px rgba(212, 163, 115, 0.03);
        position: relative;
    }
    .poem-header {
        text-align: center;
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 2rem;
    }
    .poem-text {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.6rem;
        line-height: 2;
        color: var(--ink);
        text-align: center;
        font-style: italic;
        text-shadow: 0 0 20px rgba(230, 225, 214, 0.05);
    }
    
    /* ═══ ALERTAS ═══ */
    [data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid var(--border) !important;
        background-color: var(--surface) !important;
        color: var(--ink) !important;
    }
    [data-testid="stAlert"] svg { fill: var(--accent) !important; }
    
    /* ═══ SEPARADORES ═══ */
    hr {
        border-color: var(--border) !important;
        margin: 2rem 0 !important;
    }

    /* ═══ CAPTION ═══ */
    .stCaption, [data-testid="stCaptionContainer"] {
        font-family: 'Inter', sans-serif !important;
        color: var(--ink-muted) !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.02em;
    }

    /* ═══ RESPONSIVE ═══ */
    @media (max-width: 768px) {
        .hero h1 { font-size: 2.8rem !important; }
        .poem-container { padding: 2rem 1.5rem; }
        .poem-text { font-size: 1.3rem; }
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Barra Lateral (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div class="sb-brand">
            <span class="sb-brand-icon">🖋️</span>
            <h1 class="sb-brand-title">Trovador<br>Digital</h1>
            <p class="sb-brand-sub">RAG Engine v2.0</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(
        "Transforma el contenido conceptual de tus documentos PDF "
        "en composiciones poéticas personalizadas."
    )
    
    st.markdown("---")
    
    # Credenciales de API
    ke = st.text_input(
        'Clave de API de OpenAI', 
        type="password", 
        help="Tu API key no se guardará de forma permanente."
    )
    if ke:
        os.environ['OPENAI_API_KEY'] = ke
    else:
        st.warning("⚠️ Ingresa tu clave para activar la generación.")

    st.markdown("---")
    st.caption(f"Python v{platform.python_version()} · LangChain · FAISS")

# -----------------------------------------------------------------------------
# 4. Encabezado Principal
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="hero">
        <span class="hero-kicker">Inteligencia Artificial + Poesía</span>
        <h1>De PDF a <em>Poema</em></h1>
        <p>Sube un documento y especifica el tema o enfoque para convertir la información en una composición poética única.</p>
    </div>
""", unsafe_allow_html=True)

# Cargador de Archivos
pdf = st.file_uploader("Sube tu archivo PDF aquí", type="pdf")

# -----------------------------------------------------------------------------
# 5. Procesamiento del PDF y Generación del Poema
# -----------------------------------------------------------------------------
if pdf is not None and ke:
    try:
        with st.spinner("Analizando el contenido del documento..."):
            # Extraer texto del PDF
            pdf_reader = PdfReader(pdf)
            text = ""
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
            
            # Fragmentación del texto
            text_splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=600,
                chunk_overlap=50,
                length_function=len
            )
            chunks = text_splitter.split_text(text)
            
            # Creación del vectorstore con Embeddings
            embeddings = OpenAIEmbeddings()
            knowledge_base = FAISS.from_texts(chunks, embeddings)

        # Mostrar Estadísticas
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-value">{len(text):,}</div>
                <div class="metric-label">Caracteres Extraídos</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{len(chunks)}</div>
                <div class="metric-label">Fragmentos Indexados</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Interfaz del Prompt
        st.markdown("### 🖋️ Configura tu Solicitud")
        user_topic = st.text_area(
            "Indica el tema, tono o sección sobre la cual deseas generar el poema:",
            placeholder="Ejemplo: Escribe un poema melancólico que resuma las conclusiones clave del documento...",
            height=120
        )

        generate_btn = st.button("✨ Componer Poema", type="primary", use_container_width=True)

        if generate_btn and user_topic:
            with st.spinner("El trovador digital está componiendo los versos..."):
                # Búsqueda de fragmentos relevantes
                docs = knowledge_base.similarity_search(user_topic, k=4)

                # Prompt estructurado para poemas
                poem_template = """
                Eres un poeta talentoso y lírico. Utiliza únicamente la información extraída del siguiente texto 
                para crear un poema estilizado, emotivo y creativo.

                Información del documento:
                {context}

                Instrucciones del usuario sobre el poema:
                {question}

                Poema:
                """
                
                PROMPT = PromptTemplate(
                    template=poem_template, 
                    input_variables=["context", "question"]
                )

                # Modelo LLM
                llm = ChatOpenAI(temperature=0.7, model_name="gpt-4o-mini")

                # Cadena QA personalizada
                chain = load_qa_chain(llm, chain_type="stuff", prompt=PROMPT)
                response = chain.run(input_documents=docs, question=user_topic)

                # Mostrar resultado
                response_html = response.replace('\n', '<br>')
                st.markdown(f"""
                    <div class="poem-container">
                        <div class="poem-header">Composición Generada</div>
                        <div class="poem-text">
                            {response_html}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        elif generate_btn and not user_topic:
            st.warning("Escribe una instrucción o tema para guiar la poesía.")

    except Exception as e:
        st.error(f"Error al procesar el archivo o generar el poema: {str(e)}")
        with st.expander("Ver detalles del error"):
            st.code(traceback.format_exc())

elif pdf is not None and not ke:
    st.info("👈 Por favor, ingresa tu clave API de OpenAI en el panel lateral.")
else:
    st.info("📂 Carga un archivo PDF para comenzar la experiencia poética.")
