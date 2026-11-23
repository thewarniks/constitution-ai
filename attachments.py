"""Turn uploaded files into Claude content blocks.

Ported from the old chat-ui: images are shrunk to fit 2048x2048 and re-encoded
as JPEG (quality scaled down with the image), and .docx files are reduced to
raw text like mammoth.extractRawText did. PDFs go to Claude as-is.
"""

import base64
import io

import docx
from PIL import Image

MAX_IMAGE_SIDE = 2048
MAX_FILE_BYTES = 20 * 1024 * 1024  # keeps a request well under the 32 MB API limit

IMAGE_TYPES = ["png", "jpg", "jpeg", "webp", "gif"]
DOCUMENT_TYPES = ["pdf", "docx", "txt", "md"]
ACCEPTED_TYPES = IMAGE_TYPES + DOCUMENT_TYPES


def _b64(data: bytes) -> str:
    return base64.standard_b64encode(data).decode("utf-8")


def _image_block(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data))
    quality = 0.8
    if img.width > MAX_IMAGE_SIDE or img.height > MAX_IMAGE_SIDE:
        scale = min(MAX_IMAGE_SIDE / img.width, MAX_IMAGE_SIDE / img.height)
        img = img.resize((int(img.width * scale), int(img.height * scale)))
        quality *= scale
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=max(int(quality * 100), 50))
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/jpeg", "data": _b64(buf.getvalue())},
    }


def _text_document(name: str, text: str) -> dict:
    return {
        "type": "document",
        "source": {"type": "text", "media_type": "text/plain", "data": text},
        "title": name,
    }


def extract_text(name: str, data: bytes) -> str:
    """Raw text of a .docx, .md, or .txt file."""
    if name.lower().endswith(".docx"):
        return "\n".join(p.text for p in docx.Document(io.BytesIO(data)).paragraphs)
    return data.decode("utf-8", errors="replace")


def to_content_block(name: str, data: bytes) -> dict:
    """Build the content block for one uploaded file. Raises ValueError if unsupported."""
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"{name} is larger than {MAX_FILE_BYTES // (1024 * 1024)} MB.")
    ext = name.rsplit(".", 1)[-1].lower()
    if ext in IMAGE_TYPES:
        return _image_block(data)
    if ext == "pdf":
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": _b64(data)},
            "title": name,
        }
    if ext in ("docx", "txt", "md"):
        return _text_document(name, extract_text(name, data))
    raise ValueError(f"{name}: unsupported file type.")
