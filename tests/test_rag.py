"""
Tests for Hybrid RAG Engine and Retrieval Quality Metrics.
"""
import pytest
from app.rag.engine import HybridRAGEngine

def test_rag_retrieves_sql_guideline():
    engine = HybridRAGEngine()
    query = "cursor.execute f-string SQL query injection vulnerability"
    results = engine.retrieve(query, top_k=2)

    assert len(results) > 0
    top_doc = results[0]
    assert "SQL" in top_doc["title"]
    assert top_doc["id"] == "KB-SEC-001"
    assert top_doc["similarity_score"] > 0.3

def test_rag_retrieves_resource_leak_guideline():
    engine = HybridRAGEngine()
    query = "open file descriptor memory leak context manager with statement"
    results = engine.retrieve(query, top_k=2)

    assert len(results) > 0
    top_doc = results[0]
    assert "Resource" in top_doc["title"] or "KB-REL-002" in top_doc["id"]

def test_rag_evaluation_metrics():
    engine = HybridRAGEngine()
    query = "SQL query injection defense"
    results = engine.retrieve(query, top_k=2)
    metrics = engine.evaluate_retrieval_metrics(query, results, expected_tags=["sql", "injection"])

    assert metrics["context_relevance"] > 0.0
    assert metrics["retrieval_precision"] >= 0.5
    assert metrics["groundedness"] > 0.0
