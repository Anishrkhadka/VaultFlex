# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- Initial project structure with Streamlit-based UI
- File upload and dataset scope selection
- Ingestion pipeline: PDF, DOCX, TXT, MD parsing
- SHA-256 hash deduplication logic per scope
- Chunking via `RecursiveCharacterTextSplitter`
- Embedding using `all-MiniLM-L6-v2` and storing in FAISS
- Scope-specific knowledge graph building via DeepSeek LLM
- Neo4j integration and scope-aware triple insertion
- Full scope deletion (bronze, silver, gold, graph, hashes)

### Changed
- Folder structure aligned with Medallion architecture
- `scripts/` moved to `src/data_ingestion/` for modularity
- `app.py` refactored into navigable UI via sidebar
- Replaced deprecated LangChain imports with `langchain_community`

### Fixed
- FAISS load errors due to index path mismatch
- LLM parsing failures with malformed JSON using regex cleanup
- Graph deletion logic now cleans orphaned nodes

---

## [0.1.0] – 2025-05-23

### Added
- Project scaffolding
- Working ingestion and embedding pipeline for initial scope

