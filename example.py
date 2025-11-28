import asyncio
import json
from academic_api.main_parser import ParserConfig, parse_authors

async def main():
    authors = {
        0: {
            "id": 0,
            "name": "Yann LeCun",
            "scholar_id": "WLN3QrAAAAAJ",
            "semantic_scholar_id": None,
            "arxiv_name": "Yann LeCun"
        },
    }

    config = ParserConfig(
        use_arxiv=True,
        use_semantic_scholar=True,
        scopus_api_key='d2f9ab7360044da43833b7669f9fd350',
        use_scopus=False,
        use_google_scholar=False
    )

    def show_progress(current, total, name, status):
        print(f"[{current}/{total}] {name}: {status}")

    results = await parse_authors(authors, config, show_progress)


    for key, data in results.items():
        print(f"\n{'=' * 60}")
        print(f"Author: {data['input']['name']}")
        print(f"Sources found: {data['combined']['sources_found']}")
        print(f"Citations: {data['combined']['metrics']['citations']:,}")
        print(f"h-index: {data['combined']['metrics']['h_index']}")
        print(f"Publications: {data['combined']['metrics']['publication_count']}")

        if data["errors"]:
            print(f"Errors: {data['errors']}")

    with open("parsed_authors.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved to parsed_authors.json")


if __name__ == "__main__":
    asyncio.run(main())