"""
chat_ui.py

This module defines the Streamlit-based chat interface for VaultFlex.
It allows users to ask questions against an indexed knowledge base (KB),
and receive answers via an LLM-powered retrieval system.

Key components:
- Streamlit UI to display and handle chat interactions
- Scoped knowledge base selection
- Retrieval using FAISS (vector) and optional graph context
"""

import streamlit as st
from src.utils.file_utils import get_existing_scopes
from src.config import GOLD_DIR
from src.vector.retriever import KnowledgeBaseRetriever

def run_chat_ui():
    """
    Launches the VaultFlex chat interface via Streamlit.

    This function:
    - Loads the selected KB and model from the session
    - Validates the availability of the KB
    - Manages chat history state
    - Displays previous messages
    - Captures user input and generates responses using `KnowledgeBaseRetriever`
    """
    st.markdown("<h1 style='text-align: center;'>💬 VaultFlex Chat</h1>", unsafe_allow_html=True)

    retriever = KnowledgeBaseRetriever()

    # --- Load KB and model from session ---
    selected_scope = st.session_state.get("kb")
    selected_model = st.session_state.get("llm", "gemma3:latest")

    existing_scopes = get_existing_scopes(GOLD_DIR)

    # --- Validate scope availability ---
    if not selected_scope or selected_scope not in existing_scopes:
        st.error("⚠️ No valid knowledge base selected. Please return to the home page.")
        return

    # --- Reset chat history if scope changed ---
    if st.session_state.get("last_scope") != selected_scope:
        st.session_state.messages = []
        st.session_state.last_scope = selected_scope

    # --- Initialise chat state if missing ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Back to Home Button ---
    if st.button("🔙 Back to Home"):
        st.session_state["view"] = "Welcome"
        st.session_state.pop("messages", None)
        st.session_state.pop("query", None)
        st.rerun()

    # --- Display active KB and LLM model ---
    st.markdown(f"<p style='text-align: center; color: gray;'>"
                f"Using KB: <b>{selected_scope}</b> | Model: <b>{selected_model}</b></p>",
                unsafe_allow_html=True)

    st.divider()

    # --- Display chat history ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Get user input ---
    user_input = st.chat_input("Ask a question...")

    # --- Check if there’s a preloaded prompt (e.g., redirected from home page form) ---
    prompt = st.session_state.pop("query", None)

    # Use session-passed query first, then fallback to user input
    if prompt is None:
        prompt = user_input

    if prompt:
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = retriever.answer_with_keywords_and_chunks(
                        prompt,
                        scope=selected_scope,
                        model_name=selected_model
                    )
                    st.markdown(answer)
                except Exception as e:
                    answer = f"❌ Error: {e}"
                    st.error(answer)

        # Store assistant's message in session
        st.session_state.messages.append({"role": "assistant", "content": answer})
