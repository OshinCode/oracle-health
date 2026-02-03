import os
import psutil
import datetime
import sys
import time
import sqlite3
import platform
import logging # Added for standard logging configuration
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Load the .env file
load_dotenv()

DB_PATH = "health_stats.db"

def init_db():
    """Initializes the SQLite database and creates the table if it doesn't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                cpu REAL,
                memory_percent REAL,
                disk_percent REAL,
                net_up REAL,
                net_down REAL
            )
        ''')
    print("✅ Database initialized.")

def check_env_vars():
    """Checks if required environment variables are set. Exits if missing."""
    required_vars = ['FLASK_PORT', 'FLASK_DEBUG']
    missing = [var for var in required_vars if os.getenv(var) is None]
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)

check_env_vars()
init_db()

app = Flask(__name__)

# Configure Flask logging to be visible in Gunicorn
if __name__ != '__main__':
    # Gunicorn uses 'gunicorn.error' logger
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Global trackers for Network Speed calculation
net_data = {
    "last_recv": psutil.net_io_counters().bytes_recv,
    "last_sent": psutil.net_io_counters().bytes_sent,
    "last_time": time.time()
}

def get_system_stats():
    global net_data
    cpu_usage = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load_1, load_5, load_15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0)

    current_net = psutil.net_io_counters()
    current_time = time.time()
    elapsed = current_time - net_data["last_time"]
    elapsed = elapsed if elapsed > 0 else 1
    
    download_speed = (current_net.bytes_recv - net_data["last_recv"]) / elapsed / 1024
    upload_speed = (current_net.bytes_sent - net_data["last_sent"]) / elapsed / 1024
    
    net_data.update({
        "last_recv": current_net.bytes_recv,
        "last_sent": current_net.bytes_sent,
        "last_time": current_time
    })

    uptime_seconds = int(time.time() - psutil.boot_time())
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    return {
        "cpu": cpu_usage,
        "load_avg": f"{load_1}, {load_5}, {load_15}",
        "memory_percent": memory.percent,
        "memory_used": round(memory.used / (1024**3), 2),
        "memory_total": round(memory.total / (1024**3), 2),
        "memory_cached": round((memory.cached if hasattr(memory, 'cached') else 0) / (1024**3), 2),
        "disk_percent": disk.percent,
        "net_up": f"{upload_speed:.1f} KB/s",
        "net_down": f"{download_speed:.1f} KB/s",
        "uptime": f"{hours}h {minutes}m",
        "os_info": f"{platform.system()} {platform.release()}"
    }

def log_stats_task():
    """Background task to log stats."""
    try:
        stats = get_system_stats()
        up = float(stats['net_up'].split()[0])
        down = float(stats['net_down'].split()[0])
        
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                INSERT INTO system_stats (cpu, memory_percent, disk_percent, net_up, net_down)
                VALUES (?, ?, ?, ?, ?)
            ''', (stats['cpu'], stats['memory_percent'], stats['disk_percent'], up, down))
        
        app.logger.info(f"Background Log Successful: CPU {stats['cpu']}% | RAM {stats['memory_percent']}%")
    except Exception as e:
        app.logger.error(f"Background Logging Failed: {str(e)}")

# Start the background scheduler
scheduler = BackgroundScheduler()
seconds_internal = int(os.getenv('LOG_SECONDS', 300))
scheduler.add_job(func=log_stats_task, trigger="interval", seconds=seconds_internal)
scheduler.start()
app.logger.info(f"Scheduler started. Logging every {seconds_internal} seconds.")

@app.route('/')
def index():
    return render_template('index.html', stats=get_system_stats())

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/api/stats')
def api_stats():
    # Only log this if you really need to debug dashboard polling
    return jsonify(get_system_stats())

@app.route('/api/history')
def api_history():
    limit = request.args.get('limit', default=100, type=int)
    if limit > 1000: limit = 1000

    app.logger.info(f"API History Requested: limit={limit} from {request.remote_addr}")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute('SELECT * FROM system_stats ORDER BY timestamp DESC LIMIT ?', (limit,))
        rows = cursor.fetchall()
    
    return jsonify([dict(row) for row in rows][::-1])

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    app.logger.warning(f"CLEAR HISTORY TRIGGERED from {request.remote_addr}")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('DELETE FROM system_stats')
            conn.execute("DELETE FROM sqlite_sequence WHERE name='system_stats'")
        return jsonify({"status": "success", "message": "History cleared"})
    except Exception as e:
        app.logger.error(f"Clear History Failed: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    try:
        is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        port_num = int(os.getenv('FLASK_PORT', 5000))
        app.run(host='0.0.0.0', port=port_num, debug=is_debug, use_reloader=False)
    except (KeyboardInterrupt, SystemExit):
        app.logger.info("Shutting down scheduler...")
        scheduler.shutdown()