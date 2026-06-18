import sys
import os
import pytest
from datetime import date, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.budget_tracker.logic.service import Transaction, Category, Goal, BudgetService


def _empty_data() -> dict:
    return {"transactions": [], "categories": [], "goals": []}


@pytest.fixture
def service():
    with patch("modules.budget_tracker.logic.service.load", return_value=_empty_data()), \
         patch("modules.budget_tracker.logic.service.save"):
        yield BudgetService()


class TestTransactionModel:

    def test_new_amount_rounded(self) -> None:
        tx = Transaction.new("expense", 99.999, "Продукты")
        assert tx.amount == 100.0

    def test_new_amount_always_positive(self) -> None:
        tx = Transaction.new("expense", -50, "Продукты")
        assert tx.amount == 50.0

    def test_new_uses_today_by_default(self) -> None:
        tx = Transaction.new("income", 1000, "Зарплата")
        assert tx.tx_date == date.today().isoformat()

    def test_new_with_custom_date(self) -> None:
        custom = date(2024, 1, 1)
        tx = Transaction.new("income", 1000, "Зарплата", date_arg=custom)
        assert tx.tx_date == "2024-01-01"

    def test_date_obj_property(self) -> None:
        tx = Transaction.new("expense", 100, "Продукты", date_arg=date(2024, 5, 10))
        assert tx.date_obj == date(2024, 5, 10)


class TestCategoryModel:

    def test_new_category_not_builtin(self) -> None:
        cat = Category.new("Спорт", "🏋️")
        assert cat.builtin is False

    def test_new_category_default_kind(self) -> None:
        cat = Category.new("Спорт")
        assert cat.kind == "expense"


class TestGoalModel:

    def test_new_goal_starts_at_zero(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        assert goal.saved == 0.0

    def test_progress_pct_zero_when_unsaved(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        assert goal.progress_pct == 0.0

    def test_progress_pct_50_percent(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        goal.saved = 25000
        assert goal.progress_pct == 50.0

    def test_progress_pct_capped_at_100(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        goal.saved = 80000
        assert goal.progress_pct == 100.0

    def test_progress_pct_zero_target(self) -> None:
        goal = Goal.new("Цель", 1)
        goal.target = 0
        assert goal.progress_pct == 0.0

    def test_remaining_calculated(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        goal.saved = 30000
        assert goal.remaining == 20000.0

    def test_remaining_never_negative(self) -> None:
        goal = Goal.new("Ноутбук", 50000)
        goal.saved = 80000
        assert goal.remaining == 0.0


class TestBudgetServiceCategories:

    def test_builtin_categories_created(self, service: BudgetService) -> None:
        expense_cats = service.get_categories("expense")
        income_cats = service.get_categories("income")
        assert len(expense_cats) == 10
        assert len(income_cats) == 7

    def test_get_categories_filters_by_kind(self, service: BudgetService) -> None:
        income_cats = service.get_categories("income")
        assert all(c.kind == "income" for c in income_cats)

    def test_add_custom_category(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            cat = service.add_category("Спорт", "🏋️", "expense")
        assert cat.name == "Спорт"
        assert any(c.name == "Спорт" for c in service.get_categories("expense"))

    def test_add_duplicate_category_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="уже существует"):
            with patch("modules.budget_tracker.logic.service.save"):
                service.add_category("Продукты")

    def test_add_empty_category_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="пустым"):
            with patch("modules.budget_tracker.logic.service.save"):
                service.add_category("")

    def test_delete_custom_category(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            cat = service.add_category("Временная")
        with patch("modules.budget_tracker.logic.service.save"):
            service.delete_category(cat.id)
        assert not any(c.id == cat.id for c in service.get_categories("expense"))

    def test_delete_builtin_category_raises(self, service: BudgetService) -> None:
        builtin = service.get_categories("expense")[0]
        with pytest.raises(ValueError, match="нельзя удалить"):
            service.delete_category(builtin.id)

    def test_delete_nonexistent_category_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="не найдена"):
            service.delete_category("bad_id")


class TestBudgetServiceTransactions:

    def test_add_income(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("income", 50000, "Зарплата")
        assert service.get_total_income() == 50000.0

    def test_add_expense(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("expense", 1500, "Продукты")
        assert service.get_total_expenses() == 1500.0

    def test_add_transaction_zero_amount_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="больше нуля"):
            service.add_transaction("expense", 0, "Продукты")

    def test_add_transaction_negative_amount_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="больше нуля"):
            service.add_transaction("expense", -100, "Продукты")

    def test_balance_income_minus_expense(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("income", 10000, "Зарплата")
            service.add_transaction("expense", 3000, "Продукты")
        assert service.get_balance() == 7000.0

    def test_balance_negative_when_overspent(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("income", 1000, "Зарплата")
            service.add_transaction("expense", 5000, "Продукты")
        assert service.get_balance() == -4000.0

    def test_delete_transaction(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            tx = service.add_transaction("expense", 100, "Продукты")
        with patch("modules.budget_tracker.logic.service.save"):
            service.delete_transaction(tx.id)
        assert service.get_all_transactions() == []

    def test_recent_transactions_limit(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            for i in range(15):
                service.add_transaction("expense", 10 + i, "Продукты")
        assert len(service.get_recent_transactions(10)) == 10

    def test_recent_transactions_newest_first(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("expense", 100, "Продукты", date_arg=date(2024, 1, 1))
            service.add_transaction("expense", 200, "Продукты", date_arg=date(2024, 6, 1))
        recent = service.get_recent_transactions()
        assert recent[0].amount == 200.0

    def test_expenses_by_category_this_month(self, service: BudgetService) -> None:
        today = date.today()
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("expense", 500, "Продукты", date_arg=today)
            service.add_transaction("expense", 300, "Транспорт", date_arg=today)
            service.add_transaction("expense", 200, "Продукты", date_arg=today - timedelta(days=400))
        result = service.get_expenses_by_category_this_month()
        assert result.get("Продукты") == 500.0
        assert result.get("Транспорт") == 300.0

    def test_expenses_excludes_income(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_transaction("income", 1000, "Зарплата")
        result = service.get_expenses_by_category_this_month()
        assert "Зарплата" not in result


class TestBudgetServiceGoals:

    def test_add_goal(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            goal = service.add_goal("Ноутбук", 50000)
        assert goal.name == "Ноутбук"
        assert goal.saved == 0.0

    def test_add_goal_empty_name_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="пустым"):
            service.add_goal("", 50000)

    def test_add_goal_zero_target_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="больше нуля"):
            service.add_goal("Цель", 0)

    def test_add_to_goal_increases_saved(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            goal = service.add_goal("Ноутбук", 50000)
        with patch("modules.budget_tracker.logic.service.save"):
            updated = service.add_to_goal(goal.id, 10000)
        assert updated.saved == 10000.0

    def test_add_to_goal_accumulates(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            goal = service.add_goal("Ноутбук", 50000)
        with patch("modules.budget_tracker.logic.service.save"):
            service.add_to_goal(goal.id, 10000)
            updated = service.add_to_goal(goal.id, 5000)
        assert updated.saved == 15000.0

    def test_add_to_goal_zero_amount_raises(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            goal = service.add_goal("Ноутбук", 50000)
        with pytest.raises(ValueError, match="больше нуля"):
            service.add_to_goal(goal.id, 0)

    def test_add_to_nonexistent_goal_raises(self, service: BudgetService) -> None:
        with pytest.raises(ValueError, match="не найдена"):
            service.add_to_goal("bad_id", 1000)

    def test_delete_goal(self, service: BudgetService) -> None:
        with patch("modules.budget_tracker.logic.service.save"):
            goal = service.add_goal("Ноутбук", 50000)
        with patch("modules.budget_tracker.logic.service.save"):
            service.delete_goal(goal.id)
        assert service.get_goals() == []