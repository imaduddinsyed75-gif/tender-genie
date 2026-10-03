from pathlib import Path

import agents.memory as memory


def test_seed_ingestion_and_similarity_query(tmp_path: Path, monkeypatch) -> None:
    seed_source = Path(__file__).parent / "seed_data" / "historical_bids.json"
    seed_path = tmp_path / "historical_bids.json"
    seed_path.write_text(seed_source.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr(memory, "DB_PATH", tmp_path / "chroma_db")
    monkeypatch.setattr(memory, "_client", None)
    monkeypatch.setattr(memory, "_collection", None)
    monkeypatch.setattr(memory, "_embedding_function", None)

    memory.ingest_seed(str(seed_path))
    results = memory.query_similar("firewall installation", k=3)
    won_results = memory.query_similar("firewall installation", k=3, only_won=True)

    assert len(results) == 3
    assert all("distance" in result for result in results)
    assert all({"item", "category", "notes"} <= result.keys() for result in results)
    assert all(result["outcome"] == "won" for result in won_results)
