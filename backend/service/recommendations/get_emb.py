import json
import numpy as np
from sentence_transformers import SentenceTransformer

# 1. Загружаем модель (multilingual, если тексты на разных языках)
model = SentenceTransformer('intfloat/multilingual-e5-tiny')


# Или 'all-MiniLM-L6-v2' для английского (быстрее)

def get_author_embedding(author):
    # Вектора для хранения
    vectors = []

    # 1. Векторизуем интересы (даем им вес, например, как 3 публикации)
    if author.get('interests'):
        interests_text = "Interests: " + ", ".join(author['interests'])
        # E5 требует префикс "passage: " для документов
        int_emb = model.encode("passage: " + interests_text)
        vectors.append(int_emb)
        vectors.append(int_emb)  # Дублируем для веса (опционально)

    # 2. Векторизуем публикации
    for pub in author.get('publications', []):
        # Объединяем заголовок и абстракт.
        # Заголовок важнее, поэтому он идет первым.
        text = f"{pub['title']}. {pub.get('abstract', '')}"
        # Обрезаем слишком длинные тексты, если модель не справляется,
        # но SBERT обычно сам делает truncate.
        pub_emb = model.encode("passage: " + text)
        vectors.append(pub_emb)

    if not vectors:
        return np.zeros(model.get_sentence_embedding_dimension())

    # 3. Считаем средний вектор (центроид)
    author_vector = np.mean(vectors, axis=0)

    # Нормализуем вектор (важно для косинусного сходства)
    norm = np.linalg.norm(author_vector)
    if norm > 0:
        author_vector = author_vector / norm

    return author_vector


# Пример данных
author_data = json.load(open('parsed_authors.json', 'r'))[0]

vector = get_author_embedding(author_data)
print(vector.shape)