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