"""
Tests for the SWB library catalog search feature.

Service tests mock swb.api.SWBClient directly (no real network calls).
Route tests patch the service function to avoid re-mocking SDK internals.
"""

import requests

from pdf_annotator.services.swb_client import SWBSearchError, search_books


class TestSearchBooks:
    """Test search_books() mapping and error handling."""

    def test_maps_results_to_dicts(self, monkeypatch):
        from swb.models import SearchResponse, SearchResult

        fake_results = [
            SearchResult(
                title="Der Zauberberg",
                author="Thomas Mann",
                year="1924",
                isbn="978-3-10-048472-0",
                link="https://example.org/opac/12345",
            )
        ]

        class FakeSWBClient:
            def __init__(self, base_url=None):
                self.base_url = base_url

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def search(self, query, **kwargs):
                assert query == "Zauberberg"
                return SearchResponse(total_results=1, results=fake_results)

        import swb.api

        monkeypatch.setattr(swb.api, "SWBClient", FakeSWBClient)

        results = search_books("Zauberberg")

        assert results == [
            {
                "title": "Der Zauberberg",
                "author": "Thomas Mann",
                "year": "1924",
                "isbn": "978-3-10-048472-0",
                "link": "https://example.org/opac/12345",
            }
        ]

    def test_empty_results(self, monkeypatch):
        from swb.models import SearchResponse

        class FakeSWBClient:
            def __init__(self, base_url=None):
                self.base_url = base_url

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def search(self, query, **kwargs):
                return SearchResponse(total_results=0, results=[])

        import swb.api

        monkeypatch.setattr(swb.api, "SWBClient", FakeSWBClient)

        assert search_books("nonexistent-query-xyz") == []

    def test_network_error_wrapped(self, monkeypatch):
        class FakeSWBClient:
            def __init__(self, base_url=None):
                self.base_url = base_url

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def search(self, query, **kwargs):
                raise requests.ConnectionError("boom")

        import swb.api

        monkeypatch.setattr(swb.api, "SWBClient", FakeSWBClient)

        try:
            search_books("query")
            raise AssertionError("expected SWBSearchError")
        except SWBSearchError:
            pass


class TestSwbSearchRoute:
    """Test the /swb/search endpoint."""

    def test_search_success(self, app, logged_in_client, monkeypatch):
        monkeypatch.setattr(
            "pdf_annotator.routes.swb.search_books",
            lambda query, **kwargs: [
                {
                    "title": "Der Zauberberg",
                    "author": "Thomas Mann",
                    "year": "1924",
                    "isbn": "978-3-10-048472-0",
                    "link": "https://example.org/opac/12345",
                }
            ],
        )
        response = logged_in_client.get("/swb/search?q=Zauberberg")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Der Zauberberg" in body
        assert "https://example.org/opac/12345" in body

    def test_empty_query_rejected(self, app, logged_in_client):
        response = logged_in_client.get("/swb/search?q=")
        assert response.status_code == 400

    def test_missing_query_rejected(self, app, logged_in_client):
        response = logged_in_client.get("/swb/search")
        assert response.status_code == 400

    def test_requires_login(self, client):
        response = client.get("/swb/search?q=test")
        assert response.status_code in (302, 401)

    def test_search_error_maps_to_503(self, app, logged_in_client, monkeypatch):
        def raise_error(query, **kwargs):
            raise SWBSearchError("boom")

        monkeypatch.setattr("pdf_annotator.routes.swb.search_books", raise_error)
        response = logged_in_client.get("/swb/search?q=test")
        assert response.status_code == 503
