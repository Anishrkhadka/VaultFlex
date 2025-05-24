import streamlit as st
from src.__version__ import __version__
from src.ui.data_ingest_ui import run_ingestion_ui

from src.utils.status import get_backend_status
from src.utils.ollama_manager import run_ollama_model
from src.config import LLM_MODEL
import streamlit as st


st.set_page_config(page_title="RAG Chatbot", layout="centered")

# Initialise session state
if "view" not in st.session_state:
    st.session_state["view"] = "Welcome"

st.markdown("""
    <style>
        .stButton > button {
            border-radius: 8px;
            padding: 0.6em 1em;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
        }
        .stButton > button:hover {
            background-color: #f0f2f6;
            border: 1px solid #ccc;
            transform: scale(1.02);
        }
    </style>
""", unsafe_allow_html=True)


def status_pill(label, icon, bg, fg, subtext=""):
    st.markdown(
        f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background-color: {bg};
            color: {fg};
            border-radius: 10px;
            padding: 0.75em 1em;
            font-weight: 600;
            font-size: 0.9em;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            min-height: 90px;
        ">
            <div style="font-size: 1.3em; margin-bottom: 0.25em;">{icon}</div>
            <div>{label}</div>
            <div style='font-size: 0.75em; font-weight: normal;'>{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def show_backend_status():
    status = get_backend_status()

    col1, col2, col3 = st.columns(3)

    # --- Model Pill ---
    with col1:
        status_pill("Model", "🧠", "#fce4ec", "#c2185b", subtext=LLM_MODEL)

    # --- Ollama Pill ---
    with col2:
        if status["ollama"]:
            status_pill("Ollama", "✅", "#4caf50", "white", subtext="Running")
        else:
            status_pill("Ollama", "🔴", "#f44336", "white", subtext="Ollama Down")

    # --- Neo4j Pill ---
    with col3:
        if status["neo4j"]:
            status_pill("Neo4j", "📘", "#2196f3", "white", subtext="Connected")
        else:
            status_pill("Neo4j", "❌", "#f44336", "white", subtext="Disconnected")


# --- Views ---
if st.session_state["view"] == "Welcome":
    st.markdown("## 🤖 Lightweight Chatbot")
    st.markdown("### with Memory and Retrieval-Augmentation")
    show_backend_status()

    st.markdown("---")
    st.markdown("### 👋 Welcome to your local-first AI workspace")

    st.markdown("""
- **Ingest and manage documents** into scoped datasets  
- **Generate vector indexes** and build knowledge graphs  
- **Chat with LLMs** over your own data using RAG  
""")

    st.markdown("### What would you like to do?")
    st.write("")  # spacing
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Ingest Data", use_container_width=True):
            st.session_state["view"] = "Ingest"
    with col2:
        if st.button("💬 Open Chatbot", use_container_width=True):
            st.session_state["view"] = "Chat"

elif st.session_state["view"] == "Ingest":
    if st.button("🔙 Back to Welcome", use_container_width=True):
        st.session_state["view"] = "Welcome"
    show_backend_status()
    run_ingestion_ui()

elif st.session_state["view"] == "Chat":
    if st.button("🔙 Back to Welcome", use_container_width=True):
        st.session_state["view"] = "Welcome"
    show_backend_status()
    from src.ui import main  

# --- Footer ---
st.markdown(
    """
    <hr style='margin-top: 3em;'>
    <div style='text-align: center; color: gray; font-size: 0.85em;'>
        Version: 0.1.0 &nbsp; | &nbsp; Made with ❤️ for local-first AI
    </div>
    """,
    unsafe_allow_html=True
)
