// Global variables
let allItems = [];
let filteredItems = [];
let currentPage = 1;
const itemsPerPage = 10;
let watchlist = JSON.parse(localStorage.getItem('watchlist')) || [];
let budget = 1000;

// Load eBay data and normalize it
fetch('my_items/items.json')
    .then(response => response.json())
    .then(data => {
        allItems = data.map(item => ({
            title: item.title,
            price: parseFloat(item.price),
            category: item.categoryPath || item.catalogCategory,
            image: item.image || 'placeholder.jpg',
            itemId: item.itemId || item.title, // or another unique field
            viewItemURL: item.url,
            location: item.location,
            condition: item.condition,
            shippingCost: parseFloat(item.shippingServiceCost) || 0
        }));
        applyFilters();
        renderItems();
        renderWatchlist();
    })
    .catch(error => console.error('Error loading data:', error));

// AI scoring placeholders
function calculateProfit(price) {
    return price * 0.2;
}

function calculateConfidence(item) {
    return item.condition === 'New' ? 0.9 : 0.7;
}

// Apply filters
function applyFilters() {
    const category = document.getElementById('categoryFilter').value;
    const minProfit = parseFloat(document.getElementById('minProfit').value) || 0;
    const minConfidence = parseFloat(document.getElementById('minConfidence').value) || 0;

    filteredItems = allItems.filter(item => {
        return (!category || item.category === category) &&
               item.profit >= minProfit &&
               item.confidence >= minConfidence;
    });
    currentPage = 1;
    renderItems();
}

// Render items
function renderItems() {
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageItems = filteredItems.slice(start, end);

    const container = document.getElementById('itemsContainer');
    container.innerHTML = '';

    pageItems.forEach(item => {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
            <img src="${item.image}" alt="${item.title}" onerror="this.src='placeholder.jpg'">
            <h3>${item.title}</h3>
            <p>Price: $${item.price}</p>
            <p>Profit: $${item.profit.toFixed(2)}</p>
            <p>Confidence: ${(item.confidence * 100).toFixed(0)}%</p>
            <p>Location: ${item.location}</p>
            <button onclick="addToWatchlist('${item.itemId}')">Add to Watchlist</button>
            <a href="${item.viewItemURL}" target="_blank">View Item</a>
        `;
        container.appendChild(card);
    });

    document.getElementById('pageInfo').textContent = `Page ${currentPage} of ${Math.ceil(filteredItems.length / itemsPerPage)}`;
}

// Pagination
document.getElementById('prevPage').addEventListener('click', () => {
    if (currentPage > 1) {
        currentPage--;
        renderItems();
    }
});

document.getElementById('nextPage').addEventListener('click', () => {
    if (currentPage < Math.ceil(filteredItems.length / itemsPerPage)) {
        currentPage++;
        renderItems();
    }
});

// Watchlist functions
function addToWatchlist(itemId) {
    const item = allItems.find(i => i.itemId === itemId);
    if (item && !watchlist.find(w => w.itemId === itemId)) {
        watchlist.push(item);
        localStorage.setItem('watchlist', JSON.stringify(watchlist));
        renderWatchlist();
    }
}

function renderWatchlist() {
    const list = document.getElementById('watchlistItems');
    list.innerHTML = '';
    watchlist.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.title} - $${item.price}`;
        list.appendChild(li);
    });
}

document.getElementById('exportWatchlist').addEventListener('click', () => {
    const dataStr = JSON.stringify(watchlist, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'watchlist.json';
    a.click();
});

document.getElementById('clearWatchlist').addEventListener('click', () => {
    watchlist = [];
    localStorage.setItem('watchlist', JSON.stringify(watchlist));
    renderWatchlist();
});

// Event listeners
document.getElementById('categoryFilter').addEventListener('change', applyFilters);
document.getElementById('minProfit').addEventListener('input', applyFilters);
document.getElementById('minConfidence').addEventListener('input', applyFilters);

// Tab switching
document.getElementById('simulatorTab').addEventListener('click', () => {
    document.getElementById('simulatorView').style.display = 'block';
    document.getElementById('watchlistView').style.display = 'none';
    document.getElementById('simulatorTab').classList.add('active');
    document.getElementById('watchlistTab').classList.remove('active');
});

document.getElementById('watchlistTab').addEventListener('click', () => {
    document.getElementById('simulatorView').style.display = 'none';
    document.getElementById('watchlistView').style.display = 'block';
    document.getElementById('watchlistTab').classList.add('active');
    document.getElementById('simulatorTab').classList.remove('active');
});

// Category buttons
document.querySelectorAll('.category-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.category-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('categoryFilter').value = btn.dataset.category;
        applyFilters();
        updateBreadcrumbs(btn.textContent);
    });
});

// Breadcrumbs
function updateBreadcrumbs(category) {
    document.getElementById('breadcrumbs').textContent = `Home > ${category}`;
}

// Thumbnail toggling
document.getElementById('showThumbnails').addEventListener('change', () => {
    const show = document.getElementById('showThumbnails').checked;
    document.querySelectorAll('.item-card img').forEach(img => {
        img.style.display = show ? 'block' : 'none';
    });
});