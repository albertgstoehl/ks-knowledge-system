"""Paper and academic URL detection utilities."""

import re
from typing import Optional
from urllib.parse import urlparse

ACADEMIC_DOMAINS = [
    # Preprint servers
    "arxiv.org",
    "biorxiv.org",
    "medrxiv.org",
    "ssrn.com",
    "osf.io",
    "zenodo.org",
    "cogprints.org",
    # DOI resolvers
    "doi.org",
    # Databases / indexes
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "europepmc.org",
    "semanticscholar.org",
    "scholar.google.com",
    "core.ac.uk",
    "doaj.org",
    "jstor.org",
    "philpapers.org",
    "repec.org",
    "dblp.dagstuhl.de",
    "inspirehep.net",
    "citeseerx.ist.psu.edu",
    "scienceopen.com",
    # Publishers
    "sciencedirect.com",
    "springer.com",
    "springerlink.com",
    "link.springer.com",
    "nature.com",
    "wiley.com",
    "onlinelibrary.wiley.com",
    "tandfonline.com",
    "sagepub.com",
    "cambridge.org",
    "academic.oup.com",
    "oup.com",
    "plos.org",
    "frontiersin.org",
    "mdpi.com",
    "hindawi.com",
    "bioone.org",
    "ingentaconnect.com",
    "muse.jhu.edu",
    "rsc.org",
    # Tech/CS specific
    "ieee.org",
    "ieeexplore.ieee.org",
    "acm.org",
    "dl.acm.org",
    "portal.acm.org",
    "aclanthology.org",
    # Government/institutional
    "nih.gov",
    "eric.ed.gov",
    "nber.org",
    "osti.gov",
]


def is_academic_url(url: str) -> bool:
    """Check if URL is from an academic domain."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace("www.", "")

        for academic_domain in ACADEMIC_DOMAINS:
            if domain == academic_domain or domain.endswith("." + academic_domain):
                return True
        return False
    except Exception:
        return False


def extract_doi(url: str) -> Optional[str]:
    """Extract DOI from URL if possible."""
    try:
        # Direct DOI URL: doi.org/10.xxx or dx.doi.org/10.xxx
        doi_match = re.search(r'(?:doi\.org|dx\.doi\.org)/(.+?)(?:\?|#|$)', url)
        if doi_match:
            return doi_match.group(1).rstrip('/')

        # ArXiv: convert to DOI format
        arxiv_match = re.search(r'arxiv\.org/abs/(\d+\.\d+)', url)
        if arxiv_match:
            return f"10.48550/arXiv.{arxiv_match.group(1)}"

        return None
    except Exception:
        return None
