"""
app.py

Main entry point for VaultFlex — a Streamlit app for uploading documents,
building knowledge bases, and querying them using Graph-RAG + FAISS + LLMs.

Views:
- Welcome: Logo, model/KB selection, and ask a question form
- Ingest: Upload documents to create or expand a knowledge base
- Chat: Query your selected knowledge base using RAG + graph context

Author: Anish khadka
"""

import streamlit as st
from PIL import Image
import os

from src.__version__ import __version__
from src.frontent.kb_ingest_ui import run_ingestion_ui
from src.frontent.chat_ui import run_chat_ui
from src.utils.service_status import get_backend_status
from src.config import LLM_MODEL, GOLD_DIR


# --- App Configuration ---
st.set_page_config(page_title="Chatbot with GraphRAG and RAG", layout="centered")

# --- Session State Init ---
if "view" not in st.session_state:
    st.session_state["view"] = "Welcome"
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# --- Button Styling (custom hover + rounded) ---
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


# --- Helper: Render footer status for LLM + Neo4j ---
def render_backend_status_footer():
    status = get_backend_status()

    st.markdown("<hr style='margin-top: 2em;'>", unsafe_allow_html=True)
    st.markdown("<div style='display: flex; justify-content: center; flex-wrap: wrap;'>", unsafe_allow_html=True)

    def pill(text, icon, bg):
        return f"""
            <div style="
                display: inline-flex;
                align-items: center;
                background-color: {bg};
                color: white;
                padding: 6px 14px;
                border-radius: 16px;
                font-size: 0.75em;
                font-weight: 500;
                margin: 4px;
            ">
                {icon}&nbsp;{text}
            </div>
        """

    # Service indicators
    ollama = pill("Ollama: Running" if status["ollama"] else "Ollama: Down", "✅" if status["ollama"] else "❌", "#2e7d32" if status["ollama"] else "#c62828")
    neo4j = pill("Neo4j: Connected" if status["neo4j"] else "Neo4j: Disconnected", "📘" if status["neo4j"] else "❌", "#1565c0" if status["neo4j"] else "#c62828")

    st.markdown(ollama + neo4j, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 0.2em;'>
            Version: {__version__} &nbsp; | &nbsp; Made with ❤️ VaultFlex
        </div>
        """,
        unsafe_allow_html=True
    )


# WELCOME VIEW

if st.session_state["view"] == "Welcome":
    # Upload KB Button
    if st.button("➕ Add Knowledge Base", key="add_kb_button"):
        st.session_state["view"] = "Ingest"
        st.rerun()

    # Centre-aligned Logo
    logo = Image.open("doc/images/vaultFlex_logo.png")
    col1, col2, col3 = st.columns([1, 0.6, 1])
    with col2:
        st.image(logo, width=120)

    # Title and tagline
    st.markdown("""
        <div style='text-align: center;'>
            <h1>VaultFlex</h1>
            <p style='font-size:1.2em; color: gray;'>Chat with your knowledge</p>
        </div>
    """, unsafe_allow_html=True)

    # Load available knowledge bases
    KB_DIR = GOLD_DIR
    if not os.path.exists(KB_DIR):
        os.makedirs(KB_DIR)
    available_kbs = [d for d in os.listdir(KB_DIR) if os.path.isdir(os.path.join(KB_DIR, d))]

    # Persist selected KB and model across sessions
    selected_kb = st.session_state.get("kb", available_kbs[0] if available_kbs else None)
    selected_model = st.session_state.get("llm", "gemma3:latest")

    # --- Selection controls ---
    with st.container():
        if available_kbs:
            selected_kb = st.selectbox("📚 Select a Knowledge Base", options=available_kbs, index=available_kbs.index(selected_kb))
        else:
            selected_kb = None
            st.warning("⚠️ No knowledge bases found. Please add one first.")

        model_options = ["deepseek-r1:7b", "deepseek-r1:8b", "gemma3:12b", "gemma3:latest"]
        selected_model = st.selectbox("🧠 Select a Language Model", model_options, index=model_options.index(selected_model))

    # --- Ask a question ---
    with st.form("ask_form", clear_on_submit=True):
        query = st.text_input("Ask a question", placeholder="Ask a question...")
        submitted = st.form_submit_button("Ask")

    if submitted:
        if not selected_kb:
            st.error("Please upload a knowledge base before starting a chat.")
        else:
            st.session_state["kb"] = selected_kb
            st.session_state["llm"] = selected_model
            st.session_state["query"] = query
            st.session_state["view"] = "Chat"
            st.rerun()

    # --- Footer ---
    render_backend_status_footer()

# INGESTION VIEW
elif st.session_state["view"] == "Ingest":
    run_ingestion_ui()
    render_backend_status_footer()

# CHAT VIEW
elif st.session_state["view"] == "Chat":
    run_chat_ui()
