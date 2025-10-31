// Ensure currentCategory is defined before any function uses it
let currentCategory = "all";

// Flipper Simulator: Load AI-scored items from Flipper_AI/scored_items.json
let currentPage = 1;
const ITEMS_PER_PAGE = 30;
// Main IIFE for Simulator logic
(function() {
  function renderPaginationControls(totalItems) {
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
    if (totalPages <= 1) return '';
    let controls = '<div class="pagination-controls">';
    controls += `<button ${currentPage === 1 ? 'disabled' : ''} onclick="window.simulator.goToPage(${currentPage - 1})">Prev</button>`;
    for (let i = 1; i <= totalPages; i++) {
      controls += `<button ${(i === currentPage) ? 'class=\'active\'' : ''} onclick="window.simulator.goToPage(${i})">${i}</button>`;
    }
    controls += `<button ${currentPage === totalPages ? 'disabled' : ''} onclick="window.simulator.goToPage(${currentPage + 1})">Next</button>`;
    controls += '</div>';
    return controls;
  }

  window.simulator = window.simulator || {};
  window.simulator.goToPage = function(page) {
    currentPage = page;
    renderSimulator(currentCategory, document.getElementById('message'), document.getElementById('simulatorItems'), parseFloat(document.getElementById("user-budget")?.value) || 1828.4);
  };
  // Mapping for scored_items.json (ebay-style)
  function mapScoredItem(item) {
    // Extract the most accurate product name, removing category path words
    let itemName = item.title || item.Title || item.name || item.productName || "Unknown Item";
    let categoryPath = item.categoryPath || item.primaryCategory?.categoryName || item.categoryName || "misc";  // <-- Change to lowercase
    let pathSegments = categoryPath.split(' > ').map(s => s.trim().toLowerCase());
    let nameParts = itemName.split(/[-:|>]/).map(s => s.trim());
    let cleanName = nameParts.find(part => !pathSegments.some(seg => part.toLowerCase().includes(seg))) || nameParts[nameParts.length-1] || itemName;
    if (!cleanName || cleanName.length < 2) cleanName = itemName;
    return {
      itemName: cleanName,
      categoryPath: categoryPath,
      price: item.price,
      confidence: typeof item.confidenceScore === 'number' ? item.confidenceScore : 75,
      marketplace: item.marketplace,
      id: item.itemId || `ebay-${(itemName||'').replace(/\s+/g, '-')}-${Date.now()}`,
      startingBid: item.startingBid,
      suggestedMaxBid: item.suggestedMaxBid,
      image: item.image || (item.images && item.images.length > 0 ? item.images[0] : null), // <-- Always set image
      images: item.images || (item.image ? [item.image] : []) // <-- Always set images array
    };
  }

  // Mapping for items_amazon.json
  function mapAmazonItem(item) {
    const price = item.ListPrice?.Amount
      ? item.ListPrice.Amount / 100
      : (item.Offers?.[0]?.Price || 0);
    // Extract the most accurate product name, removing category path words
    let itemName = item.Title || item.title || item.name || item.productName || "Unknown Item";
    let categoryPath = item.categoryPath || item.primaryCategory?.categoryName || item.categoryName || "misc";  // <-- Change to lowercase
    let pathSegments = categoryPath.split(' > ').map(s => s.trim().toLowerCase());
    let nameParts = itemName.split(/[-:|>]/).map(s => s.trim());
    let cleanName = nameParts.find(part => !pathSegments.some(seg => part.toLowerCase().includes(seg))) || nameParts[nameParts.length-1] || itemName;
    if (!cleanName || cleanName.length < 2) cleanName = itemName;
    return {
      itemName: cleanName,
      categoryPath: categoryPath,
      price: price,
      confidence: typeof item.confidenceScore === 'number' ? item.confidenceScore : 75,
      marketplace: "amazon",
      id: item.ASIN || `amazon-${(itemName||'').replace(/\s+/g, '-')}-${Date.now()}`,
      startingBid: parseFloat((price * 0.8).toFixed(2)),
      suggestedMaxBid: parseFloat(price),
      image: item.image || (item.images && item.images.length > 0 ? item.images[0] : null),
      images: item.images || (item.image ? [item.image] : [])
    };
  }

  // Load scored items from Python AI output (ebay and amazon)
  async function loadScoredItems() {
    try {
      // Load scored items (includes eBay-style and Amazon-style)
      const scoredResp = await fetch('Flipper_AI/scored_items.json', { cache: 'no-store' });
      let scoredItems = [];
      if (scoredResp.ok) {
        const scoredJson = await scoredResp.json();
        scoredItems = Array.isArray(scoredJson) ? scoredJson.map(mapScoredItem) : [];
      } else {
        console.error('Failed to load scored_items.json:', scoredResp.status);
      }

      // Load Amazon items
      const amazonResp = await fetch('Flipper_AI/items_amazon.json', { cache: 'no-store' });
      let amazonItems = [];
      if (amazonResp.ok) {
        const amazonJson = await amazonResp.json();
        amazonItems = Array.isArray(amazonJson) ? amazonJson.map(mapAmazonItem) : [];
      } else {
        console.error('Failed to load items_amazon.json:', amazonResp.status);
      }

      // Load eBay items (if split)
      const ebayResp = await fetch('Flipper_AI/items_ebay.json', { cache: 'no-store' });
      let ebayItems = [];
      if (ebayResp.ok) {
        const ebayJson = await ebayResp.json();
        ebayItems = Array.isArray(ebayJson) ? ebayJson.map(mapScoredItem) : [];
      } else {
        console.error('Failed to load items_ebay.json:', ebayResp.status);
      }

      // Combine and return
      return [...scoredItems, ...amazonItems, ...ebayItems];
    } catch (e) {
      handleStorageError('loading scored items', e);
      return [];
    }
  }
  let priceData = {};
  let scannedItems = [];
  // Always include both eBay and Amazon by default
  let currentMarketplaces = ["ebay", "amazon"];
  let currentSortBy = "confidence-desc";
  let isSaving = false;

  const sellTimes = {
    ebay: { electronics: "3-7 days", collectibles: "1-3 weeks", clothing: "1-2 weeks", toys: "3-7 days", default: "1-2 weeks" },
    amazon: { electronics: "1-2 weeks", collectibles: "2-4 weeks", clothing: "1-3 weeks", toys: "1-2 weeks", default: "1-3 weeks" },
    mock: { electronics: "1-2 weeks", collectibles: "2-4 weeks", clothing: "1-3 weeks", toys: "1-2 weeks", default: "Unknown" }
  };

  function mapCategory(category, marketplace) {
    const categoryMap = {
      ebay: {
        "Cell Phones & Accessories": "electronics",
        "Electronics": "electronics",
        "Collectibles": "collectibles",
        "Clothing, Shoes & Accessories": "clothing",
        "Toys & Hobbies": "toys"
      },
      amazon: {
        "Electronics": "electronics",
        "Toys & Games": "toys",
        "Clothing": "clothing",
        "Collectibles": "collectibles"
      },
      mock: {
        electronics: "electronics",
        collectibles: "collectibles",
        clothing: "clothing",
        toys: "toys"
      }
    };
    return categoryMap[marketplace][category] || "electronics";
  }

  // Load all items from scored_items.json and map to priceData
  async function loadPriceData(query = 'electronics') {
    priceData = {};
    try {
      const items = await loadScoredItems(query);
      priceData['electronics'] = items;  // Group under electronics
      console.log('Loaded eBay items:', priceData);
    } catch (e) {
      console.error('Error loading eBay data:', e);
      priceData = {};
    }
  }

  // Move renderCategoryFilter here, inside the IIFE
  function renderCategoryFilter() {
    const container = document.getElementById('category-filter');
    if (!container) return;
    // Define main categories for top-level filtering
    const mainCategories = ['electronics', 'collectibles', 'clothing', 'toys'];
    let html = `<label for="sortBy" style="margin-right: 10px;">Sort by:</label>
                <select id="sortBy" style="margin-right: 20px;">
                  <option value="confidence-desc">Confidence (High to Low)</option>
                  <option value="confidence-asc">Confidence (Low to High)</option>
                  <option value="profit-desc">Profit (High to Low)</option>
                  <option value="profit-asc">Profit (Low to High)</option>
                  <option value="price-desc">Price (High to Low)</option>
                  <option value="price-asc">Price (Low to High)</option>
                  <option value="itemName-asc">Name (A-Z)</option>
                  <option value="itemName-desc">Name (Z-A)</option>
                </select>`;
    html += `<button type="button" class="${currentCategory === 'all' ? 'selected' : ''}" data-category="all">All</button>`;
    mainCategories.forEach(cat => {
      const displayName = cat.charAt(0).toUpperCase() + cat.slice(1);
      html += `<button type="button" class="main-category ${currentCategory === cat ? 'selected' : ''}" data-category="${cat}">${displayName}</button>`;
    });
    container.innerHTML = html;
    // Add event listeners
    Array.from(container.querySelectorAll('button[data-category]')).forEach(btn => {
      btn.addEventListener('click', () => {
        currentCategory = btn.getAttribute('data-category');
        Array.from(container.querySelectorAll('button[data-category]')).forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');
        scanForProfits();
      });
    });
    // Add listener for sort dropdown
    const sortBySelect = document.getElementById("sortBy");
    if (sortBySelect) sortBySelect.addEventListener("change", scanForProfits);
  }

  function handleStorageError(action, error) {
    console.error(`Error ${action}:`, error);
    const message = document.getElementById('message');
    if (message) {
      message.innerText = `Error ${action}: ${error.message}`;
      message.style.color = "#dc3545";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
    }
  }

  function getWatchlist() {
    try {
      const watchlist = JSON.parse(localStorage.getItem("watchlist") || "[]");
      if (!Array.isArray(watchlist)) {
        console.warn("Corrupted watchlist, resetting...");
        localStorage.setItem("watchlist", JSON.stringify([]));
        return [];
      }
      console.log("Retrieved watchlist:", watchlist);
      return watchlist.filter(item => 
        item.itemName && 
        item.category && 
        typeof item.price === 'number' && 
        typeof item.confidence === 'number' && 
        item.marketplace && 
        item.id &&
        typeof item.startingBid === 'number' &&
        typeof item.suggestedMaxBid === 'number'
      );
    } catch (e) {
      handleStorageError('accessing watchlist', e);
      return [];
    }
  }

  function saveWatchlist(watchlist) {
    try {
      if (!Array.isArray(watchlist)) throw new Error('Watchlist must be an array');
      localStorage.setItem("watchlist", JSON.stringify(watchlist));
      console.log('Saved watchlist:', watchlist);
    } catch (e) {
      handleStorageError('saving watchlist', e);
    }
  }

  function isItemInWatchlist(watchlist, itemName, marketplace, category) {
    return watchlist.some(item => 
      item.itemName.toLowerCase() === itemName.toLowerCase() && 
      item.marketplace.toLowerCase() === marketplace.toLowerCase() && 
      item.category.toLowerCase() === category.toLowerCase()
    );
  }

  function clearWatchlist() {
    try {
      saveWatchlist([]);
      const message = document.getElementById('message');
      if (message) {
        message.innerText = "Watchlist cleared successfully!";
        message.style.color = "#28a745";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      renderSimulator();
    } catch (e) {
      handleStorageError('clearing watchlist', e);
    }
  }

  function saveItemToWatchlist(button) {
    if (isSaving) {
      console.log("Save in progress, skipping...");
      return false;
    }
    isSaving = true;
    const message = document.getElementById("message");
    const gallery = document.getElementById("simulatorItems");
    const budget = parseFloat(document.getElementById("user-budget")?.value) || 1828.4;

    if (!message || !gallery) {
      console.error("Required DOM elements missing for saveItemToWatchlist");
      isSaving = false;
      return false;
    }

    let itemData;
    try {
      itemData = JSON.parse(button.dataset.item.replace(/&quot;/g, '"'));
      console.log("Parsed item data for save:", itemData);
    } catch (e) {
      console.error("Error parsing item data:", e);
      message.innerText = "Error: Invalid item data.";
      message.style.color = "#dc3545";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
      isSaving = false;
      return false;
    }

    const { itemName, category, price, confidence, marketplace, id, startingBid, suggestedMaxBid } = itemData;
    const finalPrice = parseFloat((price || 0).toFixed(2));
    const sellPrice = parseFloat((finalPrice * 1.2).toFixed(2));
    const profit = sellPrice - finalPrice;
    const finalId = id || `item-${category}-${itemName.replace(/\s+/g, '-')}-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    const finalStartingBid = parseFloat((startingBid || price * 0.5 * 0.8 || 28).toFixed(2));
    const finalSuggestedMaxBid = parseFloat((suggestedMaxBid || price * 0.5 || 35).toFixed(2));

    if (!itemName || !category || isNaN(finalPrice) || isNaN(profit) || isNaN(confidence) || !marketplace || isNaN(finalStartingBid) || isNaN(finalSuggestedMaxBid)) {
      message.innerText = "Error: Invalid item data for watchlist.";
      message.style.color = "#dc3545";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
      console.error("Invalid item data:", { itemName, category, finalPrice, profit, confidence, marketplace, finalStartingBid, finalSuggestedMaxBid });
      isSaving = false;
      return false;
    }

    try {
      const watchlist = getWatchlist();
      if (isItemInWatchlist(watchlist, itemName, marketplace, category)) {
        message.innerText = `${itemName} from ${marketplace} (${category}) is already in watchlist!`;
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
        console.log(`Duplicate item blocked: ${itemName} from ${marketplace} (${category})`);
        isSaving = false;
        return false;
      }
      watchlist.push({
        itemName,
        category,
        price: finalPrice,
        profit,
        confidence: parseFloat(confidence.toFixed(0)),
        marketplace,
        id: finalId,
        sellPrice,
        sellTime: sellTimes[marketplace][category] || sellTimes[marketplace].default,
        startingBid: finalStartingBid,
        suggestedMaxBid: finalSuggestedMaxBid
      });
      saveWatchlist(watchlist);
      message.innerText = `${itemName} saved to watchlist!`;
      message.style.color = "#28a745";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
      console.log(`Saved to watchlist: ${itemName}, id: ${finalId}`);
      console.log("Current watchlist:", watchlist);
      document.getElementById("profit-form")?.reset();
      document.querySelector('input[name="category"][value="all"]').checked = true;
      clearCurrentItem();
      updateButtonVisibility(scannedItems.length > 0);
      renderSimulator(currentCategory, message, gallery, budget);
      isSaving = false;
      return true;
    } catch (e) {
      handleStorageError('saving to watchlist', e);
      isSaving = false;
      return false;
    }
  }

  function saveCheckedFlips() {
    if (isSaving) {
      console.log("Save in progress, skipping...");
      return;
    }
    isSaving = true;
    const message = document.getElementById("message");
    const gallery = document.getElementById("simulatorItems");
    const budget = parseFloat(document.getElementById("user-budget")?.value) || 1828.4;

    if (!message || !gallery) {
      console.error("Required DOM elements missing for saveCheckedFlips");
      isSaving = false;
      return;
    }

    const checkedItems = Array.from(document.querySelectorAll(".item-checkbox:checked")).map(cb => {
      try {
        return JSON.parse(cb.dataset.item.replace(/&quot;/g, '"'));
      } catch (e) {
        console.warn("Invalid checkbox data:", cb.dataset.item, e);
        return null;
      }
    }).filter(item => item !== null);

    console.log("Checked items for save:", checkedItems);

    if (!checkedItems.length) {
      message.innerText = "No items selected to save.";
      message.style.color = "#dc3545";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
      console.log("No items selected for saveCheckedFlips");
      isSaving = false;
      renderSimulator(currentCategory, message, gallery, budget);
      return;
    }

    try {
      const watchlist = getWatchlist();
      let savedCount = 0;
      const duplicates = [];
      checkedItems.forEach((item, index) => {
        const itemName = item.itemName || "Unknown Item";
        const category = item.category || "electronics";
        const price = parseFloat(item.price || 0);
        const confidence = parseFloat(item.confidence || 0);
        const marketplace = item.marketplace || "mock";
        const sellPrice = parseFloat((price * 1.2).toFixed(2));
        const profit = parseFloat((sellPrice - price).toFixed(2));
        const id = item.id || `item-${category}-${itemName.replace(/\s+/g, '-')}-${Date.now()}-${index}-${Math.floor(Math.random() * 1000)}`;
        const startingBid = parseFloat((item.startingBid || price * 0.5 * 0.8 || 28).toFixed(2));
        const suggestedMaxBid = parseFloat((item.suggestedMaxBid || price * 0.5 || 35).toFixed(2));

        if (isItemInWatchlist(watchlist, itemName, marketplace, category)) {
          duplicates.push(`${itemName} (${marketplace}, ${category})`);
          console.log(`Duplicate item blocked: ${itemName} from ${marketplace} (${category})`);
          return;
        }

        if (!itemName || !category || isNaN(price) || isNaN(profit) || isNaN(confidence) || isNaN(startingBid) || isNaN(suggestedMaxBid)) {
          console.warn(`Invalid item data skipped: ${itemName}`, { itemName, category, price, profit, confidence, startingBid, suggestedMaxBid });
          return;
        }

        watchlist.push({
          itemName,
          category,
          price,
          profit,
          confidence,
          marketplace,
          id,
          sellPrice,
          sellTime: sellTimes[marketplace][category] || sellTimes[marketplace].default,
          startingBid,
          suggestedMaxBid
        });
        savedCount++;
        console.log(`Saved to watchlist: ${itemName}, id: ${id}`);
      });

      if (duplicates.length > 0) {
        message.innerText = `Skipped ${duplicates.length} duplicate item(s): ${duplicates.join(', ')}. Saved ${savedCount} new item(s).`;
        message.style.color = duplicates.length === checkedItems.length ? "#dc3545" : "#28a745";
      } else if (savedCount === 0) {
        message.innerText = "No new items saved to watchlist.";
        message.style.color = "#dc3545";
        console.log("No new items saved to watchlist");
        isSaving = false;
        renderSimulator(currentCategory, message, gallery, budget);
        return;
      } else {
        message.innerText = `Saved ${savedCount} new item(s) to watchlist!`;
        message.style.color = "#28a745";
      }

      saveWatchlist(watchlist);
      console.log("Current watchlist:", watchlist);
      checkedItems.forEach(item => {
        const checkbox = document.querySelector(`.item-checkbox[data-id="${item.id}"]`);
        if (checkbox) checkbox.checked = false;
      });
      updateButtonVisibility(scannedItems.length > 0);
      renderSimulator(currentCategory, message, gallery, budget);
      isSaving = false;
    } catch (e) {
      handleStorageError('saving items to watchlist', e);
      isSaving = false;
    }
  }

  function getConfidenceClass(confidence) {
  if (confidence >= 95) return "confidence-purple";
  if (confidence >= 85) return "confidence-blue";
  if (confidence > 80) return "confidence-high";
  if (confidence >= 50) return "confidence-medium";
  return "confidence-low";
  }

  function getProfitClass(profit) {
    return profit > 0 ? "profit-high" : "profit-low";
  }

  // Add or update this function to return actual image URLs, checking arrays and handling relative paths
  function getThumbnail(item) {
  const thumb = item.image || (item.images && item.images.length > 0 ? item.images[0] : null);
  console.log("Original thumb:", thumb);  // Debug: Check what's in the data
  const finalThumb = thumb
    ? (thumb.startsWith('http') 
        ? thumb 
        : 'flatten_images/' + thumb.split('/').pop())  // Handles full or partial paths
    : 'https://picsum.photos/100/100?text=No+Image';  // Reliable placeholder
  console.log("Final URL:", finalThumb);  // Debug: Check the constructed URL
  return finalThumb;
}

  function getThumbnailDisplay() {
    try {
      const value = localStorage.getItem("thumbnailDisplay");
      return value === null ? false : value !== "false";
    } catch (e) {
      console.error("Error accessing thumbnailDisplay:", e);
      return false;
    }
  }

  function setThumbnailDisplay(showThumbnails) {
    try {
      localStorage.setItem("thumbnailDisplay", showThumbnails);
      console.log("Thumbnail display set to:", showThumbnails);
      const message = document.getElementById("message");
      const gallery = document.getElementById("simulatorItems");
      const budget = parseFloat(document.getElementById("user-budget")?.value) || 1828.4;
      renderSimulator(currentCategory, message, gallery, budget);
    } catch (e) {
      console.error("Error setting thumbnailDisplay:", e);
    }
  }

  function getConfidenceLimit() {
    try {
      return parseFloat(localStorage.getItem("confidenceLimit")) || 0;
    } catch (e) {
      handleStorageError('accessing confidence limit', e);
      return 0;
    }
  }

  function getProfitLimit() {
    try {
      return parseFloat(localStorage.getItem("profitLimit")) || 0;
    } catch (e) {
      handleStorageError('accessing profit limit', e);
      return 0;
    }
  }

  function setConfidenceLimit() {
    const limit = parseFloat(document.getElementById("confidenceLimit")?.value) || 0;
    const message = document.getElementById("message");
    if (isNaN(limit) || limit < 0 || limit > 100) {
      if (message) {
        message.innerText = "Confidence must be 0-100.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      return;
    }
    try {
      localStorage.setItem("confidenceLimit", limit);
      document.getElementById("confidenceLimit").value = limit;
      if (message) message.innerText = "";
      scanForProfits();
    } catch (e) {
      handleStorageError('setting confidence limit', e);
    }
  }

  function setProfitLimit() {
    const limit = parseFloat(document.getElementById("profitLimit")?.value) || 0;
    const message = document.getElementById("message");
    if (isNaN(limit) || limit < 0) {
      if (message) {
        message.innerText = "Profit must be non-negative.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      return;
    }
    try {
      localStorage.setItem("profitLimit", limit);
      document.getElementById("profitLimit").value = limit;
      if (message) message.innerText = "";
      scanForProfits();
    } catch (e) {
      handleStorageError('setting profit limit', e);
    }
  }

  function updateButtonVisibility(hasItems) {
    const saveFlipsBtn = document.getElementById("save-flips");
    if (saveFlipsBtn) saveFlipsBtn.style.display = hasItems ? "inline-block" : "none";
  }

  function clearCurrentItem() {
    window.currentPrice = null;
    window.currentConfidence = null;
    window.currentItemName = null;
    window.currentCategory = null;
    window.currentMarketplace = null;
  }

  function showTab(tabId) {
    try {
      const container = document.getElementById(tabId);
      const tabButton = document.getElementById(`${tabId}-tab`);
      if (container && tabButton) {
        document.querySelectorAll('.tab-content').forEach(tab => {
          tab.classList.remove('active');
          tab.style.display = 'none';
        });
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        container.classList.add('active');
        container.style.display = 'block';
        tabButton.classList.add('active');
        console.log(`Switched to tab: ${tabId}`);
        scanForProfits();  // <-- Change to scanForProfits to populate and render items
      } else {
        console.warn(`Tab ${tabId} missing container or button`);
      }
    } catch (e) {
      handleStorageError('switching tab', e);
    }
  }

  function updateToolbar() {
    try {
      const checkedItems = Array.from(document.querySelectorAll('.item-checkbox:checked')).map(cb => {
        try {
          return JSON.parse(cb.dataset.item.replace(/&quot;/g, '"'));
        } catch (e) {
          console.warn("Invalid checkbox data:", cb.dataset.item, e);
          return null;
        }
      }).filter(item => item !== null);

      const totalBuyPrice = checkedItems.reduce((sum, item) => sum + (parseFloat(item.price) || 0), 0);
      const totalProfit = checkedItems.reduce((sum, item) => sum + (parseFloat(item.profit) || 0), 0);
      const elements = {
        totalBuyPrice: document.getElementById('totalBuyPrice'),
        totalProfit: document.getElementById('totalProfit'),
        currentBudget: document.getElementById('currentBudget')
      };
      if (elements.totalBuyPrice) elements.totalBuyPrice.innerText = totalBuyPrice.toFixed(2);
      if (elements.totalProfit) elements.totalProfit.innerText = totalProfit.toFixed(2);
      if (elements.currentBudget) {
        const budget = parseFloat(localStorage.getItem('userBudget') || 1828.4);
        elements.currentBudget.innerText = `Current: $${budget.toFixed(2)}`;
      }
      console.log("Toolbar updated:", { totalBuyPrice, totalProfit, budget: elements.currentBudget?.innerText });
    } catch (e) {
      handleStorageError('updating toolbar', e);
    }
  }

  // Ensure scanForProfits uses currentCategory (prioritized over radio buttons) to fix category click issues
  window.scanForProfits = function() {
    const message = document.getElementById("message");
    const gallery = document.getElementById("simulatorItems");
    const budget = parseFloat(document.getElementById("user-budget")?.value) || 1828.4;
    // Prioritize currentCategory (set by category clicks) over radio button value
    const category = currentCategory || document.querySelector('input[name="category"]:checked')?.value || "all";
    const marketplaces = Array.from(document.querySelectorAll('input[name="marketplace"]:checked')).map(cb => cb.value);
    const sortBy = document.getElementById("sortBy")?.value || "confidence-desc";
    const button = document.querySelector('button[type="submit"]');

    window.currentCategory = category;
    currentMarketplaces = marketplaces.length ? marketplaces : ["ebay", "amazon", "mock"];
    currentSortBy = sortBy;

    if (budget <= 0) {
      if (message) {
        message.innerText = "Please enter a valid budget greater than 0.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      if (gallery) gallery.innerHTML = "<p class='no-items'>No items.</p>";
      scannedItems = [];
      if (button) button.classList.remove("loading");
      updateButtonVisibility(false);
      return;
    }

    if (!marketplaces.length) {
      if (message) {
        message.innerText = "Please select at least one marketplace.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      if (gallery) gallery.innerHTML = "<p class='no-items'>No items.</p>";
      scannedItems = [];
      if (button) button.classList.remove("loading");
      updateButtonVisibility(false);
      return;
    }

    if (message) message.innerText = "";
    if (gallery) gallery.innerHTML = "<p class='no-items'>Loading items...</p>";
    if (button) button.classList.add("loading");

    if (!Object.keys(priceData).length) {
      if (message) message.innerText = "Loading marketplace data...";
      loadPriceData().then(() => {
        renderSimulator(currentCategory, message, gallery, budget);
        if (button) button.classList.remove("loading");
      }).catch(() => {
        if (message) {
          message.innerText = "Failed to load marketplace data.";
          message.style.color = "#dc3545";
          message.style.display = "block";
          setTimeout(() => {
            message.style.display = "none";
            message.innerText = "";
          }, 3000);
        }
        if (gallery) gallery.innerHTML = "<p class='no-items'>No items.</p>";
        scannedItems = [];
        if (button) button.classList.remove("loading");
        updateButtonVisibility(false);
      });
    } else {
      renderSimulator(currentCategory, message, gallery, budget);
      if (button) button.classList.remove("loading");
    }
  }

  function renderSimulator(category, message, gallery, budget) {
    try {
      const confLimit = getConfidenceLimit();
      const profitLimit = getProfitLimit();
      const itemName = document.getElementById("itemName")?.value?.toLowerCase().trim() || "";
      const showThumbnails = getThumbnailDisplay();
      let output = "";
      // Updated: Filter categories to support partial matches (e.g., "electronics" matches "electronics > cell phones")
      const categories = category === "all" 
        ? Object.keys(priceData).filter(cat => Array.isArray(priceData[cat]) && priceData[cat].length)
        : Object.keys(priceData).filter(cat => cat.toLowerCase().startsWith(category.toLowerCase()) && Array.isArray(priceData[cat]) && priceData[cat].length);
      let hasValidItems = false;
      scannedItems = [];
      const seenItems = new Set();

      console.log(`Rendering categories: ${categories}, marketplaces: ${currentMarketplaces}`);

      if (!priceData || !categories.length) {
        if (message) {
          message.innerText = "No valid categories in marketplace data.";
          message.style.color = "#dc3545";
          message.style.display = "block";
          setTimeout(() => {
            message.style.display = "none";
            message.innerText = "";
          }, 3000);
        }
        if (gallery) gallery.innerHTML = "<p class='no-items'>No items.</p>";
        updateButtonVisibility(false);
        return;
      }

      const checkedIds = Array.from(document.querySelectorAll('.item-checkbox:checked')).map(cb => cb.dataset.id);
      console.log("Preserved checkbox states:", checkedIds);

      categories.forEach(cat => {
        const items = priceData[cat] || [];
        console.log(`Processing category ${cat} with ${items.length} items`);
        items.forEach((data, index) => {
          if (!data.itemName || typeof data.price !== 'number' || typeof data.confidence !== 'number') {
            console.warn(`Invalid item data in ${cat}:`, data);
            return;
          }
          if (!currentMarketplaces.includes(data.marketplace)) {
            console.log(`Skipping item ${data.itemName} due to marketplace ${data.marketplace} not in ${currentMarketplaces}`);
            return;
          }
          if (itemName && !data.itemName.toLowerCase().includes(itemName)) return;
          const conf = Math.min(90, Math.max(50, data.confidence));
          const sellPrice = parseFloat((data.price * 1.2).toFixed(2));
          const profit = sellPrice - data.price;
          if (data.price > budget) {
            console.log(`Skipping item ${data.itemName} due to budget ${data.price} > ${budget}`);
            return;
          }
          if (conf >= confLimit && profit >= profitLimit) {
            const itemKey = `${data.itemName.toLowerCase()}-${data.marketplace}-${data.categoryPath || cat}-${data.id || index}`;
            if (seenItems.has(itemKey)) {
              console.log(`Skipping duplicate item in scan: ${data.itemName} from ${data.marketplace} (${cat})`);
              return;
            }
            seenItems.add(itemKey);
            const itemId = `item-${cat}-${data.itemName.replace(/\s+/g, '-')}-${Date.now()}-${index}-${Math.floor(Math.random() * 1000)}`;
            scannedItems.push({ 
              itemName: data.itemName, 
              category: cat, 
              categoryPath: data.categoryPath || cat, // Ensure it's set
              price: data.price, 
              confidence: parseFloat(conf), 
              profit, 
              marketplace: data.marketplace,
              id: itemId,
              sellPrice,
              startingBid: data.startingBid,
              suggestedMaxBid: data.suggestedMaxBid
            });
            console.log(`Added item to scannedItems: ${data.itemName}, id: ${itemId}`);
          }
        });
      });

      scannedItems.sort((a, b) => {
        const [field, direction] = currentSortBy.split('-');
        const isDesc = direction === 'desc';
        if (field === 'itemName') {
          return isDesc ? b[field].localeCompare(a[field]) : a[field].localeCompare(b[field]);
        }
        return isDesc ? b[field] - a[field] : a[field] - b[field];
      });

      gallery.innerHTML = scannedItems.length ? '' : `<p class="no-items">No items meet the limits (conf ≥ ${confLimit}%, profit ≥ $${profitLimit}, budget ≥ $${budget.toFixed(2)}).</p>`;
      gallery.className = showThumbnails ? 'tab-content item-grid' : 'tab-content item-list';

      // Pagination: only render items for the current page
      const startIdx = (currentPage - 1) * ITEMS_PER_PAGE;
      const endIdx = startIdx + ITEMS_PER_PAGE;
      const pagedItems = scannedItems.slice(startIdx, endIdx);
      pagedItems.forEach(item => {
        const itemId = item.id;
        const profitPercent = item.price > 0 ? (item.profit / item.price * 100).toFixed(2) : 0;
        const className = `item-card ${item.marketplace}-item`;
        // Show full category path above, then actual product name below (fuzzy extraction)
        let categoryPath = (item.categoryPath || item.category || '').split(' > ').join(' > ');
        let actualName = '';
        // Fuzzy extract: remove category path words from itemName/title
        if (item.itemName) {
          const catWords = categoryPath.toLowerCase().split(/\s*>\s*|\s+/).filter(Boolean);
          const nameWords = item.itemName.split(/\s+/);
          const filtered = nameWords.filter(w => !catWords.includes(w.toLowerCase()));
          actualName = filtered.length ? filtered.join(' ') : item.itemName;
        } else if (item.title) {
          const catWords = categoryPath.toLowerCase().split(/\s*>\s*|\s+/).filter(Boolean);
          const titleWords = item.title.split(/\s+/);
          const filtered = titleWords.filter(w => !catWords.includes(w.toLowerCase()));
          actualName = filtered.length ? filtered.join(' ') : item.title;
        } else {
          actualName = item.itemName || item.title || '';
        }
        let subCategory = '';
        if (categoryPath) {
          let segs = categoryPath.split(' > ');
          subCategory = segs.length > 1 ? segs.slice(1).join(' > ') : '';
        }

        // Create clickable category path
        let categoryHtml = '';
        if (item.categoryPath) {
          const parts = item.categoryPath.split(' > ');
          let currentPath = '';
          categoryHtml = parts.map((part, index) => {
            currentPath += (index > 0 ? ' > ' : '') + part;
            return `<span class="category-part" data-path="${currentPath}" style="cursor:pointer; color:#007bff; text-decoration:underline;">${part}</span>`;
          }).join(' > ');
        }

        // Always include a thumbnail image (placeholder if none available), but style it smaller in list view
        const thumbnailHtml = `<img class="thumbnail ${showThumbnails ? '' : 'thumbnail-small'}" src="${getThumbnail(item)}" alt="${item.category}" 
 onerror="this.onerror=null;this.src='https://via.placeholder.com/100x100?text=No+Image';">`;  // Changed to visible placeholder on error

        const html = showThumbnails ? `
          <div class="${className}" id="item-${itemId}">
            <input type="checkbox" class="item-checkbox" id="checkbox-${itemId}" data-id="${itemId}" data-item='${JSON.stringify(item).replace(/'/g, "&#39;").replace(/"/g, "&quot;")}' onchange="window.simulator.updateToolbar()">
            ${thumbnailHtml}
            <div class="item-sublabel">${item.marketplace.charAt(0).toUpperCase() + item.marketplace.slice(1)}</div>
            <div class="item-category-path">${categoryHtml}</div>
            <div class="item-main-label" style="margin-top: 6px; font-weight: 500;">${actualName}</div>
            <div class="item-details">
              <p>Price: $${(item.price || 0).toFixed(2)}</p>
              <p>Sell Price: $${(item.sellPrice || 0).toFixed(2)}</p>
              <p>Profit: $${(item.profit || 0).toFixed(2)} <span class="${getProfitClass(item.profit)}">(${profitPercent}%)</span></p>
              <p>Confidence: <span class="${getConfidenceClass(item.confidence)}">${item.confidence}%</span></p>
              <button class="save-button" data-item='${JSON.stringify(item).replace(/'/g, "&#39;").replace(/"/g, "&quot;")}' onclick="event.stopPropagation(); window.simulator.saveItemToWatchlist(this)">Save</button>
              <p>Sell in: ${sellTimes[item.marketplace][item.category] || sellTimes[item.marketplace].default}</p>
              <p>Starting Bid: $${(item.startingBid || 0).toFixed(2)}</p>
              <p>Max Bid: $${(item.suggestedMaxBid || 0).toFixed(2)}</p>
            </div>
          </div>` : `
          <div class="${className} item-list-item" id="item-${itemId}">
            <div class="item-row">
              <input type="checkbox" class="item-checkbox" id="checkbox-${itemId}" data-id="${itemId}" data-item='${JSON.stringify(item).replace(/'/g, "&#39;").replace(/"/g, "&quot;")}' onchange="window.simulator.updateToolbar()">
              ${thumbnailHtml}
              <span class="item-sublabel">${item.marketplace.charAt(0).toUpperCase() + item.marketplace.slice(1)}</span>
            </div>
            <div class="item-category-path">${categoryHtml}</div>
            <div class="item-main-label" style="margin: 6px 0 0 8px; font-weight: 500;">${actualName}</div>
            <div class="item-details">
              <p>Price: $${(item.price || 0).toFixed(2)}</p>
              <p>Sell Price: $${(item.sellPrice || 0).toFixed(2)}</p>
              <p>Confidence: <span class="${getConfidenceClass(item.confidence)}">${item.confidence}%</span></p>
              <button class="save-button" data-item='${JSON.stringify(item).replace(/'/g, "&#39;").replace(/"/g, "&quot;")}' onclick="event.stopPropagation(); window.simulator.saveItemToWatchlist(this)">Save</button>
              <p>Sell in: ${sellTimes[item.marketplace][item.category] || sellTimes[item.marketplace].default}</p>
              <p>Starting Bid: $${(item.startingBid || 0).toFixed(2)}</p>
              <p>Max Bid: $${(item.suggestedMaxBid || 0).toFixed(2)}</p>
            </div>
          </div>`;
        gallery.insertAdjacentHTML('beforeend', html);

        // Add event listeners to category parts
        const card = gallery.lastElementChild;
        const categoryParts = card.querySelectorAll('.category-part');
        categoryParts.forEach(span => {
          span.addEventListener('click', (e) => {
            e.stopPropagation();
            currentCategory = span.getAttribute('data-path');
            scanForProfits();
          });
        });

        hasValidItems = true;
      });

      // Render pagination controls
      if (gallery && scannedItems.length > ITEMS_PER_PAGE) {
        gallery.insertAdjacentHTML('beforeend', renderPaginationControls(scannedItems.length));
      }

      checkedIds.forEach(id => {
        const checkbox = document.querySelector(`.item-checkbox[data-id="${id}"]`);
        if (checkbox) checkbox.checked = true;
      });

      if (message) {
        message.innerText = hasValidItems
          ? "Scanned items loaded. Select an item to save to watchlist."
          : itemName
            ? `No items matching "${itemName}" found within budget.`
            : `No items meet the limits (conf ≥ ${confLimit}%, profit ≥ $${profitLimit}, budget ≥ $${budget.toFixed(2)}).`;
        message.style.color = hasValidItems ? "#28a745" : "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      updateButtonVisibility(hasValidItems);
      updateToolbar();
      console.log(`Rendered ${scannedItems.length} items`);
    } catch (e) {
      handleStorageError('rendering simulator', e);
      if (message) {
        message.innerText = "Error rendering items.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      if (gallery) gallery.innerHTML = "<p class='no-items'>No items.</p>";
    }
  }

  function calculateProfit(e) {
    e.preventDefault();
    const budget = parseFloat(document.getElementById("user-budget")?.value) || 1828.4;
    const message = document.getElementById("message");
    const gallery = document.getElementById("simulatorItems");
    const selectedCheckbox = document.querySelector(".item-checkbox:checked");
    clearCurrentItem();

    if (budget <= 0) {
      if (message) {
        message.innerText = "Please enter a valid budget greater than 0.";
        message.style.color = "#dc3545";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      updateButtonVisibility(scannedItems.length > 0);
      renderSimulator(currentCategory, message, gallery, budget);
      return;
    }

    if (!selectedCheckbox) {
      if (message) {
        message.innerText = "No item selected. Showing scan results.";
        message.style.color = "#28a745";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
      updateButtonVisibility(scannedItems.length > 0);
      renderSimulator(currentCategory, message, gallery, budget);
      return;
    }

    let selectedItem;
    try {
      selectedItem = JSON.parse(selectedCheckbox.dataset.item.replace(/&quot;/g, '"'));
    } catch (e) {
      handleStorageError('parsing item data', e);
      updateButtonVisibility(scannedItems.length > 0);
      renderSimulator(currentCategory, message, gallery, budget);
      return;
    }

    window.currentPrice = selectedItem.price || 0;
    window.currentConfidence = selectedItem.confidence || 0;
    window.currentItemName = selectedItem.itemName || "Unknown Item";
    window.currentCategory = selectedItem.category || "electronics";
    window.currentMarketplace = selectedItem.marketplace || "mock";
    window.currentStartingBid = selectedItem.startingBid || window.currentPrice * 0.5 * 0.8 || 28;
    window.currentSuggestedMaxBid = selectedItem.suggestedMaxBid || window.currentPrice * 0.5 || 35;

    const sellPrice = parseFloat((window.currentPrice * 1.2).toFixed(2));
    const profit = parseFloat((sellPrice - window.currentPrice).toFixed(2));
    const percent = window.currentPrice > 0 ? ((profit / window.currentPrice) * 100).toFixed(2) : 0;
    const profitClass = percent > 0 ? "profit-high" : "profit-low";

    let suggestion = "";
    if (budget < window.currentPrice && window.currentPrice > 0) {
      suggestion = `<br>Budget too low! Suggested budget for ${selectedItem.itemName}: $${window.currentPrice.toFixed(2)} or higher.`;
    }

    if (message) {
      message.innerHTML = `${window.currentMarketplace.charAt(0).toUpperCase() + window.currentMarketplace.slice(1)} - ${selectedItem.itemName} usually at $${window.currentPrice.toFixed(2)} (buy at $${window.currentPrice.toFixed(2)}), sell at $${sellPrice}. Profit: $${profit.toFixed(2)} (<span class="${profitClass}">${percent}%</span>, <span class="${getConfidenceClass(window.currentConfidence)}">${window.currentConfidence}% conf</span>)<br><em>Save to watchlist to sell later.</em>${suggestion}`;
      message.style.color = profit >= 0 ? "#28a745" : "#dc3545";
      message.style.display = "block";
      setTimeout(() => {
        message.style.display = "none";
        message.innerText = "";
      }, 3000);
    }
    updateButtonVisibility(scannedItems.length > 0);
    renderSimulator(currentCategory, message, gallery, budget);
  }

  function exportWatchlist() {
    try {
      const watchlist = getWatchlist();
      const json = JSON.stringify(watchlist, null, 2);
      const blob = new Blob([json], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "flipper-watchlist.json";
      a.click();
      URL.revokeObjectURL(url);
      const message = document.getElementById("message");
      if (message) {
        message.innerText = "Watchlist exported successfully!";
        message.style.color = "#28a745";
        message.style.display = "block";
        setTimeout(() => {
          message.style.display = "none";
          message.innerText = "";
        }, 3000);
      }
    } catch (e) {
      handleStorageError('exporting watchlist', e);
    }
  }

  function importWatchlist(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(e) {
      try {
        const newItems = JSON.parse(e.target.result);
        if (!Array.isArray(newItems)) throw new Error("Invalid watchlist format");
        const watchlist = getWatchlist();
        let addedCount = 0;
        newItems.forEach(item => {
          if (!isItemInWatchlist(watchlist, item.itemName, item.marketplace, item.category)) {
            watchlist.push({
              ...item,
              price: parseFloat((item.price * 0.5 || 35).toFixed(2)),
              startingBid: parseFloat((item.startingBid || item.price * 0.5 * 0.8 || 28).toFixed(2)),
              suggestedMaxBid: parseFloat((item.suggestedMaxBid || item.price * 0.5 || 35).toFixed(2))
            });
            addedCount++;
          }
        });
        saveWatchlist(watchlist);
        const message = document.getElementById('message');
        if (message) {
          message.innerText = `Imported ${addedCount} new item(s) to watchlist!`;
          message.style.color = "#28a745";
          message.style.display = "block";
          setTimeout(() => {
            message.style.display = "none";
            message.innerText = "";
          }, 3000);
        }
        renderSimulator();
      } catch (e) {
        handleStorageError('importing watchlist', e);
      }
    };
    reader.readAsText(file);
  }

  function initializeWithRetry(attempts = 5, delay = 200) {
    let retries = 0;
    function tryInitialize() {
      try {
        console.log(`Simulator page DOM loaded, attempt ${retries + 1}`);
        const watchlist = getWatchlist();
        if (!Array.isArray(watchlist)) saveWatchlist([]);
        const simulatorItemsContainer = document.getElementById("simulatorItems");
        if (!simulatorItemsContainer) {
          console.warn(`simulatorItems element not found on attempt ${retries + 1}`);
          if (retries < attempts - 1) {
            retries++;
            setTimeout(tryInitialize, delay);
            return;
          }
          throw new Error("simulatorItems element not found after retries");
        }
        console.log("simulatorItems element found");
        const confidenceLimitInput = document.getElementById("confidenceLimit");
        if (confidenceLimitInput) {
          confidenceLimitInput.value = getConfidenceLimit();
        } else {
          console.warn("confidenceLimit element not found, skipping value set");
        }
        const profitLimitInput = document.getElementById("profitLimit");
        if (profitLimitInput) {
          profitLimitInput.value = getProfitLimit();
        } else {
          console.warn("profitLimit element not found, skipping value set");
        }
        const userBudgetInput = document.getElementById("user-budget");
        if (userBudgetInput) {
          userBudgetInput.value = localStorage.getItem("userBudget") || 1828.4;
          userBudgetInput.addEventListener("change", () => {
            const budget = parseFloat(userBudgetInput.value) || 1828.4;
            if (budget > 0) {
              localStorage.setItem("userBudget", budget.toFixed(2));
              updateToolbar();
              renderSimulator();
            } else {
              const message = document.getElementById("message");
              if (message) {
                message.innerText = "Invalid budget amount, must be positive";
                message.style.color = "#dc3545";
                message.style.display = "block";
                setTimeout(() => {
                  message.style.display = "none";
                  message.innerText = "";
                }, 3000);
              }
            }
          });
        }
        document.getElementById("profit-form")?.addEventListener("submit", calculateProfit);
        const saveFlipsBtn = document.getElementById("save-flips");
        if (saveFlipsBtn) saveFlipsBtn.addEventListener("click", saveCheckedFlips);
        const exportWatchlistBtn = document.getElementById("export-watchlist");
        if (exportWatchlistBtn) exportWatchlistBtn.addEventListener("click", exportWatchlist);
        const clearWatchlistBtn = document.getElementById("clear-watchlist");
        if (clearWatchlistBtn) clearWatchlistBtn.addEventListener("click", clearWatchlist);
        const importWatchlistInput = document.getElementById("import-watchlist");
        if (importWatchlistInput) importWatchlistInput.addEventListener("change", importWatchlist);
        const scanButton = document.querySelector('button[type="submit"]');
        if (scanButton) scanButton.addEventListener("click", scanForProfits);
        if (confidenceLimitInput) confidenceLimitInput.addEventListener("change", setConfidenceLimit);
        if (profitLimitInput) profitLimitInput.addEventListener("change", setProfitLimit);
        const sortBySelect = document.getElementById("sortBy");
        if (sortBySelect) sortBySelect.addEventListener("change", scanForProfits);
        const thumbnailToggle = document.getElementById("thumbnail-toggle");
        if (thumbnailToggle) {
          thumbnailToggle.checked = getThumbnailDisplay();
          thumbnailToggle.addEventListener("change", function() {
            setThumbnailDisplay(thumbnailToggle.checked);
          });
          console.log("thumbnail-toggle event listener added");
        }
        const simulatorTab = document.getElementById('simulatorItems-tab');
        if (simulatorTab) {
          simulatorTab.addEventListener('click', () => showTab('simulatorItems'));
        }
        // Hide the category filter
        // const categoryFilter = document.getElementById('category-filter');
        // if (categoryFilter) categoryFilter.style.display = 'none';  // <-- Comment out or remove this line

        loadPriceData().then(() => {
          console.log("Initial data load complete");
          renderCategoryFilter();  // <-- Uncomment this to show the top category filter
          showTab('simulatorItems');
        });
        // Auto-refresh items every 12 hours (43,200,000 ms)
        setInterval(() => {
          loadPriceData().then(() => {
            console.log("Auto-refreshed items from scored_items.json");
            showTab('simulatorItems');
          });
        }, 43200000); // 12 hours in milliseconds
      } catch (e) {
        handleStorageError('initializing simulator', e);
        const simulatorItemsContainer = document.getElementById("simulatorItems") || document.createElement("div");
        if (!simulatorItemsContainer.id) {
          simulatorItemsContainer.id = "simulatorItems";
          simulatorItemsContainer.className = "tab-content item-list";
          document.body.appendChild(simulatorItemsContainer);
        }
        simulatorItemsContainer.innerHTML = '<p class="no-items">Simulator unavailable due to load error.</p>';
        if (retries < attempts - 1) {
          retries++;
          setTimeout(tryInitialize, delay);
        }
      }
    }
    document.addEventListener('DOMContentLoaded', tryInitialize);
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      tryInitialize();
    }
  }

  // Replace loadScoredItems with eBay fetch
  async function loadScoredItems(query = 'electronics') {
    try {
        const response = await fetch('http://127.0.0.1:5000/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `query=${encodeURIComponent(query)}`
        });
        const items = await response.json();
        // Map eBay results to simulator format
        return items.map(item => ({
            itemName: item.title,
            categoryPath: 'Electronics',  // Default category
            price: parseFloat(item.price.replace('$', '')),
            confidence: 85,  // Default confidence
            marketplace: 'ebay',
            id: `ebay-${Date.now()}-${Math.random()}`,
            startingBid: parseFloat(item.price.replace('$', '')) * 0.8,
            suggestedMaxBid: parseFloat(item.price.replace('$', '')),
            image: item.image,
            images: [item.image]
        }));
    } catch (e) {
        console.error('Error fetching eBay data:', e);
        return [];
    }
}

// Add a search form to the simulator (add to HTML or dynamically)
function addEbaySearchForm() {
    const container = document.getElementById('category-filter') || document.body;
    const formHtml = `
        <form id="ebay-search-form" style="margin: 10px 0;">
            <input type="text" id="ebay-query" placeholder="Search eBay" required>
            <button type="submit">Search</button>
        </form>
    `;
    container.insertAdjacentHTML('afterbegin', formHtml);
    document.getElementById('ebay-search-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = document.getElementById('ebay-query').value;
        await loadPriceData(query);
        scanForProfits();  // Refresh the simulator with new data
    });
}

// Call this in initializeWithRetry
addEbaySearchForm();

  window.simulator = {
    scanForProfits: scanForProfits,
    setConfidenceLimit: setConfidenceLimit,
    setProfitLimit: setProfitLimit,
    calculateProfit: calculateProfit,
    saveItemToWatchlist: saveItemToWatchlist,
    saveCheckedFlips: saveCheckedFlips,
    exportWatchlist: exportWatchlist,
    importWatchlist: importWatchlist,
    clearWatchlist: clearWatchlist,
    showTab: showTab,
    renderSimulator: renderSimulator,
    updateToolbar: updateToolbar,
    getConfidenceClass: getConfidenceClass,
    getProfitClass: getProfitClass,
    getThumbnail: getThumbnail,
    getThumbnailDisplay: getThumbnailDisplay,
    setThumbnailDisplay: setThumbnailDisplay,
    initializeWithRetry: initializeWithRetry,
    goToPage: window.simulator.goToPage,  // Add this line to include the goToPage function
    buyItem: function(button) {
      alert("Buy functionality is not implemented.");
    }
  };

  initializeWithRetry();
})();