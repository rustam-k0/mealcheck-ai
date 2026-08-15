from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import sqlite3

from banana_bot.domain import DiaryEntry


class DiaryRepository(ABC):
    @abstractmethod
    def add(self, entry: DiaryEntry) -> DiaryEntry: ...
    @abstractmethod
    def today(self, user_id: int) -> list[DiaryEntry]: ...
    @abstractmethod
    def last(self, user_id: int) -> DiaryEntry | None: ...
    @abstractmethod
    def delete_last(self, user_id: int) -> bool: ...


class SQLiteDiaryRepository(DiaryRepository):
    def __init__(self, path: str):
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.execute("""CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, timestamp TEXT NOT NULL,
            meal_type TEXT, source TEXT NOT NULL, confirmed_items TEXT NOT NULL, total_kcal REAL NOT NULL,
            protein_g REAL NOT NULL, fat_g REAL NOT NULL, carbs_g REAL NOT NULL, uncertainty TEXT NOT NULL, model TEXT NOT NULL)""")
        self.connection.commit()

    def add(self, entry: DiaryEntry) -> DiaryEntry:
        cursor = self.connection.execute("INSERT INTO diary_entries (user_id,timestamp,meal_type,source,confirmed_items,total_kcal,protein_g,fat_g,carbs_g,uncertainty,model) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            entry.user_id, entry.timestamp.isoformat(), entry.meal_type, entry.source,
            json.dumps([x.model_dump() for x in entry.confirmed_items], ensure_ascii=False), entry.total_kcal,
            entry.protein_g, entry.fat_g, entry.carbs_g, entry.uncertainty, entry.model))
        self.connection.commit()
        return entry.model_copy(update={"id": cursor.lastrowid})

    def _rows(self, query: str, args: tuple) -> list[DiaryEntry]:
        rows = self.connection.execute(query, args).fetchall()
        return [DiaryEntry(id=r[0], user_id=r[1], timestamp=r[2], meal_type=r[3], source=r[4], confirmed_items=json.loads(r[5]), total_kcal=r[6], protein_g=r[7], fat_g=r[8], carbs_g=r[9], uncertainty=r[10], model=r[11]) for r in rows]

    def today(self, user_id: int) -> list[DiaryEntry]:
        day = datetime.now(timezone.utc).date().isoformat()
        return self._rows("SELECT * FROM diary_entries WHERE user_id=? AND substr(timestamp,1,10)=? ORDER BY id", (user_id, day))

    def last(self, user_id: int) -> DiaryEntry | None:
        rows = self._rows("SELECT * FROM diary_entries WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))
        return rows[0] if rows else None

    def delete_last(self, user_id: int) -> bool:
        last = self.last(user_id)
        if not last: return False
        self.connection.execute("DELETE FROM diary_entries WHERE id=? AND user_id=?", (last.id, user_id)); self.connection.commit(); return True
