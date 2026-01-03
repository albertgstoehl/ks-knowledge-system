# tests/test_paper_detection.py
import pytest
from src.services.paper_detection import is_academic_url, extract_doi

class TestIsAcademicUrl:
    def test_arxiv(self):
        assert is_academic_url("https://arxiv.org/abs/2301.00001") is True

    def test_doi_org(self):
        assert is_academic_url("https://doi.org/10.1000/xyz123") is True

    def test_pubmed(self):
        assert is_academic_url("https://pubmed.ncbi.nlm.nih.gov/12345678/") is True

    def test_ieee(self):
        assert is_academic_url("https://ieeexplore.ieee.org/document/123456") is True

    def test_acm(self):
        assert is_academic_url("https://dl.acm.org/doi/10.1145/123456") is True

    def test_regular_website(self):
        assert is_academic_url("https://github.com/user/repo") is False

    def test_blog(self):
        assert is_academic_url("https://medium.com/some-article") is False

    def test_youtube(self):
        assert is_academic_url("https://youtube.com/watch?v=abc123") is False


class TestExtractDoi:
    def test_doi_org_url(self):
        assert extract_doi("https://doi.org/10.1000/xyz123") == "10.1000/xyz123"

    def test_dx_doi_org_url(self):
        assert extract_doi("https://dx.doi.org/10.1234/test") == "10.1234/test"

    def test_arxiv_url(self):
        # arxiv has DOIs like 10.48550/arXiv.2301.00001
        doi = extract_doi("https://arxiv.org/abs/2301.00001")
        assert doi == "10.48550/arXiv.2301.00001"

    def test_no_doi(self):
        assert extract_doi("https://github.com/user/repo") is None
