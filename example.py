import asyncio

# Абсолютные импорты из пакета academic_api
from academic_api import (
    ArxivParser,
    GoogleScholarParser,
    SemanticScholarParser,
    ProxyType,
    format_profile,
    format_comparison,
    export,
    export_all
)


async def example_arxiv():
    """Пример работы с arXiv"""
    async with ArxivParser() as parser:
        async def on_progress(status, count):
            print(f"\r{status}", end="", flush=True)

        profile = await parser.get_author_profile(
            author_name="Yann LeCun",
            progress_callback=on_progress
        )
        print()
        print(format_profile(profile))

        # Экспорт
        export(profile, "output/lecun_arxiv.json")
        export(profile, "output/lecun_arxiv.csv")
        export(profile, "output/lecun_arxiv.bib")


async def example_semantic_scholar():
    """Пример работы с Semantic Scholar"""
    async with SemanticScholarParser() as parser:
        profile = await parser.get_author_profile(author_name="Geoffrey Hinton")
        print(format_profile(profile))
        export(profile, "output/hinton_s2.json")


async def example_google_scholar():
    """Пример работы с Google Scholar"""
    async with GoogleScholarParser(proxy_type=ProxyType.FREE) as parser:
        # Geoffrey Hinton's Google Scholar ID
        profile = await parser.get_author_profile(
            author_id="JicYPdAAAAAJ",
            fill_publications=False  # Быстрый режим без деталей публикаций
        )
        print(format_profile(profile))


async def example_search():
    """Поиск авторов"""
    async with SemanticScholarParser() as parser:
        authors = await parser.search_authors("Yoshua Bengio", limit=5)

        print("Найденные авторы:")
        for a in authors:
            print(f"  - {a.name} (ID: {a.source_id})")
            print(f"    Citations: {a.metrics.citation_count}")


async def example_multiple_sources():
    """Сравнение данных из разных источников"""
    profiles = []

    # arXiv
    async with ArxivParser() as parser:
        profile = await parser.get_author_profile(author_name="Ilya Sutskever")
        profiles.append(profile)
        print(f"✓ arXiv: {len(profile.publications)} publications")

    # Semantic Scholar
    async with SemanticScholarParser() as parser:
        profile = await parser.get_author_profile(author_name="Ilya Sutskever")
        profiles.append(profile)
        print(f"✓ Semantic Scholar: {len(profile.publications)} publications")

    # Сравнение
    print("\n" + format_comparison(profiles))


async def main():
    """Запуск всех примеров"""
    print("=" * 60)
    print("ARXIV EXAMPLE")
    print("=" * 60)
    await example_arxiv()

    print("\n" + "=" * 60)
    print("SEMANTIC SCHOLAR EXAMPLE")
    print("=" * 60)
    await example_semantic_scholar()


if __name__ == "__main__":
    asyncio.run(main())