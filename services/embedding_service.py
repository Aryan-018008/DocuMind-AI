
from sentence_transformers import SentenceTransformer


# Load the embedding model
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None


def get_embedding_model():
    """Load the model once and reuse it."""
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def generate_embeddings(texts):
    """
    Convert a list of text chunks into numerical vectors.

    Args:
        texts: List of strings.

    Returns:
        A NumPy array containing the embeddings.
    """
    if not texts:
        raise ValueError("Cannot generate embeddings for empty text.")

    if not all(isinstance(text, str) and text.strip() for text in texts):
        raise ValueError("Every item must contain non-empty text.")

    model = get_embedding_model()

    embeddings = model.encode(
    texts,
    batch_size=8,
    convert_to_numpy=True,
    normalize_embeddings=True,
    show_progress_bar=False
)

    return embeddings
