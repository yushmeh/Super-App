import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import modules.media_tracker.api.storage as storage_module
from modules.media_tracker.logic.service import MediaItem, MediaService


@pytest.fixture
def service(tmp_path, monkeypatch):
    """MediaService с изолированной временной БД для каждого теста."""
    db_path = tmp_path / "test_media.db"
    monkeypatch.setattr(storage_module, "_DB_FILE", db_path)
    return MediaService()


class TestMediaItemModel:

    def test_new_item_status_planned_by_default(self) -> None:
        item = MediaItem.new("Интерстеллар", "film")
        assert item.status == "planned"

    def test_new_item_no_rating(self) -> None:
        item = MediaItem.new("Интерстеллар", "film")
        assert item.rating is None

    def test_new_item_strips_whitespace(self) -> None:
        item = MediaItem.new("  Интерстеллар  ", "film")
        assert item.title == "Интерстеллар"

    def test_type_label(self) -> None:
        item = MediaItem.new("Дюна", "book")
        assert "Книга" in item.type_label

    def test_status_label(self) -> None:
        item = MediaItem.new("Дюна", "book", status="in_progress")
        assert item.status_label == "В процессе"

    def test_color_known_type(self) -> None:
        item = MediaItem.new("Дюна", "game")
        assert item.color == "#39FF14"

    def test_to_dict_and_from_dict_roundtrip(self) -> None:
        item = MediaItem.new("Дюна", "book")
        restored = MediaItem.from_dict(item.to_dict())
        assert restored == item


class TestMediaServiceCRUD:

    def test_initial_empty(self, service: MediaService) -> None:
        assert service.get_all() == []

    def test_add_item(self, service: MediaService) -> None:
        item = service.add_item("Интерстеллар", "film")
        assert item.title == "Интерстеллар"
        assert len(service.get_all()) == 1

    def test_add_item_persists_after_reload(self, service: MediaService) -> None:
        service.add_item("Интерстеллар", "film")
        service._reload()
        assert len(service.get_all()) == 1

    def test_add_empty_title_raises(self, service: MediaService) -> None:
        with pytest.raises(ValueError, match="пустым"):
            service.add_item("", "film")

    def test_add_unknown_type_raises(self, service: MediaService) -> None:
        with pytest.raises(ValueError, match="тип"):
            service.add_item("Что-то", "podcast")

    def test_add_unknown_status_raises(self, service: MediaService) -> None:
        with pytest.raises(ValueError, match="статус"):
            service.add_item("Что-то", "film", status="watching_now")

    def test_get_by_status(self, service: MediaService) -> None:
        service.add_item("Фильм 1", "film", status="completed")
        service.add_item("Фильм 2", "film", status="planned")
        completed = service.get_by_status("completed")
        assert len(completed) == 1
        assert completed[0].title == "Фильм 1"

    def test_get_by_type(self, service: MediaService) -> None:
        service.add_item("Фильм", "film")
        service.add_item("Книга", "book")
        films = service.get_by_type("film")
        assert len(films) == 1

    def test_edit_item_updates_fields(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        updated = service.edit_item(
            item.id, "Дюна (изд. 2)", "book", "in_progress", 8, "Хорошая книга",
        )
        assert updated.title == "Дюна (изд. 2)"
        assert updated.rating == 8
        assert updated.notes == "Хорошая книга"

    def test_edit_item_empty_title_raises(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        with pytest.raises(ValueError, match="пустым"):
            service.edit_item(item.id, "", "book", "planned", None, "")

    def test_edit_item_invalid_rating_raises(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        with pytest.raises(ValueError, match="от 1 до 10"):
            service.edit_item(item.id, "Дюна", "book", "planned", 11, "")

    def test_edit_item_rating_zero_raises(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        with pytest.raises(ValueError, match="от 1 до 10"):
            service.edit_item(item.id, "Дюна", "book", "planned", 0, "")

    def test_edit_to_completed_sets_completed_at(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        assert item.completed_at is None
        updated = service.edit_item(item.id, "Дюна", "book", "completed", None, "")
        assert updated.completed_at == date.today().isoformat()

    def test_edit_away_from_completed_clears_date(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        service.edit_item(item.id, "Дюна", "book", "completed", None, "")
        updated = service.edit_item(item.id, "Дюна", "book", "in_progress", None, "")
        assert updated.completed_at is None

    def test_delete_item(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        service.delete_item(item.id)
        assert service.get_all() == []

    def test_delete_nonexistent_raises(self, service: MediaService) -> None:
        with pytest.raises(ValueError, match="не найдена"):
            service.delete_item("bad_id")

    def test_set_rating(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        updated = service.set_rating(item.id, 9)
        assert updated.rating == 9

    def test_set_rating_out_of_range_raises(self, service: MediaService) -> None:
        item = service.add_item("Дюна", "book")
        with pytest.raises(ValueError, match="от 1 до 10"):
            service.set_rating(item.id, 15)


class TestMediaServiceStats:

    def test_count_by_status(self, service: MediaService) -> None:
        service.add_item("A", "film", status="completed")
        service.add_item("B", "film", status="completed")
        service.add_item("C", "book", status="planned")
        counts = service.count_by_status()
        assert counts["completed"] == 2
        assert counts["planned"] == 1

    def test_count_by_type(self, service: MediaService) -> None:
        service.add_item("A", "film")
        service.add_item("B", "game")
        service.add_item("C", "game")
        counts = service.count_by_type()
        assert counts["game"] == 2
        assert counts["film"] == 1

    def test_average_rating_none_when_empty(self, service: MediaService) -> None:
        assert service.average_rating() is None

    def test_average_rating_calculated(self, service: MediaService) -> None:
        a = service.add_item("A", "film")
        b = service.add_item("B", "film")
        service.set_rating(a.id, 8)
        service.set_rating(b.id, 6)
        assert service.average_rating() == 7.0

    def test_average_rating_by_type(self, service: MediaService) -> None:
        a = service.add_item("A", "film")
        b = service.add_item("B", "book")
        service.set_rating(a.id, 10)
        service.set_rating(b.id, 6)
        result = service.average_rating_by_type()
        assert result["film"] == 10.0
        assert result["book"] == 6.0

    def test_top_rated_sorted_descending(self, service: MediaService) -> None:
        a = service.add_item("A", "film")
        b = service.add_item("B", "film")
        c = service.add_item("C", "film")
        service.set_rating(a.id, 5)
        service.set_rating(b.id, 9)
        service.set_rating(c.id, 7)
        top = service.top_rated(3)
        assert [t.title for t in top] == ["B", "C", "A"]

    def test_top_rated_respects_limit(self, service: MediaService) -> None:
        for i in range(10):
            item = service.add_item(f"Item {i}", "film")
            service.set_rating(item.id, i + 1)
        assert len(service.top_rated(5)) == 5

    def test_top_rated_excludes_unrated(self, service: MediaService) -> None:
        service.add_item("Без оценки", "film")
        rated = service.add_item("С оценкой", "film")
        service.set_rating(rated.id, 8)
        top = service.top_rated()
        assert len(top) == 1

    def test_completed_this_year(self, service: MediaService) -> None:
        item = service.add_item("Фильм", "film")
        service.edit_item(item.id, "Фильм", "film", "completed", None, "")
        assert service.completed_this_year() == 1

    def test_completed_this_year_excludes_other_statuses(self, service: MediaService) -> None:
        service.add_item("Фильм", "film", status="in_progress")
        assert service.completed_this_year() == 0