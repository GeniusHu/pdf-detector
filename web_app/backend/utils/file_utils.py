#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File utilities for PDF similarity detection service
"""

import os
import uuid
import shutil
import aiofiles
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)


async def save_upload_file(
    upload_file: UploadFile,
    upload_dir: str = "uploads",
    max_size: int = 100 * 1024 * 1024  # 100MB
) -> str:
    """
    Save an uploaded file to disk

    Args:
        upload_file: FastAPI UploadFile object
        upload_dir: Directory to save the file
        max_size: Maximum allowed file size in bytes

    Returns:
        str: Path to the saved file

    Raises:
        ValueError: If file is too large or invalid type
        IOError: If file cannot be saved
    """
    try:
        # Create upload directory if it doesn't exist
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_extension = Path(upload_file.filename).suffix.lower()
        if file_extension != '.pdf':
            raise ValueError("Only PDF files are allowed")

        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = upload_path / unique_filename

        # Save file with size check
        file_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await upload_file.read(8192):
                file_size += len(chunk)
                if file_size > max_size:
                    # Clean up partial file
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
                await f.write(chunk)

        logger.info(f"Saved uploaded file: {file_path} ({file_size} bytes)")
        return str(file_path)

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error saving upload file: {str(e)}")
        raise IOError(f"Failed to save file: {str(e)}")


async def cleanup_files(file_paths: List[str]) -> None:
    """
    Clean up temporary files

    Args:
        file_paths: List of file paths to delete
    """
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Deleted file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {file_path}: {str(e)}")


def get_file_info(file_path: str) -> dict:
    """
    Get information about a file

    Args:
        file_path: Path to the file

    Returns:
        dict: File information
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    stat = os.stat(file_path)
    return {
        "path": file_path,
        "name": Path(file_path).name,
        "size": stat.st_size,
        "size_mb": round(stat.st_size / (1024 * 1024), 2),
        "created_at": stat.st_ctime,
        "modified_at": stat.st_mtime
    }


def ensure_directory(directory: str) -> None:
    """
    Ensure a directory exists

    Args:
        directory: Directory path
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str) -> str:
    """
    Generate a safe filename by removing/replacing problematic characters

    Args:
        filename: Original filename

    Returns:
        str: Safe filename
    """
    # Replace problematic characters
    replacements = {
        '/': '_', '\\': '_', ':': '_', '*': '_', '?': '_',
        '"': "'", '<': '_', '>': '_', '|': '_', '\n': '', '\r': ''
    }

    for old, new in replacements.items():
        filename = filename.replace(old, new)

    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')

    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"

    return filename


def get_file_extension(filename: str) -> str:
    """
    Get file extension in lowercase

    Args:
        filename: Filename

    Returns:
        str: File extension (including the dot)
    """
    return Path(filename).suffix.lower()


def is_valid_pdf(file_path: str) -> bool:
    """
    Check if a file is a valid PDF

    Args:
        file_path: Path to the file

    Returns:
        bool: True if valid PDF, False otherwise
    """
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            # Try to read the first page
            if len(reader.pages) > 0:
                reader.pages[0].extract_text()
            return True
    except Exception as e:
        logger.warning(f"Invalid PDF file {file_path}: {str(e)}")
        return False