from flask import Flask, render_template
import psutil
import datetime

app = Flask(__name__)

@app.route('/')
def index():
    # Gather System Data
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    
    stats = {
        "cpu": cpu_usage,
        "memory_percent": memory.percent,
        "memory_used": round(memory.used / (1024**3), 2),
        "memory_total": round(memory.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "boot_time": boot_time
    }
    
    return render_template('index.html', stats=stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)