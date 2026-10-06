import aiosqlite
from datetime import datetime
from config import DB_PATH
from content import ACHIEVEMENTS, get_agent_rank


class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path

    async def init(self):
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    xp INTEGER DEFAULT 0,
                    streak INTEGER DEFAULT 0,
                    correct_total INTEGER DEFAULT 0,
                    answers_total INTEGER DEFAULT 0,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS completed_lessons (
                    user_id INTEGER,
                    lesson_id TEXT,
                    PRIMARY KEY (user_id, lesson_id)
                );

                CREATE TABLE IF NOT EXISTS completed_tasks (
                    user_id INTEGER,
                    task_id TEXT,
                    correct INTEGER,
                    PRIMARY KEY (user_id, task_id)
                );

                CREATE TABLE IF NOT EXISTS achievements (
                    user_id INTEGER,
                    achievement_id TEXT,
                    unlocked_at TEXT,
                    PRIMARY KEY (user_id, achievement_id)
                );
            """)
            await db.commit()

    async def ensure_user(self, user_id: int, username: str, full_name: str):
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cur:
                exists = await cur.fetchone()
            if exists:
                await db.execute(
                    "UPDATE users SET username = ?, full_name = ? WHERE user_id = ?",
                    (username, full_name, user_id)
                )
            else:
                await db.execute(
                    "INSERT INTO users (user_id, username, full_name, created_at) VALUES (?, ?, ?, ?)",
                    (user_id, username, full_name, datetime.utcnow().isoformat())
                )
            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                return await cur.fetchone()

    async def add_xp(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE users SET xp = xp + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def mark_lesson_completed(self, user_id: int, lesson_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO completed_lessons (user_id, lesson_id) VALUES (?, ?)",
                    (user_id, lesson_id)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_completed_lessons(self, user_id: int) -> set:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT lesson_id FROM completed_lessons WHERE user_id = ?", (user_id,)
            ) as cur:
                rows = await cur.fetchall()
        return {r[0] for r in rows}

    async def save_task_attempt(self, user_id: int, task_id: str, correct: bool) -> tuple[bool, bool]:
        """Возвращает (first_time, xp_should_be_given)
    first_time — задача решается впервые
    xp_should_be_given — можно начислить XP (только при первом правильном ответе)"""
        async with aiosqlite.connect(self.path) as db:
            # Проверяем, решалась ли задача раньше
            async with db.execute(
                "SELECT correct FROM completed_tasks WHERE user_id = ? AND task_id = ?",
                (user_id, task_id)
            ) as cur:
                row = await cur.fetchone()

            first_time = row is None
            already_correct = row is not None and row[0] == 1

            if first_time:
                await db.execute(
                    "INSERT INTO completed_tasks (user_id, task_id, correct) VALUES (?, ?, ?)",
                    (user_id, task_id, int(correct))
                )
            else:
                # Обновляем результат (особенно важно, если раньше ответил неправильно)
                await db.execute(
                    "UPDATE completed_tasks SET correct = ? WHERE user_id = ? AND task_id = ?",
                    (int(correct), user_id, task_id)
                )

            # Статистика
            if correct:
                await db.execute(
                    "UPDATE users SET streak = streak + 1, "
                    "correct_total = correct_total + 1, "
                    "answers_total = answers_total + 1 WHERE user_id = ?",
                    (user_id,)
                )
            else:
                await db.execute(
                    "UPDATE users SET streak = 0, "
                    "answers_total = answers_total + 1 WHERE user_id = ?",
                    (user_id,)
                )

            await db.commit()

        # XP даём только если это первый правильный ответ
        xp_should_be_given = correct and not already_correct
        return first_time, xp_should_be_given

    async def get_completed_tasks(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT task_id, correct FROM completed_tasks WHERE user_id = ?", (user_id,)
            ) as cur:
                rows = await cur.fetchall()
        return {r[0]: bool(r[1]) for r in rows}

    async def unlock_achievement(self, user_id: int, ach_id: str) -> bool:
        if ach_id not in ACHIEVEMENTS:
            return False
        async with aiosqlite.connect(self.path) as db:
            try:
                await db.execute(
                    "INSERT INTO achievements (user_id, achievement_id, unlocked_at) VALUES (?, ?, ?)",
                    (user_id, ach_id, datetime.utcnow().isoformat())
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_achievements(self, user_id: int) -> list:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT achievement_id FROM achievements WHERE user_id = ?", (user_id,)
            ) as cur:
                rows = await cur.fetchall()
        return [r[0] for r in rows]

    async def check_achievements(self, user_id: int) -> list:
        user = await self.get_user(user_id)
        if not user:
            return []

        completed_lessons = await self.get_completed_lessons(user_id)
        completed_tasks = await self.get_completed_tasks(user_id)
        unlocked = set(await self.get_achievements(user_id))
        new = []

        if completed_tasks and "first_blood" not in unlocked:
            if await self.unlock_achievement(user_id, "first_blood"):
                new.append("first_blood")

        if user["streak"] >= 5 and "sherlock" not in unlocked:
            if await self.unlock_achievement(user_id, "sherlock"):
                new.append("sherlock")

        if len(completed_lessons) >= 5 and "theorist" not in unlocked:
            if await self.unlock_achievement(user_id, "theorist"):
                new.append("theorist")

        if len(completed_tasks) >= 10 and "practitioner" not in unlocked:
            if await self.unlock_achievement(user_id, "practitioner"):
                new.append("practitioner")

        if "02" in completed_lessons and "dork_master" not in unlocked:
            if await self.unlock_achievement(user_id, "dork_master"):
                new.append("dork_master")

        if (len(completed_tasks) >= 5 and all(completed_tasks.values())
                and "perfectionist" not in unlocked):
            if await self.unlock_achievement(user_id, "perfectionist"):
                new.append("perfectionist")

        return new


db = Database()
