
# import json
# import shutil
# import streamlit as st
# from neo4j import GraphDatabase

# from src.config import (
#     BRONZE_DIR, HASH_TRACK_FILE,
#     get_scope_paths, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# )
# from src.utils.file_utils import (
#     get_existing_scopes,
#     check_ingested_status
# )
# from src.vector.embedder import chunk_scope, embed_scope, build_graph


# def run_ingestion_ui():
#     """
#     VaultFlex UI: Upload and manage datasets, trigger hybrid RAG pipeline, delete scopes.

#     Workflow:
#     - Create or select a knowledge base (scope)
#     - Upload documents (PDF, DOCX, MD, TXT)
#     - Automatically build: chunks (Silver), embeddings (Gold), and graph (Neo4j)
#     - View and delete existing scopes
#     """

#     st.title("📥 Knowledge Base Ingestion & Management")

#         # --- Back to Home ---
#     if st.button("🔙 Back to Home"):
#         st.session_state["view"] = "Welcome"
#         st.rerun()

#     # --- Select/Create Dataset Scope ---
#     st.markdown("### 📂 1. Select or Create a Knowledge Base")

#     existing_scopes = get_existing_scopes(BRONZE_DIR)
#     scope_option = st.selectbox("Choose from existing or create new:", ["<New Knowledge Base>"] + existing_scopes)

#     if scope_option == "<New Knowledge Base>":
#         scope_name = st.text_input("Enter new name:")
#     else:
#         scope_name = scope_option

#     st.divider()

#     # --- Upload Files ---
#     st.markdown("### 📄 2. Upload Documents")
#     uploaded_files = st.file_uploader(
#         "Upload documents to add to this knowledge base:",
#         accept_multiple_files=True,
#         type=["pdf", "docx", "md", "txt"]
#     )

#     # --- Ingest Trigger ---
#     if st.button("📤 Ingest Documents") and scope_name and uploaded_files:
#         with st.spinner("🔎 Checking for duplicates..."):
#             already_ingested, new_files = check_ingested_status(scope_name, uploaded_files)

#         if already_ingested:
#             st.info("These files are already ingested and will be skipped:\n- " + "\n- ".join(already_ingested))

#         if not new_files:
#             st.warning("No new documents to ingest.")
#         else:
#             bronze_path = BRONZE_DIR / scope_name
#             bronze_path.mkdir(parents=True, exist_ok=True)

#             for file in new_files:
#                 file_path = bronze_path / file.name
#                 with open(file_path, "wb") as f:
#                     f.write(file.read())

#             progress = st.progress(0)
#             status_text = st.empty()

#             try:
#                 status_text.text("🔍 Step 1/3: Splitting into chunks...")
#                 chunks = chunk_scope(scope_name)
#                 progress.progress(0.33)

#                 status_text.text("📐 Step 2/3: Embedding + FAISS index...")
#                 embed_scope(scope_name, chunks)
#                 progress.progress(0.66)

#                 status_text.text("🧠 Step 3/3: Building knowledge graph...")
#                 build_graph(scope_name, chunks)
#                 progress.progress(1.0)

#                 status_text.text("✅ Done!")
#                 st.success(f"Ingestion complete for: **{scope_name}**")

#             except Exception as e:
#                 status_text.text("❌ Ingestion failed.")
#                 st.error(f"Error: {e}")

#     # --- Delete Scope (Danger Zone) ---
#     if scope_option != "<New Knowledge Base>":
#         st.divider()
#         with st.expander("⚠️ Danger Zone: Delete Knowledge Base"):
#             st.markdown("Permanently deletes all associated files and graph data.")
#             confirm = st.checkbox(f"I understand this will delete **{scope_option}** forever.")

#             if st.button("❌ Delete Knowledge Base") and confirm:
#                 deleted_count = delete_scope(scope_option)
#                 st.success(f"Deleted **{scope_option}** and {deleted_count} file entries.")
#                 st.session_state.clear()
#                 st.success("Please refresh manually.")

# # --- Helper: Delete All Files + Graph ---
# def delete_scope(scope_name: str) -> int:
#     """
#     Fully delete a scope: file system (bronze/silver/gold) and graph DB.

#     Returns:
#         int: Count of deleted hashes
#     """
#     scope_name = scope_name.strip()
#     paths = get_scope_paths(scope_name)

#     for key in ["bronze", "silver", "gold"]:
#         path = paths.get(key)
#         if path and path.exists():
#             if path.is_file():
#                 path.unlink()
#             elif path.is_dir():
#                 shutil.rmtree(path, ignore_errors=True)

#     deleted_keys = []
#     if HASH_TRACK_FILE.exists():
#         with open(HASH_TRACK_FILE, "r", encoding="utf-8") as f:
#             ingested = json.load(f)

#         prefix = f"{scope_name}/"
#         deleted_keys = [k for k in ingested if k.startswith(prefix)]
#         for k in deleted_keys:
#             ingested.pop(k)

#         with open(HASH_TRACK_FILE, "w", encoding="utf-8") as f:
#             json.dump(ingested, f, indent=2)

#     try:
#         driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
#         with driver.session() as session:
#             session.run(
#                 "MATCH (s:Entity)-[r:RELATION {scope: $scope}]->(o:Entity) DELETE r",
#                 scope=scope_name
#             )
#             session.run("MATCH (n:Entity) WHERE NOT (n)--() DELETE n")
#         driver.close()
#         print(f"[GRAPH] Deleted graph for scope: {scope_name}")
#     except Exception as e:
#         print(f"[GRAPH] Error deleting graph for scope {scope_name}: {e}")

#     return len(deleted_keys)


import json
import shutil
import streamlit as st
from neo4j import GraphDatabase

from src.config import (
    BRONZE_DIR, HASH_TRACK_FILE,
    get_scope_paths, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)
from src.utils.file_utils import get_existing_scopes, check_ingested_status
from src.vector.knowledge_ingestor import KnowledgeBaseIngestor  # renamed embedder.py

def run_ingestion_ui():
    st.title("📥 Knowledge Base Ingestion & Management")

    if st.button("🔙 Back to Home"):
        st.session_state["view"] = "Welcome"
        st.rerun()

    st.markdown("### 📂 1. Select or Create a Knowledge Base")
    existing_scopes = get_existing_scopes(BRONZE_DIR)
    scope_option = st.selectbox("Choose from existing or create new:", ["<New Knowledge Base>"] + existing_scopes)
    scope_name = st.text_input("Enter new name:") if scope_option == "<New Knowledge Base>" else scope_option

    st.divider()

    st.markdown("### 📄 2. Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload documents to add to this knowledge base:",
        accept_multiple_files=True,
        type=["pdf", "docx", "md", "txt"]
    )

    if st.button("📤 Ingest Documents") and scope_name and uploaded_files:
        with st.spinner("🔎 Checking for duplicates..."):
            already_ingested, new_files = check_ingested_status(scope_name, uploaded_files)

        if already_ingested:
            st.info("These files are already ingested and will be skipped:\n- " + "\n- ".join(already_ingested))
        if not new_files:
            st.warning("No new documents to ingest.")
        else:
            bronze_path = BRONZE_DIR / scope_name
            bronze_path.mkdir(parents=True, exist_ok=True)
            for file in new_files:
                file_path = bronze_path / file.name
                with open(file_path, "wb") as f:
                    f.write(file.read())

            ingestor = KnowledgeBaseIngestor(scope_name)
            progress = st.progress(0)
            status_text = st.empty()

            try:
                status_text.text("🔍 Step 1/3: Splitting into chunks...")
                chunks = ingestor.chunk_only()
                progress.progress(0.33)

                status_text.text("📐 Step 2/3: Embedding + FAISS index...")
                ingestor.embed_only(chunks)
                progress.progress(0.66)

                status_text.text("🧠 Step 3/3: Building knowledge graph...")
                ingestor.build_graph(chunks)
                progress.progress(1.0)

                status_text.text("✅ Done!")
                st.success(f"Ingestion complete for: **{scope_name}**")
            except Exception as e:
                status_text.text("❌ Ingestion failed.")
                st.error(f"Error: {e}")

    if scope_option != "<New Knowledge Base>":
        st.divider()
        with st.expander("⚠️ Danger Zone: Delete Knowledge Base"):
            st.markdown("Permanently deletes all associated files and graph data.")
            confirm = st.checkbox(f"I understand this will delete **{scope_option}** forever.")
            if st.button("❌ Delete Knowledge Base") and confirm:
                deleted_count = delete_scope(scope_option)
                st.success(f"Deleted **{scope_option}** and {deleted_count} file entries.")
                st.session_state.clear()
                st.success("Please refresh manually.")

def delete_scope(scope_name: str) -> int:
    scope_name = scope_name.strip()
    paths = get_scope_paths(scope_name)

    for key in ["bronze", "silver", "gold"]:
        path = paths.get(key)
        if path and path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    deleted_keys = []
    if HASH_TRACK_FILE.exists():
        with open(HASH_TRACK_FILE, "r", encoding="utf-8") as f:
            ingested = json.load(f)

        prefix = f"{scope_name}/"
        deleted_keys = [k for k in ingested if k.startswith(prefix)]
        for k in deleted_keys:
            ingested.pop(k)

        with open(HASH_TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(ingested, f, indent=2)

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run(
                "MATCH (s:Entity)-[r:RELATION {scope: $scope}]->(o:Entity) DELETE r",
                scope=scope_name
            )
            session.run("MATCH (n:Entity) WHERE NOT (n)--() DELETE n")
        driver.close()
        print(f"[GRAPH] Deleted graph for scope: {scope_name}")
    except Exception as e:
        print(f"[GRAPH] Error deleting graph for scope {scope_name}: {e}")

    return len(deleted_keys)
