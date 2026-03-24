# ============================================================
# database/db.py — Асинхронный слой работы с SQLite
# ============================================================

import aiosqlite
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from config import SERVICES, DEFAULT_START_HOUR, DEFAULT_END_HOUR, SLOT_STEP
from database.models import ALL_TABLES

DB_PATH = "bookly.db"


# ─────────────────────────────────────────────────────────────
# Соединение
# ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def get_db():
    """Асинхронный контекст-менеджер соединения с SQLite."""
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()


# ─────────────────────────────────────────────────────────────
# Инициализация
# ─────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Создаёт таблицы и наполняет справочник услуг."""
    async with get_db() as db:
        for sql in ALL_TABLES:
            await db.execute(sql)

        # Міграція: додаємо duration_min у bookings, якщо колонки ще немає
        try:
            await db.execute("ALTER TABLE bookings ADD COLUMN duration_min INTEGER")
        except Exception:
            pass

        # Заполняем услуги из config.py (минимально)
        for name, duration in SERVICES.items():
            await db.execute(
                "INSERT OR IGNORE INTO services (name, duration_min) VALUES (?, ?)",
                (name, duration),
            )

        # Инициализируем дефолтные настройки
        await db.execute(
            "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
            ("price_list_html",
             "<b>💅 Прайс</b>\n\nЗверніться до адміністратора для налаштування цін."),
        )
        await db.execute(
            "INSERT OR IGNORE INTO bot_settings (key, value) VALUES (?, ?)",
            ("portfolio_link", "https://t.me/your_channel"),
        )
        await db.commit()

    # Синхронизируем названия и длительности услуг (для обновления)
    await sync_services()


async def sync_services() -> None:
    """
    Обновляет названия и длительности услуг из config.py.
    Если количество услуг совпадает — обновляет по порядку ID.
    Иначе делает безопасный upsert по имени.
    """
    service_items = list(SERVICES.items())
    async with get_db() as db:
        async with db.execute("SELECT id FROM services ORDER BY id") as cur:
            existing = await cur.fetchall()

        if len(existing) == len(service_items):
            for idx, row in enumerate(existing):
                name, duration = service_items[idx]
                await db.execute(
                    "UPDATE services SET name = ?, duration_min = ? WHERE id = ?",
                    (name, duration, row["id"]),
                )
        else:
            for name, duration in service_items:
                await db.execute(
                    "INSERT OR IGNORE INTO services (name, duration_min) VALUES (?, ?)",
                    (name, duration),
                )
                await db.execute(
                    "UPDATE services SET duration_min = ? WHERE name = ?",
                    (duration, name),
                )
        # Заповнюємо duration_min у вже існуючих записах, якщо порожнє
        await db.execute(
            """
            UPDATE bookings
            SET duration_min = (
                SELECT s.duration_min FROM services s WHERE s.id = bookings.service_id
            )
            WHERE duration_min IS NULL
            """
        )
        await db.commit()


# ─────────────────────────────────────────────────────────────
# Услуги
# ─────────────────────────────────────────────────────────────

async def get_all_services() -> list:
    async with get_db() as db:
        async with db.execute("SELECT * FROM services ORDER BY id") as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


async def get_service(service_id: int) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM services WHERE id = ?", (service_id,)
        ) as cur:
            row = await cur.fetchone()
    return row  # type: ignore


# ─────────────────────────────────────────────────────────────
# Рабочие дни
# ─────────────────────────────────────────────────────────────

async def add_working_day(date_str: str) -> bool:
    """Добавляет рабочий день и генерирует слоты по умолчанию.
    Возвращает False, если день уже существует."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            existing = await cur.fetchone()

        if existing:
            return False

        await db.execute(
            "INSERT INTO working_days (date) VALUES (?)", (date_str,)
        )
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            day_row = await cur.fetchone()
        day_id = day_row["id"]  # type: ignore

        # Генерируем слоты с шагом SLOT_STEP минут
        current = datetime.strptime(
            f"{date_str} {DEFAULT_START_HOUR:02d}:00", "%Y-%m-%d %H:%M"
        )
        end = datetime.strptime(
            f"{date_str} {DEFAULT_END_HOUR:02d}:00", "%Y-%m-%d %H:%M"
        )
        while current < end:
            await db.execute(
                "INSERT OR IGNORE INTO time_slots (working_day_id, time_str) VALUES (?, ?)",
                (day_id, current.strftime("%H:%M")),
            )
            current += timedelta(minutes=SLOT_STEP)

        await db.commit()
    return True


async def get_available_dates() -> list:
    """Возвращает даты, где есть хотя бы один свободный слот и день не закрыт."""
    today = datetime.now().strftime("%Y-%m-%d")
    async with get_db() as db:
        async with db.execute(
            """
            SELECT DISTINCT wd.date
            FROM working_days wd
            JOIN time_slots ts ON ts.working_day_id = wd.id
            WHERE wd.is_closed = 0
              AND ts.is_available = 1
              AND wd.date >= ?
            ORDER BY wd.date
            """,
            (today,),
        ) as cur:
            rows = await cur.fetchall()
    return [r["date"] for r in rows]


async def close_day(date_str: str) -> bool:
    """Закрывает день и освобождает все активные брони на него."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return False

        await db.execute(
            "UPDATE working_days SET is_closed = 1 WHERE date = ?", (date_str,)
        )
        await db.execute(
            "UPDATE time_slots SET is_available = 1 WHERE working_day_id = ?",
            (row["id"],),
        )
        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE date = ? AND status = 'active'",
            (date_str,),
        )
        await db.commit()
    return True


async def open_day(date_str: str) -> bool:
    """Открывает ранее закрытый день."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return False

        await db.execute(
            "UPDATE working_days SET is_closed = 0 WHERE date = ?", (date_str,)
        )
        await db.commit()
    return True


async def get_all_working_days() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM working_days WHERE date >= ? ORDER BY date", (today,)
        ) as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


async def delete_working_day(date_str: str) -> bool:
    async with get_db() as db:
        await db.execute("DELETE FROM working_days WHERE date = ?", (date_str,))
        await db.commit()
    return True


# ─────────────────────────────────────────────────────────────
# Временные слоты
# ─────────────────────────────────────────────────────────────

async def get_slots_for_date(date_str: str) -> list:
    """Все слоты для даты (включая занятые)."""
    async with get_db() as db:
        async with db.execute(
            """
            SELECT ts.*
            FROM time_slots ts
            JOIN working_days wd ON wd.id = ts.working_day_id
            WHERE wd.date = ?
            ORDER BY ts.time_str
            """,
            (date_str,),
        ) as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


async def get_available_slots_for_date(date_str: str, duration_min: int) -> list:
    """
    Возвращает слоты, с которых можно начать бронирование.
    Проверяет, что все последовательные слоты (в количестве blocks)
    свободны.
    """
    all_slots = await get_slots_for_date(date_str)
    blocks_needed = max(1, duration_min // SLOT_STEP)
    result = []

    for i, slot in enumerate(all_slots):
        if not slot["is_available"]:
            continue
        if i + blocks_needed > len(all_slots):
            break
        consecutive_free = all(
            all_slots[i + j]["is_available"] for j in range(blocks_needed)
        )
        if consecutive_free:
            result.append(slot)
    return result


async def add_slot(date_str: str, time_str: str) -> bool:
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return False

        await db.execute(
            "INSERT OR IGNORE INTO time_slots (working_day_id, time_str) VALUES (?, ?)",
            (row["id"], time_str),
        )
        await db.commit()
    return True


async def delete_slot(date_str: str, time_str: str) -> bool:
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM working_days WHERE date = ?", (date_str,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            return False

        await db.execute(
            "DELETE FROM time_slots WHERE working_day_id = ? AND time_str = ?",
            (row["id"], time_str),
        )
        await db.commit()
    return True


async def free_slots_for_booking(booking_id: int) -> None:
    """Освобождает все слоты, связанные с бронированием."""
    async with get_db() as db:
        async with db.execute(
            "SELECT date, time_str, service_id, duration_min FROM bookings WHERE id = ?",
            (booking_id,),
        ) as cur:
            booking = await cur.fetchone()

        if not booking:
            return

        duration_min = booking["duration_min"]
        if duration_min is None:
            async with db.execute(
                "SELECT duration_min FROM services WHERE id = ?",
                (booking["service_id"],),
            ) as cur:
                service = await cur.fetchone()
            if not service:
                return
            duration_min = service["duration_min"]

        blocks_needed = max(1, duration_min // SLOT_STEP)
        all_slots = await get_slots_for_date(booking["date"])
        start_idx = next(
            (i for i, s in enumerate(all_slots) if s["time_str"] == booking["time_str"]),
            None,
        )
        if start_idx is None:
            return

        for j in range(blocks_needed):
            idx = start_idx + j
            if idx < len(all_slots):
                await db.execute(
                    "UPDATE time_slots SET is_available = 1 WHERE id = ?",
                    (all_slots[idx]["id"],),
                )
        await db.commit()


# ─────────────────────────────────────────────────────────────
# Записи (Bookings)
# ─────────────────────────────────────────────────────────────

async def get_user_active_booking(user_id: int) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name,
                   COALESCE(b.duration_min, s.duration_min) AS duration_min
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.user_id = ? AND b.status = 'active'
            ORDER BY b.date, b.time_str
            LIMIT 1
            """,
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row  # type: ignore


async def create_booking(
    user_id: int,
    user_name: str,
    phone: str,
    service_id: int,
    date_str: str,
    time_str: str,
    duration_min: int,
) -> int:
    """
    Создаёт бронирование, блокирует слоты.
    Возвращает ID новой записи.
    """
    all_slots = await get_slots_for_date(date_str)
    blocks_needed = max(1, duration_min // SLOT_STEP)
    start_idx = next(
        (i for i, s in enumerate(all_slots) if s["time_str"] == time_str), None
    )

    async with get_db() as db:
        # Блокируем все нужные слоты
        if start_idx is not None:
            for j in range(blocks_needed):
                idx = start_idx + j
                if idx < len(all_slots):
                    await db.execute(
                        "UPDATE time_slots SET is_available = 0 WHERE id = ?",
                        (all_slots[idx]["id"],),
                    )

        # slot_id стартового слота
        async with db.execute(
            """
            SELECT ts.id FROM time_slots ts
            JOIN working_days wd ON wd.id = ts.working_day_id
            WHERE wd.date = ? AND ts.time_str = ?
            """,
            (date_str, time_str),
        ) as cur:
            slot_row = await cur.fetchone()
        slot_id = slot_row["id"] if slot_row else 0

        await db.execute(
            """
            INSERT INTO bookings (user_id, user_name, phone, service_id, slot_id, date, time_str, duration_min)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, user_name, phone, service_id, slot_id, date_str, time_str, duration_min),
        )
        await db.commit()

        async with db.execute("SELECT last_insert_rowid() as id") as cur:
            row = await cur.fetchone()
        booking_id: int = row["id"]  # type: ignore
    return booking_id


async def cancel_booking(booking_id: int) -> Optional[dict]:
    """Отменяет бронирование и возвращает его данные (для удаления задачи напоминания)."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM bookings WHERE id = ?", (booking_id,)
        ) as cur:
            booking = await cur.fetchone()

        if not booking or booking["status"] != "active":
            return None

        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,)
        )
        await db.commit()

    await free_slots_for_booking(booking_id)
    return booking  # type: ignore


async def cancel_user_booking(user_id: int) -> Optional[dict]:
    """Отменяет активную запись пользователя."""
    booking = await get_user_active_booking(user_id)
    if not booking:
        return None
    result = await cancel_booking(booking["id"])
    return result


async def get_bookings_for_date(date_str: str) -> list:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name,
                   COALESCE(b.duration_min, s.duration_min) AS duration_min
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.date = ? AND b.status = 'active'
            ORDER BY b.time_str
            """,
            (date_str,),
        ) as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


async def get_all_active_bookings() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    async with get_db() as db:
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name,
                   COALESCE(b.duration_min, s.duration_min) AS duration_min
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.status = 'active' AND b.date >= ?
            ORDER BY b.date, b.time_str
            """,
            (today,),
        ) as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


async def get_booking_by_id(booking_id: int) -> Optional[dict]:
    async with get_db() as db:
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name,
                   COALESCE(b.duration_min, s.duration_min) AS duration_min
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.id = ?
            """,
            (booking_id,),
        ) as cur:
            row = await cur.fetchone()
    return row  # type: ignore


async def set_reminder_job_id(booking_id: int, job_id: str) -> None:
    async with get_db() as db:
        await db.execute(
            "UPDATE bookings SET reminder_job_id = ? WHERE id = ?",
            (job_id, booking_id),
        )
        await db.commit()


async def get_pending_reminder_bookings() -> list:
    """Возвращает активные записи в будущем, чтобы восстановить напоминания."""
    now = datetime.now()
    async with get_db() as db:
        async with db.execute(
            """
            SELECT b.*, s.name AS service_name,
                   COALESCE(b.duration_min, s.duration_min) AS duration_min
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE b.status = 'active'
              AND datetime(b.date || ' ' || b.time_str) > ?
            ORDER BY b.date, b.time_str
            """,
            (now.strftime("%Y-%m-%d %H:%M"),),
        ) as cur:
            rows = await cur.fetchall()
    return rows  # type: ignore


# ─────────────────────────────────────────────────────────────
# Настройки бота
# ─────────────────────────────────────────────────────────────

async def get_setting(key: str) -> Optional[str]:  # noqa
    async with get_db() as db:
        async with db.execute(
            "SELECT value FROM bot_settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row["value"] if row else None


async def set_setting(key: str, value: str) -> None:
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO bot_settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()
