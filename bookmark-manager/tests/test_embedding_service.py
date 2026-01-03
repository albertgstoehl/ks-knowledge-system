import pytest
from src.services.embedding_service import EmbeddingService

def test_embedding_generation():
    """Test embedding generation from text"""
    service = EmbeddingService()
    text = "This is a test article about technology"

    embedding = service.generate_embedding(text)

    assert len(embedding) == service.embedding_dimension
    assert all(isinstance(x, float) for x in embedding)

def test_embedding_similarity():
    """Test embedding similarity calculation"""
    service = EmbeddingService()

    text1 = "Python programming language"
    text2 = "Python coding and development"
    text3 = "Cooking recipes for dinner"

    emb1 = service.generate_embedding(text1)
    emb2 = service.generate_embedding(text2)
    emb3 = service.generate_embedding(text3)

    # Similar texts should have higher similarity
    sim_12 = service.cosine_similarity(emb1, emb2)
    sim_13 = service.cosine_similarity(emb1, emb3)

    assert sim_12 > sim_13

def test_empty_string_input():
    """Test embedding generation with empty string"""
    service = EmbeddingService()
    embedding = service.generate_embedding("")

    # Should return zero vector with correct dimension
    assert len(embedding) == service.embedding_dimension
    assert all(x == 0.0 for x in embedding)

def test_whitespace_only_input():
    """Test embedding generation with whitespace-only string"""
    service = EmbeddingService()
    embedding = service.generate_embedding("   \t\n  ")

    # Should return zero vector with correct dimension
    assert len(embedding) == service.embedding_dimension
    assert all(x == 0.0 for x in embedding)

def test_none_input():
    """Test that None input raises ValueError"""
    service = EmbeddingService()

    with pytest.raises(ValueError, match="Text parameter cannot be None"):
        service.generate_embedding(None)

def test_identical_vectors():
    """Test cosine similarity of identical vectors"""
    service = EmbeddingService()
    text = "Test text"
    emb = service.generate_embedding(text)

    similarity = service.cosine_similarity(emb, emb)

    # Identical vectors should have similarity of 1.0
    assert abs(similarity - 1.0) < 1e-6

def test_zero_vectors():
    """Test cosine similarity of zero vectors"""
    service = EmbeddingService()
    zero_vec = [0.0] * service.embedding_dimension

    similarity = service.cosine_similarity(zero_vec, zero_vec)

    # Zero vectors should have similarity of 0.0
    assert similarity == 0.0

def test_wrong_length_vectors():
    """Test that vectors of different lengths raise ValueError"""
    service = EmbeddingService()
    vec1 = [1.0, 2.0, 3.0]
    vec2 = [1.0, 2.0]

    with pytest.raises(ValueError, match="Vectors must have same length"):
        service.cosine_similarity(vec1, vec2)

def test_none_vector_input():
    """Test that None vectors raise ValueError"""
    service = EmbeddingService()
    vec = [1.0, 2.0, 3.0]

    with pytest.raises(ValueError, match="Vectors cannot be None"):
        service.cosine_similarity(None, vec)

    with pytest.raises(ValueError, match="Vectors cannot be None"):
        service.cosine_similarity(vec, None)

def test_non_list_vector_input():
    """Test that non-list vectors raise ValueError"""
    service = EmbeddingService()
    vec = [1.0, 2.0, 3.0]

    with pytest.raises(ValueError, match="Vectors must be lists"):
        service.cosine_similarity("not a list", vec)

    with pytest.raises(ValueError, match="Vectors must be lists"):
        service.cosine_similarity(vec, (1.0, 2.0, 3.0))

def test_empty_vectors():
    """Test that empty vectors raise ValueError"""
    service = EmbeddingService()

    with pytest.raises(ValueError, match="Vectors cannot be empty"):
        service.cosine_similarity([], [])
