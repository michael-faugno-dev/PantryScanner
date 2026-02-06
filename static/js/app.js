// Pantry Monitor - Frontend JavaScript

// Initialize on page load
document.addEventListener("DOMContentLoaded", function () {
  loadAllData();

  // Auto-refresh every 30 seconds
  setInterval(loadAllData, 30000);
});

// Load all data
async function loadAllData() {
  await Promise.all([
    loadStatistics(),
    loadInventory(),
    loadRecentScans(),
    loadLatestImage(),
  ]);
}

// Load statistics
async function loadStatistics() {
  try {
    const response = await fetch("/api/statistics");
    const stats = await response.json();

    document.getElementById("statTotalItems").textContent = stats.active_items;
    document.getElementById("statTotalScans").textContent = stats.total_scans;
    document.getElementById("statChanges").textContent =
      stats.changes_last_week;
    document.getElementById("statCost").textContent =
      `$${stats.total_api_cost.toFixed(4)}`;
  } catch (error) {
    console.error("Error loading statistics:", error);
  }
}

// Load inventory
async function loadInventory() {
  try {
    const response = await fetch("/api/inventory");
    const inventory = await response.json();

    const listElement = document.getElementById("inventoryList");
    const countElement = document.getElementById("itemCount");

    countElement.textContent = `${inventory.length} item${inventory.length !== 1 ? "s" : ""}`;

    if (inventory.length === 0) {
      listElement.innerHTML =
        '<div class="loading-spinner">No items in pantry yet.</div>';
      return;
    }

    // Sort by most recently seen
    inventory.sort((a, b) => new Date(b.last_seen) - new Date(a.last_seen));

    listElement.innerHTML = inventory
      .map(
        (item) => `
            <div class="inventory-item" onclick="viewItemDetails(${item.id})">
                <div class="item-info">
                    <div class="item-name">${truncateText(item.name, 60)}</div>
                    <div class="item-meta">
                        <span>📅 ${formatDaysAgo(item.last_seen)}</span>
                        <span>⏱️ ${item.days_in_pantry} days in pantry</span>
                    </div>
                </div>
                <div class="item-quantity">×${item.quantity}</div>
            </div>
        `,
      )
      .join("");
  } catch (error) {
    console.error("Error loading inventory:", error);
    document.getElementById("inventoryList").innerHTML =
      '<div class="loading-spinner">Error loading inventory.</div>';
  }
}

// Load recent scans
async function loadRecentScans() {
  try {
    const response = await fetch("/api/recent-scans");
    const scans = await response.json();

    const listElement = document.getElementById("recentScans");

    if (scans.length === 0) {
      listElement.innerHTML =
        '<div class="loading-spinner">No scans yet.</div>';
      return;
    }

    // Update last scan time in header
    if (scans.length > 0) {
      document.getElementById("lastScanTime").textContent = formatDateTime(
        scans[0].date,
      );
    }

    listElement.innerHTML = scans
      .slice(0, 5)
      .map(
        (scan) => `
            <div class="activity-item">
                <div class="activity-info">
                    <div class="activity-icon">📸</div>
                    <div class="activity-details">
                        <h4>Scan #${scan.id}</h4>
                        <div class="activity-time">${formatDateTime(scan.date)}</div>
                    </div>
                </div>
                <div class="activity-cost">
                    <div>$${scan.cost.toFixed(6)}</div>
                    <div class="activity-time">${scan.input_tokens + scan.output_tokens} tokens</div>
                </div>
            </div>
        `,
      )
      .join("");
  } catch (error) {
    console.error("Error loading recent scans:", error);
  }
}

// Load latest image
async function loadLatestImage() {
  try {
    const response = await fetch("/api/latest-image");
    const data = await response.json();

    if (data.exists) {
      const img = document.getElementById("latestImage");
      // Add timestamp to prevent caching
      img.src = `/image/current.jpg?t=${new Date().getTime()}`;

      document.getElementById("imageTimestamp").textContent = formatTimeAgo(
        data.last_updated,
      );
    }
  } catch (error) {
    console.error("Error loading latest image:", error);
  }
}

// Filter items
function filterItems() {
  const searchTerm = document.getElementById("searchInput").value.toLowerCase();
  const items = document.querySelectorAll(".inventory-item");

  items.forEach((item) => {
    const name = item.querySelector(".item-name").textContent.toLowerCase();
    if (name.includes(searchTerm)) {
      item.style.display = "flex";
    } else {
      item.style.display = "none";
    }
  });
}

// View fullscreen image
function viewFullscreen() {
  const modal = document.getElementById("imageModal");
  const modalImg = document.getElementById("modalImage");
  const img = document.getElementById("latestImage");

  modalImg.src = img.src;
  modal.classList.add("active");
}

// Close modal
function closeModal() {
  const modal = document.getElementById("imageModal");
  modal.classList.remove("active");
}

// View item details (placeholder for future feature)
function viewItemDetails(itemId) {
  console.log("View details for item:", itemId);
  // TODO: Implement item history modal
}

// Refresh all data
function refreshData() {
  const btn = document.querySelector(".btn-refresh");
  btn.style.transform = "rotate(360deg)";

  loadAllData();

  setTimeout(() => {
    btn.style.transform = "rotate(0deg)";
  }, 600);
}

// Helper: Format date/time
function formatDateTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

// Helper: Format time ago
function formatTimeAgo(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hours ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// Helper: Format days ago
function formatDaysAgo(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const hours = Math.floor(diff / 3600000);

  if (hours < 1) return "Just now";
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

// Helper: Truncate text
function truncateText(text, maxLength) {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + "...";
}

// Close modal on Escape key
document.addEventListener("keydown", function (e) {
  if (e.key === "Escape") {
    closeModal();
  }
});
