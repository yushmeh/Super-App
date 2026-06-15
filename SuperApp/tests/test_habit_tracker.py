import sys
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.habit_tracker.logic.service import Habit, HabitService, DONE, SKIPPED, NONE


def _empty_data() -> dict:
    return {"habits": []}


@pytest.fixture
def service():
    with patch("modules.habit_tracker.logic.service.load", return_value=_empty_data()), \
         patch("modules.habit_tracker.logic.service.save"):
        yield HabitService()


@pytest.fixture
def habit() -> Habit:
    return Habit.new("Зарядка")


class TestHabitModel:

    def test_new_habit_has_empty_log(self, habit: Habit) -> None:
        assert habit.log == {}

    def test_new_habit_created_today(self, habit: Habit) -> None:
        assert habit.created_at == date.today().isoformat()

    def test_status_none_by_default(self, habit: Habit) -> None:
        assert habit.status_on(date.today()) == NONE

    def test_status_returns_set_value(self, habit: Habit) -> None:
        habit.log[date.today().isoformat()] = DONE
        assert habit.status_on(date.today()) == DONE

    def test_streak_zero_empty(self, habit: Habit) -> None:
        assert habit.current_streak() == 0

    def test_streak_one_after_done_today(self, habit: Habit) -> None:
        habit.log[date.today().isoformat()] = DONE
        assert habit.current_streak() == 1

    def test_streak_five_consecutive(self, habit: Habit) -> None:
        today = date.today()
        for i in range(5):
            habit.log[(today - timedelta(days=i)).isoformat()] = DONE
        assert habit.current_streak() == 5

    def test_streak_breaks_on_skip(self, habit: Habit) -> None:
        today = date.today()
        habit.log[today.isoformat()] = DONE
        habit.log[(today - timedelta(1)).isoformat()] = DONE
        habit.log[(today - timedelta(2)).isoformat()] = SKIPPED
        habit.log[(today - timedelta(3)).isoformat()] = DONE
        assert habit.current_streak() == 2

    def test_streak_breaks_on_gap(self, habit: Habit) -> None:
        today = date.today()
        habit.log[today.isoformat()] = DONE
        habit.log[(today - timedelta(2)).isoformat()] = DONE
        assert habit.current_streak() == 1

    def test_streak_counts_yesterday_when_today_empty(self, habit: Habit) -> None:
        habit.log[(date.today() - timedelta(1)).isoformat()] = DONE
        assert habit.current_streak() == 1

    def test_skipped_today_breaks_streak(self, habit: Habit) -> None:
        today = date.today()
        habit.log[today.isoformat()] = SKIPPED
        habit.log[(today - timedelta(1)).isoformat()] = DONE
        assert habit.current_streak() == 0

    def test_best_streak_zero_empty(self, habit: Habit) -> None:
        assert habit.best_streak() == 0

    def test_best_streak_finds_longest(self, habit: Habit) -> None:
        today = date.today()
        for i in range(3):
            habit.log[(today - timedelta(i)).isoformat()] = DONE
        base = today - timedelta(10)
        for i in range(5):
            habit.log[(base + timedelta(i)).isoformat()] = DONE
        assert habit.best_streak() == 5

    def test_best_streak_ignores_skips(self, habit: Habit) -> None:
        for i in range(5):
            habit.log[(date.today() - timedelta(i)).isoformat()] = SKIPPED
        assert habit.best_streak() == 0

    def test_completion_100_all_done(self, habit: Habit) -> None:
        today = date.today()
        created = date.fromisoformat(habit.created_at)
        for i in range(7):
            day = today - timedelta(i)
            if day >= created:
                habit.log[day.isoformat()] = DONE
        assert habit.completion_rate(7) == 100.0

    def test_completion_50_percent(self, habit: Habit) -> None:
        today = date.today()
        # Сдвигаем дату создания назад, чтобы все 10 дней попали в расчёт
        habit.created_at = (today - timedelta(days=10)).isoformat()
        for i in range(10):
            if i % 2 == 0:
                habit.log[(today - timedelta(i)).isoformat()] = DONE
        assert habit.completion_rate(10) == 50.0

    def test_heatmap_ends_today(self, habit: Habit) -> None:
        data = habit.get_heatmap_data(4)
        assert data[-1][0] == date.today()

    def test_heatmap_statuses_valid(self, habit: Habit) -> None:
        data = habit.get_heatmap_data(4)
        assert all(s in (DONE, SKIPPED, NONE) for _, s in data)


class TestHabitService:

    def test_initial_empty(self, service: HabitService) -> None:
        assert service.get_habits() == []

    def test_add_habit(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Медитация", "🧘")
        habits = service.get_habits()
        assert len(habits) == 1
        assert habits[0].name == "Медитация"
        assert habits[0].emoji == "🧘"

    def test_add_strips_whitespace(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("  Бег  ")
        assert service.get_habits()[0].name == "Бег"

    def test_add_empty_name_raises(self, service: HabitService) -> None:
        with pytest.raises(ValueError, match="пустым"):
            with patch("modules.habit_tracker.logic.service.save"):
                service.add_habit("")

    def test_add_too_long_raises(self, service: HabitService) -> None:
        with pytest.raises(ValueError, match="60"):
            with patch("modules.habit_tracker.logic.service.save"):
                service.add_habit("А" * 61)

    def test_delete_habit(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Удалить")
        habit_id = service.get_habits()[0].id
        with patch("modules.habit_tracker.logic.service.save"):
            service.delete_habit(habit_id)
        assert service.get_habits() == []

    def test_delete_nonexistent_raises(self, service: HabitService) -> None:
        with pytest.raises(ValueError):
            service.delete_habit("bad_id")

    def test_rename_habit(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Старое")
        habit_id = service.get_habits()[0].id
        with patch("modules.habit_tracker.logic.service.save"):
            service.rename_habit(habit_id, "Новое")
        assert service.get_habits()[0].name == "Новое"

    def test_rename_empty_raises(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        with pytest.raises(ValueError):
            service.rename_habit(habit_id, "")

    def test_mark_done(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        with patch("modules.habit_tracker.logic.service.save"):
            updated = service.mark(habit_id, DONE)
        assert updated.status_on(date.today()) == DONE

    def test_mark_toggle_removes(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        with patch("modules.habit_tracker.logic.service.save"):
            service.mark(habit_id, DONE)
            updated = service.mark(habit_id, DONE)
        assert updated.status_on(date.today()) == NONE

    def test_mark_switches_status(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        with patch("modules.habit_tracker.logic.service.save"):
            service.mark(habit_id, DONE)
            updated = service.mark(habit_id, SKIPPED)
        assert updated.status_on(date.today()) == SKIPPED

    def test_mark_invalid_status_raises(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        with pytest.raises(ValueError, match="Недопустимый статус"):
            service.mark(habit_id, "invalid")

    def test_mark_bad_id_raises(self, service: HabitService) -> None:
        with pytest.raises(ValueError):
            service.mark("bad_id", DONE)

    def test_mark_specific_day(self, service: HabitService) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Привычка")
        habit_id = service.get_habits()[0].id
        yesterday = date.today() - timedelta(1)
        with patch("modules.habit_tracker.logic.service.save"):
            updated = service.mark(habit_id, DONE, day=yesterday)
        assert updated.status_on(yesterday) == DONE
        assert updated.status_on(date.today()) == NONE


class TestExportImport:

    def test_export_creates_valid_json(self, service: HabitService, tmp_path) -> None:
        with patch("modules.habit_tracker.logic.service.save"):
            service.add_habit("Тест")
        path = str(tmp_path / "export.json")
        from modules.habit_tracker.api.storage import export_to_file
        export_to_file(service._data, path)
        import json
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "habits" in data
        assert len(data["habits"]) == 1

    def test_import_replace(self, tmp_path) -> None:
        import json
        path = str(tmp_path / "import.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"habits": [
                {"id": "aaa", "name": "Импорт", "emoji": "⭐",
                 "created_at": "2024-01-01", "log": {}}
            ]}, f)
        with patch("modules.habit_tracker.logic.service.load", return_value=_empty_data()), \
             patch("modules.habit_tracker.logic.service.save"):
            svc = HabitService()
            count = svc.import_data(path, merge=False)
        assert count == 1

    def test_import_merge_skips_duplicates(self, tmp_path) -> None:
        import json
        with patch("modules.habit_tracker.logic.service.load", return_value=_empty_data()), \
             patch("modules.habit_tracker.logic.service.save"):
            svc = HabitService()
            svc.add_habit("Существующая")
            existing_id = svc.get_habits()[0].id
            path = str(tmp_path / "merge.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"habits": [
                    {"id": existing_id, "name": "Существующая", "emoji": "⭐",
                     "created_at": "2024-01-01", "log": {}},
                    {"id": "new123", "name": "Новая", "emoji": "💪",
                     "created_at": "2024-01-01", "log": {}},
                ]}, f)
            added = svc.import_data(path, merge=True)
        assert added == 1

    def test_import_invalid_format_raises(self, tmp_path) -> None:
        import json
        path = str(tmp_path / "bad.json")
        with open(path, "w") as f:
            json.dump({"wrong": []}, f)
        with patch("modules.habit_tracker.logic.service.load", return_value=_empty_data()), \
             patch("modules.habit_tracker.logic.service.save"):
            svc = HabitService()
            with pytest.raises(ValueError, match="Неверный формат"):
                svc.import_data(path)