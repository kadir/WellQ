"""
Security utilities for file validation and content checking.
"""
import os
import json
import magic
from django.core.exceptions import ValidationError


def validate_json_file(file, max_size_mb=100):
    """
    Validate a JSON file for security.
    
    Args:
        file: Django UploadedFile object
        max_size_mb: Maximum file size in MB (default: 100MB)
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check file extension
    if not file.name.lower().endswith('.json'):
        return False, "File must have .json extension"
    
    # Check file size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        return False, f"File size exceeds maximum of {max_size_mb}MB"
    
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(file.name)
    if safe_filename != file.name:
        return False, "Invalid filename - path traversal detected"
    
    # Check MIME type (if python-magic is available)
    try:
        file.seek(0)
        mime_type = magic.from_buffer(file.read(1024), mime=True)
        file.seek(0)
        
        # Allow JSON and text/plain (some systems report JSON as text/plain)
        allowed_mimes = ['application/json', 'text/plain', 'text/json']
        if mime_type not in allowed_mimes:
            return False, f"Invalid file type: {mime_type}. Expected JSON file."
    except ImportError:
        # python-magic not installed, skip MIME check but log warning
        import warnings
        warnings.warn("python-magic not installed. MIME type validation skipped.")
    except Exception as e:
        # If magic fails, continue but log
        import warnings
        warnings.warn(f"MIME type check failed: {e}")
    
    # Validate JSON structure (check if it's valid JSON)
    try:
        file.seek(0)
        # Read a sample to check if it's valid JSON
        sample = file.read(min(1024, file.size))
        file.seek(0)
        
        # Try to parse as JSON
        json.loads(sample)
    except json.JSONDecodeError:
        # If sample is too small, try parsing the whole file (with size limit)
        try:
            file.seek(0)
            content = file.read(max_size_bytes)
            file.seek(0)
            json.loads(content)
        except json.JSONDecodeError:
            return False, "File is not valid JSON"
        except MemoryError:
            return False, "File is too large to parse"
    
    return True, None


def validate_file_content(file, allowed_extensions=None, max_size_mb=100):
    """
    Generic file validation function.
    
    Args:
        file: Django UploadedFile object
        allowed_extensions: List of allowed extensions (e.g., ['.json', '.txt'])
        max_size_mb: Maximum file size in MB
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = ['.json']
    
    # Check extension
    file_ext = os.path.splitext(file.name)[1].lower()
    if file_ext not in allowed_extensions:
        return False, f"File extension not allowed. Allowed: {', '.join(allowed_extensions)}"
    
    # Check size
    max_size_bytes = max_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        return False, f"File size exceeds maximum of {max_size_mb}MB"
    
    # Sanitize filename
    safe_filename = os.path.basename(file.name)
    if safe_filename != file.name:
        return False, "Invalid filename - path traversal detected"
    
    return True, None


def safe_json_load(file, max_size_mb=100):
    """
    Safely load JSON from a file with size limits.
    
    Args:
        file: File-like object or path
        max_size_mb: Maximum size in MB
    
    Returns:
        dict: Parsed JSON data
    
    Raises:
        ValueError: If file is too large or invalid
        json.JSONDecodeError: If JSON is invalid
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if hasattr(file, 'read'):
        # File-like object
        file.seek(0)
        content = file.read(max_size_bytes + 1)
        if len(content) > max_size_bytes:
            raise ValueError(f"File exceeds maximum size of {max_size_mb}MB")
        file.seek(0)
    else:
        # Assume it's a file path
        file_size = os.path.getsize(file)
        if file_size > max_size_bytes:
            raise ValueError(f"File exceeds maximum size of {max_size_mb}MB")
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read(max_size_bytes + 1)
            if len(content) > max_size_bytes:
                raise ValueError(f"File exceeds maximum size of {max_size_mb}MB")
    
    return json.loads(content)

