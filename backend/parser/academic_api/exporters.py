"""
Унифицированные экспортеры для всех форматов
"""

import json
import csv
from pathlib import Path
from typing import Union
from datetime import datetime

from .models import AuthorProfile, Publication, SourceType


class Exporter:
    """Базовый класс экспортера"""

    @staticmethod
    def _ensure_path(filepath: str) -> Path:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class JSONExporter(Exporter):
    """Экспорт в JSON"""

    @staticmethod
    def export_profile(profile: AuthorProfile, filepath: str, indent: int = 2):
        """Экспорт профиля автора"""
        path = Exporter._ensure_path(filepath)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=indent)

        print(f"✓ JSON: {path}")

    @staticmethod
    def export_publications(publications: list[Publication], filepath: str, indent: int = 2):
        """Экспорт списка публикаций"""
        path = Exporter._ensure_path(filepath)

        data = {
            "count": len(publications),
            "exported_at": datetime.now().isoformat(),
            "publications": [p.to_dict() for p in publications]
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)

        print(f"✓ JSON: {path}")

    @staticmethod
    def import_profile(filepath: str) -> AuthorProfile:
        """Импорт профиля из JSON"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return AuthorProfile.from_dict(data)

    @staticmethod
    def import_publications(filepath: str) -> list[Publication]:
        """Импорт публикаций из JSON"""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        pubs = data.get("publications", data)
        if isinstance(pubs, list):
            return [Publication.from_dict(p) for p in pubs]
        return []


class CSVExporter(Exporter):
    """Экспорт в CSV"""

    PUBLICATION_FIELDS = [
        "title", "authors", "year", "venue", "citation_count",
        "doi", "arxiv_id", "source", "source_id",
        "primary_category", "categories", "abstract",
        "url", "pdf_url"
    ]

    PROFILE_FIELDS = [
        "name", "source", "source_id", "affiliation", "orcid",
        "citation_count", "h_index", "i10_index", "publication_count",
        "interests", "homepage", "url"
    ]

    @classmethod
    def export_publications(
        cls,
        publications: list[Publication],
        filepath: str,
        fields: list[str] = None
    ):
        """Экспорт публикаций в CSV"""
        path = Exporter._ensure_path(filepath)
        fields = fields or cls.PUBLICATION_FIELDS

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(fields)

            for pub in publications:
                row = []
                for field in fields:
                    if field == "authors":
                        row.append("; ".join(pub.author_names))
                    elif field == "doi":
                        row.append(pub.external_ids.doi or "")
                    elif field == "arxiv_id":
                        row.append(pub.external_ids.arxiv_id or "")
                    elif field == "categories":
                        row.append("; ".join(pub.categories))
                    elif field == "source":
                        row.append(pub.source.value)
                    else:
                        value = getattr(pub, field, "")
                        row.append(value if value is not None else "")
                writer.writerow(row)

        print(f"✓ CSV: {path}")

    @classmethod
    def export_profile_summary(cls, profile: AuthorProfile, filepath: str):
        """Экспорт краткой информации о профиле"""
        path = Exporter._ensure_path(filepath)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(cls.PROFILE_FIELDS)
            writer.writerow([
                profile.name,
                profile.source.value,
                profile.source_id,
                profile.affiliation or "",
                profile.orcid or "",
                profile.metrics.citation_count,
                profile.metrics.h_index,
                profile.metrics.i10_index,
                profile.metrics.publication_count,
                "; ".join(profile.interests),
                profile.homepage or "",
                profile.url or ""
            ])

        print(f"✓ CSV: {path}")

    @classmethod
    def export_coauthors(cls, profile: AuthorProfile, filepath: str):
        """Экспорт соавторов в CSV"""
        path = Exporter._ensure_path(filepath)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "affiliation", "author_id", "collaboration_count"])

            for coauthor in profile.coauthors:
                writer.writerow([
                    coauthor.author.name,
                    coauthor.author.affiliation or "",
                    coauthor.author.author_id or "",
                    coauthor.collaboration_count
                ])

        print(f"✓ CSV (coauthors): {path}")


class BibTeXExporter(Exporter):
    """Экспорт в BibTeX"""

    @staticmethod
    def _make_key(pub: Publication) -> str:
        """Генерация уникального ключа"""
        first_author = "Unknown"
        if pub.authors:
            name = pub.authors[0].name
            parts = name.split()
            first_author = parts[-1] if parts else name

        year = pub.year or "XXXX"
        title_word = pub.title.split()[0] if pub.title else "untitled"

        # Убираем спецсимволы
        key = f"{first_author}{year}_{title_word}"
        key = "".join(c if c.isalnum() or c == "_" else "_" for c in key)

        return key

    @staticmethod
    def _escape_latex(text: str) -> str:
        """Экранирование спецсимволов LaTeX"""
        if not text:
            return ""
        replacements = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}"
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    @classmethod
    def _pub_to_bibtex(cls, pub: Publication) -> str:
        """Конвертация публикации в BibTeX запись"""
        key = cls._make_key(pub)

        # Определяем тип
        entry_type = "article"
        if pub.venue_type:
            type_map = {
                "conference": "inproceedings",
                "workshop": "inproceedings",
                "book": "book",
                "book_chapter": "incollection",
                "thesis": "phdthesis",
                "preprint": "misc"
            }
            entry_type = type_map.get(pub.venue_type.lower(), "article")
        elif pub.source == SourceType.ARXIV:
            entry_type = "misc"

        lines = [f"@{entry_type}{{{key},"]

        # Обязательные поля
        lines.append(f'    title = {{{cls._escape_latex(pub.title)}}},')

        if pub.authors:
            authors_str = " and ".join(a.name for a in pub.authors)
            lines.append(f'    author = {{{cls._escape_latex(authors_str)}}},')

        if pub.year:
            lines.append(f'    year = {{{pub.year}}},')

        # Venue
        if pub.venue:
            if entry_type == "article":
                lines.append(f'    journal = {{{cls._escape_latex(pub.venue)}}},')
            elif entry_type in ("inproceedings", "incollection"):
                lines.append(f'    booktitle = {{{cls._escape_latex(pub.venue)}}},')

        # Опциональные поля
        if pub.publisher:
            lines.append(f'    publisher = {{{cls._escape_latex(pub.publisher)}}},')
        if pub.volume:
            lines.append(f'    volume = {{{pub.volume}}},')
        if pub.issue:
            lines.append(f'    number = {{{pub.issue}}},')
        if pub.pages:
            lines.append(f'    pages = {{{pub.pages}}},')

        # Идентификаторы
        if pub.external_ids.doi:
            lines.append(f'    doi = {{{pub.external_ids.doi}}},')
        if pub.external_ids.arxiv_id:
            lines.append(f'    eprint = {{{pub.external_ids.arxiv_id}}},')
            lines.append('    archivePrefix = {arXiv},')
            if pub.primary_category:
                lines.append(f'    primaryClass = {{{pub.primary_category}}},')

        # URL
        if pub.url:
            lines.append(f'    url = {{{pub.url}}},')

        # Abstract
        if pub.abstract:
            abstract = pub.abstract[:500] + "..." if len(pub.abstract) > 500 else pub.abstract
            lines.append(f'    abstract = {{{cls._escape_latex(abstract)}}},')

        # Keywords
        if pub.keywords:
            lines.append(f'    keywords = {{{", ".join(pub.keywords)}}},')

        # Убираем последнюю запятую
        lines[-1] = lines[-1].rstrip(",")
        lines.append("}")

        return "\n".join(lines)

    @classmethod
    def export_publications(cls, publications: list[Publication], filepath: str):
        """Экспорт публикаций в BibTeX"""
        path = Exporter._ensure_path(filepath)

        entries = [cls._pub_to_bibtex(pub) for pub in publications]

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(entries))

        print(f"✓ BibTeX: {path}")

    @classmethod
    def export_profile(cls, profile: AuthorProfile, filepath: str):
        """Экспорт всех публикаций автора в BibTeX"""
        cls.export_publications(profile.publications, filepath)


class MarkdownExporter(Exporter):
    """Экспорт в Markdown"""

    @classmethod
    def export_profile(cls, profile: AuthorProfile, filepath: str):
        """Экспорт профиля в Markdown"""
        path = Exporter._ensure_path(filepath)

        lines = [
            f"# {profile.name}",
            "",
            f"**Source:** {profile.source.value}",
            f"**ID:** `{profile.source_id}`",
            ""
        ]

        if profile.affiliation:
            lines.append(f"**Affiliation:** {profile.affiliation}")
        if profile.orcid:
            lines.append(f"**ORCID:** [{profile.orcid}](https://orcid.org/{profile.orcid})")
        if profile.homepage:
            lines.append(f"**Homepage:** [{profile.homepage}]({profile.homepage})")

        lines.extend([
            "",
            "## Metrics",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Citations | {profile.metrics.citation_count:,} |",
            f"| h-index | {profile.metrics.h_index} |",
            f"| i10-index | {profile.metrics.i10_index} |",
            f"| Publications | {profile.metrics.publication_count} |",
            ""
        ])

        if profile.interests:
            lines.extend([
                "## Research Interests",
                "",
                ", ".join(f"`{i}`" for i in profile.interests),
                ""
            ])

        lines.extend([
            "## Top Publications",
            ""
        ])

        for i, pub in enumerate(profile.top_publications, 1):
            authors = ", ".join(pub.author_names[:3])
            if len(pub.author_names) > 3:
                authors += " et al."

            lines.append(f"### {i}. {pub.title}")
            lines.append("")
            lines.append(f"*{authors}* ({pub.year or 'N/A'})")
            lines.append("")
            lines.append(f"**Citations:** {pub.citation_count}")
            if pub.venue:
                lines.append(f"**Venue:** {pub.venue}")
            if pub.url:
                lines.append(f"**URL:** [{pub.url}]({pub.url})")
            lines.append("")

        if profile.coauthors:
            lines.extend([
                "## Top Co-authors",
                "",
                "| Name | Collaborations |",
                "|------|----------------|"
            ])
            for c in profile.top_coauthors:
                lines.append(f"| {c.author.name} | {c.collaboration_count} |")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"✓ Markdown: {path}")


class HTMLExporter(Exporter):
    """Экспорт в HTML"""

    @classmethod
    def export_profile(cls, profile: AuthorProfile, filepath: str):
        """Экспорт профиля в HTML"""
        path = Exporter._ensure_path(filepath)

        # Генерация HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{profile.name} - Academic Profile</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 20px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; }}
        .metric {{ background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #333; }}
        .metric-label {{ color: #666; font-size: 0.9em; }}
        .publication {{ border-left: 3px solid #007bff; padding-left: 15px; margin: 20px 0; }}
        .pub-title {{ font-weight: bold; margin-bottom: 5px; }}
        .pub-authors {{ color: #666; font-size: 0.9em; }}
        .pub-venue {{ color: #888; font-style: italic; }}
        .citation-count {{ background: #28a745; color: white; padding: 2px 8px; 
                          border-radius: 12px; font-size: 0.8em; }}
        .interests {{ display: flex; flex-wrap: wrap; gap: 8px; }}
        .interest {{ background: #e9ecef; padding: 4px 12px; border-radius: 15px; font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{profile.name}</h1>
        <p><strong>Source:</strong> {profile.source.value} | <strong>ID:</strong> {profile.source_id}</p>
        {"<p><strong>Affiliation:</strong> " + profile.affiliation + "</p>" if profile.affiliation else ""}
    </div>
    
    <h2>Metrics</h2>
    <div class="metrics">
        <div class="metric">
            <div class="metric-value">{profile.metrics.citation_count:,}</div>
            <div class="metric-label">Citations</div>
        </div>
        <div class="metric">
            <div class="metric-value">{profile.metrics.h_index}</div>
            <div class="metric-label">h-index</div>
        </div>
        <div class="metric">
            <div class="metric-value">{profile.metrics.i10_index}</div>
            <div class="metric-label">i10-index</div>
        </div>
        <div class="metric">
            <div class="metric-value">{len(profile.publications)}</div>
            <div class="metric-label">Publications</div>
        </div>
    </div>
    
    {"<h2>Research Interests</h2><div class='interests'>" + "".join(f"<span class='interest'>{i}</span>" for i in profile.interests) + "</div>" if profile.interests else ""}
    
    <h2>Top Publications</h2>
"""

        for pub in profile.top_publications:
            authors = ", ".join(pub.author_names[:3])
            if len(pub.author_names) > 3:
                authors += " et al."

            html += f"""
    <div class="publication">
        <div class="pub-title">{pub.title} <span class="citation-count">{pub.citation_count} citations</span></div>
        <div class="pub-authors">{authors} ({pub.year or 'N/A'})</div>
        {"<div class='pub-venue'>" + pub.venue + "</div>" if pub.venue else ""}
    </div>
"""

        if profile.coauthors:
            html += """
    <h2>Top Co-authors</h2>
    <table>
        <tr><th>Name</th><th>Affiliation</th><th>Collaborations</th></tr>
"""
            for c in profile.top_coauthors:
                html += f"        <tr><td>{c.author.name}</td><td>{c.author.affiliation or '-'}</td><td>{c.collaboration_count}</td></tr>\n"
            html += "    </table>\n"

        html += f"""
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #888; font-size: 0.9em;">
        Generated at {profile.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}
    </footer>
</body>
</html>
"""

        with open(path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"✓ HTML: {path}")


# === Удобный интерфейс ===

def export(
    data: Union[AuthorProfile, list[Publication]],
    filepath: str,
    format: str = "auto"
):
    """
    Универсальный экспорт

    Args:
        data: AuthorProfile или список Publication
        filepath: Путь к файлу
        format: Формат (json, csv, bib, md, html) или 'auto' для определения по расширению
    """
    if format == "auto":
        suffix = Path(filepath).suffix.lower()
        format_map = {
            ".json": "json",
            ".csv": "csv",
            ".bib": "bib",
            ".bibtex": "bib",
            ".md": "md",
            ".markdown": "md",
            ".html": "html",
            ".htm": "html"
        }
        format = format_map.get(suffix, "json")

    is_profile = isinstance(data, AuthorProfile)
    publications = data.publications if is_profile else data

    if format == "json":
        if is_profile:
            JSONExporter.export_profile(data, filepath)
        else:
            JSONExporter.export_publications(publications, filepath)

    elif format == "csv":
        CSVExporter.export_publications(publications, filepath)

    elif format == "bib":
        BibTeXExporter.export_publications(publications, filepath)

    elif format == "md":
        if is_profile:
            MarkdownExporter.export_profile(data, filepath)
        else:
            raise ValueError("Markdown export requires AuthorProfile")

    elif format == "html":
        if is_profile:
            HTMLExporter.export_profile(data, filepath)
        else:
            raise ValueError("HTML export requires AuthorProfile")

    else:
        raise ValueError(f"Unknown format: {format}")


def export_all(profile: AuthorProfile, base_path: str):
    """Экспорт во все форматы"""
    base = Path(base_path)
    name = profile.name.replace(" ", "_")

    export(profile, str(base / f"{name}.json"))
    export(profile, str(base / f"{name}.csv"))
    export(profile, str(base / f"{name}.bib"))
    export(profile, str(base / f"{name}.md"))
    export(profile, str(base / f"{name}.html"))

    # Дополнительно: соавторы
    CSVExporter.export_coauthors(profile, str(base / f"{name}_coauthors.csv"))