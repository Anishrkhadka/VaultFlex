import streamlit as st
from src.utils.file_utils import get_existing_scopes
from src.config import GOLD_DIR
from src.vector.retriever import KnowledgeBaseRetriever


# def run_chat_ui():
#     st.title("💬 Chat with Your Database Base")

#     retriever = KnowledgeBaseRetriever()

#     # Sidebar config
#     with st.sidebar:
#         existing_scopes = get_existing_scopes(GOLD_DIR)
#         scope_option = st.selectbox("Database List:", ["<Default Scope>"]+ existing_scopes)
#         model_options = ["deepseek-r1:7b", "gemma3:12b", "gemma3:latest"]
#         selected_model = st.selectbox("Select a language model:", model_options)

#     # Warn if no real scope selected
#     if scope_option == "<Default Scope>":
#         st.warning("⚠️ Please select a valid knowledge scope from the sidebar.")
#         return 

#     # Initialize session state for chat history
#     if "messages" not in st.session_state:
#         st.session_state.messages = []

#     # Show chat history
#     for msg in st.session_state.messages:
#         with st.chat_message(msg["role"]):
#             st.markdown(msg["content"])

#     # User input
#     if prompt := st.chat_input("Ask a question..."):
#         # Display user message
#         st.chat_message("user").markdown(prompt)
#         st.session_state.messages.append({"role": "user", "content": prompt})

#         # Generate assistant response
#         with st.chat_message("assistant"):
#             with st.spinner("Thinking..."):
#                 try:
#                     answer = retriever.answer_with_keywords_and_chunks(
#                         prompt,
#                         scope=scope_option,
#                         model_name=selected_model
#                     )
#                     st.markdown(answer)
#                 except Exception as e:
#                     answer = f"❌ Error: {e}"
#                     st.error(answer)

#         st.session_state.messages.append({"role": "assistant", "content": answer})
import streamlit as st
from src.utils.file_utils import get_existing_scopes
from src.config import GOLD_DIR
from src.vector.retriever import KnowledgeBaseRetriever


def run_chat_ui():
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

    # --- Chat history state ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Back to Home ---
    if st.button("🔙 Back to Home"):
        st.session_state["view"] = "Welcome"
        st.session_state.pop("messages", None)
        st.session_state.pop("query", None)
        st.rerun()

    # --- Display selected scope + model ---
    st.markdown(f"<p style='text-align: center; color: gray;'>"
                f"Using KB: <b>{selected_scope}</b> | Model: <b>{selected_model}</b></p>",
                unsafe_allow_html=True)

    st.divider()

    # --- Show Chat History ---
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # --- Show chat input box always ---
    user_input = st.chat_input("Ask a question...")

    # --- Use initial query from session (once) ---
    prompt = st.session_state.pop("query", None)

    # Prefer session query first, then normal input
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

        st.session_state.messages.append({"role": "assistant", "content": answer})


