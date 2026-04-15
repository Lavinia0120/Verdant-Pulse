# Verdant Pulse

Verdant Pulse is a small full-stack plant monitoring app built with HTML, CSS, JavaScript, Python, and SQLite.

## Features

- Colorful dashboard with plant cards and a detail panel
- SQLite database for plant profiles and care logs
- Add new plants with image URLs and care notes
- Water a plant directly from the UI
- Filter by room, health status, and search text
- Seeded example data for quick demos

## Run

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Database

By default the SQLite database is stored in:

`%LOCALAPPDATA%\PlantCareDashboard\plants.db`

You can override it with:

`PLANT_DASHBOARD_DB`
