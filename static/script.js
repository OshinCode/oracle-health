document.addEventListener('DOMContentLoaded', () => {
    // Initialize Theme Logic
    toggleDarkMode();

    // Initialize Live Stats Loop
    startLiveUpdates();
});

function toggleDarkMode() {
    const toggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    const getCookie = (name) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    };

    // 1. Just update the button text (the head script already set the theme)
    const savedTheme = getCookie('theme');
    if (savedTheme === 'dark') {
        toggleBtn.innerHTML = '☀️ Light Mode';
    }

    // 2. Keep the toggle logic for clicking
    toggleBtn.addEventListener('click', () => {
        const currentTheme = htmlElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        htmlElement.setAttribute('data-theme', newTheme);
        toggleBtn.innerHTML = newTheme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode';

        document.cookie = `theme=${newTheme}; path=/; max-age=${60 * 60 * 24 * 30}; SameSite=Lax`;
    });
}

/**
 * Fetches JSON data from /api/stats and updates the DOM elements 
 * without refreshing the entire page.
 */
async function startLiveUpdates() {
    const updateStats = async () => {
        try {
            const response = await fetch('/api/stats');
            if (!response.ok) throw new Error('Network response was not ok');

            const data = await response.json();

            document.getElementById('load-val').innerText = data.load_avg;
            document.getElementById('os-info').innerText = data.os_info;
            document.getElementById('mem-cached').innerText = data.memory_cached;

            // Update CPU Text and Bar
            document.getElementById('cpu-val').innerText = `${data.cpu}%`;
            document.getElementById('cpu-bar').style.width = `${data.cpu}%`;

            // Update Memory Text and GB values
            document.getElementById('mem-val').innerText = `${data.memory_percent}%`;
            document.getElementById('mem-used').innerText = data.memory_used;

            // Update Disk Text and Bar
            document.getElementById('disk-val').innerText = `${data.disk_percent}%`;
            document.getElementById('disk-bar').style.width = `${data.disk_percent}%`;

            // --- PRO TIP: UPDATE TIMESTAMP & PULSE EFFECT ---
            const updateSpan = document.getElementById('last-update');
            if (updateSpan) {
                const now = new Date();
                updateSpan.innerText = now.toLocaleTimeString();

                // Visual Pulse: Flash green for 1 second
                updateSpan.style.color = '#2ecc71';
                updateSpan.style.transition = 'color 0.3s ease';
                setTimeout(() => {
                    updateSpan.style.color = ''; // Returns to CSS default
                }, 1000);
            }

        } catch (error) {
            console.error('Error fetching live stats:', error);
            const updateSpan = document.getElementById('last-update');
            if (updateSpan) updateSpan.innerText = "Update Failed";
        }
    };

    // Run once immediately
    updateStats();

    // Set the loop
    setInterval(updateStats, 5000);
}

/* --- Existing Dashboard Logic --- */
// (Keep your DOMContentLoaded, toggleDarkMode, and startLiveUpdates here)

/* --- NEW: History Page Logic --- */
let usageChartInstance = null;
let networkChartInstance = null;

async function loadCharts() {
    const limitSelect = document.getElementById('limit-select');
    if (!limitSelect) return; // Exit if not on the history page

    try {
        const limit = limitSelect.value;
        const response = await fetch(`/api/history?limit=${limit}`);
        const data = await response.json();

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
        const textColor = isDark ? '#b0b0b0' : '#6c757d';

        const labels = data.map(entry => entry.timestamp.split(' ')[1]);

        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                x: { grid: { color: gridColor }, ticks: { color: textColor } },
                y: { grid: { color: gridColor }, ticks: { color: textColor } }
            },
            plugins: { 
                legend: { labels: { color: textColor } },
                tooltip: {
                    enabled: true,
                    backgroundColor: isDark ? '#2b2b2b' : 'rgba(0, 0, 0, 0.8)',
                    titleColor: isDark ? '#e0e0e0' : '#fff',
                    bodyColor: isDark ? '#e0e0e0' : '#fff',
                    borderColor: isDark ? '#444' : 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) {
                                const isNetwork = context.chart.canvas.id === 'networkChart';
                                label += context.parsed.y + (isNetwork ? ' KB/s' : '%');
                            }
                            return label;
                        }
                    }
                }
            }
        };

        if (usageChartInstance) usageChartInstance.destroy();
        if (networkChartInstance) networkChartInstance.destroy();

        usageChartInstance = new Chart(document.getElementById('usageChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'CPU %', data: data.map(e => e.cpu), borderColor: '#0d6efd', tension: 0.3, pointRadius: 0 },
                    { label: 'RAM %', data: data.map(e => e.memory_percent), borderColor: '#198754', tension: 0.3, pointRadius: 0 },
                    { label: 'Disk %', data: data.map(e => e.disk_percent), borderColor: '#dc3545', tension: 0.3, pointRadius: 0 }
                ]
            },
            options: { ...commonOptions, scales: { ...commonOptions.scales, y: { ...commonOptions.scales.y, min: 0, max: 100 } } }
        });

        networkChartInstance = new Chart(document.getElementById('networkChart'), {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Upload (KB/s)', data: data.map(e => e.net_up), borderColor: '#0dcaf0', pointRadius: 0 },
                    { label: 'Download (KB/s)', data: data.map(e => e.net_down), borderColor: '#2ecc71', pointRadius: 0 }
                ]
            },
            options: commonOptions
        });
    } catch (error) {
        console.error("Failed to load history charts:", error);
    }
}

// Automatically trigger loadCharts if we are on the history page
if (window.location.pathname === '/history') {
    document.addEventListener('DOMContentLoaded', loadCharts);
}