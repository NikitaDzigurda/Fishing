from vector_db import AuthorSearchEngine


# 1. Подготовка тестовых данных (Ваша структура)
users_data = {
    101: {
        "combined": {
            "name": "Dr. Alice Smith",
            "interests": ["Machine Learning", "NLP", "Transformers"],
            "publications": [
                {"title": "Attention is all you need",
                 "abstract": "We propose a new simple network architecture based solely on attention mechanisms."},
                {"title": "BERT embeddings",
                 "abstract": "Deep bidirectional transformers for language understanding."}
            ]
        }
    },
    102: {
        "combined": {
            "name": "Prof. Bob Jones",
            "interests": ["Biology", "Genetics", "Cells"],
            "publications": [
                {"title": "CRISPR gene editing", "abstract": "A precise method for editing genomic DNA."},
                {"title": "Cell division mechanics", "abstract": "Study of mitosis in eukaryotic cells."}
            ]
        }
    },
    103: {
        "combined": {
            "name": "Charlie Brown",
            "interests": ["Deep Learning", "Computer Vision"],
            "publications": [
                {"title": "ImageNet classification",
                 "abstract": "Deep convolutional neural networks for image recognition."},
                {"title": "ResNet architecture", "abstract": "Deep residual learning for image recognition."}
            ]
        }
    }
}

# 2. Инициализация движка
engine = AuthorSearchEngine()

# 3. Индексация данных
engine.process_and_index(users_data)

print("\n--- Тест 1: Поиск похожих на Alice (ID 101) ---")
# Alice занимается NLP. Ближе всего к ней должен быть Charlie (Deep Learning), а не Bob (Biology).
similar_users = engine.search_similar_to_author(101, top_k=2)
for u in similar_users:
    print(f"ID: {u['id']}, Name: {u['name']}, Score: {u['score']:.4f}, Interests: {u['interests']}")

print("\n--- Тест 2: Поиск по текстовому запросу ---")
query = "I need someone who knows about DNA and genes"
results = engine.search_by_text(query, top_k=1)
for u in results:
    print(f"Запрос: '{query}' -> Найдено: {u['name']} (Score: {u['score']:.4f})")