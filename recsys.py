from vector_db import AuthorSearchEngine
from typing import Dict, List
import datetime

class RecSys:
    def __init__(self, authors_data:dict):
        # Инициализация движка поиска авторов
        self.engine = AuthorSearchEngine()
        self.authors_data = authors_data
        self._index_users()
        self._init_coauthors_map()
        self._init_second_degree_coauthors()

    def _index_users(self):
        # Индексация данных пользователей
        self.engine.process_and_index(self.authors_data)

    def _init_coauthors_map(self):
        self.coauthors_map = {}
        for user_id, user_info in self.authors_data.items():
            combined = user_info.get('combined', {})
            coauthors = combined.get('coauthors', [])
            self.coauthors_map[user_id] = coauthors

    def _init_second_degree_coauthors(self):
        self.second_degree_map = {}

        for user_id, direct_coauthors_list in self.coauthors_map.items():
            direct_contacts_set = set(direct_coauthors_list)
            candidates_set = set()

            for intermediary_id in direct_coauthors_list:
                intermediary_contacts = self.coauthors_map.get(intermediary_id, [])

                for candidate_id in intermediary_contacts:
                    if candidate_id == user_id:
                        continue

                    if candidate_id in direct_contacts_set:
                        continue

                    candidates_set.add(candidate_id)

            self.second_degree_map[user_id] = list(candidates_set)

    def recommend_similar_users(self, user_id, top_k=5):
        # Рекомендация похожих пользователей по ID
        return self.engine.search_similar_to_author(user_id, top_k=top_k)

    def recommend_by_query(self, query, top_k=5):
        # Рекомендация пользователей по текстовому запросу
        return self.engine.search_by_text(query, top_k=top_k)

    def _get_last_publication_year(self, user_id):
        """
        Вспомогательный метод: ищет самый свежий год в публикациях автора.
        Предполагается, что в publications есть поле 'year'.
        Если его нет или список пуст, возвращаем None.
        """
        user_info = self.authors_data.get(user_id, {})
        combined = user_info.get('combined', {})
        publications = combined.get('publications', [])

        if not publications:
            return None

        years = []
        for pub in publications:
            # Пытаемся найти год (как int или str)
            y = pub.get('year')
            if y:
                try:
                    years.append(int(y))
                except ValueError:
                    continue

        return max(years) if years else None

    def recommend(self, user_id, query_text, top_n=5, search_limit=50):
        """
        Финальная функция рекомендаций.

        Параметры:
        - user_id: ID того, для кого ищем (чтобы исключить его самого и учесть его связи).
        - query_text: Текст запроса (тема исследования).
        - top_n: Сколько итоговых авторов вернуть.
        - search_limit: Сколько кандидатов брать из векторного поиска (воронка).
          Берем с запасом (50), чтобы социальные связи могли поднять наверх тех,
          кто чуть ниже по вектору.
        """

        # 1. Векторный поиск (Semantic Search)
        # Получаем кандидатов по смыслу
        candidates = self.engine.search_by_text(query_text, top_k=search_limit)

        # 2. Подготовка социальных графов (O(1) доступ)
        # Прямые соавторы
        direct_friends = set(self.coauthors_map.get(user_id, []))
        # Соавторы соавторов
        friends_of_friends = set(self.second_degree_map.get(user_id, []))

        # Текущий год для расчета актуальности
        current_year = datetime.datetime.now().year

        ranked_results = []

        # 3. Итерация и ранжирование
        for cand in candidates:
            cid = cand['id']  # ID кандидата
            vector_score = cand['score']  # Косинусное сходство (обычно 0.0 - 1.0)

            # Исключаем самого себя
            if cid == user_id:
                continue

            # --- A. Социальный буст (Social Boost) ---
            # Мы прибавляем очки к векторному скору
            social_bonus = 0.0
            status = "New connection"

            if cid in direct_friends:
                social_bonus = 0.25  # Сильный буст (знакомы лично)
                status = "Co-author"
            elif cid in friends_of_friends:
                social_bonus = 0.10  # Средний буст (знакомый знакомого)
                status = "2nd degree"

            # --- B. Временной коэффициент (Time Decay) ---
            # Мы умножаем скор на коэффициент активности
            last_year = self._get_last_publication_year(cid)
            time_coef = 1.0  # По умолчанию (если нет данных, считаем активным)

            if last_year:
                diff = current_year - last_year
                if diff <= 2:
                    time_coef = 1.0  # Активен (0-2 года)
                elif diff <= 5:
                    time_coef = 0.85  # Недавний (3-5 лет)
                elif diff <= 10:
                    time_coef = 0.6  # Давно писал
                else:
                    time_coef = 0.4  # Очень давно (пенсионер/неактивен)

            # --- C. Финальная формула ---
            # (Вектор + Соц.связи) * Активность
            raw_score = vector_score + social_bonus
            final_score = raw_score * time_coef

            ranked_results.append({
                "id": cid,
                "name": self.authors_data[cid]['combined'].get('name', 'Unknown'),
                "final_score": round(final_score, 4),
                "details": {
                    "vector_score": round(vector_score, 4),
                    "social_bonus": social_bonus,
                    "connection": status,
                    "last_year": last_year
                }
            })

        # 4. Сортировка по финальному скору (от большего к меньшему)
        ranked_results.sort(key=lambda x: x['final_score'], reverse=True)

        # Возвращаем топ N
        return ranked_results[:top_n]

if __name__ == "__main__":
    # Пример использования
    import json

    # Загрузка данных авторов из JSON файла
    with open('parsed_authors.json', 'r') as f:
        authors_data = json.load(f)

    recsys = RecSys(authors_data)

    user_id = 1  # Предположим, что мы рекомендуем для автора с ID 1
    query = "machine learning and natural language processing"

    recommendations = recsys.recommend(user_id, query, top_n=5)

    for rec in recommendations:
        print(f"ID: {rec['id']}, Name: {rec['name']}, Final Score: {rec['final_score']}, Details: {rec['details']}")