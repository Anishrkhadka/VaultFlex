"""
Module: ingest_docs.py

This module defines the document ingestion pipeline for the RAG chatbot system.
It handles:
- File deduplication via SHA-256 hashing
- Document loading (PDF, DOCX, TXT, MD)
- Text chunking
- Embedding with HuggingFace models and FAISS storage
- LLM-based graph triple extraction and Neo4j insertion

This is structured under a Medallion architecture:
- Bronze: raw files
- Silver: structured chunks
- Gold: vector index (FAISS)
"""

import os
import json
import hashlib
from pathlib import Path

from src.config import get_scope_paths, CHUNK_SIZE, CHUNK_OVERLAP, HASH_TRACK_FILE, EMBEDDING_MODEL
from src.data_ingestion.graph_builder_llm import GraphBuilderLLM

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


def get_file_hash(file_obj):
    """
    Compute SHA-256 hash of a file.

    Args:
        file_obj (Path or Streamlit UploadedFile): Input file object

    Returns:
        str: Hexadecimal hash value
    """
    hasher = hashlib.sha256()

    if hasattr(file_obj, "read") and callable(file_obj.read):
        file_bytes = file_obj.read()
        file_obj.seek(0)
    else:
        with open(file_obj, "rb") as f:
            file_bytes = f.read()

    hasher.update(file_bytes)
    return hasher.hexdigest()


def is_already_ingested(scope_name, file_path):
    """
    Check if a file has already been ingested by its hash and scope.

    Args:
        scope_name (str): Dataset scope identifier
        file_path (Path): File to check

    Returns:
        bool: True if already ingested, False otherwise
    """
    file_hash = get_file_hash(file_path)
    scoped_key = f"{scope_name}/{file_path.name}"

    if os.path.exists(HASH_TRACK_FILE):
        with open(HASH_TRACK_FILE, "r") as f:
            ingested = json.load(f)
    else:
        ingested = {}

    if scoped_key in ingested and ingested[scoped_key] == file_hash:
        return True

    # Save new hash
    ingested[scoped_key] = file_hash
    with open(HASH_TRACK_FILE, "w") as f:
        json.dump(ingested, f, indent=2)

    return False


def load_documents(source_dir, scope_name):
    """
    Load all documents from a directory and return LangChain Document objects.

    Args:
        source_dir (Path): Folder path for raw documents
        scope_name (str): Dataset scope to check for duplication

    Returns:
        list: Parsed LangChain Documents
    """
    docs = []
    for file_path in Path(source_dir).glob("*"):
        ext = file_path.suffix.lower()
        print(f"Scanning file: {file_path.name} (ext: {ext})")

        if is_already_ingested(scope_name, file_path):
            print(f"Skipping already ingested file: {file_path.name}")
            continue

        try:
            if ext == ".pdf":
                loader = PyMuPDFLoader(str(file_path))
            elif ext == ".docx":
                loader = UnstructuredWordDocumentLoader(str(file_path))
            elif ext == ".md":
                loader = UnstructuredMarkdownLoader(str(file_path))
            elif ext == ".txt":
                loader = TextLoader(str(file_path), encoding="utf-8")
            else:
                print(f"Skipping unsupported file: {file_path}")
                continue
            docs.extend(loader.load())
        except Exception as e:
            print(f"Error loading {file_path.name}: {e}")
    return docs


def split_documents(docs):
    """
    Split documents into overlapping text chunks.

    Args:
        docs (list): List of LangChain Document objects

    Returns:
        list: Chunks of documents
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_documents(docs)


def save_chunks_to_silver(chunks, output_file):
    """
    Save text chunks to a JSON file in the Silver layer.

    Args:
        chunks (list): List of document chunks
        output_file (str): Output file path
    """
    chunk_data = [doc.dict() for doc in chunks]
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunk_data, f, ensure_ascii=False, indent=2)


def store_embeddings(chunks, output_dir):
    """
    Generate embeddings from chunks and store in a FAISS index.

    Args:
        chunks (list): Document chunks
        output_dir (str): Directory to save FAISS index
    """
    if not chunks:
        print("No chunks to store in FAISS. Skipping FAISS index creation.")
        return

    print(f"Storing {len(chunks)} chunks in FAISS...")

    embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    try:
        db = FAISS.from_documents(chunks, embedder)
        os.makedirs(output_dir, exist_ok=True)
        db.save_local(output_dir)
        print(f"FAISS index saved to: {output_dir}")
    except Exception as e:
        print(f"Error saving FAISS index: {e}")


def ingest_scope(scope: str):
    """
    Full ingestion pipeline for a given dataset scope.

    - Loads documents from Bronze
    - Splits and saves chunks to Silver
    - Embeds and stores vectors in Gold (FAISS)
    - Extracts triples and pushes to Neo4j

    Args:
        scope (str): Dataset scope name
    """
    paths = get_scope_paths(scope)
    os.makedirs(paths["bronze"], exist_ok=True)
    os.makedirs(paths["gold"], exist_ok=True)

    raw_docs = load_documents(paths["bronze"], scope)
    if not raw_docs:
        print(f"No new documents found for scope: {scope}")
        return

    chunks = split_documents(raw_docs)
    save_chunks_to_silver(chunks, paths["silver"])
    store_embeddings(chunks, paths["gold"])
    print(f"Ingestion complete for scope '{scope}': {len(chunks)} chunks saved.")

    # Build Knowledge Graph from chunks
    try:
        print(f"[GRAPH] Starting graph construction for scope '{scope}'...")
        graph_builder = GraphBuilderLLM()
        graph_builder.process_chunks(chunks, scope)
        graph_builder.close()
        print(f"[GRAPH] Graph construction complete for scope '{scope}'.")
    except Exception as e:
        print(f"[GRAPH] Failed to build graph for scope '{scope}': {e}")
