import streamlit as st
from src.utils.file_utils import get_existing_scopes
from src.config import GOLD_DIR
from src.vector.retriever import KnowledgeBaseRetriever


def run_chat_ui():
    st.title("💬 Chat with Your Database Base")

    retriever = KnowledgeBaseRetriever()

    # Sidebar config
    with st.sidebar:
        existing_scopes = get_existing_scopes(GOLD_DIR)
        scope_option = st.selectbox("Database List:", existing_scopes)
        model_options = ["deepseek-r1:7b", "gemma3:12b", "gemma3:latest"]
        selected_model = st.selectbox("Select a language model:", model_options)

    # Warn if no real scope selected
    if scope_option == "<Default Scope>":
        st.warning("⚠️ Please select a valid knowledge scope from the sidebar.")
        return  # Exit early if no valid scope

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Show chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if prompt := st.chat_input("Ask a question..."):
        # Display user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer = retriever.answer_with_keywords_and_chunks(
                        prompt,
                        scope=scope_option,
                        model_name=selected_model
                    )
                    st.markdown(answer)
                except Exception as e:
                    answer = f"❌ Error: {e}"
                    st.error(answer)

        st.session_state.messages.append({"role": "assistant", "content": answer})

