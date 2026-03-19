"""K4 — Vector RAG Agent: Retrieves relevant medical articles.
For the demo, uses simple text matching instead of FAISS to avoid the
sentence-transformers dependency. Can be upgraded to FAISS later."""

import os
from pathlib import Path
from agents.base_agent import BaseAgent


class VectorRAGAgent(BaseAgent):
    name = "VectorRAG"
    layer = "knowledge"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.articles_dir = kwargs.get(
            "articles_dir",
            Path(__file__).parent.parent.parent / "neurohealth_demo" / "data" / "articles"
        )

    def _process(self, state: dict) -> dict:
        symptoms = state.get("extracted_symptoms", [])
        candidates = state.get("candidate_conditions", [])
        query_terms = symptoms.copy()

        # Add condition names as search terms
        for c in candidates[:3]:
            query_terms.append(c.get("name", "").lower())

        # Simple keyword search across article files
        results = []
        articles_path = self.articles_dir
        if not articles_path.exists():
            # Try alternative path
            articles_path = Path(__file__).parent.parent / "data" / "articles"

        if articles_path.exists():
            for article_file in articles_path.glob("*.txt"):
                text = article_file.read_text(encoding="utf-8")
                text_lower = text.lower()

                # Score = how many query terms appear in the article
                score = sum(1 for term in query_terms if term in text_lower)

                if score > 0:
                    # Take first 500 chars as context
                    snippet = text[:500].strip()
                    results.append({
                        "text": snippet,
                        "source": article_file.stem,
                        "score": round(score / max(len(query_terms), 1), 2),
                        "match_method": "keyword",
                    })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "rag_context": results[:5],  # Top 5 articles
        }
