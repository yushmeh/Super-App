import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import modules.schedule_tracker.api.storage as storage_module
from modules.schedule_tracker.logic.engine import Lesson, ScheduleEngine


@pytest.fixture
def engine(tmp_path, monkeypatch):
    """ScheduleEngine с изолированной временной БД для каждого теста."""
    db_path = tmp_path / "test_schedule.db"
    monkeypatch.setattr(storage_module, "_DB_FILE", db_path)
    return ScheduleEngine()


class TestLessonModel:

    def test_new_lesson_is_active(self) -> None:
        lesson = Lesson.new("Матанализ", 0, "09:00", "10:30")
        assert lesson.is_active is True

    def test_new_lesson_strips_whitespace(self) -> None:
        lesson = Lesson.new("  Матанализ  ", 0, "09:00", "10:30")
        assert lesson.title == "Матанализ"

    def test_new_lesson_assigns_color_by_type(self) -> None:
        lesson = Lesson.new("Лаба", 0, "09:00", "10:30", lesson_type="lab")
        assert lesson.color == "#A855F7"

    def test_duration_minutes(self) -> None:
        lesson = Lesson.new("Пара", 0, "09:00", "10:30")
        assert lesson.duration_minutes == 90

    def test_type_label(self) -> None:
        lesson = Lesson.new("Пара", 0, "09:00", "10:30", lesson_type="seminar")
        assert lesson.type_label == "Семинар"

    def test_day_name(self) -> None:
        lesson = Lesson.new("Пара", 2, "09:00", "10:30")
        assert lesson.day_name == "Среда"

    def test_to_dict_converts_bool_to_int(self) -> None:
        lesson = Lesson.new("Пара", 0, "09:00", "10:30")
        d = lesson.to_dict()
        assert d["is_active"] == 1

    def test_from_dict_converts_int_to_bool(self) -> None:
        lesson = Lesson.from_dict({
            "id": "abc", "title": "Пара", "teacher": "", "room": "",
            "lesson_type": "lecture", "day_of_week": 0,
            "time_start": "09:00", "time_end": "10:30",
            "color": "#00D4FF", "is_active": 0,
        })
        assert lesson.is_active is False


class TestScheduleEngineCRUD:

    def test_initial_empty(self, engine: ScheduleEngine) -> None:
        assert engine.get_all() == []

    def test_add_lesson(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        assert lesson.title == "Матанализ"
        assert len(engine.get_all()) == 1

    def test_add_lesson_persists_after_reload(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        engine._reload()
        assert len(engine.get_all()) == 1

    def test_add_empty_title_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="пустым"):
            engine.add_lesson("", 0, "09:00", "10:30")

    def test_add_invalid_day_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="день недели"):
            engine.add_lesson("Пара", 7, "09:00", "10:30")

    def test_add_invalid_time_format_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="формат времени"):
            engine.add_lesson("Пара", 0, "9h00", "10:30")

    def test_add_end_before_start_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="позже"):
            engine.add_lesson("Пара", 0, "10:30", "09:00")

    def test_add_end_equal_start_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="позже"):
            engine.add_lesson("Пара", 0, "09:00", "09:00")

    def test_add_overlapping_lesson_raises(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        with pytest.raises(ValueError, match="Пересечение"):
            engine.add_lesson("Физика", 0, "10:00", "11:00")

    def test_add_non_overlapping_same_day_ok(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        lesson2 = engine.add_lesson("Физика", 0, "10:30", "12:00")
        assert lesson2.title == "Физика"

    def test_add_same_time_different_day_ok(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        lesson2 = engine.add_lesson("Физика", 1, "09:00", "10:30")
        assert lesson2.title == "Физика"

    def test_get_by_day_filters_correctly(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        engine.add_lesson("Физика", 1, "09:00", "10:30")
        monday_lessons = engine.get_by_day(0)
        assert len(monday_lessons) == 1
        assert monday_lessons[0].title == "Матанализ"

    def test_get_by_day_sorted_by_time(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Вторая пара", 0, "10:30", "12:00")
        engine.add_lesson("Первая пара", 0, "09:00", "10:30")
        lessons = engine.get_by_day(0)
        assert lessons[0].title == "Первая пара"

    def test_edit_lesson(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        updated = engine.edit_lesson(
            lesson.id, "Алгебра", 0, "09:00", "10:30",
        )
        assert updated.title == "Алгебра"

    def test_edit_lesson_allows_overlap_with_itself(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        # Редактирование того же занятия не должно конфликтовать с самим собой
        updated = engine.edit_lesson(lesson.id, "Матанализ", 0, "09:00", "11:00")
        assert updated.time_end == "11:00"

    def test_edit_nonexistent_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="не найдено"):
            engine.edit_lesson("bad_id", "Пара", 0, "09:00", "10:30")

    def test_delete_lesson(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        engine.delete_lesson(lesson.id)
        assert engine.get_all() == []

    def test_delete_nonexistent_raises(self, engine: ScheduleEngine) -> None:
        with pytest.raises(ValueError, match="не найдено"):
            engine.delete_lesson("bad_id")

    def test_toggle_active(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Матанализ", 0, "09:00", "10:30")
        updated = engine.toggle_active(lesson.id)
        assert updated.is_active is False
        updated2 = engine.toggle_active(lesson.id)
        assert updated2.is_active is True


class TestScheduleEngineWorkload:

    def test_hours_per_day(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Пара", 0, "09:00", "10:30")  # 90 минут = 2 ак.ч.
        hours = engine.hours_per_day()
        assert hours["Понедельник"] == pytest.approx(2.0)

    def test_hours_per_day_excludes_inactive(self, engine: ScheduleEngine) -> None:
        lesson = engine.add_lesson("Пара", 0, "09:00", "10:30")
        engine.toggle_active(lesson.id)
        hours = engine.hours_per_day()
        assert hours["Понедельник"] == 0.0

    def test_hours_per_type(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Лекция", 0, "09:00", "10:30", lesson_type="lecture")
        hours = engine.hours_per_type()
        assert hours["Лекция"] == pytest.approx(2.0)

    def test_total_hours_per_week(self, engine: ScheduleEngine) -> None:
        engine.add_lesson("Пара1", 0, "09:00", "10:30")
        engine.add_lesson("Пара2", 1, "09:00", "10:30")
        assert engine.total_hours_per_week() == pytest.approx(4.0)


class TestScheduleEngineTimer:

    def test_current_lesson_none_when_no_lessons(self, engine: ScheduleEngine) -> None:
        assert engine.current_lesson() is None

    def test_current_lesson_detects_ongoing(self, engine: ScheduleEngine) -> None:
        now = datetime.now()
        dow = now.weekday()
        start = (now - timedelta(minutes=10)).strftime("%H:%M")
        end   = (now + timedelta(minutes=10)).strftime("%H:%M")
        engine.add_lesson("Текущая пара", dow, start, end)
        current = engine.current_lesson()
        assert current is not None
        assert current.title == "Текущая пара"

    def test_next_lesson_none_when_empty(self, engine: ScheduleEngine) -> None:
        assert engine.next_lesson() is None

    def test_next_lesson_finds_upcoming(self, engine: ScheduleEngine) -> None:
        now = datetime.now()
        dow = now.weekday()
        future_start = (now + timedelta(hours=1)).strftime("%H:%M")
        future_end   = (now + timedelta(hours=2)).strftime("%H:%M")
        engine.add_lesson("Будущая пара", dow, future_start, future_end)
        result = engine.next_lesson()
        assert result is not None
        lesson, delta = result
        assert lesson.title == "Будущая пара"
        assert delta.total_seconds() > 0

    def test_next_lesson_ignores_inactive(self, engine: ScheduleEngine) -> None:
        now = datetime.now()
        dow = now.weekday()
        future_start = (now + timedelta(hours=1)).strftime("%H:%M")
        future_end   = (now + timedelta(hours=2)).strftime("%H:%M")
        lesson = engine.add_lesson("Отменённая", dow, future_start, future_end)
        engine.toggle_active(lesson.id)
        result = engine.next_lesson()
        assert result is None