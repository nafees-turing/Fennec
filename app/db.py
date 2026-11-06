import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    module_id TEXT NOT NULL,
    status TEXT NOT NULL,
    input_value TEXT NOT NULL,
    error TEXT,
    lookup_id TEXT,
    in_profile INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS pending_lookups (
    case_id INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY,
    case_id INTEGER NOT NULL REFERENCES cases(id),
    run_id INTEGER NOT NULL REFERENCES runs(id),
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence TEXT NOT NULL,
    evidence TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identity_unions (
    case_id INTEGER NOT NULL,
    left_key TEXT NOT NULL,
    right_key TEXT NOT NULL,
    UNIQUE(case_id, left_key, right_key)
);

CREATE TABLE IF NOT EXISTS profile_edits (
    case_id INTEGER NOT NULL,
    anchor TEXT NOT NULL,
    title TEXT,
    notes TEXT,
    primary_email TEXT,
    primary_phone TEXT,
    PRIMARY KEY (case_id, anchor)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(runs)").fetchall()}
        if "lookup_id" not in cols:
            conn.execute("ALTER TABLE runs ADD COLUMN lookup_id TEXT")
        if "in_profile" not in cols:
            conn.execute("ALTER TABLE runs ADD COLUMN in_profile INTEGER NOT NULL DEFAULT 1")


def get_setting(path: Path, key: str) -> str | None:
    with connect(path) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return None if row is None else str(row["value"])


def set_setting(path: Path, key: str, value: str) -> None:
    with connect(path) as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def create_case(path: Path, name: str, notes: str) -> dict:
    with connect(path) as conn:
        cur = conn.execute(
            "INSERT INTO cases (name, notes) VALUES (?, ?)",
            (name, notes),
        )
        return dict(conn.execute("SELECT * FROM cases WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_cases(path: Path) -> list[dict]:
    with connect(path) as conn:
        rows = conn.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def get_case(path: Path, case_id: int) -> dict | None:
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return dict(row) if row else None


def add_run(
    path: Path,
    case_id: int,
    module_id: str,
    status: str,
    input_value: str,
    error: str | None,
    findings: list[dict],
    lookup_id: str | None = None,
    in_profile: bool = True,
) -> dict:
    with connect(path) as conn:
        cur = conn.execute(
            """
            INSERT INTO runs (case_id, module_id, status, input_value, error, lookup_id, in_profile)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (case_id, module_id, status, input_value, error, lookup_id, 1 if in_profile else 0),
        )
        run_id = cur.lastrowid
        for finding in findings:
            conn.execute(
                """
                INSERT INTO findings
                    (case_id, run_id, kind, value, source, confidence, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_id,
                    run_id,
                    finding["kind"],
                    finding["value"],
                    finding["source"],
                    finding["confidence"],
                    finding.get("evidence", ""),
                ),
            )
        run = dict(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())
    run["findings"] = list_findings(path, case_id, run_id)
    return run


def list_runs(path: Path, case_id: int) -> list[dict]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE case_id = ? ORDER BY id DESC",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_findings(path: Path, case_id: int, run_id: int | None = None) -> list[dict]:
    sql = "SELECT * FROM findings WHERE case_id = ?"
    params: list = [case_id]
    if run_id is not None:
        sql += " AND run_id = ?"
        params.append(run_id)
    sql += " ORDER BY id"
    with connect(path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def delete_findings(path: Path, case_id: int, finding_ids: list[int]) -> int:
    ids = [int(item) for item in finding_ids]
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    with connect(path) as conn:
        run_ids = [
            int(row["run_id"])
            for row in conn.execute(
                f"SELECT DISTINCT run_id FROM findings WHERE case_id = ? AND id IN ({placeholders})",
                [case_id, *ids],
            ).fetchall()
        ]
        if not run_ids:
            return 0
        run_ph = ",".join("?" * len(run_ids))
        cur = conn.execute(
            f"DELETE FROM findings WHERE case_id = ? AND run_id IN ({run_ph})",
            [case_id, *run_ids],
        )
        conn.execute(
            f"DELETE FROM runs WHERE case_id = ? AND id IN ({run_ph})",
            [case_id, *run_ids],
        )
        return cur.rowcount


def set_pending(path: Path, case_id: int, payload: str) -> None:
    with connect(path) as conn:
        conn.execute(
            """
            INSERT INTO pending_lookups (case_id, payload) VALUES (?, ?)
            ON CONFLICT(case_id) DO UPDATE SET payload = excluded.payload
            """,
            (case_id, payload),
        )


def get_pending(path: Path, case_id: int) -> str | None:
    with connect(path) as conn:
        row = conn.execute("SELECT payload FROM pending_lookups WHERE case_id = ?", (case_id,)).fetchone()
    return None if row is None else str(row["payload"])


def clear_pending(path: Path, case_id: int) -> None:
    with connect(path) as conn:
        conn.execute("DELETE FROM pending_lookups WHERE case_id = ?", (case_id,))


def mark_runs_in_profile(path: Path, case_id: int, lookup_id: str) -> None:
    with connect(path) as conn:
        conn.execute(
            "UPDATE runs SET in_profile = 1 WHERE case_id = ? AND lookup_id = ?",
            (case_id, lookup_id),
        )


def list_unions(path: Path, case_id: int) -> list[tuple[str, str]]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT left_key, right_key FROM identity_unions WHERE case_id = ?",
            (case_id,),
        ).fetchall()
    return [(str(row["left_key"]), str(row["right_key"])) for row in rows]


def add_union(path: Path, case_id: int, left_key: str, right_key: str) -> None:
    if not left_key or not right_key or left_key == right_key:
        return
    with connect(path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO identity_unions (case_id, left_key, right_key)
            VALUES (?, ?, ?)
            """,
            (case_id, left_key, right_key),
        )


def list_edits(path: Path, case_id: int) -> list[dict]:
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT anchor, title, notes, primary_email, primary_phone FROM profile_edits WHERE case_id = ?",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_edit(path: Path, case_id: int, anchor: str, fields: dict) -> dict:
    with connect(path) as conn:
        existing = conn.execute(
            "SELECT * FROM profile_edits WHERE case_id = ? AND anchor = ?",
            (case_id, anchor),
        ).fetchone()
        title = fields.get("title", existing["title"] if existing else None)
        notes = fields.get("notes", existing["notes"] if existing else None)
        email = fields.get("primary_email", existing["primary_email"] if existing else None)
        phone = fields.get("primary_phone", existing["primary_phone"] if existing else None)
        conn.execute(
            """
            INSERT INTO profile_edits (case_id, anchor, title, notes, primary_email, primary_phone)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(case_id, anchor) DO UPDATE SET
                title = excluded.title,
                notes = excluded.notes,
                primary_email = excluded.primary_email,
                primary_phone = excluded.primary_phone
            """,
            (case_id, anchor, title, notes, email, phone),
        )
        row = conn.execute(
            "SELECT * FROM profile_edits WHERE case_id = ? AND anchor = ?",
            (case_id, anchor),
        ).fetchone()
    return dict(row)


