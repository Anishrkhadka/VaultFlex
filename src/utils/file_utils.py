"""
file_utils.py

Utility functions for file handling within the VaultFlex ingestion pipeline.

Responsibilities:
- File deduplication via SHA-256 hashing
- Scope discovery (from folder structure)
- Determining which uploaded files have already been ingested
"""

import hashlib
import json
from pathlib import Path
from typing import List, Tuple, Union, BinaryIO
from src.config import HASH_TRACK_FILE


def get_file_hash(file_obj: Union[Path, BinaryIO]) -> str:
    """
    Compute a SHA-256 hash for a given file.

    Args:
        file_obj (Path or file-like object): File to hash.
            Can be a local Path or Streamlit UploadedFile.

    Returns:
        str: Hexadecimal SHA-256 hash string.
    """
    hasher = hashlib.sha256()

    if hasattr(file_obj, "read") and callable(file_obj.read):
        # e.g., Streamlit UploadedFile
        file_bytes = file_obj.read()
        file_obj.seek(0)  # Reset for re-reading later
    else:
        with open(file_obj, "rb") as f:
            file_bytes = f.read()

    hasher.update(file_bytes)
    return hasher.hexdigest()


def get_existing_scopes(bronze_dir: Path) -> List[str]:
    """
    List all existing knowledge base scopes (directories) in the bronze layer.

    Args:
        bronze_dir (Path): Path to the 'bronze' directory.

    Returns:
        List[str]: Sorted list of scope names (directory names).
    """
    return sorted([p.name for p in bronze_dir.iterdir() if p.is_dir()])


def check_ingested_status(
    scope_name: str,
    files: List[BinaryIO],
    hash_file: Path = HASH_TRACK_FILE
) -> Tuple[List[str], List[BinaryIO]]:
    """
    Check which uploaded files are new vs. already ingested (based on hash tracking).

    Args:
        scope_name (str): The dataset scope (e.g., "hr_docs").
        files (List[UploadedFile]): List of files uploaded via Streamlit.
        hash_file (Path, optional): Path to the JSON file that stores ingested hashes.
            Defaults to HASH_TRACK_FILE.

    Returns:
        Tuple[List[str], List[UploadedFile]]:
            - List of filenames already ingested
            - List of UploadedFile objects that are new
    """
    if hash_file.exists():
        with open(hash_file, "r", encoding="utf-8") as f:
            ingested = json.load(f)
    else:
        ingested = {}

    already_ingested = []
    new_files = []

    for file in files:
        file_hash = get_file_hash(file)
        scoped_key = f"{scope_name}/{file.name}"
        if scoped_key in ingested and ingested[scoped_key] == file_hash:
            already_ingested.append(file.name)
        else:
            new_files.append(file)

    return already_ingested, new_files
