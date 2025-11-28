import google.generativeai as genai
from vector_db import AuthorSearchEngine
from typing import Dict, List
import datetime
import json
import os


class RecSys:
    def __init__(self, authors_data: dict, gemini_api_key: str):
        # 1. Инициализация Gemini
        genai.configure(api_key=gemini_api_key)
        # Используем модель flash для скорости или pro для качества
        self.model = genai.GenerativeModel('gemini-2.5-flash')

        # 2. Инициализация движка и данных
        self.engine = AuthorSearchEngine()
        self.authors_data = authors_data
        self._index_users()
        self._init_coauthors_map()
        self._init_second_degree_coauthors()

    def _index_users(self):
        self.engine.process_and_index(self.authors_data)

    def _init_coauthors_map(self):
        self.coauthors_map = {}
        for user_id, user_info in self.authors_data.items():
            combined = user_info.get('combined', {})
            # Преобразуем user_id в тот же тип, что в ключах (обычно str в JSON или int)
            coauthors = combined.get('authors', [])
            self.coauthors_map[user_id] = coauthors

    def _init_second_degree_coauthors(self):
        self.second_degree_map = {}
        for user_id, direct_coauthors_list in self.coauthors_map.items():
            direct_contacts_set = set(direct_coauthors_list)
            candidates_set = set()
            for intermediary_id in direct_coauthors_list:
                # Безопасное получение, если ID вдруг нет в базе
                intermediary_contacts = self.coauthors_map.get(intermediary_id, [])
                for candidate_id in intermediary_contacts:
                    if candidate_id == user_id: continue
                    if candidate_id in direct_contacts_set: continue
                    candidates_set.add(candidate_id)
            self.second_degree_map[user_id] = list(candidates_set)

    def _get_last_publication_year(self, user_id):
        user_info = self.authors_data.get(user_id, {})
        combined = user_info.get('combined', {})
        publications = combined.get('publications', [])
        if not publications: return None
        years = []
        for pub in publications:
            y = pub.get('year')
            if y:
                try:
                    years.append(int(y))
                except ValueError:
                    continue
        return max(years) if years else None

    def _prepare_candidates_for_llm(self, candidates_list, query):
        """
        Формирует текстовое представление кандидатов для промпта.
        """
        context_text = f"User Query: '{query}'\n\nCandidates to rank:\n"

        for cand in candidates_list:
            cid = cand['id']
            # Получаем данные автора
            data = self.authors_data.get(cid, {}).get('combined', {})
            name = data.get('name', 'Unknown')
            interests = ", ".join(data.get('interests', [])[:5])  # Берем топ-5 интересов

            # Берем 2 последние публикации для контекста
            pubs = data.get('publications', [])[:2]
            pubs_str = ""
            for p in pubs:
                title = p.get('title', 'No title')
                abstract = p.get('abstract', 'No abstract')[:150] + "..."  # Обрезаем длинные абстракты
                pubs_str += f"  - Title: {title}\n    Abstract: {abstract}\n"

            # Информация о "теплой" связи из эвристического этапа
            conn_status = cand['details']['connection']

            context_text += (
                f"ID: {cid}\n"
                f"Name: {name}\n"
                f"Interests: {interests}\n"
                f"Relationship: {conn_status}\n"
                f"Recent Work:\n{pubs_str}\n"
                f"--------------------------------\n"
            )

        return context_text

    def _rerank_with_gemini(self, candidates_list, query, top_n):
        """
        Отправляет запрос в LLM для финальной сортировки.
        """
        if not candidates_list:
            return []

        candidates_context = self._prepare_candidates_for_llm(candidates_list, query)

        prompt = f"""
        You are an expert scientific matchmaker. 
        Your task is to rank the following candidates based on their relevance to the User Query: "{query}".

        Consider:
        1. Semantic relevance of their research (titles and abstracts) to the query.
        2. Their listed research interests.
        3. The "Relationship" field (prioritize "Co-author" slightly if relevance is equal, but relevance is king).

        Return the result strictly in JSON format. 
        The JSON should be a list of objects, where each object has:
        - "id": (integer or string, matching the input ID)
        - "rank": (integer, 1 being best)
        - "reasoning": (short explanation why this person fits the query)

        Input Data:
        {candidates_context}
        """

        try:
            # Запрос к модели с требованием JSON
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )

            # Парсинг ответа
            llm_ranking = json.loads(response.text)

            # Собираем финальный результат, объединяя данные LLM и исходные данные
            final_results = []

            # Создаем lookup словарь исходных кандидатов для быстрого доступа
            cand_map = {c['id']: c for c in candidates_list}

            for rank_item in llm_ranking:
                cid = rank_item.get('id')
                # Приведение типов ID, если JSON вернул строку, а у нас int (или наоборот)
                # Пытаемся найти как есть, потом как int, потом как str
                found_cand = cand_map.get(cid)
                if not found_cand:
                    found_cand = cand_map.get(int(cid)) if str(cid).isdigit() else None
                if not found_cand:
                    found_cand = cand_map.get(str(cid))

                if found_cand:
                    final_results.append({
                        "id": cid,
                        "name": found_cand['name'],
                        "llm_reasoning": rank_item.get('reasoning'),
                        "heuristic_details": found_cand['details']  # сохраняем старые метрики для отладки
                    })

            # Если LLM вернула меньше, чем было (или галлюцинировала с ID),
            # можно дополнить список оставшимися из эвристики (опционально).
            # Здесь просто возвращаем то, что ранжировала LLM.
            return final_results[:top_n]

        except Exception as e:
            print(f"LLM Ranking failed: {e}. Falling back to heuristic ranking.")
            # Если API упал или закончились квоты, возвращаем эвристическую сортировку
            return candidates_list[:top_n]

    def recommend(self, user_id, query_text, top_n=5, search_limit=50, use_llm=True):
        """
        search_limit: сколько кандидатов достаем из базы векторов (воронка 1)
        pre_llm_limit: сколько лучших по эвристике отправляем в LLM (воронка 2)
        top_n: сколько итоговых показываем пользователю
        """
        # 1. Векторный поиск
        candidates = self.engine.search_by_text(query_text, top_k=search_limit)

        direct_friends = set(self.coauthors_map.get(user_id, []))
        friends_of_friends = set(self.second_degree_map.get(user_id, []))
        current_year = datetime.datetime.now().year

        heuristic_results = []

        # 2. Эвристическое ранжирование (грубая фильтрация)
        for cand in candidates:
            cid = cand['id']
            vector_score = cand['score']

            if str(cid) == str(user_id): continue  # Исключаем себя

            # Социальный буст
            social_bonus = 0.0
            status = "None"
            if cid in direct_friends:
                social_bonus = 0.25
                status = "Co-author"
            elif cid in friends_of_friends:
                social_bonus = 0.10
                status = "2nd degree"

            # Временной коэффициент
            last_year = self._get_last_publication_year(cid)
            time_coef = 1.0
            if last_year:
                diff = current_year - last_year
                if diff > 10:
                    time_coef = 0.2
                elif diff > 5:
                    time_coef = 0.4
                elif diff > 2:
                    time_coef = 0.7
            final_score = (vector_score + social_bonus) * time_coef

            # Безопасное получение имени
            name = self.authors_data.get(cid, {}).get('combined', {}).get('name', 'Unknown Author')

            heuristic_results.append({
                "id": cid,
                "name": name,
                "final_score": round(final_score, 4),
                "details": {
                    "vector_score": round(vector_score, 4),
                    "connection": status,
                    "last_year": last_year
                }
            })

        # Сортируем по эвристике
        heuristic_results.sort(key=lambda x: x['final_score'], reverse=True)

        if not use_llm:
            return heuristic_results[:top_n]

        # 3. LLM Reranking
        # Берем топ-10 (или топ-15) лучших по эвристике, чтобы не тратить токены на мусор
        candidates_for_llm = heuristic_results[:15]

        print(f"Sending {len(candidates_for_llm)} candidates to Gemini for reranking...")

        llm_results = self._rerank_with_gemini(candidates_for_llm, query_text, top_n)

        return llm_results
