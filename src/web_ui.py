
import os
import sys
import threading
import schedule
import time
from datetime import datetime
import logging
import queue
import webbrowser
from flask import Flask, render_template_string, render_template, request, jsonify, redirect, url_for

# Adjust path to find src/config modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.main import run_sync
from config import settings

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Scheduler Global State
scheduler_running = False
stop_event = threading.Event()
scheduler_thread = None

# Log Queue
log_queue = queue.Queue()
log_history = []

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            log_entry = self.format(record)
            log_queue.put(log_entry)
        except Exception:
            pass

# Redirect logging
def setup_logging_redirect():
    handler = QueueHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Attach to key loggers
    logging.getLogger("TanhkapayPythonProgram").addHandler(handler)
    logging.getLogger("PaythonProgram").addHandler(handler)
    logging.getLogger("werkzeug").setLevel(logging.ERROR) # Quiet flask logs

setup_logging_redirect()

# --- Templates ---

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tanhkapay Sync Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; background-color: #f8f9fa; }
        .container { max-width: 900px; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .nav-link.active { font-weight: bold; border-bottom: 2px solid #0d6efd; }
        #logs-container { height: 400px; overflow-y: scroll; background: #212529; color: #0f0; padding: 15px; font-family: monospace; border-radius: 5px; }
        .log-entry { margin-bottom: 2px; }
    </style>
</head>
<body>
    <div class="container">
        <h2 class="mb-4 text-primary">Tanhkapay Sync Manager</h2>
        
        <ul class="nav nav-tabs mb-4">
            <li class="nav-item">
                <a class="nav-link {{ 'active' if active_tab == 'dashboard' else '' }}" href="/">Dashboard</a>
            </li>
            <li class="nav-item">
                <a class="nav-link {{ 'active' if active_tab == 'config' else '' }}" href="/config">Configuration</a>
            </li>
            <li class="nav-item">
                <a class="nav-link {{ 'active' if active_tab == 'logs' else '' }}" href="/logs">Logs</a>
            </li>
        </ul>
        
        {% for category, message in get_flashed_messages(with_categories=true) %}
            <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        {% endfor %}
        
        {% block content %}{% endblock %}
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Auto-dismiss alerts
        setTimeout(function() {
            var alerts = document.querySelectorAll('.alert');
            alerts.forEach(function(alert) {
                var bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    </script>
    {% block scripts %}{% endblock %}
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="row">
    <div class="col-md-6">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-primary text-white">Manual Sync</div>
            <div class="card-body">
                <p>Trigger a one-time synchronization immediately.</p>
                <button id="btn-run-now" class="btn btn-primary w-100" onclick="runSync()">Run Sync Now</button>
                <div id="sync-status" class="mt-3"></div>
            </div>
        </div>
    </div>
    <div class="col-md-6">
        <div class="card shadow-sm h-100">
            <div class="card-header bg-success text-white">Automated Scheduler</div>
            <div class="card-body">
                <div class="mb-3">
                    <label for="interval" class="form-label">Sync Interval (minutes)</label>
                    <input type="number" id="interval" class="form-control" value="{{ interval }}" min="1">
                </div>
                <!-- Controls -->
                <div id="scheduler-controls">
                    <button id="btn-start-sched" class="btn btn-success w-100 mb-2" onclick="toggleScheduler('start')">Start Scheduler</button>
                    <button id="btn-stop-sched" class="btn btn-danger w-100 mb-2 d-none" onclick="toggleScheduler('stop')">Stop Scheduler</button>
                </div>
                
                <div class="mt-3 pt-3 border-top">
                    <div class="d-flex justify-content-between">
                         <span>Status:</span>
                         <span id="sched-status-text" class="fw-bold text-secondary">Idle</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
    function updateSchedulerUI(running, interval) {
        const btnStart = document.getElementById('btn-start-sched');
        const btnStop = document.getElementById('btn-stop-sched');
        const statusText = document.getElementById('sched-status-text');
        const input = document.getElementById('interval');
        
        if (running) {
            btnStart.classList.add('d-none');
            btnStop.classList.remove('d-none');
            statusText.innerText = "Active (Every " + interval + " min)";
            statusText.className = "fw-bold text-success";
            input.disabled = true;
            input.value = interval;
        } else {
            btnStart.classList.remove('d-none');
            btnStop.classList.add('d-none');
            statusText.innerText = "Idle";
            statusText.className = "fw-bold text-secondary";
            input.disabled = false;
        }
    }

    function toggleScheduler(action) {
        const interval = document.getElementById('interval').value;
        fetch('/api/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action, interval: interval })
        })
        .then(res => res.json())
        .then(data => {
            if(data.success) {
                updateSchedulerUI(data.status === 'running', data.interval);
            } else {
                alert(data.message);
            }
        });
    }

    function runSync() {
        const btn = document.getElementById('btn-run-now');
        const status = document.getElementById('sync-status');
        btn.disabled = true;
        status.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div> Syncing...';
        
        fetch('/api/run', { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                const color = data.success ? 'text-success' : 'text-danger';
                status.innerHTML = `<div class="${color} fw-bold">${data.message}</div>`;
            })
            .catch(err => {
                status.innerHTML = `<div class="text-danger fw-bold">Error: ${err}</div>`;
            })
            .finally(() => {
                btn.disabled = false;
            });
    }

    // Check status on load
    fetch('/api/schedule/status')
        .then(res => res.json())
        .then(data => {
            updateSchedulerUI(data.running, data.interval);
        });

</script>
{% endblock %}
"""

CONFIG_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="card shadow-sm">
    <div class="card-header bg-info text-white">Application Configuration</div>
    <div class="card-body">
        <form action="/config" method="POST">
            {% for key, value in configs.items() %}
            <div class="mb-3 row">
                <label for="{{ key }}" class="col-sm-4 col-form-label fw-bold">{{ key }}</label>
                <div class="col-sm-8">
                    <input type="text" class="form-control" id="{{ key }}" name="{{ key }}" value="{{ value }}">
                </div>
            </div>
            {% endfor %}
            <div class="d-grid gap-2">
                <button type="submit" class="btn btn-primary">Save Configuration</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

LOGS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <h3>Application Logs</h3>
    <button class="btn btn-outline-secondary btn-sm" onclick="fetchLogs()">Refresh Logs</button>
</div>
<div id="logs-container">Loading logs...</div>
{% endblock %}

{% block scripts %}
<script>
    function fetchLogs() {
        fetch('/api/logs')
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('logs-container');
                container.innerText = data.logs;
                container.scrollTop = container.scrollHeight;
            });
    }
    fetchLogs();
    setInterval(fetchLogs, 5000); // Auto refresh every 5s
</script>
{% endblock %}
"""

# Setup Jinja2 DictLoader
from jinja2 import DictLoader
# Use jinja_env.loader to ensure it takes effect
app.jinja_env.loader = DictLoader({
    'base': BASE_TEMPLATE,
    'dashboard': DASHBOARD_TEMPLATE,
    'config': CONFIG_TEMPLATE,
    'logs': LOGS_TEMPLATE
})

# --- Routes ---

@app.route('/')
def index():
    return render_template('dashboard', active_tab='dashboard', interval=60)

@app.route('/config', methods=['GET', 'POST'])
def config_page():
    global current_dir
    env_path = os.path.join(parent_dir, 'config', '.env')

    if request.method == 'POST':
        try:
            content = ""
            for key in request.form:
                content += f"{key}={request.form[key]}\n"
            
            with open(env_path, 'w') as f:
                f.write(content)
            
            from dotenv import load_dotenv
            load_dotenv(env_path, override=True)
            return render_template('config', active_tab='config', configs=request.form, message="Saved!", category="success")
        
        except Exception as e:
            return f"Error: {e}"

    configs = {
        'DB_CONNECTION_STRING': settings.get_db_connection_string() or "",
        'TP_API_URL': settings.get_tp_api_url() or "",
        'API_USERNAME': settings.get_api_username() or "",
        'API_PASSWORD': settings.get_api_password() or "",
        'LOG_PATH': settings.get_log_path(),
        'LOG_LEVEL': settings.get_log_level()
    }
    return render_template('config', active_tab='config', configs=configs)

@app.route('/logs')
def logs_page():
    return render_template('logs', active_tab='logs')

@app.route('/api/run', methods=['POST'])
def api_run():
    logging.getLogger("TanhkapayPythonProgram").info("Manual sync initiated from Web UI.")
    try:
        result = run_sync()
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/logs')
def api_logs():
    # Drain queue to history list
    while not log_queue.empty():
        log_history.append(log_queue.get())
        if len(log_history) > 500:
            log_history.pop(0)
            
    return jsonify({'logs': "".join(log_history)})

# Scheduler
current_interval = 60
scheduler_running = False

@app.route('/api/schedule', methods=['POST'])
def api_schedule():
    global scheduler_running, current_interval, scheduler_thread, stop_event
    data = request.json
    action = data.get('action')
    interval = data.get('interval')
    
    if action == 'start':
        try:
            current_interval = int(interval)
            if current_interval <= 0: raise ValueError
        except:
            return jsonify({'success': False, 'message': 'Invalid interval'})
            
        if not scheduler_running:
            scheduler_running = True
            stop_event.clear()
            schedule.clear()
            schedule.every(current_interval).minutes.do(lambda: run_sync_safe())
            
            scheduler_thread = threading.Thread(target=run_scheduler_loop, daemon=True)
            scheduler_thread.start()
            logging.getLogger("TanhkapayPythonProgram").info(f"Scheduler started (Every {current_interval} min).")
            
        return jsonify({'success': True, 'status': 'running', 'interval': current_interval})
        
    elif action == 'stop':
        scheduler_running = False
        stop_event.set()
        logging.getLogger("TanhkapayPythonProgram").info("Scheduler stopped.")
        return jsonify({'success': True, 'status': 'stopped'})

    return jsonify({'success': False})

@app.route('/api/schedule/status')
def api_sched_status():
    return jsonify({'running': scheduler_running, 'interval': current_interval})

def run_sync_safe():
    logging.getLogger("TanhkapayPythonProgram").info("Scheduled sync starting...")
    try:
        run_sync()
    except Exception as e:
        logging.getLogger("TanhkapayPythonProgram").error(f"Scheduled sync failed: {e}")

def run_scheduler_loop():
    while scheduler_running and not stop_event.is_set():
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:5000")
    app.run(port=5000, debug=True, use_reloader=False)
