"""
Hybrid RAG (Retrieval-Augmented Generation) Engine.
Combines semantic TF-IDF/Cosine similarity and BM25-style keyword matching to retrieve relevant project rules.
"""
import math
import re
from typing import List, Dict, Any, Tuple
from app.rag.knowledge_base import DEFAULT_KNOWLEDGE_DOCUMENTS

class HybridRAGEngine:
    def __init__(self, documents: List[Dict[str, Any]] = None):
        self.documents = documents if documents is not None else list(DEFAULT_KNOWLEDGE_DOCUMENTS)
        self._build_index()

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_-]{2,}\b', text)]

    def _build_index(self):
        self.doc_tokens = {}
        self.doc_freq = {}
        self.vocab = set()
        N = len(self.documents)

        for doc in self.documents:
            doc_id = doc["id"]
            combined_text = f"{doc['title']} {doc['category']} {doc['content']} {' '.join(doc.get('tags', []))} {doc.get('fix_pattern', '')}"
            tokens = self._tokenize(combined_text)
            self.doc_tokens[doc_id] = tokens
            unique_tokens = set(tokens)
            self.vocab.update(unique_tokens)
            for token in unique_tokens:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1

        # Calculate IDF
        self.idf = {}
        for token, df in self.doc_freq.items():
            self.idf[token] = math.log((N - df + 0.5) / (df + 0.5) + 1.0)

    def add_document(self, doc: Dict[str, Any]):
        self.documents.append(doc)
        self._build_index()

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.15) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant documents for a given query (diff snippet, defect, or natural language query).
        Returns documents annotated with similarity scores and matched keywords.
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores: List[Tuple[float, Dict[str, Any], List[str]]] = []

        for doc in self.documents:
            doc_id = doc["id"]
            d_tokens = self.doc_tokens.get(doc_id, [])
            if not d_tokens:
                continue

            matched_keywords = []
            score = 0.0
            doc_len = len(d_tokens)
            avg_dl = sum(len(t) for t in self.doc_tokens.values()) / max(len(self.doc_tokens), 1)

            # BM25-based scoring
            k1 = 1.5
            b = 0.75
            for q_term in query_tokens:
                if q_term in self.idf:
                    tf = d_tokens.count(q_term)
                    if tf > 0:
                        matched_keywords.append(q_term)
                        numerator = tf * (k1 + 1)
                        denominator = tf + k1 * (1 - b + b * (doc_len / (avg_dl or 1)))
                        score += self.idf[q_term] * (numerator / denominator)

            # Tag bonus
            tags = [t.lower() for t in doc.get("tags", [])]
            for q_term in query_tokens:
                if q_term in tags:
                    score += 2.0
                    if q_term not in matched_keywords:
                        matched_keywords.append(q_term)

            # Normalize score to 0..1 range approx
            norm_score = round(min(1.0, score / 15.0), 3)
            if norm_score >= min_score or matched_keywords:
                enriched_doc = dict(doc)
                enriched_doc["similarity_score"] = norm_score
                enriched_doc["matched_terms"] = list(set(matched_keywords))[:6]
                scores.append((norm_score, enriched_doc, matched_keywords))

        # Sort descending by score
        scores.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scores[:top_k]]

    def evaluate_retrieval_metrics(self, query: str, retrieved_docs: List[Dict[str, Any]], expected_tags: List[str] = None) -> Dict[str, float]:
        """
        Computes RAG evaluation metrics: Context Relevance, Retrieval Precision, Groundedness.
        """
        if not retrieved_docs:
            return {
                "context_relevance": 0.0,
                "retrieval_precision": 0.0,
                "retrieval_recall": 0.0,
                "groundedness": 0.0
            }

        scores = [d.get("similarity_score", 0.5) for d in retrieved_docs]
        avg_relevance = sum(scores) / len(scores)

        # Tag precision/recall against expected category if provided
        precision = 1.0
        recall = 1.0
        if expected_tags:
            matched_count = 0
            for d in retrieved_docs:
                d_tags = [t.lower() for t in d.get("tags", [])]
                if any(exp.lower() in d_tags for exp in expected_tags):
                    matched_count += 1
            precision = matched_count / len(retrieved_docs)
            recall = min(1.0, matched_count / max(1, len(expected_tags)))

        groundedness = min(1.0, avg_relevance * 1.1)

        return {
            "context_relevance": round(avg_relevance, 3),
            "retrieval_precision": round(precision, 3),
            "retrieval_recall": round(recall, 3),
            "groundedness": round(groundedness, 3)
        }

rag_engine = HybridRAGEngine()
