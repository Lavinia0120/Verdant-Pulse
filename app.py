from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, g, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = Path(os.getenv("LOCALAPPDATA", str(BASE_DIR / "instance"))) / "PlantCareDashboard"
DEFAULT_DATABASE = str(DEFAULT_DATA_DIR / "plants.db")


SEED_PLANTS = [
    {
        "name": "Monstera Deliciosa",
        "room": "Living Room",
        "species": "Monstera",
        "moisture": 58,
        "light_level": "Bright indirect",
        "water_target_ml": 220,
        "health_status": "Thriving",
        "image_url": "/static/images/plant-monstera.svg",
        "notes": "Large leaves, rotate weekly for even growth.",
        "last_watered": "2026-04-12",
    },
    {
        "name": "Calathea Orbifolia",
        "room": "Bedroom",
        "species": "Calathea",
        "moisture": 33,
        "light_level": "Filtered light",
        "water_target_ml": 180,
        "health_status": "Needs water",
        "image_url": "/static/images/plant-calathea.svg",
        "notes": "Prefers humidity and soft light.",
        "last_watered": "2026-04-09",
    },
    {
        "name": "Snake Plant",
        "room": "Office",
        "species": "Sansevieria",
        "moisture": 73,
        "light_level": "Low to medium",
        "water_target_ml": 120,
        "health_status": "Stable",
        "image_url": "/static/images/plant-snake.svg",
        "notes": "Low maintenance and ideal for corners.",
        "last_watered": "2026-04-14",
    },
    {
        "name": "Peace Lily",
        "room": "Kitchen",
        "species": "Spathiphyllum",
        "moisture": 41,
        "light_level": "Medium indirect",
        "water_target_ml": 160,
        "health_status": "Watch closely",
        "image_url": "/static/images/plant-lily.svg",
        "notes": "Leaves droop slightly when thirsty.",
        "last_watered": "2026-04-10",
    },
]


def resolve_database_location() -> str:
    configured_location = os.getenv("PLANT_DASHBOARD_DB")
    if configured_location:
        if configured_location == ":memory:":
            return "file:plant_dashboard?mode=memory&cache=shared"
        return configured_location

    try:
        DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DEFAULT_DATABASE
    except OSError:
        fallback_dir = BASE_DIR / "instance"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return str(fallback_dir / "plants.db")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["DATABASE"] = resolve_database_location()

    @app.route("/")
    def index() -> str:
        return render_template("index.html", owner_name="Lavinia")

    @app.route("/api/dashboard", methods=["GET"])
    def dashboard() -> Any:
        return jsonify(build_dashboard_payload())

    @app.route("/api/plants", methods=["POST"])
    def create_plant() -> Any:
        payload = request.get_json(silent=True) or request.form

        name = str(payload.get("name", "")).strip()
        room = str(payload.get("room", "")).strip()
        species = str(payload.get("species", "")).strip()
        light_level = str(payload.get("light_level", "")).strip()
        notes = str(payload.get("notes", "")).strip()
        image_url = str(payload.get("image_url", "")).strip() or "/static/images/plant-generic.svg"
        health_status = str(payload.get("health_status", "Stable")).strip() or "Stable"
        last_watered = str(payload.get("last_watered", "")).strip()

        errors: list[str] = []

        if not name:
            errors.append("Plant name is required.")
        if not room:
            errors.append("Room is required.")
        if not species:
            errors.append("Species is required.")
        if not light_level:
            errors.append("Light level is required.")

        moisture = parse_int(payload.get("moisture"), "Moisture", 0, 100, errors)
        water_target_ml = parse_int(payload.get("water_target_ml"), "Water target", 50, 1000, errors)

        if errors:
            return jsonify({"errors": errors}), 400

        db = get_db()
        db.execute(
            """
            INSERT INTO plants (
                name, room, species, moisture, light_level, water_target_ml,
                health_status, image_url, notes, last_watered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                room,
                species,
                moisture,
                light_level,
                water_target_ml,
                health_status,
                image_url,
                notes,
                last_watered,
            ),
        )
        db.commit()
        return jsonify(build_dashboard_payload()), 201

    @app.route("/api/plants/<int:plant_id>/water", methods=["POST"])
    def water_plant(plant_id: int) -> Any:
        payload = request.get_json(silent=True) or {}
        water_amount = int(payload.get("water_amount", 0) or 0)

        db = get_db()
        plant = db.execute("SELECT * FROM plants WHERE id = ?", (plant_id,)).fetchone()
        if plant is None:
            return jsonify({"error": "Plant not found."}), 404

        added_moisture = max(8, min(35, water_amount // 8 if water_amount else 18))
        new_moisture = min(100, plant["moisture"] + added_moisture)
        new_status = get_health_status(new_moisture)
        watered_on = str(payload.get("watered_on", "")).strip() or "2026-04-15"

        db.execute(
            """
            UPDATE plants
            SET moisture = ?, health_status = ?, last_watered = ?
            WHERE id = ?
            """,
            (new_moisture, new_status, watered_on, plant_id),
        )
        db.execute(
            """
            INSERT INTO care_logs (plant_id, action, details, created_on)
            VALUES (?, 'Watered', ?, ?)
            """,
            (plant_id, f"Added {water_amount or plant['water_target_ml']} ml of water.", watered_on),
        )
        db.commit()
        return jsonify(build_dashboard_payload())

    @app.teardown_appcontext
    def close_db(_: BaseException | None) -> None:
        if current_app.config["DATABASE"].startswith("file:plant_dashboard?mode=memory"):
            return
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with app.app_context():
        init_db()
        seed_if_empty()

    return app


def parse_int(value: Any, label: str, minimum: int, maximum: int, errors: list[str]) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be a number.")
        return minimum

    if parsed < minimum or parsed > maximum:
        errors.append(f"{label} must be between {minimum} and {maximum}.")
    return parsed


def get_db() -> sqlite3.Connection:
    database_location = current_app.config["DATABASE"]

    if database_location.startswith("file:plant_dashboard?mode=memory"):
        memory_db = current_app.config.get("_MEMORY_DB")
        if memory_db is None:
            memory_db = sqlite3.connect(database_location, uri=True)
            memory_db.row_factory = sqlite3.Row
            current_app.config["_MEMORY_DB"] = memory_db
        return memory_db

    if "db" not in g:
        db = sqlite3.connect(database_location, uri=database_location.startswith("file:"))
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS plants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            room TEXT NOT NULL,
            species TEXT NOT NULL,
            moisture INTEGER NOT NULL,
            light_level TEXT NOT NULL,
            water_target_ml INTEGER NOT NULL,
            health_status TEXT NOT NULL,
            image_url TEXT NOT NULL,
            notes TEXT,
            last_watered TEXT
        );

        CREATE TABLE IF NOT EXISTS care_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_on TEXT NOT NULL,
            FOREIGN KEY (plant_id) REFERENCES plants(id)
        );
        """
    )
    db.commit()


def seed_if_empty() -> None:
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS count FROM plants").fetchone()["count"]
    if count:
        return

    for plant in SEED_PLANTS:
        cursor = db.execute(
            """
            INSERT INTO plants (
                name, room, species, moisture, light_level, water_target_ml,
                health_status, image_url, notes, last_watered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plant["name"],
                plant["room"],
                plant["species"],
                plant["moisture"],
                plant["light_level"],
                plant["water_target_ml"],
                plant["health_status"],
                plant["image_url"],
                plant["notes"],
                plant["last_watered"],
            ),
        )
        db.execute(
            """
            INSERT INTO care_logs (plant_id, action, details, created_on)
            VALUES (?, 'Checked', ?, ?)
            """,
            (cursor.lastrowid, "Initial care profile added to dashboard.", plant["last_watered"]),
        )
    db.commit()


def get_health_status(moisture: int) -> str:
    if moisture >= 70:
        return "Thriving"
    if moisture >= 50:
        return "Stable"
    if moisture >= 35:
        return "Watch closely"
    return "Needs water"


def build_dashboard_payload() -> dict[str, Any]:
    db = get_db()
    plant_rows = db.execute(
        """
        SELECT id, name, room, species, moisture, light_level, water_target_ml,
               health_status, image_url, notes, last_watered
        FROM plants
        ORDER BY name
        """
    ).fetchall()

    plants: list[dict[str, Any]] = []
    for row in plant_rows:
        logs = db.execute(
            """
            SELECT action, details, created_on
            FROM care_logs
            WHERE plant_id = ?
            ORDER BY id DESC
            LIMIT 3
            """,
            (row["id"],),
        ).fetchall()
        plant = dict(row)
        plant["care_logs"] = [dict(log) for log in logs]
        plants.append(plant)

    thirsty_count = sum(1 for plant in plants if plant["moisture"] < 40)
    thriving_count = sum(1 for plant in plants if plant["health_status"] == "Thriving")
    average_moisture = round(sum(plant["moisture"] for plant in plants) / len(plants), 1) if plants else 0

    stats = {
        "total_plants": len(plants),
        "average_moisture": average_moisture,
        "needs_attention": thirsty_count,
        "thriving_count": thriving_count,
    }
    return {"plants": plants, "stats": stats}


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
