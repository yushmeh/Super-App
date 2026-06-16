import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, date, time, timedelta
from typing import Optional

from modules.schedule_tracker.api.storage import (
    init_db, fetch_all, insert, update, delete, set_active
)

LESSON_TYPES = {
    "lecture":  "Лекция",
    "practice": "Практика",
    "seminar":  "Семинар",
    "lab":      "Лабораторная",
    "exam":     "Экзамен",
    "other":    "Другое",
}

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

TYPE_COLORS = {
    "lecture":  "#00D4FF",
    "practice": "#39FF14",
    "seminar":  "#FFD700",
    "lab":      "#A855F7",
    "exam":     "#FF6B35",
    "other":    "#64748B",
}


@dataclass
class Lesson:
    id:          str
    title:       str        # Название предмета
    teacher:     str        # Преподаватель
    room:        str        # Аудитория
    lesson_type: str        # Ключ из LESSON_TYPES
    day_of_week: int        # 0=Пн, 6=Вс
    time_start:  str        # "HH:MM"
    time_end:    str        # "HH:MM"
    color:       str        # HEX-цвет
    is_active:   bool       # Активно / отменено

    @staticmethod
    def new(
        title: str,
        day_of_week: int,
        time_start: str,
        time_end: str,
        teacher: str = "",
        room: str = "",
        lesson_type: str = "lecture",
    ) -> "Lesson":
        color = TYPE_COLORS.get(lesson_type, TYPE_COLORS["other"])
        return Lesson(
            id=str(uuid.uuid4())[:8],
            title=title.strip(),
            teacher=teacher.strip(),
            room=room.strip(),
            lesson_type=lesson_type,
            day_of_week=day_of_week,
            time_start=time_start,
            time_end=time_end,
            color=color,
            is_active=True,
        )

    @property
    def start_time(self) -> time:
        h, m = map(int, self.time_start.split(":"))
        return time(h, m)

    @property
    def end_time(self) -> time:
        h, m = map(int, self.time_end.split(":"))
        return time(h, m)

    @property
    def duration_minutes(self) -> int:
        start = datetime.combine(date.today(), self.start_time)
        end   = datetime.combine(date.today(), self.end_time)
        return int((end - start).total_seconds() // 60)

    @property
    def type_label(self) -> str:
        return LESSON_TYPES.get(self.lesson_type, self.lesson_type)

    @property
    def day_name(self) -> str:
        return DAY_NAMES[self.day_of_week]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_active"] = 1 if self.is_active else 0
        return d

    @staticmethod
    def from_dict(data: dict) -> "Lesson":
        d = dict(data)
        d["is_active"] = bool(d.get("is_active", 1))
        return Lesson(**d)


class ScheduleEngine:
    """
    Фасад бизнес-логики расписания. UI работает только через этот класс.
    При инициализации создаёт/открывает SQLite БД.
    """

    def __init__(self) -> None:
        init_db()
        self._cache: list[Lesson] = []
        self._reload()

    def _reload(self) -> None:
        self._cache = [Lesson.from_dict(r) for r in fetch_all()]

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def get_all(self) -> list[Lesson]:
        return list(self._cache)

    def get_by_day(self, day: int) -> list[Lesson]:
        """Занятия на указанный день (0=Пн), отсортированные по времени начала."""
        return sorted(
            [l for l in self._cache if l.day_of_week == day],
            key=lambda l: l.time_start,
        )

    def add_lesson(
        self,
        title: str,
        day_of_week: int,
        time_start: str,
        time_end: str,
        teacher: str = "",
        room: str = "",
        lesson_type: str = "lecture",
    ) -> Lesson:
        """
        Создаёт занятие. ValueError при некорректных данных:
        - пустое название
        - day_of_week вне 0–6
        - неверный формат времени
        - время конца не позже времени начала
        - пересечение с существующим занятием того же дня
        """
        self._validate(title, day_of_week, time_start, time_end, exclude_id=None)
        lesson = Lesson.new(title, day_of_week, time_start, time_end, teacher, room, lesson_type)
        insert(lesson.to_dict())
        self._reload()
        return lesson

    def edit_lesson(
        self,
        lesson_id: str,
        title: str,
        day_of_week: int,
        time_start: str,
        time_end: str,
        teacher: str = "",
        room: str = "",
        lesson_type: str = "lecture",
    ) -> Lesson:
        lesson = self._find(lesson_id)
        self._validate(title, day_of_week, time_start, time_end, exclude_id=lesson_id)
        lesson.title       = title.strip()
        lesson.teacher     = teacher.strip()
        lesson.room        = room.strip()
        lesson.lesson_type = lesson_type
        lesson.day_of_week = day_of_week
        lesson.time_start  = time_start
        lesson.time_end    = time_end
        lesson.color       = TYPE_COLORS.get(lesson_type, TYPE_COLORS["other"])
        update(lesson.to_dict())
        self._reload()
        return lesson

    def delete_lesson(self, lesson_id: str) -> None:
        self._find(lesson_id)
        delete(lesson_id)
        self._reload()

    def toggle_active(self, lesson_id: str) -> Lesson:
        """Переключает статус занятия: активно / отменено."""
        lesson = self._find(lesson_id)
        lesson.is_active = not lesson.is_active
        set_active(lesson_id, lesson.is_active)
        self._reload()
        return lesson

    # ── Расчёты нагрузки ─────────────────────────────────────────────────────

    def hours_per_day(self) -> dict[str, float]:
        """Академические часы (45 мин = 1 ч) по дням недели."""
        result = {name: 0.0 for name in DAY_NAMES}
        for l in self._cache:
            if l.is_active:
                result[l.day_name] += round(l.duration_minutes / 45, 2)
        return result

    def hours_per_type(self) -> dict[str, float]:
        """Академические часы по типу занятия."""
        result: dict[str, float] = {}
        for l in self._cache:
            if l.is_active:
                label = l.type_label
                result[label] = round(result.get(label, 0.0) + l.duration_minutes / 45, 2)
        return result

    def total_hours_per_week(self) -> float:
        return round(sum(
            l.duration_minutes / 45 for l in self._cache if l.is_active
        ), 2)

    def next_lesson(self) -> Optional[tuple[Lesson, timedelta]]:
        """
        Возвращает ближайшее предстоящее занятие и timedelta до его начала.
        Смотрит в пределах текущей + следующей недели.
        Возвращает None если занятий нет.
        """
        now = datetime.now()
        today_dow = now.weekday()  # 0=Пн

        best_lesson: Optional[Lesson] = None
        best_delta: Optional[timedelta] = None

        for days_ahead in range(14):
            target_dow = (today_dow + days_ahead) % 7
            lessons_that_day = self.get_by_day(target_dow)
            for l in lessons_that_day:
                if not l.is_active:
                    continue
                h, m = map(int, l.time_start.split(":"))
                target_dt = datetime.combine(
                    now.date() + timedelta(days=days_ahead),
                    time(h, m),
                )
                delta = target_dt - now
                if delta.total_seconds() > 0:
                    if best_delta is None or delta < best_delta:
                        best_lesson = l
                        best_delta  = delta
                    break  # занятия отсортированы, берём первое подходящее

        if best_lesson and best_delta:
            return best_lesson, best_delta
        return None

    def current_lesson(self) -> Optional[Lesson]:
        """Возвращает занятие, идущее прямо сейчас (если есть)."""
        now = datetime.now()
        dow = now.weekday()
        current_time = now.strftime("%H:%M")
        for l in self.get_by_day(dow):
            if l.is_active and l.time_start <= current_time <= l.time_end:
                return l
        return None

    # ── Вспомогательные методы ────────────────────────────────────────────────

    def _find(self, lesson_id: str) -> Lesson:
        for l in self._cache:
            if l.id == lesson_id:
                return l
        raise ValueError(f"Занятие с id='{lesson_id}' не найдено")

    def _validate(
        self,
        title: str,
        day_of_week: int,
        time_start: str,
        time_end: str,
        exclude_id: Optional[str],
    ) -> None:
        if not title.strip():
            raise ValueError("Название занятия не может быть пустым")
        if day_of_week not in range(7):
            raise ValueError("Некорректный день недели (ожидается 0–6)")
        try:
            h_s, m_s = map(int, time_start.split(":"))
            h_e, m_e = map(int, time_end.split(":"))
            t_start = time(h_s, m_s)
            t_end   = time(h_e, m_e)
        except (ValueError, AttributeError):
            raise ValueError("Некорректный формат времени (ожидается HH:MM)")
        if t_end <= t_start:
            raise ValueError("Время окончания должно быть позже времени начала")

        # Проверка пересечений
        for existing in self._cache:
            if existing.id == exclude_id:
                continue
            if existing.day_of_week != day_of_week:
                continue
            if existing.time_start < time_end and existing.time_end > time_start:
                raise ValueError(
                    f"Пересечение с занятием «{existing.title}» "
                    f"({existing.time_start}–{existing.time_end})"
                )