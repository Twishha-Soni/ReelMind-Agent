from dataclasses import dataclass
from .config import TOP_K_RESULTS, EMBEDDING_MODEL
from sentence_transformers import SentenceTransformer
import chromadb

# Same singleton pattern as embedder.py —
# must use the same model as ingest time so vectors are in the same space
_model = SentenceTransformer(EMBEDDING_MODEL)
_client = chromadb.PersistentClient(path="./chroma_store")

def _get_collection():
    return _client.get_or_create_collection(name="reels")

@dataclass
class RetrievedReel:
    """
    A single search result — everything needed to show the user a match.
    Mirrors DocIQ's RetrievedChunk but carries reel-specific metadata.
    """
    url: str
    summary: str
    timestamp: str
    similarity: float     # 1.0 = identical meaning, 0.0 = unrelated


def search_reel(query: str, top_k: int = TOP_K_RESULTS) -> list[RetrievedReel]:
    """
    Embed the query and find the most semantically similar reels in ChromaDB.
    Returns results sorted by similarity, highest first.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return[]
    
    query_vector = _model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    # Unwrap the batch layer — we sent one query so we want index 0
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved=[]
    for doc, meta, dist in zip(documents, metadatas, distances):
        retrieved.append(RetrievedReel(
            url=meta["url"],
            summary=meta["summary"],
            timestamp=meta["timestamp"],
            similarity=round(1-dist,4)
        ))

    retrieved.sort(key=lambda r: r.similarity,reverse=True)
    return retrieved