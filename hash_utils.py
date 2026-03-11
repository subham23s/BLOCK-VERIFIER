import hashlib


def generate_file_hash(file_path: str) -> str:
    """Generate SHA-256 hash from a file path."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(4096):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_bytes_hash(data: bytes) -> str:
    """Generate SHA-256 hash from raw bytes (e.g., uploaded file in memory)."""
    sha256 = hashlib.sha256()
    sha256.update(data)
    return sha256.hexdigest()


def detect_file_type(filename: str) -> str:
    """Detect file category from extension."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    image_exts = {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "svg"}
    doc_exts = {"pdf", "docx", "doc", "txt", "csv", "xlsx", "pptx"}
    model_exts = {"joblib", "pkl", "h5", "pt", "pth", "onnx"}
    if ext in image_exts:
        return "image"
    elif ext in doc_exts:
        return "document"
    elif ext in model_exts:
        return "ml_model"
    return "file"
