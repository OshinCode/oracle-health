import os
import psutil
import datetime
import sys
import time  # Added for speed calculation
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import platform

# 1. Load the .env file
load_dotenv()

def check_env_vars():
    """Checks if required environment variables are set. Exits if missing."""
    required_vars = ['FLASK_PORT', 'FLASK_DEBUG']
    missing = [var for var in required_vars if os.getenv(var) is None]
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please ensure your .env file exists and contains these values.")
        sys.exit(1)
    
    print("✅ Environment check passed.")

check_env_vars()

app = Flask(__name__)

# --- NEW: Global trackers for Network Speed calculation ---
net_data = {
    "last_recv": psutil.net_io_counters().bytes_recv,
    "last_sent": psutil.net_io_counters().bytes_sent,
    "last_time": time.time()
}

def get_system_stats():
    global net_data
    
    # Existing basic stats
    cpu_usage = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # --- NEW: Load Average (1, 5, 15 min) ---
    # Standard for Linux: shows system pressure
    load_1, load_5, load_15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0)

    # Calculate Network Speed
    current_net = psutil.net_io_counters()
    current_time = time.time()
    elapsed = current_time - net_data["last_time"]
    download_speed = (current_net.bytes_recv - net_data["last_recv"]) / elapsed / 1024
    upload_speed = (current_net.bytes_sent - net_data["last_sent"]) / elapsed / 1024
    
    net_data.update({
        "last_recv": current_net.bytes_recv,
        "last_sent": current_net.bytes_sent,
        "last_time": current_time
    })

    # Calculate Uptime
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

@app.route('/')
def index():
    stats = get_system_stats()
    stats["boot_time"] = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    return render_template('index.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    # Calling get_system_stats() triggers the calculation logic
    return jsonify(get_system_stats())

if __name__ == '__main__':
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port_num = int(os.getenv('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', port=port_num, debug=is_debug)