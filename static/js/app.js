const plantGrid = document.getElementById("plantGrid");
const detailPanel = document.getElementById("detailPanel");
const totalPlants = document.getElementById("totalPlants");
const needsAttention = document.getElementById("needsAttention");
const averageMoisture = document.getElementById("averageMoisture");
const thrivingCount = document.getElementById("thrivingCount");
const searchInput = document.getElementById("searchInput");
const roomFilters = document.getElementById("roomFilters");
const tipText = document.getElementById("tipText");
const plantForm = document.getElementById("plantForm");
const formMessage = document.getElementById("formMessage");
const plantModal = document.getElementById("plantModal");
const openFormButton = document.getElementById("openFormButton");
const closeFormButton = document.getElementById("closeFormButton");
const focusThirstyButton = document.getElementById("focusThirstyButton");
const healthPills = Array.from(document.querySelectorAll("[data-health]"));

let dashboardData = { plants: [], stats: {} };
let selectedPlantId = null;
let activeRoom = "all";
let activeHealth = "all";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function statusClass(value) {
  return String(value).toLowerCase().replaceAll(" ", "-");
}

function setFormMessage(message, isError = false) {
  formMessage.textContent = message;
  formMessage.style.color = isError ? "#bb4d3f" : "#5f7569";
}

function updateStats(stats) {
  totalPlants.textContent = stats.total_plants ?? 0;
  needsAttention.textContent = stats.needs_attention ?? 0;
  averageMoisture.textContent = `${stats.average_moisture ?? 0}%`;
  thrivingCount.textContent = stats.thriving_count ?? 0;
}

function getFilteredPlants() {
  const query = searchInput.value.trim().toLowerCase();

  return dashboardData.plants.filter((plant) => {
    const matchesRoom = activeRoom === "all" || plant.room === activeRoom;
    const matchesHealth = activeHealth === "all" || plant.health_status === activeHealth;
    const haystack = `${plant.name} ${plant.species} ${plant.room}`.toLowerCase();
    return matchesRoom && matchesHealth && (!query || haystack.includes(query));
  });
}

function renderRoomFilters(plants) {
  const rooms = ["all", ...new Set(plants.map((plant) => plant.room))];
  roomFilters.innerHTML = rooms
    .map(
      (room) => `
        <button type="button" class="filter-pill ${room === activeRoom ? "active" : ""}" data-room="${escapeHtml(room)}">
          ${escapeHtml(room === "all" ? "All rooms" : room)}
        </button>
      `
    )
    .join("");
}

function renderPlantCards() {
  const plants = getFilteredPlants();

  if (!plants.length) {
    plantGrid.innerHTML = `
      <article class="plant-card">
        <p class="mini-label">No results</p>
        <h3 class="plant-name">Nothing matches these filters</h3>
        <p class="plant-meta">Try another room, health status, or search term.</p>
      </article>
    `;
    return;
  }

  plantGrid.innerHTML = plants
    .map(
      (plant) => `
        <article class="plant-card ${plant.id === selectedPlantId ? "active" : ""}" data-id="${plant.id}">
          <div class="plant-card-top">
            <div>
              <p class="mini-label">${escapeHtml(plant.room)}</p>
              <h3 class="plant-name">${escapeHtml(plant.name)}</h3>
              <p class="plant-meta">${escapeHtml(plant.species)}</p>
            </div>
            <span class="status-pill ${statusClass(plant.health_status)}">${escapeHtml(plant.health_status)}</span>
          </div>
          <img src="${escapeHtml(plant.image_url)}" alt="${escapeHtml(plant.name)}" />
          <div class="moisture-row">
            <div class="meter-track">
              <div class="meter-fill" style="width: ${plant.moisture}%"></div>
            </div>
            <div class="meter-label">
              <span>Moisture</span>
              <strong>${plant.moisture}%</strong>
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function buildCareLogs(logs) {
  if (!logs.length) {
    return `<div class="care-log"><strong>No logs yet</strong><p>This plant does not have recent actions.</p></div>`;
  }

  return logs
    .map(
      (log) => `
        <div class="care-log">
          <strong>${escapeHtml(log.action)}</strong>
          <p>${escapeHtml(log.details)}</p>
          <time>${escapeHtml(log.created_on)}</time>
        </div>
      `
    )
    .join("");
}

function renderDetails() {
  const plant = dashboardData.plants.find((item) => item.id === selectedPlantId);

  if (!plant) {
    detailPanel.className = "detail-panel empty";
    detailPanel.innerHTML = `
      <p class="mini-label">Plant details</p>
      <h3>Select a plant</h3>
      <p>Its moisture, notes, room, and recent care activity will appear here.</p>
    `;
    return;
  }

  detailPanel.className = "detail-panel";
  detailPanel.innerHTML = `
    <div class="detail-header">
      <img class="detail-image" src="${escapeHtml(plant.image_url)}" alt="${escapeHtml(plant.name)}" />
      <div class="detail-title">
        <div>
          <p class="mini-label">${escapeHtml(plant.room)}</p>
          <h3>${escapeHtml(plant.name)}</h3>
          <p class="detail-meta">${escapeHtml(plant.species)} • ${escapeHtml(plant.light_level)}</p>
        </div>
        <span class="status-pill ${statusClass(plant.health_status)}">${escapeHtml(plant.health_status)}</span>
      </div>
    </div>

    <div class="detail-stats">
      <div class="detail-stat">
        <span>Soil moisture</span>
        <strong>${plant.moisture}%</strong>
      </div>
      <div class="detail-stat">
        <span>Water target</span>
        <strong>${plant.water_target_ml} ml</strong>
      </div>
      <div class="detail-stat">
        <span>Last watered</span>
        <strong>${escapeHtml(plant.last_watered || "Not set")}</strong>
      </div>
      <div class="detail-stat">
        <span>Light</span>
        <strong>${escapeHtml(plant.light_level)}</strong>
      </div>
    </div>

    <div class="plant-actions">
      <button type="button" class="action-button" data-water-id="${plant.id}" data-water-amount="${plant.water_target_ml}">
        Water ${escapeHtml(plant.name)}
      </button>
    </div>

    <p>${escapeHtml(plant.notes || "No care notes added yet.")}</p>

    <div class="section-heading">
      <p class="mini-label">Recent care</p>
      <h3>Activity log</h3>
    </div>
    <div class="care-log-list">
      ${buildCareLogs(plant.care_logs)}
    </div>
  `;

  tipText.textContent = `${plant.name} in the ${plant.room} is currently at ${plant.moisture}% moisture.`;
}

function refreshUI() {
  updateStats(dashboardData.stats);
  renderRoomFilters(dashboardData.plants);
  renderPlantCards();

  const visiblePlants = getFilteredPlants();
  if (!visiblePlants.some((plant) => plant.id === selectedPlantId)) {
    selectedPlantId = visiblePlants[0]?.id ?? null;
  }
  renderDetails();
}

async function loadDashboard() {
  const response = await fetch("/api/dashboard");
  dashboardData = await response.json();
  if (!selectedPlantId) {
    selectedPlantId = dashboardData.plants[0]?.id ?? null;
  }
  refreshUI();
}

async function waterPlant(plantId, waterAmount) {
  const response = await fetch(`/api/plants/${plantId}/water`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      water_amount: waterAmount,
      watered_on: new Date().toISOString().split("T")[0],
    }),
  });
  dashboardData = await response.json();
  selectedPlantId = plantId;
  refreshUI();
}

async function submitPlantForm(event) {
  event.preventDefault();
  setFormMessage("Saving plant...");

  const payload = Object.fromEntries(new FormData(plantForm).entries());
  const response = await fetch("/api/plants", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    setFormMessage(errorData.errors?.join(" ") || "Could not save plant.", true);
    return;
  }

  dashboardData = await response.json();
  selectedPlantId = Math.max(...dashboardData.plants.map((plant) => plant.id));
  plantForm.reset();
  setTodayDefault();
  setFormMessage("Plant saved successfully.");
  plantModal.classList.add("hidden");
  refreshUI();
}

function setTodayDefault() {
  const dateField = plantForm.querySelector('input[name="last_watered"]');
  dateField.value = new Date().toISOString().split("T")[0];
}

plantGrid.addEventListener("click", (event) => {
  const card = event.target.closest("[data-id]");
  if (!card) {
    return;
  }
  selectedPlantId = Number(card.dataset.id);
  renderPlantCards();
  renderDetails();
});

detailPanel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-water-id]");
  if (!button) {
    return;
  }
  waterPlant(Number(button.dataset.waterId), Number(button.dataset.waterAmount)).catch(() => {
    tipText.textContent = "Watering action failed. Please try again.";
  });
});

searchInput.addEventListener("input", refreshUI);

roomFilters.addEventListener("click", (event) => {
  const pill = event.target.closest("[data-room]");
  if (!pill) {
    return;
  }
  activeRoom = pill.dataset.room;
  refreshUI();
});

healthPills.forEach((pill) => {
  pill.addEventListener("click", () => {
    activeHealth = pill.dataset.health;
    healthPills.forEach((item) => item.classList.remove("active"));
    pill.classList.add("active");
    refreshUI();
  });
});

openFormButton.addEventListener("click", () => plantModal.classList.remove("hidden"));
closeFormButton.addEventListener("click", () => plantModal.classList.add("hidden"));
focusThirstyButton.addEventListener("click", () => {
  activeHealth = "Needs water";
  healthPills.forEach((pill) => pill.classList.toggle("active", pill.dataset.health === "Needs water"));
  refreshUI();
});
plantForm.addEventListener("submit", submitPlantForm);

setTodayDefault();
loadDashboard().catch(() => {
  tipText.textContent = "The dashboard could not load right now.";
});
