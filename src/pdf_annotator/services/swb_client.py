"""
Library catalog search for PDF Annotator.

Wraps the `swb` package's Python API (not its CLI) to search German
library union catalogs (SWB/K10plus/DNB/...) for text selected in the
PDF viewer. Uses the official public endpoint — no configuration or
API key required.
"""

import requests

from pdf_annotator.utils.logger import get_logger

logger = get_logger(__name__)


class SWBSearchError(Exception):
    """Raised when the library catalog search fails."""


def search_books(query: str, max_results: int = 20) -> list[dict]:
    """
    Search library catalogs for the given query.

    Args:
        query: Free-text search query (e.g. text selected in the PDF viewer)
        max_results: Maximum number of results to return (default: 20)

    Raises:
        SWBSearchError: If the underlying API request fails

    Returns:
        List of dicts with title, author, year, isbn, link
    """
    from swb.api import SWBClient
    from swb.models import SearchIndex
    from swb.profiles import get_profile

    try:
        # Default "swb" profile only covers the regional SWB network
        # (Baden-Württemberg/Saarland/Sachsen). Use the broader K10plus
        # union catalog so results aren't missing books held elsewhere.
        with SWBClient(base_url=get_profile("k10plus").url) as client:
            response = client.search(
                query, index=SearchIndex.ALL, maximum_records=max_results
            )
    except (requests.RequestException, ValueError) as e:
        logger.error("SWB search failed: %s", e)
        raise SWBSearchError("Fehler bei der Bibliothekssuche") from e

    return [
        {
            "title": result.title,
            "author": result.author,
            "year": result.year,
            "isbn": result.isbn,
            "link": result.link,
        }
        for result in response.results
    ]
