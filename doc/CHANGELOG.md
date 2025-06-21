# Changelog

All notable changes to this project will be documented in this file.

---
## [v1.0.0] – 2025-06-21

### Added
- **First release** of VaultFex
- End-to-end system: ingestion, embedding, graph construction, and querying
- Complete **demo video** demonstrating scoped knowledge interaction
- Fully structured and aligned **Project Charter** 
- Inline **docstrings** and code comments for all core modules (FAISS, GraphRAG, LLM coordination)
- Streamlit UI with:
  - Dataset scoping and ingestion flow
  - LLM and Knowledge Base switching
  - Hybrid FAISS + Neo4j GraphRAG chat
- Mermaid diagrams showing Medallion architecture

### Changed
- Final UI polish for first stable release
- Documentation updated to reflect working v1 architecture and flows

---
## [Unreleased] – 2025-06-20

### Added
- Minimalist **home page UI** with search bar and version/status footer
- GUI-based **knowledge base selection** and **LLM model selector** on home page
- `Chat Settings` expander in chat view to switch KB and model mid-session
- "Add Knowledge Base" button with direct routing to ingestion page
- First-question-from-home flow: preserves input and transitions into full chat
- Hybrid RAG architecture:
  - FAISS vector index (Gold layer)
  - GraphRAG using Neo4j + DeepSeek LLM for triple extraction

### Changed
- Chat UI refactored for clarity and state preservation:
  - Chat history now resets when changing KB or returning to home
  - `st.chat_input` now always visible, even after initial query
- Home page retains selected KB and LLM between views (no unwanted resets)
- Restructured ingestion UI with clearer steps: scope selection, upload, progress, and delete
- Internal docstrings and comments rewritten for clarity and maintainability

### Fixed
- Fixed issue where `GraphRAG` retrieval failed due to improper scope/model binding
- Fixed bug where initial chat query would block further user input
- Corrected handling of model and KB switching during an active session


## [Unreleased] - 2025-06-14

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

