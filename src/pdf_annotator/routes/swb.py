"""
Library catalog search route for PDF Annotator.

Stateless search endpoint for the "SWB-Suche" button — takes PDF-viewer
selected text and renders a results page in a new tab. Not tied to any
document, so no ownership check is needed — only authentication.
"""

from typing import Any

from flask import Blueprint, render_template, request
from flask_login import login_required

from pdf_annotator.services.swb_client import SWBSearchError, search_books
from pdf_annotator.utils.logger import get_logger
from pdf_annotator.utils.validators import validate_search_query

logger = get_logger(__name__)

swb_bp = Blueprint("swb", __name__, url_prefix="/swb")


@swb_bp.route("/search", methods=["GET"])
@login_required
def search() -> Any:
    """
    Search library catalogs and render a results page.

    Query Params:
        q: Search query (e.g. text selected in the PDF viewer)

    Returns:
        Rendered HTML results page

    Example:
        GET /swb/search?q=Faust
    """
    query = request.args.get("q", "")
    is_valid, error_msg = validate_search_query(query)
    if not is_valid:
        return render_template(
            "swb_results.html", query=query, error=error_msg, results=None
        ), 400

    try:
        results = search_books(query)
    except SWBSearchError as e:
        return render_template(
            "swb_results.html", query=query, error=str(e), results=None
        ), 503
    except Exception as e:
        logger.error(f"Error in SWB search: {e}", exc_info=True)
        return render_template(
            "swb_results.html",
            query=query,
            error="Interner Serverfehler",
            results=None,
        ), 500

    return render_template("swb_results.html", query=query, error=None, results=results)
