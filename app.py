import os
import psutil
import datetime
import sys
from flask import Flask, render_template, jsonify
from dotenv import load_dotenv

# 1. Load the .env file
load_dotenv()

def check_env_vars():
    """Checks if required environment variables are set. Exits if missing."""
    required_vars = ['FLASK_PORT', 'FLASK_DEBUG']
    missing = [var for var in required_vars if os.getenv(var) is None]
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
        print("Please ensure your .env file exists and contains these values.")
        sys.exit(1)  # Stop the app immediately
    
    print("✅ Environment check passed.")

# Run the check before starting the app
check_env_vars()

app = Flask(__name__)

# --- (Rest of your helper functions and routes stay the same) ---

def get_system_stats():
    cpu_usage = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    return {
        "cpu": cpu_usage,
        "memory_percent": memory.percent,
        "memory_used": round(memory.used / (1024**3), 2),
        "memory_total": round(memory.total / (1024**3), 2),
        "disk_percent": disk.percent
    }

@app.route('/')
def index():
    stats = get_system_stats()
    stats["boot_time"] = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    return render_template('index.html', stats=stats)

@app.route('/api/stats')
def api_stats():
    return jsonify(get_system_stats())

if __name__ == '__main__':
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port_num = int(os.getenv('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', port=port_num, debug=is_debug)