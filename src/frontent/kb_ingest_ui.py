"""
kb_ingest_ui.py

This module defines the Streamlit interface for uploading, ingesting,
and deleting documents into a structured knowledge base within VaultFlex.

Features:
- Upload documents into a named scope (KB)
- Automatically preprocess, chunk, embed (FAISS), and extract triples (Neo4j)
- Skip already-ingested files using hash-based deduplication
- Support for deleting all files, vectors, and graph nodes for a given scope
"""

import json
import shutil
import streamlit as st
from neo4j import GraphDatabase

from src.config import (
    BRONZE_DIR, HASH_TRACK_FILE,
    get_scope_paths, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
)
from src.utils.file_utils import get_existing_scopes, check_ingested_status
from src.vector.embedder import KnowledgeBaseIngestor 


def run_ingestion_ui():
    """
    Renders the Streamlit UI for uploading and ingesting documents into a KB.

    Steps:
    1. User selects or creates a scope (knowledge base).
    2. User uploads one or more supported files.
    3. System checks for duplicates via file hash.
    4. New files are:
        - Stored in the bronze layer
        - Chunked and embedded into FAISS
        - Used to build a graph in Neo4j
    5. Optional: user can delete the entire scope and its assets.
    """
    st.title("📥 Knowledge Base Ingestion & Management")

    # --- Return to Home Button ---
    if st.button("🔙 Back to Home"):
        st.session_state["view"] = "Welcome"
        st.rerun()

    # --- Scope selection ---
    st.markdown("### 📂 1. Select or Create a Knowledge Base")
    existing_scopes = get_existing_scopes(BRONZE_DIR)
    scope_option = st.selectbox("Choose from existing or create new:", ["<New Knowledge Base>"] + existing_scopes)
    scope_name = st.text_input("Enter new name:") if scope_option == "<New Knowledge Base>" else scope_option

    st.divider()

    # --- File Upload Section ---
    st.markdown("### 📄 2. Upload Documents")
    uploaded_files = st.file_uploader(
        "Upload documents to add to this knowledge base:",
        accept_multiple_files=True,
        type=["pdf", "docx", "md", "txt"]
    )

    # --- Ingest Button Logic ---
    if st.button("📤 Ingest Documents") and scope_name and uploaded_files:
        with st.spinner("🔎 Checking for duplicates..."):
            already_ingested, new_files = check_ingested_status(scope_name, uploaded_files)

        if already_ingested:
            st.info("These files are already ingested and will be skipped:\n- " + "\n- ".join(already_ingested))
        if not new_files:
            st.warning("No new documents to ingest.")
        else:
            # --- Save new files to Bronze layer ---
            bronze_path = BRONZE_DIR / scope_name
            bronze_path.mkdir(parents=True, exist_ok=True)
            for file in new_files:
                file_path = bronze_path / file.name
                with open(file_path, "wb") as f:
                    f.write(file.read())

            # --- Run Ingestion Pipeline ---
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

    # --- Deletion Section ---
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
    """
    Deletes all resources associated with a given scope (knowledge base):
    - Raw files (bronze), cleaned chunks (silver), and embeddings (gold)
    - Entries from the HASH_TRACK_FILE
    - Nodes and relationships from Neo4j with matching scope

    Args:
        scope_name (str): The scope (KB) name to delete.

    Returns:
        int: Number of hash entries removed from the HASH_TRACK_FILE
    """
    scope_name = scope_name.strip()
    paths = get_scope_paths(scope_name)

    # --- Delete local medallion directories ---
    for key in ["bronze", "silver", "gold"]:
        path = paths.get(key)
        if path and path.exists():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    # --- Remove file hash entries ---
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

    # --- Delete Neo4j nodes and relationships for this scope ---
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        with driver.session() as session:
            session.run("""
                MATCH ()-[r]-() WHERE r.scope = $scope DELETE r
            """, scope=scope_name)

            session.run("""
                MATCH (n) WHERE n.scope = $scope DELETE n
            """, scope=scope_name)

            session.run("""
                MATCH (n) WHERE NOT (n)--() DELETE n
            """)
        driver.close()
        print(f"[GRAPH] Deleted all graph elements for scope: {scope_name}")
    except Exception as e:
        print(f"[GRAPH] Error deleting graph for scope {scope_name}: {e}")

    return len(deleted_keys)
