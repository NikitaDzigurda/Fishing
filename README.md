Гайд на использование

```python
from recsys import RecSys

# Инициализация системы рекомендаций с пользовательскими данными в виде как джсон в чате
recsys = RecSys(users_data, gemini_api_key='')

# Получение рекомендаций на основе айди текущего пользователя и текстового описания желаемого проекта
result = recsys.recommend(115, 'I want to do cybersecurity research focusing on network defense strategies.', top_n=3)
```

Вид result:
```python
[
    {
        'id': 106, 
        'name': 'Sarah Connor', 
        'llm_reasoning': "Sarah's research interests directly include 'Cybersecurity' and 'Network Security'. Her recent work on 'Zero-day exploit detection' is highly relevant to developing 'network defense strategies'.", 
        'heuristic_details': 
            {
                'vector_score': 0.8387, 
                'connection': 'None', 
                'last_year': 2022
            }
    }
]

```
