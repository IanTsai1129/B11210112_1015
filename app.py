import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, abort, g

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key"  # flash 訊息需要用到
app.config["DATABASE"] = "blog.db"


# ---------- 資料庫 ----------
def get_db():
    """每個 request 共用一個資料庫連線"""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row  # 讓查詢結果可以用 post["title"] 取值
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """建立 posts 資料表（若不存在）"""
    db = sqlite3.connect(app.config["DATABASE"])
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            author     TEXT NOT NULL,
            content    TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT (datetime('now', 'localtime'))
        )
        """
    )
    db.commit()
    db.close()


def get_post_or_404(post_id):
    post = get_db().execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        abort(404)
    return post


def validate(form):
    """檢查表單三個欄位都有填寫，回傳 (資料, 錯誤訊息)"""
    data = {
        "title": form.get("title", "").strip(),
        "author": form.get("author", "").strip(),
        "content": form.get("content", "").strip(),
    }
    labels = {"title": "標題", "author": "作者", "content": "文章內容"}
    missing = [labels[k] for k, v in data.items() if not v]
    error = f"請填寫：{'、'.join(missing)}" if missing else None
    return data, error


# ---------- 路由 ----------
@app.route("/")
def index():
    """首頁：列出所有文章"""
    posts = get_db().execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render_template("index.html", posts=posts)


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    """單篇文章頁"""
    return render_template("post.html", post=get_post_or_404(post_id))


@app.route("/create", methods=["GET", "POST"])
def create():
    """新增文章"""
    if request.method == "POST":
        data, error = validate(request.form)
        if error:
            flash(error, "error")
            return render_template("form.html", post=data, mode="create")
        db = get_db()
        cur = db.execute(
            "INSERT INTO posts (title, author, content) VALUES (?, ?, ?)",
            (data["title"], data["author"], data["content"]),
        )
        db.commit()
        flash("文章已發布！", "success")
        return redirect(url_for("post_detail", post_id=cur.lastrowid))
    return render_template("form.html", post={}, mode="create")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
def edit(post_id):
    """編輯文章"""
    post = get_post_or_404(post_id)
    if request.method == "POST":
        data, error = validate(request.form)
        if error:
            flash(error, "error")
            data["id"] = post_id
            return render_template("form.html", post=data, mode="edit")
        db = get_db()
        db.execute(
            "UPDATE posts SET title = ?, author = ?, content = ? WHERE id = ?",
            (data["title"], data["author"], data["content"], post_id),
        )
        db.commit()
        flash("文章已更新！", "success")
        return redirect(url_for("post_detail", post_id=post_id))
    return render_template("form.html", post=post, mode="edit")


@app.route("/post/<int:post_id>/delete", methods=["POST"])
def delete(post_id):
    """刪除文章（只接受 POST，避免被連結誤觸）"""
    get_post_or_404(post_id)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("文章已刪除。", "success")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True)