const form = document.getElementById('search-form');
const queryInput = document.getElementById('query-input');
const locationInput = document.getElementById('location-input');
const searchBtn = document.getElementById('search-btn');
const statusBox = document.getElementById('status-box');
const statusText = document.getElementById('status-text');
const resultsContainer = document.getElementById('results-container');
const quickPills = document.querySelectorAll('.pill');

// Quick pill selection
quickPills.forEach((pill) => {
  pill.addEventListener('click', () => {
    queryInput.value = pill.getAttribute('data-query');
    form.dispatchEvent(new Event('submit', { cancelable: true }));
  });
});

// Form submission
form.addEventListener('submit', async (event) => {
  event.preventDefault();

  const query = queryInput.value.trim();
  const location = locationInput.value.trim();

  if (!query || !location) {
    showStatus('Please enter both a search item and a delivery location.', 'error');
    return;
  }

  // Clear previous results & activate loading state
  resultsContainer.innerHTML = '';
  searchBtn.classList.add('loading');
  searchBtn.disabled = true;
  showStatus(`Searching Blinkit and Instamart for "${query}" delivered to "${location}"…`, 'loading');

  try {
    const endpoint = `/search?q=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`;
    const response = await fetch(endpoint);
    const data = await response.json();

    if (!response.ok) {
      showStatus(data.detail || 'Failed to fetch search results.', 'error');
      return;
    }

    if (!data.results || data.results.length === 0) {
      showStatus(`No matching listings found on either platform for "${query}".`, 'default');
      return;
    }

    const matchCount = data.results.filter(r => r.blinkit && r.instamart).length;
    showStatus(
      `Found ${data.results.length} total result(s) (${matchCount} direct comparisons) for "${data.query}" in "${data.location}".`,
      'default'
    );

    renderResults(data.results);
  } catch (err) {
    showStatus('Could not connect to the comparison server. Please verify the backend is running.', 'error');
  } finally {
    searchBtn.classList.remove('loading');
    searchBtn.disabled = false;
  }
});

function showStatus(message, type = 'default') {
  statusBox.className = `status-box ${type}`;
  statusText.textContent = message;
}

function renderResults(pairs) {
  resultsContainer.innerHTML = '';

  pairs.forEach((pair) => {
    const card = document.createElement('div');
    card.className = 'result-card';

    const blinkitIsCheaper = pair.cheaper === 'blinkit';
    const instamartIsCheaper = pair.cheaper === 'instamart';
    const isTie = pair.cheaper === 'tie';

    let savingsDiff = 0;
    if (pair.blinkit && pair.instamart) {
      savingsDiff = Math.abs(pair.blinkit.price - pair.instamart.price);
    }

    card.appendChild(renderPlatformColumn('Blinkit', pair.blinkit, blinkitIsCheaper, isTie, savingsDiff));
    card.appendChild(renderPlatformColumn('Instamart', pair.instamart, instamartIsCheaper, isTie, savingsDiff));

    resultsContainer.appendChild(card);
  });
}

function renderPlatformColumn(platformName, listing, isWinner, isTie, savingsDiff) {
  const col = document.createElement('div');
  col.className = `listing-column ${isWinner ? 'is-winner' : ''}`;

  const platformClass = platformName.toLowerCase();

  if (!listing) {
    col.innerHTML = `
      <div class="platform-tag ${platformClass}">${platformName}</div>
      <div class="no-listing">
        <p>No matching product listed on ${platformName}</p>
      </div>
    `;
    return col;
  }

  let badgeHtml = '';
  if (isWinner && savingsDiff > 0) {
    badgeHtml = `<span class="savings-badge">Save ₹${savingsDiff.toFixed(0)}</span>`;
  } else if (isTie) {
    badgeHtml = `<span class="savings-badge" style="background:#38bdf8; color:#0c4a6e;">Equal Price</span>`;
  }

  const stockClass = listing.in_stock ? 'in-stock' : 'out-of-stock';
  const stockLabel = listing.in_stock ? 'In Stock' : 'Out of Stock';

  col.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
      <div class="platform-tag ${platformClass}">${platformName}</div>
      ${badgeHtml}
    </div>
    <div class="item-title">${escapeHtml(listing.name)}</div>
    <div class="item-quantity">${escapeHtml(listing.quantity || 'Pack')}</div>
    <div class="price-row">
      <div class="item-price">₹${listing.price.toFixed(0)}</div>
      <span class="stock-tag ${stockClass}">${stockLabel}</span>
    </div>
  `;

  return col;
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
