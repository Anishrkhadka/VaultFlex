# Shared helper functions
"""
file_utils.py

General-purpose utility functions for:
- File hashing
- Dataset scope discovery
- Ingestion deduplication

Used by Streamlit UI, CLI tools, and core pipelines.
"""

import hashlib
import json
from pathlib import Path
from typing import List, Tuple, Union
from src.config import HASH_TRACK_FILE


def get_file_hash(file_obj: Union[Path, any]) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        file_obj (Path or Streamlit UploadedFile): File to hash

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


def get_existing_scopes(bronze_dir: Path) -> List[str]:
    """
    List all dataset scopes (subdirectories) in the bronze layer.

    Args:
        bronze_dir (Path): Path to /data/bronze

    Returns:
        list[str]: Sorted list of scope names
    """
    return sorted([p.name for p in bronze_dir.iterdir() if p.is_dir()])


def check_ingested_status(
    scope_name: str,
    files: List[any],
    hash_file: Path = HASH_TRACK_FILE
) -> Tuple[List[str], List[any]]:
    """
    Determine which uploaded files are new vs. already ingested.

    Args:
        scope_name (str): Dataset name
        files (list[UploadedFile]): Files from Streamlit upload
        hash_file (Path): Path to hash tracker JSON

    Returns:
        (list[str], list[UploadedFile]): Already ingested filenames, new files
    """
    if hash_file.exists():
        with open(hash_file, "r") as f:
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
