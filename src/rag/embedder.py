import hashlib
from datetime import datetime
from sentence_transformers import SentenceTransformer
import chromadb
from .config import EMBEDDING_MODEL

# ── Singletons
# load once at module level, reuse everywhere.
# SentenceTransformer downloads the model on first run, then loads from cache.
_model = SentenceTransformer(EMBEDDING_MODEL)

# PersistentClient saves to disk — data survives bot restarts.
# Path is relative to wherever you run the bot from (project root).
_client = chromadb.PersistentClient(path="./chroma_store")

def _get_collection():
    """
    Get or create the ChromaDB collection for reels.
    Safe to call repeatedly — never duplicates the collection.
    """
    return _client.get_or_create_collection(name="reels")

def _url_to_id(url: str) -> str:
    """
    Derive a stable, unique ID from a URL using SHA-256 hashing.

    Why not use the URL directly as the ID?
    ChromaDB IDs must be short, filesystem-safe strings.
    URLs contain slashes, colons, and query params that can cause issues.
    A hash is always a fixed-length alphanumeric string — safe and unique.

    hashlib is a Python standard library module — no installation needed.
    sha256(url).hexdigest() gives a 64-character hex string like "a3f9c2...".

    Same URL → same hash every time → upsert overwrites instead of duplicating.
    This is your free duplicate detection.
    """
    return hashlib.sha256(url.encode()).hexdigest()

def store_reel(url: str, summary: str) -> None:
    """
    Embed the summary and store it in ChromaDB with full metadata.

    What gets stored:
    - The vector embedding of the summary (for semantic search)
    - The summary text itself (returned during retrieval)
    - Metadata: url, summary, timestamp (shown to user in search results)

    Calling this twice with the same URL is safe — upsert overwrites silently.
    Think of it like JPA's save() — insert if new, update if ID exists.
    """
    collection = _get_collection()

    # Embed the summary — this is the vector ChromaDB will search against
    vector = _model.encode(summary).tolist()

    # Stable ID derived from the URL — same URL always maps to same ID
    reel_id = _url_to_id(url)

    # ISO 8601 timestamp — e.g. "2026-06-08T10:30:00"
    timestamp = datetime.now().isoformat(timespec="seconds")

    collection.upsert(
        ids=[reel_id],
        documents=[summary],       # the text ChromaDB returns during search
        embeddings=[vector],
        metadatas=[{
            "url": url,
            "summary": summary,
            "timestamp": timestamp,
        }]
    )

    print(f"Stored reel: {url}")

def is_already_indexed(url: str) -> bool:
    """
    Check whether a URL has already been indexed.

    Uses the same hash function as store_reel — same URL → same ID.
    ChromaDB's get() returns an empty results dict if the ID doesn't exist,
    so we check whether the returned ids list is non-empty.

    We'll call this in Level 6 before downloading — no point re-downloading
    and re-analyzing a reel that's already in the store.
    """
    collection = _get_collection()
    reel_id = _url_to_id(url)

    results = collection.get(ids=[reel_id])
    return len(results["ids"]) > 0

