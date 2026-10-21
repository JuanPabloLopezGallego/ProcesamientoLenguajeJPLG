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
    page_title="PDF Bard - Poemas RAG",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. Estilos Personalizados (CSS)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Fondo global y tipografía */
    .stApp {
        background: linear-gradient(135deg, #0f0c20 0%, #1a103c 50%, #0d0818 100%);
        color: #e0e0e0;
    }
    
    /* Títulos estilizados */
    h1, h2, h3 {
        color: #dcb3ff !important;
        font-family: 'Georgia', serif;
    }
    
    /* Cajas métricas e información */
    .metric-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(220, 179, 255, 0.2);
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        backdrop-filter: blur(10px);
    }
    
    /* Resultado del Poema */
    .poem-box {
        background: rgba(43, 20, 75, 0.6);
        border-left: 4px solid #b366ff;
        border-radius: 8px;
        padding: 25px;
        font-family: 'Georgia', serif;
        font-style: italic;
        line-height: 1.8;
        font-size: 1.15rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        color: #f3e8ff;
    }

    /* Personalización del área de texto */
    .stTextArea textarea {
        background-color: rgba(20, 10, 35, 0.8) !important;
        color: #ffffff !important;
        border: 1px solid #7c3aed !important;
        border-radius: 10px !important;
    }

    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. Barra Lateral (Sidebar)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/open-book.png", width=100)
    st.title("Poeta RAG 📜")
    st.markdown("Transforma el contenido conceptual de tus documentos PDF en composiciones poéticas personalizadas.")
    st.markdown("---")
    
    # Credenciales de API
    ke = st.text_input('Clave de API de OpenAI', type="password", help="Tu API key no se guardará de forma permanente.")
    if ke:
        os.environ['OPENAI_API_KEY'] = ke
    else:
        st.warning("⚠️ Ingresa tu clave de OpenAI para activar la generación.")

    # Imagen decorativa opcional
    try:
        image = Image.open('Chat_pdf.png')
        st.image(image, use_column_width=True)
    except Exception:
        pass

    st.markdown("---")
    st.caption(f"Python v{platform.python_version()} | RAG Engine v2.0")

# -----------------------------------------------------------------------------
# 4. Encabezado Principal
# -----------------------------------------------------------------------------
st.title("📜 Trovador Digital: De PDF a Poema")
st.write("Sube un documento y especifica el tema o enfoque para convertir la información en un poema único.")

# Cargador de Archivos
pdf = st.file_uploader("Sube tu archivo PDF aquí", type="pdf")

# -----------------------------------------------------------------------------
# 5. Procesamiento del PDF y Generación del Poema
# -----------------------------------------------------------------------------
if pdf is not None and ke:
    try:
        with st.spinner("Procesando y analizando el contenido del PDF..."):
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

        # Mostrar Estadísticas con estilo
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{len(text):,}</h3>
                <p>Caracteres Extraídos</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>{len(chunks)}</h3>
                <p>Fragmentos Indexados</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Interfaz del Prompt para Poemas
        st.subheader("🖋️ Configura tu Solicitud Poética")
        user_topic = st.text_area(
            "Indica el tema, tono o sección sobre la cual deseas generar el poema:",
            placeholder="Ejemplo: Escribe un poema melancólico que resuma las conclusiones clave del documento..."
        )

        generate_btn = st.button("✨ Generar Poema", type="primary", use_container_width=True)

        if generate_btn and user_topic:
            with st.spinner("El trovador digital está componiendo los versos..."):
                # Búsqueda de fragmentos relevantes
                docs = knowledge_base.similarity_search(user_topic, k=4)

                # Prompt estructurado específicamente para generación de poemas
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

                # Cadena QA personalizada con el prompt de poema
                chain = load_qa_chain(llm, chain_type="stuff", prompt=PROMPT)
                response = chain.run(input_documents=docs, question=user_topic)

                # Mostrar resultado con caja destacada
                st.markdown("### 🎭 Poema Resultante")
                st.markdown(f'<div class="poem-box">{response.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

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
