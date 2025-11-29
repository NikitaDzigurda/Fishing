"""
Форматирование вывода в консоль
"""

from .models import AuthorProfile, Publication, SourceType


def format_profile(profile: AuthorProfile, verbose: bool = True) -> str:
    """Форматирование профиля автора"""

    source_emoji = {
        SourceType.ARXIV: "📄",
        SourceType.GOOGLE_SCHOLAR: "🎓",
        SourceType.SEMANTIC_SCHOLAR: "🔬",
        SourceType.DBLP: "💾",
        SourceType.OPENALEX: "📚",
    }.get(profile.source, "📖")

    lines = [
        "═" * 70,
        f"  {source_emoji} {profile.name}",
        "═" * 70,
        "",
        f"📍 Source: {profile.source.value} | ID: {profile.source_id}",
    ]

    if profile.affiliation:
        lines.append(f"🏛️  Affiliation: {profile.affiliation}")
    if profile.orcid:
        lines.append(f"🆔 ORCID: {profile.orcid}")
    if profile.email_domain:
        lines.append(f"📧 Email: @{profile.email_domain}")
    if profile.homepage:
        lines.append(f"🌐 Homepage: {profile.homepage}")

    lines.extend([
        "",
        "📊 METRICS",
        f"   Citations: {profile.metrics.citation_count:,}" +
        (f" (last 5y: {profile.metrics.citation_count_recent:,})" if profile.metrics.citation_count_recent else ""),
        f"   h-index: {profile.metrics.h_index}" +
        (f" (last 5y: {profile.metrics.h_index_recent})" if profile.metrics.h_index_recent else ""),
        f"   i10-index: {profile.metrics.i10_index}" +
        (f" (last 5y: {profile.metrics.i10_index_recent})" if profile.metrics.i10_index_recent else ""),
        f"   Publications: {len(profile.publications)}",
    ])

    if profile.years_active:
        lines.append(f"   Years active: {profile.years_active}")
        avg = len(profile.publications) / profile.years_active if profile.years_active else 0
        lines.append(f"   Avg papers/year: {avg:.1f}")

    if profile.interests:
        lines.extend([
            "",
            "🔬 INTERESTS",
            "   " + ", ".join(profile.interests[:10])
        ])

    if verbose and profile.citations_per_year:
        lines.extend(["", "📈 CITATIONS BY YEAR"])
        years = sorted(profile.citations_per_year.keys())[-10:]
        max_cites = max(profile.citations_per_year.get(y, 0) for y in years) or 1
        for year in years:
            count = profile.citations_per_year.get(year, 0)
            bar = "█" * int(30 * count / max_cites)
            lines.append(f"   {year}: {count:>6,} {bar}")

    categories = profile.categories_count
    if categories:
        lines.extend(["", "📁 TOP CATEGORIES"])
        for cat, count in list(categories.items())[:10]:
            lines.append(f"   {cat:<25} {count:>4}")

    if profile.publications:
        lines.extend(["", "🏆 TOP PUBLICATIONS BY CITATIONS"])
        for i, pub in enumerate(profile.top_publications, 1):
            lines.append("")
            lines.append(f"   {i}. [{pub.citation_count:,} cit.] {pub.title[:55]}...")
            authors = ", ".join(pub.author_names[:3])
            if len(pub.author_names) > 3:
                authors += " et al."
            lines.append(f"      {authors} ({pub.year or 'N/A'})")
            if pub.venue:
                lines.append(f"      📰 {pub.venue[:50]}")

    if profile.coauthors:
        lines.extend(["", "👥 TOP CO-AUTHORS"])
        for c in profile.top_coauthors:
            aff = f" ({c.author.affiliation})" if c.author.affiliation else ""
            lines.append(f"   • {c.author.name}{aff} — {c.collaboration_count} papers")

    lines.extend([
        "",
        "═" * 70,
        f"Fetched: {profile.fetched_at.strftime('%Y-%m-%d %H:%M:%S')}"
    ])

    return "\n".join(lines)


def format_publication(pub: Publication, index: int = None) -> str:
    """Форматирование одной публикации"""
    prefix = f"{index}. " if index else ""

    lines = [
        f"{prefix}[{pub.citation_count} cit.] {pub.title}",
        f"   Authors: {', '.join(pub.author_names[:5])}" +
        ("..." if len(pub.author_names) > 5 else ""),
        f"   Year: {pub.year or 'N/A'} | Source: {pub.source.value}",
    ]

    if pub.venue:
        lines.append(f"   Venue: {pub.venue}")
    if pub.external_ids.doi:
        lines.append(f"   DOI: {pub.external_ids.doi}")
    if pub.url:
        lines.append(f"   URL: {pub.url}")

    return "\n".join(lines)


def format_publications_list(publications: list[Publication], limit: int = 20) -> str:
    """Форматирование списка публикаций"""
    lines = [
        f"Total: {len(publications)} publications",
        "─" * 50
    ]

    for i, pub in enumerate(publications[:limit], 1):
        lines.append("")
        lines.append(format_publication(pub, i))

    if len(publications) > limit:
        lines.append("")
        lines.append(f"... and {len(publications) - limit} more")

    return "\n".join(lines)


def format_comparison(profiles: list[AuthorProfile]) -> str:
    """Сравнение нескольких авторов"""
    if not profiles:
        return "No profiles to compare"

    # Заголовок
    name_width = max(len(p.name) for p in profiles) + 2

    lines = [
        "═" * 80,
        "  AUTHOR COMPARISON",
        "═" * 80,
        "",
        f"{'Author':<{name_width}} {'Pubs':>8} {'Cites':>10} {'h-idx':>7} {'i10':>7} {'Source':<15}",
        "─" * 80
    ]

    # Сортировка по цитированиям
    sorted_profiles = sorted(profiles, key=lambda p: -p.metrics.citation_count)

    for p in sorted_profiles:
        lines.append(
            f"{p.name:<{name_width}} "
            f"{len(p.publications):>8} "
            f"{p.metrics.citation_count:>10,} "
            f"{p.metrics.h_index:>7} "
            f"{p.metrics.i10_index:>7} "
            f"{p.source.value:<15}"
        )

    lines.extend(["", "═" * 80])

    return "\n".join(lines)