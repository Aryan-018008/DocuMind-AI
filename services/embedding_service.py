
# from sentence_transformers import SentenceTransformer


# # Load the embedding model
# MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# _model = None


# def get_embedding_model():
#     """Load the model once and reuse it."""
#     global _model

#     if _model is None:
#         _model = SentenceTransformer(MODEL_NAME)

#     return _model


# def generate_embeddings(texts):
#     """
#     Convert a list of text chunks into numerical vectors.

#     Args:
#         texts: List of strings.

#     Returns:
#         A NumPy array containing the embeddings.
#     """
#     if not texts:
#         raise ValueError("Cannot generate embeddings for empty text.")

#     if not all(isinstance(text, str) and text.strip() for text in texts):
#         raise ValueError("Every item must contain non-empty text.")

#     model = get_embedding_model()

#     embeddings = model.encode(
#     texts,
#     batch_size=8,
#     convert_to_numpy=True,
#     normalize_embeddings=True,
#     show_progress_bar=False
# )

#     return embeddings

from fastembed import TextEmbedding
import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    """Load the FastEmbed model once and reuse it."""
    global _model

    if _model is None:
        _model = TextEmbedding(
            model_name=MODEL_NAME,
            threads=1,
        )

    return _model


def generate_embeddings(texts):
    """Convert text chunks into normalized NumPy embeddings."""
    if not texts:
        raise ValueError("Cannot generate embeddings for empty text.")

    if not all(
        isinstance(text, str) and text.strip()
        for text in texts
    ):
        raise ValueError(
            "Every item must contain non-empty text."
        )

    model = get_embedding_model()

    embeddings = list(
        model.embed(
            texts,
            batch_size=8,
        )
    )

    result = np.asarray(embeddings, dtype=np.float32)

    if result.ndim != 2 or not np.isfinite(result).all():
        raise ValueError("Invalid embeddings generated.")

    # Normalize vectors for cosine similarity with FAISS.
    norms = np.linalg.norm(result, axis=1, keepdims=True)

    if np.any(norms == 0):
        raise ValueError("A chunk produced a zero-length embedding.")

    return np.ascontiguousarray(result / norms, dtype=np.float32)
