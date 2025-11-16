# Single-file Flask LinkStack-like app
# Save this as flask_linkstack_singlefile.py
# Requirements: flask, flask_sqlalchemy, python-dotenv (optional)

from flask import Flask, request, redirect, url_for, render_template_string, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'links.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = os.environ.get('FLASK_SECRET', 'change-me-in-prod')
# Admin password used for simple dashboard auth. Set ADMIN_PASSWORD env var in production.
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# --- DB ---
db = SQLAlchemy(app)

class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    icon = db.Column(db.String(1000), nullable=True)  # can be filename in uploads or external URL
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Link {self.title}>'

# create DB if not exists
with app.app_context():
    db.create_all()

# --- Helpers ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Public page (linkstack page) ---

INDEX_HTML = '''
<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ site_title or 'لینک‌استک' }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body { background: #f8f9fa; font-family: Tahoma, Arial, sans-serif }
      .card-link { text-decoration: none; }
      .icon { width: 42px; height: 42px; object-fit: contain; }
    </style>
  </head>
  <body>
    <div class="container py-5">
      <div class="row justify-content-center">
        <div class="col-md-6 text-center">
          <h1 class="mb-4">{{ site_title or 'لینک‌های من' }}</h1>
          {% for link in links %}
          <a href="{{ link.url }}" target="_blank" class="d-block mb-3 card-link">
            <div class="card shadow-sm">
              <div class="card-body d-flex align-items-center">
                {% if link.icon %}
                  {% if link.icon.startswith('http') %}
                    <img src="{{ link.icon }}" alt="icon" class="icon me-3">
                  {% else %}
                    <img src="/static/uploads/{{ link.icon }}" alt="icon" class="icon me-3">
                  {% endif %}
                {% endif %}
                <div class="flex-grow-1 text-start">{{ link.title }}</div>
              </div>
            </div>
          </a>
          {% endfor %}
          <div class="mt-4 small text-muted">صفحه ساخته شده با Flask — <a href="/admin">ورود به داشبورد</a></div>
        </div>
      </div>
    </div>
  </body>
</html>
'''

@app.route('/')
def index():
    links = Link.query.order_by(Link.position.asc(), Link.created_at.asc()).all()
    return render_template_string(INDEX_HTML, links=links, site_title=os.environ.get('SITE_TITLE', 'لینک‌های من'))

# --- Admin (very simple auth) ---

ADMIN_HTML = '''
<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>داشبورد مدیریت</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
    <div class="container py-5">
      <div class="row">
        <div class="col-md-8">
          <h2>داشبورد</h2>
          {% with messages = get_flashed_messages() %}
            {% if messages %}
              <div class="alert alert-info">{{ messages[0] }}</div>
            {% endif %}
          {% endwith %}

          <form method="post" action="/admin/add" enctype="multipart/form-data" class="mb-4">
            <div class="row g-2">
              <div class="col-md-4">
                <input name="title" class="form-control" placeholder="عنوان" required>
              </div>
              <div class="col-md-4">
                <input name="url" class="form-control" placeholder="https://example.com" required>
              </div>
              <div class="col-md-2">
                <input name="icon_url" class="form-control" placeholder="آدرس آیکون (اختیاری)">
              </div>
              <div class="col-md-2">
                <input type="file" name="icon_file" class="form-control">
              </div>
            </div>
            <div class="mt-2">
              <button class="btn btn-primary">افزودن لینک</button>
            </div>
          </form>

          <table class="table table-striped">
            <thead><tr><th>#</th><th>عنوان</th><th>آدرس</th><th>آیکون</th><th>عملیات</th></tr></thead>
            <tbody>
              {% for link in links %}
              <tr>
                <td>{{ loop.index }}</td>
                <td>{{ link.title }}</td>
                <td style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ link.url }}</td>
                <td>
                  {% if link.icon %}
                    {% if link.icon.startswith('http') %}
                      <img src="{{ link.icon }}" width="40">
                    {% else %}
                      <img src="/static/uploads/{{ link.icon }}" width="40">
                    {% endif %}
                  {% endif %}
                </td>
                <td>
                  <form method="post" action="/admin/delete/{{ link.id }}" style="display:inline">
                    <button class="btn btn-sm btn-danger" onclick="return confirm('حذف شود؟')">حذف</button>
                  </form>
                  <a href="/admin/edit/{{ link.id }}" class="btn btn-sm btn-secondary">ویرایش</a>
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="col-md-4">
          <h5>تنظیمات</h5>
          <form method="post" action="/admin/login">
            <div class="mb-2">
              <input name="password" type="password" class="form-control" placeholder="رمز ادمین" required>
            </div>
            <button class="btn btn-outline-primary">ورود</button>
          </form>

          <div class="mt-4">
            <form method="post" action="/admin/reorder">
              <label class="form-label">ترتیب دستی (idها کاما جدا)</label>
              <input name="order" class="form-control" placeholder="مثال: 3,1,2">
              <button class="btn btn-sm btn-success mt-2">اعمال ترتیب</button>
            </form>
          </div>

        </div>

      </div>
    </div>
  </body>
</html>
'''

EDIT_HTML = '''
<!doctype html>
<html lang="fa" dir="rtl">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>ویرایش لینک</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  </head>
  <body>
    <div class="container py-5">
      <h3>ویرایش</h3>
      <form method="post" action="" enctype="multipart/form-data">
        <div class="mb-2">
          <input name="title" value="{{ link.title }}" class="form-control" required>
        </div>
        <div class="mb-2">
          <input name="url" value="{{ link.url }}" class="form-control" required>
        </div>
        <div class="mb-2">
          <input name="icon_url" value="{{ link.icon if link.icon and link.icon.startswith('http') else '' }}" class="form-control">
        </div>
        <div class="mb-2">
          <input type="file" name="icon_file" class="form-control">
        </div>
        <button class="btn btn-primary">ذخیره</button>
        <a href="/admin" class="btn btn-secondary">انصراف</a>
      </form>
    </div>
  </body>
</html>
'''

# middleware: very small auth via session cookie
from functools import wraps
from flask import session

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash('لطفا ابتدا وارد شوید')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # show admin page; login handled at /admin/login
    links = Link.query.order_by(Link.position.asc(), Link.created_at.asc()).all()
    return render_template_string(ADMIN_HTML, links=links)

@app.route('/admin/login', methods=['POST'])
def admin_login():
    password = request.form.get('password','')
    if password == ADMIN_PASSWORD:
        session['is_admin'] = True
        flash('ورود موفق')
        return redirect(url_for('admin'))
    else:
        flash('رمز اشتباه')
        return redirect(url_for('admin'))

@app.route('/admin/add', methods=['POST'])
@admin_required
def admin_add():
    title = request.form.get('title')
    url = request.form.get('url')
    icon_url = request.form.get('icon_url','').strip()
    icon_file = request.files.get('icon_file')

    filename = None
    if icon_file and icon_file.filename != '' and allowed_file(icon_file.filename):
        fname = secure_filename(icon_file.filename)
        # avoid collisions
        fname = f"{int(datetime.utcnow().timestamp())}_{fname}"
        icon_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        filename = fname
    elif icon_url:
        filename = icon_url

    # compute position = max(position)+1
    max_pos = db.session.query(db.func.max(Link.position)).scalar() or 0
    new_link = Link(title=title, url=url, icon=filename, position=(max_pos+1))
    db.session.add(new_link)
    db.session.commit()
    flash('لینک اضافه شد')
    return redirect(url_for('admin'))

@app.route('/admin/edit/<int:id>', methods=['GET','POST'])
@admin_required
def admin_edit(id):
    link = Link.query.get_or_404(id)
    if request.method == 'POST':
        link.title = request.form.get('title')
        link.url = request.form.get('url')
        icon_url = request.form.get('icon_url','').strip()
        icon_file = request.files.get('icon_file')
        if icon_file and icon_file.filename != '' and allowed_file(icon_file.filename):
            fname = secure_filename(icon_file.filename)
            fname = f"{int(datetime.utcnow().timestamp())}_{fname}"
            icon_file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
            link.icon = fname
        elif icon_url:
            link.icon = icon_url
        db.session.commit()
        flash('ذخیره شد')
        return redirect(url_for('admin'))
    return render_template_string(EDIT_HTML, link=link)

@app.route('/admin/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete(id):
    link = Link.query.get_or_404(id)
    # optionally remove uploaded icon file
    if link.icon and not link.icon.startswith('http'):
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], link.icon))
        except Exception:
            pass
    db.session.delete(link)
    db.session.commit()
    flash('حذف شد')
    return redirect(url_for('admin'))

@app.route('/admin/reorder', methods=['POST'])
@admin_required
def admin_reorder():
    order = request.form.get('order','')
    if not order:
        flash('هیچ ترتیبی ارسال نشد')
        return redirect(url_for('admin'))
    ids = [int(x.strip()) for x in order.split(',') if x.strip().isdigit()]
    for pos, idv in enumerate(ids, start=1):
        link = Link.query.get(idv)
        if link:
            link.position = pos
    db.session.commit()
    flash('ترتیب اعمال شد')
    return redirect(url_for('admin'))

# static route for uploads is handled by Flask automatically under /static/uploads

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)