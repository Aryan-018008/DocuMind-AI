
import re
import unicodedata

import faiss
import numpy as np

from services.embedding_service import generate_embeddings


class VectorStore:
    STOP_WORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been",
        "being", "of", "to", "in", "on", "at", "by", "for", "from",
        "and", "or", "but", "with", "as", "into", "about", "this",
        "that", "these", "those", "it", "its", "i", "we", "you",
        "he", "she", "they", "them", "my", "your", "our", "their",
        "what", "which", "who", "when", "where", "why", "how",
        "do", "does", "did", "can", "could", "would", "should",
        "please", "tell", "me", "explain", "describe", "show",
        "find", "give", "list", "document", "pdf", "file",
    }

    def __init__(self):
        self.index = None
        self.chunks = []
        self.dimension = None

    @staticmethod
    def _normalize(text):
        text = unicodedata.normalize("NFKC", str(text))
        text = (
            text.replace("\u019f", "ti")
                .replace("\u0275", "ti")
                .replace("\u03b8", "ti")
                .replace("\u03f4", "ti")
        )
        return text.lower()

    # @classmethod
    # def _tokenize(cls, text):
    #     text = cls._normalize(text)
    #     tokens = re.findall(r"[a-z0-9]+", text)

    #     # Light normalization: allow common word-form matches without
    #     # relying on PDF-specific vocabulary or external NLP packages.
    #     normalized = set()

    #     for token in tokens:
    #         if token in cls.STOP_WORDS:
    #             continue

    #         normalized.add(token)

    #         if len(token) > 5 and token.endswith("ing"):
    #             normalized.add(token[:-3])
    #             normalized.add(token[:-3] + "e")

    #         elif len(token) > 4 and token.endswith("ies"):
    #             normalized.add(token[:-3] + "y")

    #         elif len(token) > 4 and token.endswith("es"):
    #             normalized.add(token[:-2])

    #         elif len(token) > 3 and token.endswith("s"):
    #             normalized.add(token[:-1])

    #         elif len(token) > 4 and token.endswith("ed"):
    #             normalized.add(token[:-2])

    #     return normalized

    
    @classmethod
    def _tokenize(cls, text):
        text = cls._normalize(text)
        tokens = re.findall(r"[a-z0-9]+", text)

        # Keep one normalized token per original word.
        normalized = set()

        for token in tokens:
            if token in cls.STOP_WORDS:
                continue

            # Normalize common plural forms without adding extra tokens.
            if len(token) > 4 and token.endswith("ies"):
                token = token[:-3] + "y"
            elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
                token = token[:-1]

            normalized.add(token)

        return normalized


    def build_index(self, chunks):
        if not isinstance(chunks, list) or not chunks:
            raise ValueError("Provide a non-empty list of chunks.")

        valid_chunks = []

        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue

            text = chunk.get("text")

            if not isinstance(text, str) or not text.strip():
                continue

            valid_chunks.append(dict(chunk))

        if not valid_chunks:
            raise ValueError("No valid text chunks were provided.")

        texts = [chunk["text"] for chunk in valid_chunks]
        embeddings = np.asarray(
            generate_embeddings(texts),
            dtype=np.float32,
        )

        if embeddings.ndim != 2:
            raise ValueError("Embeddings must be a 2D array.")

        if embeddings.shape[0] != len(valid_chunks):
            raise ValueError("Embedding count does not match chunk count.")

        if embeddings.shape[1] == 0:
            raise ValueError("Embedding dimension cannot be zero.")

        if not np.isfinite(embeddings).all():
            raise ValueError("Embeddings contain invalid numeric values.")

        # Cosine similarity is computed using normalized vectors.
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)

        if np.any(norms == 0):
            raise ValueError("A chunk produced a zero-length embedding.")

        embeddings = np.ascontiguousarray(
            embeddings / norms,
            dtype=np.float32,
        )

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        self.chunks = valid_chunks

        return len(self.chunks)

    def search(self, query, top_k=3):
        if self.index is None or not self.chunks:
            raise RuntimeError("Build the vector index before searching.")

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1:
            raise ValueError("top_k must be a positive integer.")

        query_embedding = np.asarray(
            generate_embeddings([query.strip()]),
            dtype=np.float32,
        )

        if query_embedding.ndim != 2:
            raise ValueError("Query embedding must be a 2D array.")

        if query_embedding.shape != (1, self.dimension):
            raise ValueError("Query embedding dimension does not match index.")

        if not np.isfinite(query_embedding).all():
            raise ValueError("Query embedding contains invalid values.")

        query_norm = np.linalg.norm(query_embedding)

        if query_norm == 0:
            raise ValueError("Query embedding has zero length.")

        query_embedding = np.ascontiguousarray(
            query_embedding / query_norm,
            dtype=np.float32,
        )

        # Retrieve every indexed chunk so hybrid ranking can compare
        # semantic similarity and lexical relevance consistently.
        similarities, indices = self.index.search(
            query_embedding,
            len(self.chunks),
        )

        query_tokens = self._tokenize(query)
        results = []

        for semantic_score, idx in zip(
            similarities[0],
            indices[0],
        ):
            if idx < 0:
                continue

            chunk = self.chunks[int(idx)]
            chunk_tokens = self._tokenize(chunk["text"])

            matched_keywords = sorted(query_tokens & chunk_tokens)

            if query_tokens:
                keyword_score = (
                    len(matched_keywords) / len(query_tokens)
                )
            else:
                keyword_score = 0.0

            # Ignore negative cosine scores when combining with keyword
            # relevance; preserve the raw score for diagnostics.
            semantic_component = max(float(semantic_score), 0.0)

            combined_score = (
                0.75 * semantic_component
                + 0.25 * keyword_score
            )

            results.append({
                **chunk,
                "similarity_score": float(semantic_score),
                "keyword_score": float(keyword_score),
                "combined_score": float(combined_score),
                "matched_keywords": matched_keywords,
            })

        results.sort(
            key=lambda item: item["combined_score"],
            reverse=True,
        )

        return results[:min(top_k, len(results))]
