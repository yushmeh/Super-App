import uuid
from dataclasses import dataclass, asdict
from datetime import date
from typing import Optional

from modules.budget_tracker.api.storage import load, save


@dataclass
class Transaction:
    id:         str
    kind:       str    # "income" | "expense"
    amount:     float
    category:   str
    note:       str
    tx_date:    str    # ISO формат: "YYYY-MM-DD"

    @staticmethod
    def new(
        kind: str,
        amount: float,
        category: str,
        note: str = "",
        date_arg: Optional[date] = None,
    ) -> "Transaction":
        return Transaction(
            id=str(uuid.uuid4())[:8],
            kind=kind,
            amount=round(abs(amount), 2),
            category=category,
            note=note,
            tx_date=(date_arg or date.today()).isoformat(),
        )

    @property
    def date_obj(self) -> date:
        return date.fromisoformat(self.tx_date)


@dataclass
class Category:
    id:       str
    name:     str
    icon:     str
    builtin:  bool
    kind:     str   # "income" | "expense" | "both"

    @staticmethod
    def new(name: str, icon: str = "📦", kind: str = "expense") -> "Category":
        return Category(id=str(uuid.uuid4())[:8], name=name, icon=icon, builtin=False, kind=kind)


@dataclass
class Goal:
    id:          str
    name:        str
    target:      float
    saved:       float
    icon:        str
    created_at:  str

    @staticmethod
    def new(name: str, target: float, icon: str = "🎯") -> "Goal":
        return Goal(
            id=str(uuid.uuid4())[:8],
            name=name,
            target=round(abs(target), 2),
            saved=0.0,
            icon=icon,
            created_at=date.today().isoformat(),
        )

    @property
    def progress_pct(self) -> float:
        if self.target <= 0:
            return 0.0
        return min(100.0, round(self.saved / self.target * 100, 1))

    @property
    def remaining(self) -> float:
        return max(0.0, round(self.target - self.saved, 2))


# Встроенные категории расходов
_BUILTIN_EXPENSE: list[tuple[str, str]] = [
    ("Продукты",         "🛒"),
    ("Транспорт",        "🚌"),
    ("Жильё",            "🏠"),
    ("Развлечения",      "🎮"),
    ("Здоровье",         "💊"),
    ("Одежда",           "👕"),
    ("Кафе и рестораны", "☕"),
    ("Образование",      "📚"),
    ("Связь",            "📱"),
    ("Прочее",           "📦"),
]

# Встроенные категории доходов
_BUILTIN_INCOME: list[tuple[str, str]] = [
    ("Зарплата",         "💼"),
    ("Стипендия",        "🎓"),
    ("Подработка",       "🔧"),
    ("Фриланс",          "💻"),
    ("Подарок",          "🎁"),
    ("Возврат средств",  "↩️"),
    ("Другой доход",     "💰"),
]


class BudgetService:
    """Фасад бизнес-логики. UI работает только через этот класс."""

    def __init__(self) -> None:
        self._data = load()
        self._migrate_transactions()
        self._ensure_builtin_categories()

    def _migrate_transactions(self) -> None:
        """
        Миграция старых записей: поле "date" → "tx_date".
        Запускается один раз при старте — исправляет данные сохранённые
        до переименования поля.
        """
        changed = False
        for t in self._data["transactions"]:
            if "date" in t and "tx_date" not in t:
                t["tx_date"] = t.pop("date")
                changed = True
        if changed:
            save(self._data)

    def _ensure_builtin_categories(self) -> None:
        existing = {c["name"] for c in self._data["categories"]}
        changed = False
        for name, icon in _BUILTIN_EXPENSE:
            if name not in existing:
                self._data["categories"].append(
                    asdict(Category(str(uuid.uuid4())[:8], name, icon, True, "expense"))
                )
                changed = True
        for name, icon in _BUILTIN_INCOME:
            if name not in existing:
                self._data["categories"].append(
                    asdict(Category(str(uuid.uuid4())[:8], name, icon, True, "income"))
                )
                changed = True
        if changed:
            save(self._data)

    def get_categories(self, kind: str = "expense") -> list[Category]:
        """
        Возвращает категории по типу транзакции.
        kind="expense" → только расходные
        kind="income"  → только доходные
        """
        result = []
        for c in self._data["categories"]:
            # Поддержка старых записей без поля kind
            cat_kind = c.get("kind", "expense")
            if cat_kind == kind or cat_kind == "both":
                result.append(Category(**{**c, "kind": cat_kind}))
        return result

    def add_category(self, name: str, icon: str = "📦", kind: str = "expense") -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Название категории не может быть пустым")
        existing = {c["name"].lower() for c in self._data["categories"]}
        if name.lower() in existing:
            raise ValueError(f"Категория «{name}» уже существует")
        cat = Category.new(name, icon, kind)
        self._data["categories"].append(asdict(cat))
        save(self._data)
        return cat

    def delete_category(self, category_id: str) -> None:
        cats = self._data["categories"]
        target = next((c for c in cats if c["id"] == category_id), None)
        if target is None:
            raise ValueError("Категория не найдена")
        if target.get("builtin", False):
            raise ValueError("Встроенные категории нельзя удалить")
        self._data["categories"] = [c for c in cats if c["id"] != category_id]
        save(self._data)

    def add_transaction(
        self,
        kind: str,
        amount: float,
        category: str,
        note: str = "",
        date_arg: Optional[date] = None,
    ) -> Transaction:
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
        tx = Transaction.new(kind, amount, category, note, date_arg)
        self._data["transactions"].append(asdict(tx))
        save(self._data)
        return tx

    def delete_transaction(self, tx_id: str) -> None:
        self._data["transactions"] = [
            t for t in self._data["transactions"] if t["id"] != tx_id
        ]
        save(self._data)

    def get_all_transactions(self) -> list[Transaction]:
        # Сортируем по дате (убывание), при одинаковой дате — по порядку добавления (убывание)
        indexed = list(enumerate(self._data["transactions"]))
        indexed.sort(key=lambda x: (x[1]["tx_date"], x[0]), reverse=True)
        return [Transaction(**t) for _, t in indexed]

    def get_recent_transactions(self, limit: int = 10) -> list[Transaction]:
        return self.get_all_transactions()[:limit]

    def get_balance(self) -> float:
        total = 0.0
        for t in self._data["transactions"]:
            total += t["amount"] if t["kind"] == "income" else -t["amount"]
        return round(total, 2)

    def get_total_income(self) -> float:
        return round(sum(
            t["amount"] for t in self._data["transactions"] if t["kind"] == "income"
        ), 2)

    def get_total_expenses(self) -> float:
        return round(sum(
            t["amount"] for t in self._data["transactions"] if t["kind"] == "expense"
        ), 2)

    def get_expenses_by_category_this_month(self) -> dict[str, float]:
        """Расходы по категориям за текущий месяц, отсортированные по убыванию."""
        today = date.today()
        result: dict[str, float] = {}
        for t in self._data["transactions"]:
            if t["kind"] != "expense":
                continue
            # Поддержка обоих вариантов ключа (старые данные могли сохраниться как "date")
            raw_date = t.get("tx_date") or t.get("date", "")
            if not raw_date:
                continue
            tx_date = date.fromisoformat(raw_date)
            if tx_date.year != today.year or tx_date.month != today.month:
                continue
            result[t["category"]] = round(result.get(t["category"], 0.0) + t["amount"], 2)
        return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))

    def get_goals(self) -> list[Goal]:
        return [Goal(**g) for g in self._data["goals"]]

    def add_goal(self, name: str, target: float, icon: str = "🎯") -> Goal:
        name = name.strip()
        if not name:
            raise ValueError("Название цели не может быть пустым")
        if target <= 0:
            raise ValueError("Целевая сумма должна быть больше нуля")
        goal = Goal.new(name, target, icon)
        self._data["goals"].append(asdict(goal))
        save(self._data)
        return goal

    def add_to_goal(self, goal_id: str, amount: float) -> Goal:
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть больше нуля")
        for g in self._data["goals"]:
            if g["id"] == goal_id:
                g["saved"] = round(g["saved"] + amount, 2)
                save(self._data)
                return Goal(**g)
        raise ValueError("Цель не найдена")

    def delete_goal(self, goal_id: str) -> None:
        self._data["goals"] = [g for g in self._data["goals"] if g["id"] != goal_id]
        save(self._data)