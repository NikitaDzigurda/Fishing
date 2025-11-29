import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Tuple
from tqdm import tqdm


class AuthorSearchEngine:
    def __init__(self, model_name: str = 'intfloat/multilingual-e5-small'):
        """
        Инициализация движка.
        model_name: название модели с HuggingFace. 
                    'all-MiniLM-L6-v2' - быстрая и легкая.
                    'intfloat/multilingual-e5-large' - мощная, мультиязычная.
        """
        print(f"Загрузка модели {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

        # Индекс FAISS
        self.index = None

        # Хранилища данных
        self.authors_vectors = None  # numpy массив всех векторов
        self.id_map = {}  # Map: внутренний ID faiss -> реальный ID автора (из словаря)
        self.reverse_id_map = {}  # Map: реальный ID автора -> внутренний ID faiss
        self.author_data_cache = {}  # Копия данных для вывода результатов

    def _get_single_author_vector(self, author_info: dict) -> np.ndarray:
        """
        Превращает данные одного автора в усредненный вектор.
        """
        texts_to_embed = []

        # 1. Добавляем интересы (если есть)
        # Интересы очень важны, можно добавить их несколько раз для веса, 
        # либо просто добавить в список.
        interests = author_info.get('interests', [])
        if interests:
            # Объединяем интересы в строку
            interests_text = f"{', '.join(interests)}"
            texts_to_embed.append(interests_text)
            # Хакинг весов: добавляем интересы дважды, чтобы они сильнее влияли на вектор
            # texts_to_embed.append(interests_text)

            # 2. Добавляем публикации
        publications = author_info.get('publications', [])
        for pub in publications:
            title = pub.get('title', '')
            abstract = pub.get('abstract', '')
            # Формируем текст: Заголовок важнее абстракта
            text = f"{title}. {abstract}"
            if len(text) > 5:  # Игнорируем пустые
                texts_to_embed.append(text)

        # Если у автора нет данных, возвращаем нулевой вектор
        if not texts_to_embed:
            return np.zeros(self.dimension, dtype=np.float32)

        # 3. Векторизуем все куски текста (Batch encoding)
        embeddings = self.model.encode(texts_to_embed, convert_to_numpy=True, normalize_embeddings=True)

        # 4. Считаем среднее (Mean Pooling)
        # Получаем один вектор, описывающий автора целиком
        author_vector = np.mean(embeddings, axis=0)

        return author_vector

    def process_and_index(self, data: Dict):
        """
        Основной метод: принимает словарь авторов, векторизует и строит индекс.
        Ожидаемый формат data: 
        {
            author_id: {
                'combined': {
                    'name': '...', 
                    'interests': [...],
                    'publications': [{'title': '...', 'abstract': '...'}, ...]
                }
            },
            ...
        }
        """
        vector_list = []
        valid_ids = []

        print(f"Обработка {len(data)} авторов...")

        # faiss_id - это просто порядковый номер (0, 1, 2...)
        for faiss_id, (real_id, content) in tqdm(enumerate(data.items()), total=len(data.items())):
            # Извлекаем полезную нагрузку из структуры 'combined'
            author_info = content.get('combined', {})

            # Кэшируем данные для отображения при поиске
            self.author_data_cache[real_id] = author_info

            # Получаем вектор
            vec = self._get_single_author_vector(author_info)

            vector_list.append(vec)

            # Сохраняем маппинг ID
            self.id_map[faiss_id] = real_id
            self.reverse_id_map[real_id] = faiss_id

        # Преобразуем в матрицу float32 (требование FAISS)
        self.authors_vectors = np.array(vector_list, dtype=np.float32)

        # Создаем индекс
        # IndexFlatIP использует Inner Product. 
        # Так как векторы нормализованы (L2), Inner Product == Cosine Similarity
        self.index = faiss.IndexFlatIP(self.dimension)

        # Добавляем векторы в базу
        self.index.add(self.authors_vectors)

        print(f"Индекс построен. Всего векторов: {self.index.ntotal}")

    def search_similar_to_author(self, author_id, top_k: int = 5) -> List[Tuple]:
        """
        Ищет авторов, похожих на автора с указанным ID (который уже есть в базе).
        """
        if author_id not in self.reverse_id_map:
            raise ValueError(f"Автор с ID {author_id} не найден в базе.")

        # Получаем внутренний ID FAISS
        faiss_id = self.reverse_id_map[author_id]

        # Берем вектор этого автора
        # reshape(1, -1) нужен, так как faiss ожидает матрицу запросов
        query_vector = self.authors_vectors[faiss_id].reshape(1, -1)

        return self._run_search(query_vector, top_k, exclude_id=author_id)

    def search_by_text(self, query_text: str, top_k: int = 5) -> List[Tuple]:
        """
        Ищет авторов по произвольному текстовому описанию (например: "expert in NLP and transformers").
        """
        # Векторизуем запрос
        query_vector = self.model.encode([query_text], convert_to_numpy=True)
        # Нормализуем
        faiss.normalize_L2(query_vector)

        return self._run_search(query_vector, top_k)

    def _run_search(self, query_vector, top_k, exclude_id=None):
        """Внутренняя функция поиска"""
        # Ищем с запасом, так как можем исключить самого себя
        k_search = top_k + 1 if exclude_id is not None else top_k

        # D - дистанции (сходство), I - индексы найденных соседей
        D, I = self.index.search(query_vector, k_search)

        results = []
        # I[0] так как у нас 1 вектор запроса
        for score, neighbor_faiss_id in zip(D[0], I[0]):
            if neighbor_faiss_id == -1: continue  # Ничего не найдено

            real_id = self.id_map[neighbor_faiss_id]

            # Исключаем самого себя из результатов
            if exclude_id is not None and real_id == exclude_id:
                continue

            author_info = self.author_data_cache[real_id]
            results.append({
                "id": real_id,
                "score": float(score),  # Косинусное сходство (от -1 до 1)
                "name": author_info.get('name', 'Unknown'),
                "interests": author_info.get('interests', [])
            })

            if len(results) >= top_k:
                break

        return results
