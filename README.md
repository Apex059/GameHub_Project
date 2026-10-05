# GameHub — Gaming Community Web App

A portable college-project implementation based on the provided GameHub research paper.

&#x20;## Screenshots

!\[Home page](screenshots/home.png)

!\[Games page](screenshots/games.png)

!\[Leaderboard](screenshots/leaderboard.png)

## Technology stack

* Frontend: HTML5, CSS3, JavaScript, Bootstrap 5
* Backend: Python Flask
* Database: SQLite
* Authentication: Flask-Login + Werkzeug password hashing
* Recommendation logic: Python + Pandas content-based filtering

## Features

* Responsive home page
* Register / login / logout
* Game catalog with genre/platform filtering
* Game details, ratings and reviews
* Personal game library
* Community forum
* Genre-based recommendations
* Tournament creation and registration
* Leaderboard
* Responsive navigation for phone/tablet/laptop

## Run locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Run:
`python -m venv .venv`
4. Activate the environment:
Windows:
`.venv\\Scripts\\activate`
macOS/Linux:
`source .venv/bin/activate`
5. Install packages:
`pip install -r requirements.txt`
6. Start:
`python app.py`
7. Open:
`http://127.0.0.1:5000`

The SQLite database is created automatically on first run.

## Demo account

Username: demo
Password: demo123

You can also create your own account.

## Deploying online

The app is structured for a normal Flask host such as Render or PythonAnywhere. For production, replace SQLite with a managed database and set a secure SECRET\_KEY environment variable.

