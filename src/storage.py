"""Persistence layer for activities, participants, and enrollments."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class ActivityNotFoundError(Exception):
    """Raised when an activity does not exist."""


class AlreadySignedUpError(Exception):
    """Raised when a participant is already enrolled in an activity."""


class NotSignedUpError(Exception):
    """Raised when a participant is not enrolled in an activity."""


class ActivityFullError(Exception):
    """Raised when an activity has reached max participants."""


class ActivityRepository:
    """Repository layer that hides SQLite details from API routes."""

    def __init__(self, db_path: Path, seed_file_path: Path) -> None:
        self.db_path = db_path
        self.seed_file_path = seed_file_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT NOT NULL,
                    schedule TEXT NOT NULL,
                    max_participants INTEGER NOT NULL CHECK (max_participants > 0)
                );

                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS enrollments (
                    activity_id INTEGER NOT NULL,
                    participant_id INTEGER NOT NULL,
                    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (activity_id, participant_id),
                    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
                );
                """
            )

            activity_count = connection.execute(
                "SELECT COUNT(*) AS count FROM activities"
            ).fetchone()["count"]

            if activity_count == 0:
                self._seed_activities(connection)

            connection.commit()

    def _seed_activities(self, connection: sqlite3.Connection) -> None:
        with self.seed_file_path.open("r", encoding="utf-8") as seed_file:
            seed_data = json.load(seed_file)

        for activity in seed_data.get("activities", []):
            cursor = connection.execute(
                """
                INSERT INTO activities (name, description, schedule, max_participants)
                VALUES (?, ?, ?, ?)
                """,
                (
                    activity["name"],
                    activity["description"],
                    activity["schedule"],
                    activity["max_participants"],
                ),
            )
            activity_id = cursor.lastrowid

            for email in activity.get("participants", []):
                participant_id = self._upsert_participant(connection, email)
                connection.execute(
                    """
                    INSERT OR IGNORE INTO enrollments (activity_id, participant_id)
                    VALUES (?, ?)
                    """,
                    (activity_id, participant_id),
                )

    def _upsert_participant(self, connection: sqlite3.Connection, email: str) -> int:
        connection.execute(
            "INSERT OR IGNORE INTO participants (email) VALUES (?)",
            (email,),
        )
        row = connection.execute(
            "SELECT id FROM participants WHERE email = ?",
            (email,),
        ).fetchone()
        return int(row["id"])

    def list_activities(self) -> dict[str, Any]:
        with self._connect() as connection:
            activity_rows = connection.execute(
                """
                SELECT id, name, description, schedule, max_participants
                FROM activities
                ORDER BY name
                """
            ).fetchall()

            activities: dict[str, Any] = {}
            for row in activity_rows:
                participants = connection.execute(
                    """
                    SELECT p.email
                    FROM enrollments e
                    JOIN participants p ON p.id = e.participant_id
                    WHERE e.activity_id = ?
                    ORDER BY p.email
                    """,
                    (row["id"],),
                ).fetchall()

                activities[row["name"]] = {
                    "description": row["description"],
                    "schedule": row["schedule"],
                    "max_participants": row["max_participants"],
                    "participants": [participant["email"] for participant in participants],
                }

            return activities

    def signup(self, activity_name: str, email: str) -> None:
        with self._connect() as connection:
            activity = connection.execute(
                "SELECT id, max_participants FROM activities WHERE name = ?",
                (activity_name,),
            ).fetchone()

            if activity is None:
                raise ActivityNotFoundError()

            participant_id = self._upsert_participant(connection, email)

            existing_enrollment = connection.execute(
                """
                SELECT 1 FROM enrollments
                WHERE activity_id = ? AND participant_id = ?
                """,
                (activity["id"], participant_id),
            ).fetchone()

            if existing_enrollment is not None:
                raise AlreadySignedUpError()

            enrollment_count = connection.execute(
                "SELECT COUNT(*) AS count FROM enrollments WHERE activity_id = ?",
                (activity["id"],),
            ).fetchone()["count"]

            if enrollment_count >= activity["max_participants"]:
                raise ActivityFullError()

            connection.execute(
                """
                INSERT INTO enrollments (activity_id, participant_id)
                VALUES (?, ?)
                """,
                (activity["id"], participant_id),
            )
            connection.commit()

    def unregister(self, activity_name: str, email: str) -> None:
        with self._connect() as connection:
            activity = connection.execute(
                "SELECT id FROM activities WHERE name = ?",
                (activity_name,),
            ).fetchone()

            if activity is None:
                raise ActivityNotFoundError()

            participant = connection.execute(
                "SELECT id FROM participants WHERE email = ?",
                (email,),
            ).fetchone()

            if participant is None:
                raise NotSignedUpError()

            deleted = connection.execute(
                """
                DELETE FROM enrollments
                WHERE activity_id = ? AND participant_id = ?
                """,
                (activity["id"], participant["id"]),
            )

            if deleted.rowcount == 0:
                raise NotSignedUpError()

            connection.commit()
