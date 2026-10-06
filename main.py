import random
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TOKEN
from database import db
from content import LESSONS, TASKS, LEVEL_NAMES, ACHIEVEMENTS, get_agent_rank
from keyboards import (
    main_menu_kb, theory_levels_kb, lessons_list_kb, lesson_view_kb,
    practice_levels_kb, tasks_list_kb, task_options_kb, after_answer_kb,
    back_to_menu_kb
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ---------- СТАРТ ----------
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await db.ensure_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )
    await message.answer(
        "<b>Академия Кошкомальчиков</b>\n\n"
        "Добро пожаловать.\n"
        "Здесь готовят тех, кто умеет находить людей, компании и цифровые следы.\n\n"
        "Выбери раздел:",
        reply_markup=main_menu_kb()
    )


# ---------- ГЛАВНОЕ МЕНЮ ----------
@dp.callback_query(F.data == "menu:main")
async def menu_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Академия Кошкомальчиков</b>\n\nВыбери раздел:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:theory")
async def menu_theory(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Теория</b>\n\nВыбери уровень:",
        reply_markup=theory_levels_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "menu:practice")
async def menu_practice(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Практика</b>\n\nВыбери уровень:",
        reply_markup=practice_levels_kb()
    )
    await callback.answer()


# ---------- ТЕОРИЯ ----------
@dp.callback_query(F.data.startswith("theory:list:"))
async def theory_list(callback: CallbackQuery):
    level = callback.data.split(":")[2]
    completed = await db.get_completed_lessons(callback.from_user.id)
    await callback.message.edit_text(
        f"<b>Теория — {LEVEL_NAMES[level]}</b>\n\nВыбери урок:",
        reply_markup=lessons_list_kb(level, completed)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("theory:open:"))
async def theory_open(callback: CallbackQuery):
    lesson_id = callback.data.split(":")[2]
    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    completed = await db.get_completed_lessons(callback.from_user.id)
    is_completed = lesson_id in completed

    text = (
        f"<b>Урок {lesson['id']}. {lesson['title']}</b>\n\n"
        f"{lesson['content']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=lesson_view_kb(lesson_id, is_completed)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("theory:done:"))
async def theory_done(callback: CallbackQuery):
    lesson_id = callback.data.split(":")[2]
    first_time = await db.mark_lesson_completed(callback.from_user.id, lesson_id)

    if first_time:
        await db.add_xp(callback.from_user.id, 25)
        new_achs = await db.check_achievements(callback.from_user.id)
        text = "✅ Урок отмечен как пройденный\n+25 XP"
        if new_achs:
            for ach in new_achs:
                info = ACHIEVEMENTS[ach]
                text += f"\n\n🏆 Достижение: <b>{info['title']}</b>\n{info['desc']}"
        await callback.answer(text, show_alert=True)
    else:
        await callback.answer("Урок уже был пройден ранее")

    # Обновляем сообщение
    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    completed = await db.get_completed_lessons(callback.from_user.id)
    await callback.message.edit_reply_markup(
        reply_markup=lesson_view_kb(lesson_id, True)
    )


@dp.callback_query(F.data.startswith("theory:open:"))
async def theory_open(callback: CallbackQuery):
    lesson_id = callback.data.split(":")[2]
    lesson = next((l for l in LESSONS if l["id"] == lesson_id), None)
    if not lesson:
        await callback.answer("Урок не найден", show_alert=True)
        return

    # Запоминаем уровень, чтобы кнопка "К урокам" возвращала правильно
    if not hasattr(dp, "user_level"):
        dp.user_level = {}
    dp.user_level[callback.from_user.id] = lesson["level"]

    completed = await db.get_completed_lessons(callback.from_user.id)
    is_completed = lesson_id in completed

    text = (
        f"<b>Урок {lesson['id']}. {lesson['title']}</b>\n\n"
        f"{lesson['content']}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=lesson_view_kb(lesson_id, is_completed)
    )
    await callback.answer()


@dp.callback_query(F.data == "theory:back")
async def theory_back(callback: CallbackQuery):
    level = getattr(dp, "user_level", {}).get(callback.from_user.id, "beginner")
    completed = await db.get_completed_lessons(callback.from_user.id)
    
    await callback.message.edit_text(
        f"<b>Теория — {LEVEL_NAMES[level]}</b>\n\nВыбери урок:",
        reply_markup=lessons_list_kb(level, completed)
    )
    await callback.answer()


# ---------- ПРАКТИКА ----------
@dp.callback_query(F.data.startswith("practice:list:"))
async def practice_list(callback: CallbackQuery):
    level = callback.data.split(":")[2]
    completed = await db.get_completed_tasks(callback.from_user.id)
    await callback.message.edit_text(
        f"<b>Практика — {LEVEL_NAMES[level]}</b>\n\nВыбери задачу:",
        reply_markup=tasks_list_kb(level, completed)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("practice:open:"))
async def practice_open(callback: CallbackQuery):
    _, _, level, idx = callback.data.split(":")
    idx = int(idx)
    tasks = TASKS.get(level, [])
    if idx >= len(tasks):
        await callback.answer("Задача не найдена", show_alert=True)
        return

    task = tasks[idx]
    letters = ["A", "B", "C", "D"]
    
    options_text = "\n".join(
        f"<b>{letters[i]})</b> {opt}" for i, opt in enumerate(task["options"])
    )

    text = (
        f"<b>{task['title']}</b>\n\n"
        f"{task['question']}\n\n"
        f"{options_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=task_options_kb(level, idx, task["options"])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("practice:answer:"))
async def practice_answer(callback: CallbackQuery):
    _, _, level, idx, chosen = callback.data.split(":")
    idx = int(idx)
    chosen = int(chosen)

    task = TASKS[level][idx]
    correct = chosen == task["correct"]

    first_time, give_xp = await db.save_task_attempt(
        callback.from_user.id, task["id"], correct
    )

    if correct and give_xp:
        xp = 30
        await db.add_xp(callback.from_user.id, xp)
        result = f"<b>Верно</b> (+{xp} XP)"
    elif correct:
        result = "<b>Верно</b> (XP уже было получено ранее)"
    else:
        result = "<b>Неверно</b>"

    text = (
        f"{result}\n\n"
        f"<b>Правильный ответ:</b>\n{task['options'][task['correct']]}\n\n"
        f"<b>Пояснение:</b>\n{task['explain']}"
    )

    new_achs = await db.check_achievements(callback.from_user.id)
    if new_achs:
        for ach in new_achs:
            info = ACHIEVEMENTS[ach]
            text += f"\n\n🏆 <b>{info['title']}</b>\n{info['desc']}"

    has_next = idx + 1 < len(TASKS[level])
    await callback.message.edit_text(
        text,
        reply_markup=after_answer_kb(level, idx, has_next)
    )
    await callback.answer()


# ---------- ДОСЬЕ ----------
@dp.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала нажми /start", show_alert=True)
        return

    completed_lessons = await db.get_completed_lessons(callback.from_user.id)
    completed_tasks = await db.get_completed_tasks(callback.from_user.id)
    achievements = await db.get_achievements(callback.from_user.id)

    total_lessons = len(LESSONS)
    total_tasks = sum(len(v) for v in TASKS.values())
    success_rate = 0
    if user["answers_total"] > 0:
        success_rate = round(user["correct_total"] / user["answers_total"] * 100)

    rank = get_agent_rank(user["xp"])

    text = (
        f"<b>ЛИЧНОЕ ДОСЬЕ АГЕНТА</b>\n\n"
        f"👤 Профиль: @{user['username'] or 'без username'}\n"
        f"🎖 Звание: <b>{rank}</b>\n"
        f"⭐️ XP: <b>{user['xp']}</b>\n\n"
        f"<b>Статистика</b>\n"
        f"• Пройдено уроков: {len(completed_lessons)} / {total_lessons}\n"
        f"• Решено задач: {len(completed_tasks)} / {total_tasks}\n"
        f"• Успешность: {success_rate}%\n"
        f"• Серия верных: {user['streak']}\n\n"
        f"<b>Достижения</b>\n"
    )

    if achievements:
        for ach_id in achievements:
            info = ACHIEVEMENTS[ach_id]
            text += f"• {info['title']} — {info['desc']}\n"
    else:
        text += "Пока нет\n"

    await callback.message.edit_text(text, reply_markup=back_to_menu_kb())
    await callback.answer()


# ---------- ЗАПУСК ----------
async def main():
    await db.init()
    print("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
