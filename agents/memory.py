import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "historical_bids"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client: Any = None
_embedding_function: Any = None
_collection: Any = None


def _get_embedding_function() -> Any:
    global _embedding_function
    if _embedding_function is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

        _embedding_function = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _embedding_function


def _get_collection() -> Any:
    global _client, _collection
    if _collection is None:
        import chromadb

        _client = chromadb.PersistentClient(path=str(DB_PATH))
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_get_embedding_function(),
        )
    return _collection


def ingest_seed(path: str = "agents/seed_data/historical_bids.json") -> None:
    collection = _get_collection()
    if collection.count() > 0:
        return

    seed_path = Path(path)
    if not seed_path.is_absolute():
        seed_path = PROJECT_ROOT / seed_path
    records = json.loads(seed_path.read_text(encoding="utf-8"))

    collection.add(
        ids=[record["id"] for record in records],
        documents=[
            f"{record['item']} {record['category']} {record['notes']}"
            for record in records
        ],
        metadatas=[
            dict(record)
            for record in records
        ],
    )


def query_similar(text: str, k: int = 5, only_won: bool = False) -> list[dict]:
    collection = _get_collection()
    query = {"query_texts": [text], "n_results": k}
    if only_won:
        query["where"] = {"outcome": "won"}

    result = collection.query(**query)
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]
    return [
        {**metadata, "distance": distance}
        for metadata, distance in zip(metadatas, distances)
    ]
