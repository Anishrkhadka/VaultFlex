"""
embedder.py

Defines the `KnowledgeBaseIngestor` class, which handles the ingestion pipeline
for a single knowledge base (scope) in VaultFlex.

Responsibilities:
- Load and hash uploaded documents (bronze layer)
- Chunk documents into segments (silver layer)
- Generate and persist embeddings using FAISS (gold layer)
- Extract semantic triples via LLM and store in Neo4j
"""

import os
import json
import hashlib
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

from src.config import get_scope_paths, CHUNK_SIZE, CHUNK_OVERLAP, HASH_TRACK_FILE, EMBEDDING_MODEL
from src.vector.llm_graph_builder import GraphBuilderLLM


class KnowledgeBaseIngestor:
    """
    Main class to orchestrate the ingestion of documents into VaultFlex's medallion pipeline.

    This includes:
    - File deduplication via hashing
    - Document loading and chunking
    - FAISS embedding index creation
    - Graph-based triple extraction via LLM
    """

    def __init__(self, scope: str):
        """
        Args:
            scope (str): Name of the knowledge base or dataset
        """
        self.scope = scope
        self.paths = get_scope_paths(scope)
        os.makedirs(self.paths["bronze"], exist_ok=True)
        os.makedirs(self.paths["gold"], exist_ok=True)

    def get_file_hash(self, file_obj) -> str:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_obj (Path or file-like): Local file or Streamlit upload

        Returns:
            str: Hexadecimal hash string
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

    def is_already_ingested(self, file_path: Path) -> bool:
        """
        Check if the file has already been processed by comparing stored hashes.

        Args:
            file_path (Path): Path to the file

        Returns:
            bool: True if the file is already ingested
        """
        file_hash = self.get_file_hash(file_path)
        scoped_key = f"{self.scope}/{file_path.name}"

        if os.path.exists(HASH_TRACK_FILE):
            with open(HASH_TRACK_FILE, "r") as f:
                ingested = json.load(f)
        else:
            ingested = {}

        if scoped_key in ingested and ingested[scoped_key] == file_hash:
            return True

        ingested[scoped_key] = file_hash
        with open(HASH_TRACK_FILE, "w") as f:
            json.dump(ingested, f, indent=2)
        return False

    def load_documents(self) -> list:
        """
        Load all new documents from the bronze layer, skipping duplicates.

        Returns:
            list[Document]: LangChain-compatible document objects
        """
        docs = []
        for file_path in Path(self.paths["bronze"]).glob("*"):
            ext = file_path.suffix.lower()
            if self.is_already_ingested(file_path):
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
                    continue
                docs.extend(loader.load())
            except Exception as e:
                print(f"Error loading {file_path.name}: {e}")
        return docs

    def split_documents(self, docs: list) -> list:
        """
        Split documents into overlapping chunks.

        Args:
            docs (list): List of LangChain Document objects

        Returns:
            list: List of chunked documents
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        return splitter.split_documents(docs)

    def save_chunks_to_silver(self, chunks: list):
        """
        Persist cleaned chunks as JSON to the silver layer.

        Args:
            chunks (list): Chunked documents to save
        """
        chunk_data = [doc.dict() for doc in chunks]
        with open(self.paths["silver"], "w", encoding="utf-8") as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)

    def store_embeddings(self, chunks: list):
        """
        Generate vector embeddings and save them as a FAISS index.

        Args:
            chunks (list): List of chunked documents
        """
        if not chunks:
            print("No chunks to store in FAISS.")
            return
        embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        try:
            db = FAISS.from_documents(chunks, embedder)
            os.makedirs(self.paths["gold"], exist_ok=True)
            db.save_local(self.paths["gold"])
        except Exception as e:
            print(f"Error saving FAISS index: {e}")

    def ingest(self):
        """
        Full ingestion pipeline:
        - Load and deduplicate documents
        - Chunk and save cleaned text
        - Embed and index into FAISS
        - Extract triples and build graph
        """
        raw_docs = self.load_documents()
        if not raw_docs:
            print(f"No new documents for scope: {self.scope}")
            return

        chunks = self.split_documents(raw_docs)
        self.save_chunks_to_silver(chunks)
        self.store_embeddings(chunks)
        self.build_graph(chunks)

    def chunk_only(self) -> list:
        """
        Run only the loading and chunking stages.

        Returns:
            list: List of text chunks (LangChain Document format)
        """
        raw_docs = self.load_documents()
        if not raw_docs:
            print(f"No new documents for scope: {self.scope}")
            return []
        chunks = self.split_documents(raw_docs)
        self.save_chunks_to_silver(chunks)
        return chunks

    def embed_only(self, chunks: list):
        """
        Run only the embedding and FAISS storage step.

        Args:
            chunks (list): Chunked documents
        """
        self.store_embeddings(chunks)

    def build_graph(self, chunks: list):
        """
        Run knowledge graph extraction via LLM and push to Neo4j.

        Args:
            chunks (list): Chunked documents to extract triples from
        """
        graph_builder = GraphBuilderLLM()
        try:
            graph_builder.process_chunks(chunks, self.scope)
            graph_builder.close()
        except Exception as e:
            print(f"[GRAPH] Error building graph: {e}")
