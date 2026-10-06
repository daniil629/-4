from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from content import LESSONS, TASKS, LEVEL_NAMES


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📚 Теория", callback_data="menu:theory")
    kb.button(text="🎯 Практика", callback_data="menu:practice")
    kb.button(text="👤 Досье", callback_data="menu:profile")
    kb.adjust(1)
    return kb.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 В главное меню", callback_data="menu:main")
    return kb.as_markup()


def theory_levels_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Начальный", callback_data="theory:list:beginner")
    kb.button(text="🟡 Средний", callback_data="theory:list:intermediate")
    kb.button(text="🔴 Профессиональный", callback_data="theory:list:pro")
    kb.button(text="🏠 В главное меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def lessons_list_kb(level: str, completed: set) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for lesson in LESSONS:
        if lesson["level"] != level:
            continue
        mark = "✅" if lesson["id"] in completed else "📖"
        kb.button(
            text=f"{mark} {lesson['id']}. {lesson['title']}",
            callback_data=f"theory:open:{lesson['id']}"
        )
    kb.button(text="⬅️ К уровням", callback_data="menu:theory")
    kb.button(text="🏠 В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def lesson_view_kb(lesson_id: str, is_completed: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if not is_completed:
        kb.button(text="✅ Отметить как пройденный", callback_data=f"theory:done:{lesson_id}")
    kb.button(text="⬅️ К урокам", callback_data="theory:back")
    kb.button(text="🏠 Меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def practice_levels_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Начальный", callback_data="practice:list:beginner")
    kb.button(text="🟡 Средний", callback_data="practice:list:intermediate")
    kb.button(text="🔴 Профессиональный", callback_data="practice:list:pro")
    kb.button(text="🏠 В главное меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def tasks_list_kb(level: str, completed: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, task in enumerate(TASKS[level]):
        if task["id"] in completed:
            mark = "✅" if completed[task["id"]] else "❌"
        else:
            mark = "🎯"
        kb.button(
            text=f"{mark} {i+1}. {task['title']}",
            callback_data=f"practice:open:{level}:{i}"
        )
    kb.button(text="⬅️ К уровням", callback_data="menu:practice")
    kb.button(text="🏠 В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def task_options_kb(level: str, idx: int, options: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    letters = ["A", "B", "C", "D"]
    for i in range(len(options)):
        kb.button(
            text=letters[i],
            callback_data=f"practice:answer:{level}:{idx}:{i}"
        )
    kb.button(text="⬅️ К задачам", callback_data=f"practice:list:{level}")
    kb.adjust(4, 1)   # 4 кнопки в ряд + кнопка назад
    return kb.as_markup()


def after_answer_kb(level: str, idx: int, has_next: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_next:
        kb.button(text="➡️ Следующая задача", callback_data=f"practice:open:{level}:{idx+1}")
    kb.button(text="📋 К списку задач", callback_data=f"practice:list:{level}")
    kb.button(text="🏠 В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()
