import streamlit as st
from src.__version__ import __version__
from src.ui.data_ingest_ui import run_ingestion_ui
from src.utils.service_status import get_backend_status

from src.config import LLM_MODEL

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
    model = pill(f"Model: {LLM_MODEL}", "🧠", "#8e24aa")
    ollama = pill("Ollama: Running" if status["ollama"] else "Ollama: Down", 
                  "✅" if status["ollama"] else "❌", 
                  "#2e7d32" if status["ollama"] else "#c62828")
    neo4j = pill("Neo4j: Connected" if status["neo4j"] else "Neo4j: Disconnected",
                 "📘" if status["neo4j"] else "❌", 
                 "#1565c0" if status["neo4j"] else "#c62828")

    # --- Show all pills
    st.markdown(model + ollama + neo4j, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Footer Text
    st.markdown(
        f"""
        <div style='text-align: center; color: gray; font-size: 0.8em; margin-top: 0.2em;'>
            Version: {__version__} &nbsp; | &nbsp; Made with ❤️ for local-first AI
        </div>
        """,
        unsafe_allow_html=True
    )



# --- Main Views ---
if st.session_state["view"] == "Welcome":
    st.markdown("## 🤖 Lightweight Chatbot")
    st.markdown("### with Memory and Retrieval-Augmentation")

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
    run_ingestion_ui()

elif st.session_state["view"] == "Chat":
    if st.button("🔙 Back to Welcome", use_container_width=True):
        st.session_state["view"] = "Welcome"
  

# --- Footer ---
render_backend_status_footer()
