"""
Базовый класс для всех парсеров
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable

from .models import AuthorProfile, Publication, SearchResult, SourceType

ProgressCallback = Callable[[str, int], Awaitable[None]]


class BaseParser(ABC):
    """
    Абстрактный базовый класс для всех академических парсеров
    """

    source: SourceType = SourceType.UNKNOWN

    def __init__(self):
        self._session = None

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    @abstractmethod
    async def init(self):
        """Инициализация (создание сессии и т.д.)"""
        pass

    @abstractmethod
    async def close(self):
        """Закрытие ресурсов"""
        pass

    @abstractmethod
    async def get_author_profile(
            self,
            author_id: Optional[str] = None,
            author_name: Optional[str] = None,
            author_url: Optional[str] = None,
            progress_callback: Optional[ProgressCallback] = None
    ) -> AuthorProfile:
        """
        Получить полный профиль автора

        Args:
            author_id: ID автора в источнике
            author_name: Имя автора (для поиска)
            author_url: URL профиля
            progress_callback: async callback(status, count)

        Returns:
            AuthorProfile
        """
        pass

    @abstractmethod
    async def search_authors(
            self,
            query: str,
            limit: int = 10
    ) -> list[AuthorProfile]:
        """
        Поиск авторов по имени

        Args:
            query: Поисковый запрос
            limit: Максимум результатов

        Returns:
            Список кратких профилей
        """
        pass

    @abstractmethod
    async def search_publications(
            self,
            query: str,
            limit: int = 20,
            year_start: Optional[int] = None,
            year_end: Optional[int] = None
    ) -> list[Publication]:
        """
        Поиск публикаций

        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            year_start: Начальный год
            year_end: Конечный год

        Returns:
            Список публикаций
        """
        pass

    @abstractmethod
    async def get_publication(self, publication_id: str) -> Publication:
        """
        Получить публикацию по ID

        Args:
            publication_id: ID публикации

        Returns:
            Publication
        """
        pass

    @classmethod
    def parse_url(cls, url: str) -> dict:
        """
        Парсинг URL для извлечения ID

        Args:
            url: URL профиля или публикации

        Returns:
            dict с распознанными параметрами
        """
        raise NotImplementedError

    async def get_multiple_profiles(
            self,
            identifiers: list[str],
            progress_callback: Optional[Callable[[str, str, int], Awaitable[None]]] = None
    ) -> dict[str, AuthorProfile]:
        """
        Получить профили нескольких авторов

        Args:
            identifiers: Список ID или имён
            progress_callback: async callback(identifier, status, count)

        Returns:
            dict {identifier: AuthorProfile}
        """
        profiles = {}

        for identifier in identifiers:
            try:
                async def inner_progress(status, count):
                    if progress_callback:
                        await progress_callback(identifier, status, count)

                # Пробуем как ID, если не работает — как имя
                try:
                    profile = await self.get_author_profile(
                        author_id=identifier,
                        progress_callback=inner_progress
                    )
                except:
                    profile = await self.get_author_profile(
                        author_name=identifier,
                        progress_callback=inner_progress
                    )

                profiles[identifier] = profile

            except Exception as e:
                print(f"✗ Error for {identifier}: {e}")

        return profiles