
# import faiss
# import numpy as np
# import re

# from services.embedding_service import generate_embeddings


# class VectorStore:
#     """Store and search PDF text chunks using FAISS."""

#     def __init__(self):
#         self.index = None
#         self.chunks = []

#     def build_index(self, chunks):
#         """Generate embeddings and build a FAISS index."""

#         if not chunks:
#             raise ValueError("Cannot build an index without chunks.")

#         texts = [chunk["text"] for chunk in chunks]

#         embeddings = generate_embeddings(texts)
#         embeddings = np.asarray(embeddings, dtype=np.float32)

#         if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
#             raise ValueError("Invalid embedding dimensions.")

#         # Normalized vectors + inner product = cosine similarity
#         index = faiss.IndexFlatIP(embeddings.shape[1])
#         index.add(embeddings)

#         self.index = index
#         self.chunks = [dict(chunk) for chunk in chunks]

#         return index.ntotal

#     def search(self, query, top_k=3):
#         """Search chunks using semantic and keyword relevance."""

#         if self.index is None or not self.chunks:
#             raise ValueError("Build the vector index before searching.")

#         if not isinstance(query, str) or not query.strip():
#             raise ValueError("Search query cannot be empty.")

#         if (
#             not isinstance(top_k, int)
#             or isinstance(top_k, bool)
#             or top_k < 1
#         ):
#             raise ValueError("top_k must be a positive integer.")

#         # 1. Semantic search across all chunks
#         query_embedding = generate_embeddings([query])
#         query_embedding = np.asarray(
#             query_embedding, dtype=np.float32
#         )

#         scores, indices = self.index.search(
#             query_embedding, self.index.ntotal
#         )

#         semantic_scores = {
#             int(idx): float(score)
#             for score, idx in zip(scores[0], indices[0])
#             if idx >= 0
#         }

#         # 2. Remove common words from the query
#         stop_words = {
#             "what", "is", "the", "a", "an", "on", "in",
#             "of", "to", "and", "for", "from", "listed",
#             "tell", "me", "please", "where"
#         }

#         query_terms = set(
#             re.findall(r"\b\w+\b", query.lower())
#         ) - stop_words

#         results = []

#         # 3. Combine semantic, keyword, and field relevance
#         for idx, chunk in enumerate(self.chunks):
#             text = chunk["text"].lower()

#             text_terms = set(
#                 re.findall(r"\b\w+\b", text)
#             )

#             matched_terms = query_terms & text_terms

#             keyword_score = (
#                 len(matched_terms) / len(query_terms)
#                 if query_terms else 0.0
#             )

#             semantic_score = semantic_scores.get(idx, 0.0)

#             # Give extra priority to matching field labels
#             # normalized_text = re.sub(r"\s+", " ", text)
#             # normalized_query = query.lower()

#             # field_boost = 0.0

#             # if "venue" in normalized_query:
#             #     if re.search(
#             #         r"\bexam\s+venue\b",
#             #         normalized_text
#             #     ):
#             #         field_boost = 0.5

#             # Give priority to chunks containing an actual venue field.(Particular Target)
#             normalized_text = re.sub(r"\s+", " ", text)
#             normalized_query = query.lower()

#             field_boost = 0.0

#             if "venue" in normalized_query:
#              venue_pattern = (
#                   r"\bexam\s+venue\s*:?\s*"
#                   r"(?!listed\b|is\b|was\b|will\b)"
#                   r"[A-Za-z0-9]"
#                )

#             if re.search(venue_pattern, normalized_text):
#              field_boost = 0.5

#             combined_score = (
#                 0.7 * semantic_score
#                 + 0.3 * keyword_score
#                 + field_boost
#             )

#             result = dict(chunk)
#             result["similarity_score"] = semantic_score
#             result["keyword_score"] = keyword_score
#             result["field_boost"] = field_boost
#             result["combined_score"] = combined_score
            

#             results.append(result)

#         # 4. Highest combined score first
#         results.sort(
#             key=lambda item: item["combined_score"],
#             reverse=True
#         )

#         return results[:min(top_k, len(results))]


import re
import unicodedata

import faiss
import numpy as np

from services.embedding_service import generate_embeddings


class VectorStore:
    """Store and retrieve PDF chunks using semantic and keyword relevance."""

    STOP_WORDS = {
        "what", "is", "the", "a", "an", "on", "in", "of",
        "to", "and", "for", "from", "tell", "me", "please",
        "where", "when", "who", "which", "how", "does",
        "do", "can", "could", "would", "should", "my",
        "your", "their", "this", "that", "be", "are",
        "was", "were", "has", "have", "had", "listed"
    }

    def __init__(self):
        self.index = None
        self.chunks = []

     
            
    @staticmethod
    def _tokenize(text):
        """Normalize PDF text and extract searchable keywords."""
        text = unicodedata.normalize("NFKC", text)

        # Repair the exact PDF extraction artifact.
        text = text.replace("\u019f", "ti")
        text = text.replace("\u0275", "ti")

        text = text.lower()

        return set(re.findall(r"[a-z0-9]+", text))


    def build_index(self, chunks):
        """Generate embeddings and build a FAISS index."""
        if not chunks:
            raise ValueError("Cannot build an index without chunks.")

        texts = [chunk.get("text", "") for chunk in chunks]

        if any(
            not isinstance(text, str) or not text.strip()
            for text in texts
        ):
            raise ValueError(
                "Every chunk must contain non-empty text."
            )

        embeddings = generate_embeddings(texts)
        embeddings = np.asarray(embeddings, dtype=np.float32)

        if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
            raise ValueError("Invalid embedding dimensions.")

        if not np.isfinite(embeddings).all():
            raise ValueError("Embeddings contain invalid numeric values.")

        # Inner product represents cosine similarity when vectors
        # are normalized by the embedding service.
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        self.index = index
        self.chunks = [dict(chunk) for chunk in chunks]

        return index.ntotal

    def search(self, query, top_k=3):
        """Rank chunks using semantic similarity and keyword overlap."""
        if self.index is None or not self.chunks:
            raise ValueError(
                "Build the vector index before searching."
            )

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query cannot be empty.")

        if (
            not isinstance(top_k, int)
            or isinstance(top_k, bool)
            or top_k < 1
        ):
            raise ValueError("top_k must be a positive integer.")

        # 1. Calculate semantic similarity for all chunks.
        query_embedding = generate_embeddings([query])
        query_embedding = np.asarray(
            query_embedding, dtype=np.float32
        )

        scores, indices = self.index.search(
            query_embedding, self.index.ntotal
        )

        semantic_scores = {
            int(idx): float(score)
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        }

        # 2. Tokenize the query and remove common question words.
        query_tokens = self._tokenize(query) - self.STOP_WORDS
        print("\nQuery tokens used:", sorted(query_tokens))

        results = []

        # 3. Calculate keyword and combined relevance scores.
        for idx, chunk in enumerate(self.chunks):
            chunk_tokens = self._tokenize(chunk["text"])
            matched_tokens = query_tokens & chunk_tokens
            print(f"Chunk {idx} | Matched: {sorted(matched_tokens)}")

            keyword_score = (
                len(matched_tokens) / len(query_tokens)
                if query_tokens else 0.0
            )

            semantic_score = semantic_scores.get(idx, 0.0)

            combined_score = (
                0.7 * semantic_score
                + 0.3 * keyword_score
            )

            result = dict(chunk)
            result["similarity_score"] = semantic_score
            result["keyword_score"] = keyword_score
            result["combined_score"] = combined_score
            result["matched_keywords"] = sorted(matched_tokens)

            results.append(result)

        # 4. Return the highest-ranked chunks first.
        results.sort(
            key=lambda item: item["combined_score"],
            reverse=True
        )

        return results[:min(top_k, len(results))]
