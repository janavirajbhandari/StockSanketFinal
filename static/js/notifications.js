// Initialize notifications from localStorage or empty array if none exists
const storedNotifications = localStorage.getItem('notifications');
let notifications = storedNotifications ? JSON.parse(storedNotifications) : [];

// Also track watchlist stocks and processed alerts
let watchlistStocks = new Set();
let processedAlerts = new Map(); // Use Map to store timestamp of last alert for each symbol
let wsReconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 5000;

// Track WebSocket connection
let websocket = null;

window.markAsRead = function(id, event) {
    if (event) {
        event.stopPropagation();
    }
    try {
        notifications = notifications.map(n => 
            n.id === id ? { ...n, read: true } : n
        );
        localStorage.setItem('notifications', JSON.stringify(notifications));
        renderNotifications();
    } catch (error) {
        console.error("❌ Error marking notification as read:", error);
    }
};

// Function to update watchlist stocks
function updateWatchlistStocks() {
    fetch('/watchlists/')
        .then(response => response.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const watchlistRows = doc.querySelectorAll('.watchlist-row');
            watchlistStocks.clear();
            watchlistRows.forEach(row => {
                const symbol = row.getAttribute('data-symbol');
                if (symbol) watchlistStocks.add(symbol);
            });
        })
        .catch(error => console.error('Error fetching watchlist:', error));
}

// Update watchlist stocks on page load and every minute
document.addEventListener('DOMContentLoaded', updateWatchlistStocks);
setInterval(updateWatchlistStocks, 60000);

// WebSocket connection
function connectWebSocket() {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        console.log("✅ WebSocket already connected");
        return;
    }

    if (wsReconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        console.error("❌ Maximum WebSocket reconnection attempts reached");
        return;
    }

    console.log("🔌 Connecting to WebSocket...");
    websocket = new WebSocket(
        `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/stock_alerts/`
    );

    websocket.onopen = function() {
        console.log("✅ WebSocket connected!");
        wsReconnectAttempts = 0;
        createToastContainer();
    };

    websocket.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            if (data && data.symbol && data.change !== undefined) {
                // Check if there's an unread notification for this symbol
                const hasUnreadNotification = notifications.some(
                    notif => notif.symbol === data.symbol && !notif.read
                );
                
                // Skip if there's already an unread notification for this symbol
                if (hasUnreadNotification) {
                    console.log("⚠️ Skipping alert - unread notification exists for:", data.symbol);
                    return;
                }
                
                console.log("🎯 Processing new alert:", data);
                handleNewAlert(data);
            }
        } catch (error) {
            console.error("❌ Error processing message:", error);
        }
    };

    websocket.onerror = function(e) {
        console.error("❌ WebSocket error:", e);
        wsReconnectAttempts++;
    };

    websocket.onclose = function(e) {
        console.log("🔌 WebSocket closed.", e.reason);
        websocket = null;
        
        if (wsReconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            const delay = RECONNECT_DELAY * Math.pow(2, wsReconnectAttempts);
            console.log(`🔄 Reconnecting in ${delay/1000}s... (Attempt ${wsReconnectAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`);
            setTimeout(connectWebSocket, delay);
        }
    };
}

// Initialize WebSocket connection when document is ready
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Initializing notifications system");
    createToastContainer();
    renderNotifications();
    connectWebSocket();
});

// Reconnect WebSocket when page becomes visible
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
        console.log("📱 Page visible - checking WebSocket connection");
        connectWebSocket();
    }
});

function handleNewAlert(alert) {
    console.log("🔔 Handling new alert:", alert);
    try {
        showToast(alert);
        addNotification(alert);
    } catch (error) {
        console.error("❌ Error handling alert:", error);
    }
}

function createToastContainer() {
    if (!document.querySelector('.toast-container')) {
        const container = document.createElement('div');
        container.className = 'toast-container fixed top-20 right-4 z-50';
        
        // Add CSS for animations if not already present
        if (!document.getElementById('toast-animations')) {
            const style = document.createElement('style');
            style.id = 'toast-animations';
            style.textContent = `
                @keyframes slideIn {
                    from {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                    to {
                        transform: translateX(0);
                        opacity: 1;
                    }
                }
                
                @keyframes fadeOut {
                    from {
                        transform: translateX(0);
                        opacity: 1;
                    }
                    to {
                        transform: translateX(100%);
                        opacity: 0;
                    }
                }
                
                .toast-container {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(container);
        console.log("✅ Toast container created");
        return container;
    }
    return document.querySelector('.toast-container');
}

function showToast(alert) {
    try {
        const container = document.querySelector('.toast-container');
        if (!container) {
            console.error("❌ Toast container not found!");
            return;
        }
        
        const isInWatchlist = watchlistStocks.has(alert.symbol);
        const toast = document.createElement('div');
        
        toast.className = `fixed top-4 right-4 bg-white rounded-lg shadow-lg p-4 mb-4 border-l-4 min-w-[300px] w-[400px] ${
            alert.change > 0 ? 'border-green-500' : 'border-red-500'
        } ${isInWatchlist ? 'border-yellow-500' : ''}`;
        
        toast.style.zIndex = '9999';  // Ensure it's above other elements
        
        toast.innerHTML = `
            <div class="flex justify-between items-start w-full">
                <div class="flex-grow">
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-lg">${alert.symbol}</span>
                        ${isInWatchlist ? '<span class="text-yellow-500 text-xl">⭐</span>' : ''}
                    </div>
                    <div class="mt-2">
                        <p class="${alert.change > 0 ? 'text-green-600' : 'text-red-600'} text-base font-semibold">
                            ${alert.change > 0 ? '▲' : '▼'} ${Math.abs(alert.change)}%
                        </p>
                        <p class="text-gray-600 font-medium">Rs. ${alert.ltp}</p>
                        <p class="text-gray-400 text-sm mt-1">${alert.timestamp}</p>
                    </div>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" 
                        class="text-gray-500 hover:text-gray-700 text-xl font-bold">
                    ×
                </button>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Add slide-in animation
        toast.style.animation = 'slideIn 0.3s ease-out';
        
        // Remove after 5 seconds with fade-out
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    } catch (error) {
        console.error("❌ Error showing toast:", error);
    }
}

function addNotification(alert) {
    try {
        const notification = {
            id: Date.now(),
            message: `${alert.symbol} ${alert.change > 0 ? 'increased' : 'decreased'} by ${Math.abs(alert.change)}%`,
            type: alert.change > 0 ? 'success' : 'error',
            read: false,
            timestamp: alert.timestamp,
            symbol: alert.symbol,
            ltp: alert.ltp
        };
        
        notifications.unshift(notification);
        if (notifications.length > 50) notifications.pop();
        localStorage.setItem('notifications', JSON.stringify(notifications));
        renderNotifications();
    } catch (error) {
        console.error("❌ Error adding notification:", error);
    }
}

function renderNotifications() {
    try {
        const list = document.getElementById("notification-list");
        const count = document.getElementById("notif-count");
        
        if (!list || !count) {
            console.warn("⚠️ Notification elements not found in DOM");
            return;
        }
        
        list.innerHTML = "";
        let unreadCount = 0;

        notifications.forEach((notif) => {
            if (!notif.read) unreadCount++;
            
            const li = document.createElement("div");
            li.className = `px-4 py-3 hover:bg-gray-50 cursor-pointer ${notif.read ? 'bg-gray-50' : 'bg-white'} border-b border-gray-200`;
            
            li.innerHTML = `
                <div class="flex justify-between items-start">
                    <div class="flex-grow cursor-pointer" onclick="window.location.href='/stockDetail/?symbol=${encodeURIComponent(notif.symbol)}'">
                        <div class="${notif.type === 'error' ? 'text-red-600' : 'text-green-600'} font-medium">
                            ${notif.symbol}
                        </div>
                        <div class="text-sm text-gray-600">${notif.message}</div>
                        <div class="text-xs text-gray-400 mt-1">${notif.timestamp}</div>
                    </div>
                    ${!notif.read ? `
                        <button onclick="markAsRead(${notif.id}, event)" 
                                class="text-xs text-blue-500 hover:underline ml-2">
                            Mark as read
                        </button>
                    ` : ''}
                </div>
            `;
            
            list.appendChild(li);
        });

        // Update notification count
        count.textContent = unreadCount.toString();
        count.classList.toggle('hidden', unreadCount === 0);
        
    } catch (error) {
        console.error("❌ Error rendering notifications:", error);
    }
}

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
    console.log("🚀 Initializing notifications system");
    createToastContainer();
    renderNotifications();
}); 