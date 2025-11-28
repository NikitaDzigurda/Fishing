"""
Academic API - унифицированный сбор данных из академических источников
"""

from .models import (
    SourceType,
    ExternalIds,
    Author,
    Publication,
    Metrics,
    CoAuthor,
    AuthorProfile,
    SearchResult
)

from .base import BaseParser

from .exporters import (
    export,
    export_all,
    JSONExporter,
    CSVExporter,
    BibTeXExporter,
    MarkdownExporter,
    HTMLExporter
)

from .formatters import (
    format_profile,
    format_publication,
    format_publications_list,
    format_comparison
)

from .parsers.arxiv import ArxivParser
from .parsers.google_scholar import GoogleScholarParser, ProxyType
from .parsers.semantic_scholar import SemanticScholarParser
from .parsers.scopus import ScopusParser


__all__ = [
    # Models
    "SourceType", "ExternalIds", "Author", "Publication",
    "Metrics", "CoAuthor", "AuthorProfile", "SearchResult",

    # Base
    "BaseParser",

    # Parsers
    "ArxivParser",
    "GoogleScholarParser", "ProxyType",
    "SemanticScholarParser",
    "ScopusParser",

    # Export
    "export", "export_all",
    "JSONExporter", "CSVExporter", "BibTeXExporter",
    "MarkdownExporter", "HTMLExporter",

    # Formatters
    "format_profile", "format_publication",
    "format_publications_list", "format_comparison"
]