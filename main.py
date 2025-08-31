from flask import Flask, request, render_template, session, redirect, url_for
import random, string
from threading import Thread, Event

app = Flask(__name__)
app.debug = True
app.secret_key = 'k8m2p9x7w4n6q1v5z3c8b7f2j9r4t6y1u3i5o8e2a7s9d4g6h1l3'

# ----------------- Admin Credentials -----------------
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'adminpass123'

# ----------------- Approval System -----------------
approved_users = set()
pending_requests = set()

# ----------------- Helper -----------------
def get_user_id():
    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    return ip

@app.before_request
def check_approval():
    path = request.path or '/'
    if path.startswith('/static') or path == '/favicon.ico':
        return

    # Admin paths protection
    if path.startswith('/admin'):
        if path == '/admin/login':
            return
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return

    # Approval pages always accessible
    if path.startswith('/approval'):
        return

    # Non-admin users must be approved
    if not session.get('admin_logged_in'):
        user_id = get_user_id()
        if user_id not in approved_users:
            return redirect(url_for('approval_request'))

# ----------------- Routes -----------------
@app.route('/')
def home():
    show_popup = session.pop('show_approval_popup', False)
    return render_template("home.html", show_popup=show_popup)

@app.route('/approval_request', methods=['GET','POST'])
def approval_request():
    user_id = get_user_id()
    if user_id in approved_users or session.get('admin_logged_in'):
        return redirect(url_for('home'))
    if request.method == 'POST':
        if user_id not in pending_requests:
            pending_requests.add(user_id)
            return render_template('approval_sent.html')
        else:
            return render_template('approval_request.html', already_requested=True)
    return render_template('approval_request.html')

@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error=True)
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html', pending_requests=list(pending_requests), approved_users=list(approved_users))

@app.route('/admin/approve/<user_id>')
def approve_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if user_id in pending_requests:
        pending_requests.remove(user_id)
        approved_users.add(user_id)
        # Show animated popup on next dashboard visit
        if get_user_id() == user_id:
            session['show_approval_popup'] = True
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<user_id>')
def reject_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if user_id in pending_requests:
        pending_requests.remove(user_id)
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', portt=10000)
