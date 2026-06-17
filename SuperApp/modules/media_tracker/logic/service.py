import uuid
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

from modules.media_tracker.api.storage import init_db, fetch_all, insert, update, delete

MEDIA_TYPES = {
    "film":   "🎬 Фильм",
    "series": "📺 Сериал",
    "book":   "📖 Книга",
    "game":   "🎮 Игра",
}

STATUSES = {
    "planned":     "Запланировано",
    "in_progress": "В процессе",
    "completed":   "Завершено",
}

TYPE_COLORS = {
    "film":   "#00D4FF",
    "series": "#A855F7",
    "book":   "#FFD700",
    "game":   "#39FF14",
}


@dataclass
class MediaItem:
    id:           str
    title:        str
    media_type:   str             # ключ из MEDIA_TYPES
    status:       str             # ключ из STATUSES
    rating:       Optional[int]   # 1-10 или None
    notes:        str
    added_at:     str             # ISO дата
    completed_at: Optional[str]   # ISO дата или None

    @staticmethod
    def new(title: str, media_type: str, status: str = "planned") -> "MediaItem":
        return MediaItem(
            id=str(uuid.uuid4())[:8],
            title=title.strip(),
            media_type=media_type,
            status=status,
            rating=None,
            notes="",
            added_at=date.today().isoformat(),
            completed_at=None,
        )

    @property
    def type_label(self) -> str:
        return MEDIA_TYPES.get(self.media_type, self.media_type)

    @property
    def status_label(self) -> str:
        return STATUSES.get(self.status, self.status)

    @property
    def color(self) -> str:
        return TYPE_COLORS.get(self.media_type, "#64748B")

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "MediaItem":
        return MediaItem(**data)


class MediaService:
    """Фасад бизнес-логики медиатрекера. UI работает только через этот класс."""

    def __init__(self) -> None:
        init_db()
        self._cache: list[MediaItem] = []
        self._reload()

    def _reload(self) -> None:
        self._cache = [MediaItem.from_dict(r) for r in fetch_all()]

    def get_all(self) -> list[MediaItem]:
        return list(self._cache)

    def get_by_status(self, status: str) -> list[MediaItem]:
        return [m for m in self._cache if m.status == status]

    def get_by_type(self, media_type: str) -> list[MediaItem]:
        return [m for m in self._cache if m.media_type == media_type]

    def add_item(self, title: str, media_type: str, status: str = "planned") -> MediaItem:
        """ValueError при пустом названии или неизвестном типе/статусе."""
        title = title.strip()
        if not title:
            raise ValueError("Название не может быть пустым")
        if media_type not in MEDIA_TYPES:
            raise ValueError(f"Неизвестный тип: {media_type!r}")
        if status not in STATUSES:
            raise ValueError(f"Неизвестный статус: {status!r}")
        item = MediaItem.new(title, media_type, status)
        insert(item.to_dict())
        self._reload()
        return item

    def edit_item(
        self,
        item_id: str,
        title: str,
        media_type: str,
        status: str,
        rating: Optional[int],
        notes: str,
    ) -> MediaItem:
        item = self._find(item_id)
        title = title.strip()
        if not title:
            raise ValueError("Название не может быть пустым")
        if rating is not None and not (1 <= rating <= 10):
            raise ValueError("Оценка должна быть от 1 до 10")

        item.title      = title
        item.media_type = media_type
        item.status     = status
        item.rating     = rating
        item.notes      = notes.strip()

        if status == "completed" and item.completed_at is None:
            item.completed_at = date.today().isoformat()
        elif status != "completed":
            item.completed_at = None

        update(item.to_dict())
        self._reload()
        return item

    def delete_item(self, item_id: str) -> None:
        self._find(item_id)
        delete(item_id)
        self._reload()

    def set_rating(self, item_id: str, rating: int) -> MediaItem:
        if not (1 <= rating <= 10):
            raise ValueError("Оценка должна быть от 1 до 10")
        item = self._find(item_id)
        item.rating = rating
        update(item.to_dict())
        self._reload()
        return item

    def count_by_status(self) -> dict[str, int]:
        result = {key: 0 for key in STATUSES}
        for m in self._cache:
            result[m.status] += 1
        return result

    def count_by_type(self) -> dict[str, int]:
        result = {key: 0 for key in MEDIA_TYPES}
        for m in self._cache:
            result[m.media_type] += 1
        return result

    def average_rating(self) -> Optional[float]:
        rated = [m.rating for m in self._cache if m.rating is not None]
        if not rated:
            return None
        return round(sum(rated) / len(rated), 1)

    def average_rating_by_type(self) -> dict[str, float]:
        result: dict[str, list[int]] = {key: [] for key in MEDIA_TYPES}
        for m in self._cache:
            if m.rating is not None:
                result[m.media_type].append(m.rating)
        return {
            key: round(sum(vals) / len(vals), 1)
            for key, vals in result.items() if vals
        }

    def top_rated(self, limit: int = 5) -> list[MediaItem]:
        rated = [m for m in self._cache if m.rating is not None]
        return sorted(rated, key=lambda m: m.rating, reverse=True)[:limit]

    def completed_this_year(self) -> int:
        year = date.today().year
        return sum(
            1 for m in self._cache
            if m.completed_at and date.fromisoformat(m.completed_at).year == year
        )

    def _find(self, item_id: str) -> MediaItem:
        for m in self._cache:
            if m.id == item_id:
                return m
        raise ValueError(f"Запись с id='{item_id}' не найдена")