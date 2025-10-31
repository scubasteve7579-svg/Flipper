document.addEventListener('DOMContentLoaded', function() {
    // Global variables
    let allItems = [];
    let filteredItems = [];
    let watchlist = JSON.parse(localStorage.getItem('watchlist')) || [];
    let totalProfit = 0;
    let currentBudget = 1828.40;  // Default from HTML

    // Function to search eBay
    function searchEbay(query) {
        fetch(`/search?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                allItems = data.map(item => ({
                    title: item.title || 'No Title',
                    price: parseFloat((item.price || '$0').replace('$', '') || 0),
                    profit: calculateProfit(item),
                    confidence: calculateConfidence(item),
                    image: item.image || '',
                    url: item.url || '#',
                    location: 'eBay'
                }));
                populateCategories();
                applyFilters();
            })
            .catch(error => console.error('Search error:', error));
    }

    // Load initial data (comment out if not needed)
    // searchEbay('laptops');

    // Populate category filter as buttons
    function populateCategories() {
        const categoryFilter = document.getElementById('category-filter');
        categoryFilter.innerHTML = '';
        const categories = [...new Set(allItems.map(item => item.category || 'Uncategorized'))];
        categories.forEach(cat => {
            const button = document.createElement('button');
            button.className = 'category-btn';
            button.dataset.category = cat;
            button.textContent = cat;
            button.addEventListener('click', () => {
                // Optional: filter by category
                applyFilters();
            });
            categoryFilter.appendChild(button);
        });
    }

    // Apply filters
    function applyFilters() {
        const minProfit = parseFloat(document.getElementById('profitLimit').value) || 0;
        const minConfidence = parseFloat(document.getElementById('confidenceLimit').value) || 0;
        const sortBy = document.getElementById('sortBy').value;

        filteredItems = allItems.filter(item =>
            item.profit >= minProfit &&
            item.confidence >= minConfidence
        );

        // Sort
        filteredItems.sort((a, b) => {
            switch (sortBy) {
                case 'confidence-desc': return b.confidence - a.confidence;
                case 'confidence-asc': return a.confidence - b.confidence;
                case 'profit-desc': return b.profit - a.profit;
                case 'profit-asc': return a.profit - b.profit;
                case 'itemName-asc': return a.title.localeCompare(b.title);
                case 'itemName-desc': return b.title.localeCompare(a.title);
                default: return 0;
            }
        });

        renderItems();
    }

    // Render items
    function renderItems() {
        const container = document.getElementById('simulatorItems');
        container.innerHTML = '';
        if (filteredItems.length === 0) {
            container.innerHTML = '<p class="no-items">No items found.</p>';
            return;
        }

        filteredItems.forEach(item => {
            const card = document.createElement('div');
            card.className = 'item-card';
            const showThumbnails = document.getElementById('thumbnail-toggle').checked;
            card.innerHTML = `
                ${showThumbnails ? `<img src="${item.image}" alt="Item" class="thumbnail">` : ''}
                <div class="item-details">
                    <h3>${item.title}</h3>
                    <p>Price: $${item.price}</p>
                    <p class="profit-display ${item.profit > 0 ? 'profit-high' : 'profit-low'}">Profit: $${item.profit}</p>
                    <p class="${item.confidence > 70 ? 'confidence-high' : item.confidence > 40 ? 'confidence-medium' : 'confidence-low'}">Confidence: ${item.confidence}%</p>
                    <p>Location: ${item.location}</p>
                    <button onclick="addToWatchlist('${item.title}')">Add to Watchlist</button>
                    <a href="${item.url}" target="_blank">View on eBay</a>
                </div>
            `;
            container.appendChild(card);
        });

        updateToolbar();
    }

    // Update toolbar
    function updateToolbar() {
        totalProfit = filteredItems.reduce((sum, item) => sum + item.profit, 0);
        document.getElementById('totalProfit').textContent = totalProfit.toFixed(2);
        document.getElementById('currentBudget').textContent = currentBudget.toFixed(2);
    }

    // Watchlist functions
    function addToWatchlist(title) {
        if (!watchlist.includes(title)) {
            watchlist.push(title);
            localStorage.setItem('watchlist', JSON.stringify(watchlist));
        }
    }

    // Event listeners
    document.getElementById('profit-form').addEventListener('submit', function(event) {
        event.preventDefault();
        const query = document.getElementById('itemName').value;
        if (query) searchEbay(query);
    });

    document.getElementById('profitLimit').addEventListener('input', applyFilters);
    document.getElementById('confidenceLimit').addEventListener('input', applyFilters);
    document.getElementById('sortBy').addEventListener('change', applyFilters);
    document.getElementById('thumbnail-toggle').addEventListener('change', renderItems);

    document.getElementById('save-flips').addEventListener('click', () => {
        // Placeholder: save selected items
        alert('Save selected flips not implemented yet.');
    });

    document.getElementById('export-watchlist').addEventListener('click', () => {
        const dataStr = JSON.stringify(watchlist, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'watchlist.json';
        a.click();
    });

    document.getElementById('clear-watchlist').addEventListener('click', () => {
        watchlist = [];
        localStorage.removeItem('watchlist');
    });

    document.getElementById('import-watchlist').addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    watchlist = JSON.parse(e.target.result);
                    localStorage.setItem('watchlist', JSON.stringify(watchlist));
                } catch (error) {
                    alert('Invalid JSON file.');
                }
            };
            reader.readAsText(file);
        }
    });

    // Placeholder functions
    function calculateProfit(item) {
        return Math.random() * 100;
    }

    function calculateConfidence(item) {
        return Math.random() * 100;
    }
});