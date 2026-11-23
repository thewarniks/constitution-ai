"""Reference datasets: text files the chatbot searches before answering.

Files live in ./datasets (upload them from the web page or copy them in).
Each file is split into chunks, and the chunks most relevant to the user's
question are found with BM25 keyword ranking and passed to the model as
reference passages. No extra libraries or embeddings are needed.
"""

import json
import math
import re
from collections import Counter
from pathlib import Path

from werkzeug.utils import secure_filename

from attachments import extract_text

DATASETS_DIR = Path(__file__).parent / "datasets"
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".jsonl", ".docx"}
CHUNK_CHARS = 1200
STOPWORDS = set(
    "a an and are as at be by for from has have i if in is it its of on or that the this to was were will with "
    "my me we you your he she they them their what which who how can do does not no".split()
)

_index_cache: dict[str, tuple[float, "Index"]] = {}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\w+", text.lower()) if t not in STOPWORDS and len(t) > 1]


def _read(path: Path) -> str:
    text = extract_text(path.name, path.read_bytes())
    if path.suffix.lower() in (".json", ".jsonl"):
        # Pretty-print JSON so records split into readable chunks.
        try:
            data = json.loads(text)
            text = "\n\n".join(json.dumps(r, ensure_ascii=False) for r in data) if isinstance(data, list) \
                else json.dumps(data, ensure_ascii=False, indent=1)
        except json.JSONDecodeError:
            pass  # JSON Lines or not JSON at all: keep line by line
    return text


def _chunk(text: str) -> list[str]:
    """Split on blank lines (or single lines for CSV-like files), then pack up to CHUNK_CHARS."""
    pieces = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(pieces) <= 1:
        pieces = [p.strip() for p in text.splitlines() if p.strip()]
    chunks, current = [], ""
    for piece in pieces:
        while len(piece) > CHUNK_CHARS:  # a single huge paragraph
            chunks.append(piece[:CHUNK_CHARS])
            piece = piece[CHUNK_CHARS:]
        if current and len(current) + len(piece) + 2 > CHUNK_CHARS:
            chunks.append(current)
            current = ""
        current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


class Index:
    """BM25 over one dataset file's chunks."""

    k1, b = 1.5, 0.75

    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self.tfs = [Counter(_tokens(c)) for c in chunks]
        self.lengths = [sum(tf.values()) for tf in self.tfs]
        self.avg_len = (sum(self.lengths) / len(self.lengths)) if chunks else 0
        df = Counter(term for tf in self.tfs for term in tf)
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def scores(self, query_terms: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tfs, self.lengths):
            s = 0.0
            for t in query_terms:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * length / self.avg_len))
            out.append(s)
        return out


def _path(name: str) -> Path:
    path = DATASETS_DIR / secure_filename(name)
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {name}")
    return path


def _index(path: Path) -> Index:
    mtime = path.stat().st_mtime
    cached = _index_cache.get(path.name)
    if cached and cached[0] == mtime:
        return cached[1]
    index = Index(_chunk(_read(path)))
    _index_cache[path.name] = (mtime, index)
    return index


def list_datasets() -> list[dict]:
    DATASETS_DIR.mkdir(exist_ok=True)
    out = []
    for path in sorted(DATASETS_DIR.iterdir()):
        if path.suffix.lower() in ALLOWED_EXTENSIONS and path.is_file():
            try:
                chunks = len(_index(path).chunks)
            except Exception:
                chunks = 0
            out.append({"name": path.name, "size": path.stat().st_size, "chunks": chunks})
    return out


def save_dataset(filename: str, data: bytes) -> str:
    DATASETS_DIR.mkdir(exist_ok=True)
    path = _path(filename)
    path.write_bytes(data)
    _index(path)  # fail now, not mid-chat, if the file can't be read
    return path.name


def delete_dataset(name: str) -> None:
    path = _path(name)
    path.unlink(missing_ok=True)
    _index_cache.pop(path.name, None)


def search(query: str, names: list[str], top_k: int = 5) -> list[dict]:
    """The top_k most relevant chunks across the chosen datasets."""
    terms = _tokens(query)
    if not terms:
        return []
    hits = []
    for name in names:
        try:
            path = _path(name)
            if not path.exists():
                continue
            index = _index(path)
        except (ValueError, OSError):
            continue
        for i, score in enumerate(index.scores(terms)):
            if score > 0:
                hits.append({"dataset": path.name, "chunk": i + 1, "score": score, "text": index.chunks[i]})
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits[:top_k]
