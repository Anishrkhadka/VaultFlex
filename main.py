import streamlit as st
from src.__version__ import __version__
from src.ui.data_ingest_ui import run_ingestion_ui
from src.utils.service_status import get_backend_status
from src.ui.chat_ui import run_chat_ui
import os
from src.config import LLM_MODEL, GOLD_DIR
from PIL import Image

st.set_page_config(page_title="Chatbot with GraphRAG and RAG", layout="centered")

# --- Session Init ---
if "view" not in st.session_state:
    st.session_state["view"] = "Welcome"

# --- Button Styling ---
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

# --- Status Pills for Footer ---
def status_pill_footer(label, icon, color, subtext=""):
    st.markdown(
        f"""
        <div style="
            display: inline-block;
            background-color: {color};
            color: white;
            border-radius: 6px;
            padding: 4px 10px;
            margin: 0 6px;
            font-size: 0.75em;
            font-weight: 500;
        ">
            {icon} {label}: {subtext}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_backend_status_footer():
    status = get_backend_status()

    # --- Divider
    st.markdown("<hr style='margin-top: 2em;'>", unsafe_allow_html=True)

    # --- Start row container
    st.markdown(
        """
        <div style='display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; margin-bottom: 0.8em;'>
        """, unsafe_allow_html=True
    )

    # --- Pill builder
    def pill(text, icon, bg):
        return f"""
            <div style="
                text-align: center; 
                display: inline-flex;
                align-items: center;
                background-color: {bg};
                color: white;
                padding: 6px 14px;
                border-radius: 16px;
                font-size: 0.75em;
                font-weight: 500;
                box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                margin: 4px;
                white-space: nowrap;
            ">
                {icon}&nbsp;{text}
            </div>
        """

    # --- Pills
    ollama = pill("Ollama: Running" if status["ollama"] else "Ollama: Down", 
                  "✅" if status["ollama"] else "❌", 
                  "#2e7d32" if status["ollama"] else "#c62828")
    neo4j = pill("Neo4j: Connected" if status["neo4j"] else "Neo4j: Disconnected",
                 "📘" if status["neo4j"] else "❌", 
                 "#1565c0" if status["neo4j"] else "#c62828")

    # --- Show all pills
    st.markdown(ollama + neo4j, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Footer Text
    st.markdown(
        f"""
        <div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 0.2em;'>
            Version: {__version__} &nbsp; | &nbsp; Made with ❤️ VaultFlex
        </div>
        """,
        unsafe_allow_html=True
    )

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []


# --- Main Views ---
if st.session_state["view"] == "Welcome":
    KB_DIR = GOLD_DIR

    # --- Top-left: Add Knowledge Base Button ---
    if st.button("➕ Add Knowledge Base", key="add_kb_button"):
        st.session_state["view"] = "Ingest"
        st.rerun()


    # --- Centre the logo ---
    logo = Image.open("doc/images/vaultFlex_logo.png")
    col1, col2, col3 = st.columns([1, 0.6, 1])
    with col1:
        st.empty()
    with col2:
        st.image(logo, width=120)
    with col3:
        st.empty()
    # --- App Title ---
    st.markdown(
        f"""
        <div style='text-align: center;'>
            <h1>VaultFlex</h1>
            <p style='font-size:1.2em; color: gray;'>Chat with your knowledge</p>
        </div>
        """,
        unsafe_allow_html=True
)

    # --- Load Knowledge Bases ---
    if not os.path.exists(KB_DIR):
        os.makedirs(KB_DIR)
    available_kbs = [d for d in os.listdir(KB_DIR) if os.path.isdir(os.path.join(KB_DIR, d))]

    # --- KB and Model Selection ---
    selected_kb = st.session_state.get("kb")
    selected_model = st.session_state.get("llm", "gemma3:latest")

    # Update defaults if not set
    if not selected_kb and available_kbs:
        selected_kb = available_kbs[0]
        st.session_state["kb"] = selected_kb

    if "llm" not in st.session_state:
        st.session_state["llm"] = selected_model


    with st.container():
        if available_kbs:
            selected_kb = st.selectbox("📚 Select a Knowledge Base", options=available_kbs, index=available_kbs.index(selected_kb) if selected_kb in available_kbs else 0)
        else:
            selected_kb = None
            st.warning("⚠️ No knowledge bases found. Please add one first.")

        model_options = ["deepseek-r1:7b", "deepseek-r1:8b","gemma3:12b", "gemma3:latest"]
        selected_model = st.selectbox("🧠 Select a Language Model", model_options, index=model_options.index(selected_model) if selected_model in model_options else 0)

    # --- Question Form ---
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
elif st.session_state["view"] == "Ingest":
    run_ingestion_ui()
    render_backend_status_footer()

elif st.session_state["view"] == "Chat":
    run_chat_ui()
    
