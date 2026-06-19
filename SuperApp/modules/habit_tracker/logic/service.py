import uuid
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Optional

from modules.habit_tracker.api.storage import (
    load, save, export_to_file, import_from_file
)

# Статусы дня
DONE    = "done"
SKIPPED = "skipped"
NONE    = "none"


@dataclass
class Habit:
    id:         str
    name:       str
    emoji:      str             # иконка-эмодзи
    created_at: str             # ISO дата создания
    log:        dict[str, str]  # {"YYYY-MM-DD": "done"|"skipped"}

    @staticmethod
    def new(name: str, emoji: str = "⭐") -> "Habit":
        return Habit(
            id=str(uuid.uuid4())[:8],
            name=name.strip(),
            emoji=emoji,
            created_at=date.today().isoformat(),
            log={},
        )

    def status_on(self, day: date) -> str:
        """Статус привычки на конкретный день."""
        return self.log.get(day.isoformat(), NONE)

    def current_streak(self) -> int:
        """
        Текущая серия: количество дней подряд со статусом 'done'
        считая назад от сегодня (пропуски обрывают серию).
        """
        streak = 0
        day = date.today()
        while True:
            status = self.log.get(day.isoformat(), NONE)
            if status == DONE:
                streak += 1
                day -= timedelta(days=1)
            elif status == SKIPPED:
                # Пропуск обрывает серию
                break
            else:
                # Нет отметки: если это сегодня — продолжаем смотреть вчера,
                # если раньше — серия закончилась
                if day == date.today():
                    day -= timedelta(days=1)
                else:
                    break
        return streak

    def best_streak(self) -> int:
        """Лучшая серия 'done' за всё время."""
        if not self.log:
            return 0

        done_dates = sorted(
            date.fromisoformat(d)
            for d, s in self.log.items()
            if s == DONE
        )
        if not done_dates:
            return 0

        best = 1
        current = 1
        for i in range(1, len(done_dates)):
            if (done_dates[i] - done_dates[i - 1]).days == 1:
                current += 1
                best = max(best, current)
            else:
                current = 1
        return best

    def completion_rate(self, days: int = 30) -> float:
        """
        Процент выполнения за последние N дней.
        Учитываются только дни после создания привычки.
        """
        today = date.today()
        created = date.fromisoformat(self.created_at)
        done_count = 0
        total = 0
        for i in range(days):
            day = today - timedelta(days=i)
            if day < created:
                break
            total += 1
            if self.log.get(day.isoformat()) == DONE:
                done_count += 1
        if total == 0:
            return 0.0
        return round(done_count / total * 100, 1)

    def get_heatmap_data(self, weeks: int = 18) -> list[tuple[date, str]]:
        """
        Данные для тепловой карты: список (дата, статус) за последние N недель.
        Начинается с ближайшего понедельника назад.
        """
        today = date.today()
        # Начало с понедельника
        start = today - timedelta(days=today.weekday() + weeks * 7)
        result = []
        day = start
        while day <= today:
            result.append((day, self.log.get(day.isoformat(), NONE)))
            day += timedelta(days=1)
        return result


class HabitService:
    """Фасад бизнес-логики трекера привычек."""

    def __init__(self) -> None:
        self._data = load()

    def get_habits(self) -> list[Habit]:
        return [Habit(**h) for h in self._data["habits"]]

    def add_habit(self, name: str, emoji: str = "⭐") -> Habit:
        name = name.strip()
        if not name:
            raise ValueError("Название привычки не может быть пустым")
        if len(name) > 60:
            raise ValueError("Название не должно превышать 60 символов")
        habit = Habit.new(name, emoji)
        self._data["habits"].append(asdict(habit))
        save(self._data)
        return habit

    def rename_habit(self, habit_id: str, new_name: str) -> Habit:
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Название не может быть пустым")
        for h in self._data["habits"]:
            if h["id"] == habit_id:
                h["name"] = new_name
                save(self._data)
                return Habit(**h)
        raise ValueError("Привычка не найдена")

    def delete_habit(self, habit_id: str) -> None:
        before = len(self._data["habits"])
        self._data["habits"] = [h for h in self._data["habits"] if h["id"] != habit_id]
        if len(self._data["habits"]) == before:
            raise ValueError("Привычка не найдена")
        save(self._data)

    def mark(self, habit_id: str, status: str, day: Optional[date] = None) -> Habit:
        """
        Отмечает привычку на указанный день.
        """
        if status not in (DONE, SKIPPED):
            raise ValueError(f"Недопустимый статус: {status!r}")
        target_day = (day or date.today()).isoformat()

        for h in self._data["habits"]:
            if h["id"] == habit_id:
                if h["log"].get(target_day) == status:
                    # Повторный клик — снять отметку
                    del h["log"][target_day]
                else:
                    h["log"][target_day] = status
                save(self._data)
                return Habit(**h)
        raise ValueError("Привычка не найдена")

    def export(self, path: str) -> None:
        """Экспортирует все данные в JSON-файл."""
        export_to_file(self._data, path)

    def import_data(self, path: str, merge: bool = False) -> int:
        """
        Импортирует данные из JSON-файла.
        """
        imported = import_from_file(path)
        if merge:
            existing_ids = {h["id"] for h in self._data["habits"]}
            added = 0
            for h in imported["habits"]:
                if h["id"] not in existing_ids:
                    self._data["habits"].append(h)
                    added += 1
            save(self._data)
            return added
        else:
            self._data = imported
            save(self._data)
            return len(imported["habits"])