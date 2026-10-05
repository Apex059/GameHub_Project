import os
import sqlite3
from datetime import datetime
from functools import wraps

import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "gamehub.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "gamehub-dev-secret-change-me")

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.email = row["email"]
        self.genres = row["genres"] or ""
        self.bio = row["bio"] or ""


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        genres TEXT DEFAULT '',
        bio TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        platform TEXT NOT NULL,
        description TEXT NOT NULL,
        image TEXT DEFAULT '',
        release_year INTEGER DEFAULT 2025
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        review TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, game_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS library (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Playing',
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, game_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id INTEGER,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS tournaments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        game_id INTEGER NOT NULL,
        format TEXT NOT NULL,
        max_players INTEGER NOT NULL DEFAULT 16,
        event_date TEXT NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(creator_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(game_id) REFERENCES games(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tournament_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tournament_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        UNIQUE(tournament_id, user_id),
        FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        tournament_id INTEGER NOT NULL,
        points INTEGER NOT NULL DEFAULT 0,
        UNIQUE(user_id, tournament_id),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
    );
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game_id INTEGER NOT NULL,
        score INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(game_id) REFERENCES games(id)
    )
    """)

    count = conn.execute("SELECT COUNT(*) AS c FROM games").fetchone()["c"]
    if count == 0:
        games = [
            ("Valorant", "FPS", "PC", "A competitive 5v5 tactical shooter focused on teamwork, abilities and precision.", "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=900&q=80", 2020),
            ("Minecraft", "Sandbox", "PC / Mobile / Console", "A creative sandbox adventure where players build, explore and survive in block-based worlds.", "https://images.unsplash.com/photo-1607513746994-51f730aeeffa?auto=format&fit=crop&w=900&q=80", 2011),
            ("Apex Legends", "Battle Royale", "PC / Console", "A squad-based battle royale featuring distinct legends, movement and fast tactical combat.", "https://images.unsplash.com/photo-1560253023-3ec5d502959f?auto=format&fit=crop&w=900&q=80", 2019),
            ("Rocket League", "Sports", "PC / Console", "Football with rocket-powered cars, combining arcade action with competitive skill.", "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=900&q=80", 2015),
            ("Hades", "RPG", "PC / Console", "A fast-paced action roguelike built around repeated runs, upgrades and story progression.", "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=900&q=80", 2020),
            ("Stardew Valley", "Simulation", "PC / Mobile / Console", "A relaxing farming and life simulation game with exploration, relationships and crafting.", "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80", 2016),
            ("Elden Ring", "RPG", "PC / Console", "An expansive action RPG with exploration, challenging combat and a large interconnected world.", "https://images.unsplash.com/photo-1519608487953-e999c86e7455?auto=format&fit=crop&w=900&q=80", 2022),
            ("Overwatch 2", "FPS", "PC / Console", "A team-based hero shooter where players combine unique abilities and roles.", "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=900&q=80", 2022),
        ]
        conn.executemany("INSERT INTO games(title,genre,platform,description,image,release_year) VALUES (?,?,?,?,?,?)", games)

    demo = conn.execute("SELECT id FROM users WHERE username='demo'").fetchone()
    if not demo:
        conn.execute(
            "INSERT INTO users(username,email,password,genres,bio) VALUES (?,?,?,?,?)",
            ("demo", "demo@gamehub.local", generate_password_hash("demo123"), "FPS,RPG", "Welcome to my GameHub profile!")
        )

    # Demo tournament
    if conn.execute("SELECT COUNT(*) AS c FROM tournaments").fetchone()["c"] == 0:
        demo_id = conn.execute("SELECT id FROM users WHERE username='demo'").fetchone()["id"]
        valorant_id = conn.execute("SELECT id FROM games WHERE title='Valorant'").fetchone()["id"]
        conn.execute(
            "INSERT INTO tournaments(creator_id,name,game_id,format,max_players,event_date,description) VALUES(?,?,?,?,?,?,?)",
            (demo_id, "GameHub Valorant Night", valorant_id, "Single Elimination", 16, "2026-12-15", "A friendly community tournament.")
        )
    conn.commit()
    conn.close()


@login_manager.user_loader
def load_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return User(row) if row else None


def game_stats(conn, game_id):
    row = conn.execute(
        "SELECT COUNT(*) AS n, COALESCE(AVG(rating),0) AS avg FROM reviews WHERE game_id=?",
        (game_id,)
    ).fetchone()
    return row["n"], round(row["avg"], 1)


@app.context_processor
def inject_globals():
    return {"year": datetime.now().year}


@app.route("/")
def index():
    conn = db()
    games = conn.execute("SELECT * FROM games ORDER BY id DESC LIMIT 6").fetchall()
    tournaments = conn.execute("""
        SELECT t.*, g.title AS game_title,
               (SELECT COUNT(*) FROM tournament_players tp WHERE tp.tournament_id=t.id) AS players
        FROM tournaments t JOIN games g ON g.id=t.game_id
        ORDER BY t.event_date ASC LIMIT 3
    """).fetchall()
    conn.close()
    return render_template("index.html", games=games, tournaments=tournaments)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        genres = ",".join(request.form.getlist("genres"))
        if len(username) < 3 or len(password) < 6:
            flash("Username must be 3+ characters and password 6+ characters.", "danger")
        else:
            conn = db()
            try:
                conn.execute("INSERT INTO users(username,email,password,genres) VALUES(?,?,?,?)",
                             (username, email, generate_password_hash(password), genres))
                conn.commit()
                flash("Account created. You can now log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Username or email already exists.", "danger")
            finally:
                conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        identifier = request.form["identifier"].strip()
        password = request.form["password"]
        conn = db()
        row = conn.execute("SELECT * FROM users WHERE username=? OR email=?", (identifier, identifier.lower())).fetchone()
        conn.close()
        if row and check_password_hash(row["password"], password):
            login_user(User(row))
            return redirect(url_for("dashboard"))
        flash("Invalid username/email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    library = conn.execute("""
        SELECT g.*, l.status FROM library l JOIN games g ON g.id=l.game_id
        WHERE l.user_id=? ORDER BY l.added_at DESC
    """, (current_user.id,)).fetchall()
    recommendations = recommend_games(conn, current_user)
    reviews = conn.execute("""
        SELECT r.*, g.title FROM reviews r JOIN games g ON g.id=r.game_id
        WHERE r.user_id=? ORDER BY r.created_at DESC LIMIT 5
    """, (current_user.id,)).fetchall()
    conn.close()
    return render_template("dashboard.html", library=library, recommendations=recommendations, reviews=reviews)


def recommend_games(conn, user):
    genres = [g.strip().lower() for g in (user.genres or "").split(",") if g.strip()]
    reviewed = {r["game_id"] for r in conn.execute("SELECT game_id FROM reviews WHERE user_id=?", (user.id,)).fetchall()}
    library = {r["game_id"] for r in conn.execute("SELECT game_id FROM library WHERE user_id=?", (user.id,)).fetchall()}
    rows = conn.execute("SELECT * FROM games").fetchall()
    if not rows:
        return []
    df = pd.DataFrame([dict(r) for r in rows])
    df["score"] = df["genre"].str.lower().apply(lambda x: 1 if x in genres else 0)
    df["seen"] = df["id"].apply(lambda x: x in reviewed or x in library)
    result = df[(df["seen"] == False)].sort_values(["score", "title"], ascending=[False, True]).head(4)
    return result.to_dict("records")


@app.route("/games")
def games():
    conn = db()
    q = request.args.get("q", "").strip()
    genre = request.args.get("genre", "")
    platform = request.args.get("platform", "")
    sql = "SELECT * FROM games WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if genre:
        sql += " AND genre=?"
        params.append(genre)
    if platform:
        sql += " AND platform LIKE ?"
        params.append(f"%{platform}%")
    rows = conn.execute(sql + " ORDER BY title", params).fetchall()
    genres = conn.execute("SELECT DISTINCT genre FROM games ORDER BY genre").fetchall()
    conn.close()
    return render_template("games.html", games=rows, genres=genres, q=q, selected_genre=genre, selected_platform=platform)


@app.route("/games/<int:game_id>", methods=["GET", "POST"])
def game_detail(game_id):
    conn = db()
    game = conn.execute("SELECT * FROM games WHERE id=?", (game_id,)).fetchone()
    if not game:
        conn.close()
        abort(404)
    if request.method == "POST":
        if not current_user.is_authenticated:
            conn.close()
            return redirect(url_for("login"))
        rating = int(request.form["rating"])
        review = request.form["review"].strip()
        conn.execute("""
            INSERT INTO reviews(user_id,game_id,rating,review) VALUES(?,?,?,?)
            ON CONFLICT(user_id,game_id) DO UPDATE SET rating=excluded.rating, review=excluded.review
        """, (current_user.id, game_id, rating, review))
        conn.commit()
        flash("Your review was saved.", "success")
        return redirect(url_for("game_detail", game_id=game_id))
    reviews = conn.execute("""
        SELECT r.*, u.username FROM reviews r JOIN users u ON u.id=r.user_id
        WHERE r.game_id=? ORDER BY r.created_at DESC
    """, (game_id,)).fetchall()
    count, avg = game_stats(conn, game_id)
    in_library = False
    if current_user.is_authenticated:
        in_library = bool(conn.execute("SELECT 1 FROM library WHERE user_id=? AND game_id=?", (current_user.id, game_id)).fetchone())
    conn.close()
    return render_template("game_detail.html", game=game, reviews=reviews, count=count, avg=avg, in_library=in_library)

@app.route("/games/<int:game_id>/play")
def play_game(game_id):
    conn = db()

    game = conn.execute(
        "SELECT * FROM games WHERE id=?",
        (game_id,)
    ).fetchone()

    if not game:
        conn.close()
        abort(404)

    best_score = 0

    if game["title"] in ["Aim Trainer", "Target Shooter", "Block Builder", "Car Soccer"] and current_user.is_authenticated:
        result = conn.execute(
            """
            SELECT COALESCE(MAX(score), 0) AS best_score
            FROM game_scores
            WHERE game_id=? AND user_id=?
            """,
            (
                game_id,
                current_user.id
            )
        ).fetchone()

        best_score = result["best_score"]

    conn.close()

    if game["title"] == "Aim Trainer":
        return render_template(
            "play_aim.html",
            game=game,
            best_score=best_score
        )

    if game["title"] == "Block Builder":
           return render_template(
               "play_block.html",
               game=game,
               best_score=best_score
           )

    if game["title"] == "Car Soccer":
           return render_template(
               "play_car.html",
               game=game,
               best_score=best_score
           )

@app.route("/games/<int:game_id>/library", methods=["POST"])
@login_required
def toggle_library(game_id):
    conn = db()
    exists = conn.execute("SELECT id FROM library WHERE user_id=? AND game_id=?", (current_user.id, game_id)).fetchone()
    if exists:
        conn.execute("DELETE FROM library WHERE id=?", (exists["id"],))
        flash("Removed from your library.", "info")
    else:
        conn.execute("INSERT INTO library(user_id,game_id,status) VALUES(?,?,?)", (current_user.id, game_id, "Playing"))
        flash("Added to your library.", "success")
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("games"))


@app.route("/profile/<username>")
def profile(username):
    conn = db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        conn.close()
        abort(404)
    library = conn.execute("""
        SELECT g.title,g.genre,l.status FROM library l JOIN games g ON g.id=l.game_id WHERE l.user_id=?
    """, (user["id"],)).fetchall()
    review_count = conn.execute("SELECT COUNT(*) AS c FROM reviews WHERE user_id=?", (user["id"],)).fetchone()["c"]
    tournament_count = conn.execute("SELECT COUNT(*) AS c FROM tournament_players WHERE user_id=?", (user["id"],)).fetchone()["c"]
    conn.close()
    return render_template("profile.html", user=user, library=library, review_count=review_count, tournament_count=tournament_count)


@app.route("/forum", methods=["GET", "POST"])
@login_required
def forum():
    conn = db()
    if request.method == "POST":
        title = request.form["title"].strip()
        body = request.form["body"].strip()
        game_id = request.form.get("game_id") or None
        if title and body:
            conn.execute("INSERT INTO posts(user_id,game_id,title,body) VALUES(?,?,?,?)",
                         (current_user.id, game_id, title, body))
            conn.commit()
            flash("Discussion posted.", "success")
            return redirect(url_for("forum"))
    posts = conn.execute("""
        SELECT p.*, u.username, g.title AS game_title
        FROM posts p JOIN users u ON u.id=p.user_id
        LEFT JOIN games g ON g.id=p.game_id ORDER BY p.created_at DESC
    """).fetchall()
    games = conn.execute("SELECT id,title FROM games ORDER BY title").fetchall()
    conn.close()
    return render_template("forum.html", posts=posts, games=games)


@app.route("/tournaments", methods=["GET", "POST"])
@login_required
def tournaments():
    conn = db()
    if request.method == "POST":
        name = request.form["name"].strip()
        game_id = request.form["game_id"]
        fmt = request.form["format"]
        max_players = int(request.form["max_players"])
        event_date = request.form["event_date"]
        desc = request.form.get("description", "").strip()
        conn.execute("""INSERT INTO tournaments(creator_id,name,game_id,format,max_players,event_date,description)
                        VALUES(?,?,?,?,?,?,?)""",
                     (current_user.id, name, game_id, fmt, max_players, event_date, desc))
        conn.commit()
        flash("Tournament created.", "success")
        return redirect(url_for("tournaments"))
    rows = conn.execute("""
        SELECT t.*, g.title AS game_title, u.username AS creator,
               (SELECT COUNT(*) FROM tournament_players tp WHERE tp.tournament_id=t.id) AS players
        FROM tournaments t JOIN games g ON g.id=t.game_id JOIN users u ON u.id=t.creator_id
        ORDER BY t.event_date ASC
    """).fetchall()
    games = conn.execute("SELECT id,title FROM games ORDER BY title").fetchall()
    conn.close()
    return render_template("tournaments.html", tournaments=rows, games=games)


@app.route("/tournaments/<int:tournament_id>/join", methods=["POST"])
@login_required
def join_tournament(tournament_id):
    conn = db()
    t = conn.execute("SELECT * FROM tournaments WHERE id=?", (tournament_id,)).fetchone()
    if not t:
        conn.close()
        abort(404)
    count = conn.execute("SELECT COUNT(*) AS c FROM tournament_players WHERE tournament_id=?", (tournament_id,)).fetchone()["c"]
    if count >= t["max_players"]:
        flash("This tournament is full.", "warning")
    else:
        try:
            conn.execute("INSERT INTO tournament_players(tournament_id,user_id) VALUES(?,?)", (tournament_id, current_user.id))
            conn.commit()
            flash("You joined the tournament.", "success")
        except sqlite3.IntegrityError:
            flash("You are already registered.", "info")
    conn.close()
    return redirect(url_for("tournaments"))

@app.route("/games/<int:game_id>/score", methods=["POST"])
@login_required
def save_game_score(game_id):
    data = request.get_json(silent=True) or {}
    score = int(data.get("score", 0))

    if score < 0:
        score = 0

    conn = db()

    game = conn.execute(
        "SELECT id FROM games WHERE id=?",
        (game_id,)
    ).fetchone()

    if not game:
        conn.close()
        abort(404)

    conn.execute(
        "INSERT INTO game_scores(user_id, game_id, score) VALUES (?,?,?)",
        (current_user.id, game_id, score)
    )

    conn.commit()
    conn.close()

    return {"success": True}

@app.route("/leaderboard")
def leaderboard():
    conn = db()
    rows = conn.execute("""
        SELECT u.username,
               COALESCE(SUM(gs.score), 0) AS points,
               COUNT(gs.id) AS tournaments
        FROM users u
        LEFT JOIN game_scores gs ON gs.user_id = u.id
        GROUP BY u.id
        HAVING COUNT(gs.id) > 0
        ORDER BY points DESC, tournaments DESC, u.username ASC
    """).fetchall()
    conn.close()
    return render_template("leaderboard.html", rows=rows)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
