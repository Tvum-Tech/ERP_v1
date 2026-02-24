// Defensive Polyfill for Utils.escapeHtml
// This fixes "TypeError: Utils.escapeHtml is not a function" if utils.js is cached or loads late.
if (typeof window.Utils === 'undefined') window.Utils = {};
if (typeof window.Utils.escapeHtml !== 'function') {
    window.Utils.escapeHtml = function (text) {
        if (!text && text !== 0) return '';
        return String(text)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    };
}

const ConfigurationBuilder = {
    state: {
        projectId: null,
        areaId: null,
        masterProducts: [], // Master product list from API
        masterProductsMap: {}, // Map prod_id -> product for quick lookup and onclick safety
        products: [], // Array of { id, data, qty, price } - selected products
        compatibleDrivers: [], // From API
        compatibleAccessories: [], // From API
        selectedDrivers: {}, // Map id -> { qty, data }
        selectedAccessories: {}, // Map id -> { qty, data }
        areaInfo: null,
        projectInfo: null
    },

    async init() {
        // Parse URL for IDs: /projects/1/areas/2/configurations/add/
        const pathParts = window.location.pathname.split('/');
        // parts: ["", "projects", "1", "areas", "2", "configurations", "add", ""]
        this.state.projectId = pathParts[2];
        this.state.areaId = pathParts[4];

        this.cacheDOM();
        this.bindEvents();

        // CRITICAL: Fetch context and products in parallel
        await Promise.all([
            this.fetchContext(),
            this.fetchProductMasterList()  // THIS IS THE CRITICAL FIX
        ]);
    },

    cacheDOM() {
        this.dom = {
            // Context
            ctxProject: document.getElementById('ctx-project-name'),
            ctxAreaName: document.getElementById('ctx-area-name'),
            ctxAreaCode: document.getElementById('ctx-area-code'),

            // Search
            searchInput: document.getElementById('product-search-input'),
            searchResults: document.getElementById('product-search-results'),

            // Products
            productList: document.getElementById('selected-products-list'),
            productBrowseList: document.getElementById('product-browse-list'),

            // Right Pane
            driversList: document.getElementById('compatible-drivers-list'),
            accessoriesList: document.getElementById('compatible-accessories-list'),
            driverCount: document.getElementById('driver-count'),
            accessoryCount: document.getElementById('accessory-count'),

            // Footer
            totalPrice: document.getElementById('config-total-price'),
            saveBtn: document.getElementById('btn-save-config')
        };
    },

    bindEvents() {
        // Search Debounce
        this.dom.searchInput.addEventListener('input', Utils.debounce((e) => this.handleSearch(e.target.value), 300));

        // Hide search results on click outside
        document.addEventListener('click', (e) => {
            if (!this.dom.searchInput.contains(e.target) && !this.dom.searchResults.contains(e.target)) {
                this.dom.searchResults.style.display = 'none';
            }
        });

        // Back button
        const backBtn = document.getElementById('btn-back');
        if (backBtn) {
            backBtn.addEventListener('click', () => window.history.back());
        }

        // EVENT DELEGATION: Product browse list items
        this.dom.productBrowseList.addEventListener('click', (e) => {
            const item = e.target.closest('[data-product-id]');
            if (item && !item.classList.contains('already-selected')) {
                const prodId = parseInt(item.dataset.productId);
                this.addProduct(prodId);
            }
        });

        // EVENT DELEGATION: Search results
        this.dom.searchResults.addEventListener('click', (e) => {
            const item = e.target.closest('[data-product-id]');
            if (item) {
                const prodId = parseInt(item.dataset.productId);
                this.addProduct(prodId);
            }
        });

        // EVENT DELEGATION: Product list (remove button, qty/price inputs)
        this.dom.productList.addEventListener('click', (e) => {
            const removeBtn = e.target.closest('[data-remove-product]');
            if (removeBtn) {
                const prodId = parseInt(removeBtn.dataset.removeProduct);
                this.removeProduct(prodId);
            }
        });

        this.dom.productList.addEventListener('change', (e) => {
            const qtyInput = e.target.closest('[data-product-qty]');
            if (qtyInput) {
                const prodId = parseInt(qtyInput.dataset.productQty);
                this.updateProductQty(prodId, qtyInput.value);
                return;
            }

            const priceInput = e.target.closest('[data-product-price]');
            if (priceInput) {
                const prodId = parseInt(priceInput.dataset.productPrice);
                this.updateProductPrice(prodId, priceInput.value);
            }
        });

        // EVENT DELEGATION: Drivers list
        this.dom.driversList.addEventListener('click', (e) => {
            // Prevent action if clicking on qty input
            if (e.target.closest('[data-driver-qty]')) {
                e.stopPropagation();
                return;
            }

            const driverItem = e.target.closest('[data-driver-id]');
            if (driverItem) {
                const driverId = parseInt(driverItem.dataset.driverId);
                this.toggleDriver(driverId);
            }
        });

        this.dom.driversList.addEventListener('change', (e) => {
            const qtyInput = e.target.closest('[data-driver-qty]');
            if (qtyInput) {
                const driverId = parseInt(qtyInput.dataset.driverQty);
                this.updateDriverQty(driverId, qtyInput.value);
            }
        });

        // EVENT DELEGATION: Accessories list
        this.dom.accessoriesList.addEventListener('click', (e) => {
            // Prevent action if clicking on qty input
            if (e.target.closest('[data-accessory-qty]')) {
                e.stopPropagation();
                return;
            }

            const accItem = e.target.closest('[data-accessory-id]');
            if (accItem) {
                const accId = parseInt(accItem.dataset.accessoryId);
                this.toggleAccessory(accId);
            }
        });

        this.dom.accessoriesList.addEventListener('change', (e) => {
            const qtyInput = e.target.closest('[data-accessory-qty]');
            if (qtyInput) {
                const accId = parseInt(qtyInput.dataset.accessoryQty);
                this.updateAccessoryQty(accId, qtyInput.value);
            }
        });

        // Save button
        this.dom.saveBtn.addEventListener('click', () => this.saveConfiguration());
    },

    // ================= PRODUCT MASTER LIST =================
    async fetchProductMasterList() {
        try {
            const browseListElement = document.getElementById('product-browse-list');
            const browseCountElement = document.getElementById('product-browse-count');

            // Fetch products from API
            const response = await API.get('/masters/products/');

            // Handle both paginated and non-paginated responses
            // Paginated: { results: [...], count, next, previous }
            // Direct: [...]
            let products = Array.isArray(response) ? response : (response.results || []);

            // Defensive: Ensure products is an array
            if (!Array.isArray(products)) {
                console.error('[ConfigBuilder] Products API did not return an array', response);
                browseListElement.innerHTML = `
                    <div class="empty-state-placeholder" style="color: var(--text-error);">
                        <i class="fa-solid fa-exclamation-triangle"></i>
                        <p>Failed to load products (Invalid API response)</p>
                    </div>
                `;
                browseCountElement.textContent = '0';
                this.state.masterProducts = [];
                return;
            }

            // Store in state
            this.state.masterProducts = products;

            // Build product map for onclick safety (avoids JSON parsing in onclick attributes)
            this.state.masterProductsMap = {};
            products.forEach(p => {
                if (p && typeof p.prod_id !== 'undefined') {
                    this.state.masterProductsMap[p.prod_id] = p;
                }
            });

            // Update count
            browseCountElement.textContent = `${products.length} products`;

            // Render product browse list
            this.renderProductBrowseList();

            if (products.length === 0) {
                browseListElement.innerHTML = `
                    <div class="empty-state-placeholder">
                        <i class="fa-solid fa-inbox"></i>
                        <p>No products available in Masters Library</p>
                        <small>Add products to the Masters module first</small>
                    </div>
                `;
            }

        } catch (error) {
            console.error('[ConfigBuilder] Failed to fetch product master list:', error);
            const browseListElement = document.getElementById('product-browse-list');
            const browseCountElement = document.getElementById('product-browse-count');

            browseListElement.innerHTML = `
                <div class="empty-state-placeholder" style="color: var(--text-error);">
                    <i class="fa-solid fa-circle-exclamation"></i>
                    <p>Failed to load products</p>
                    <small>${error.message || 'Check network connection'}</small>
                </div>
            `;
            browseCountElement.textContent = '0';
            this.state.masterProducts = [];
        }
    },

    renderProductBrowseList(productsToRender = null) {
        const browseListElement = document.getElementById('product-browse-list');
        const products = productsToRender || this.state.masterProducts;

        // Defensive: Check if products array exists
        if (!Array.isArray(products) || products.length === 0) {
            browseListElement.innerHTML = `
                <div class="empty-state-placeholder">
                    <i class="fa-solid fa-inbox"></i>
                    <p>No products found</p>
                </div>
            `;
            return;
        }

        // Map of already selected product IDs for quick lookup (use prod_id from API)
        const selectedIds = new Set(this.state.products.map(p => p.prod_id));

        // Render each product as a browse item
        browseListElement.innerHTML = products.map(product => {
            // Defensive: Ensure product has required fields (backend uses prod_id as primary key)
            if (!product || typeof product.prod_id === 'undefined') {
                console.warn('[ConfigBuilder] Product missing prod_id:', product);
                return '';
            }

            const isSelected = selectedIds.has(product.prod_id);
            const make = product.make || 'Unnamed Product';
            const orderCode = product.order_code || 'N/A';
            const basePrice = product.base_price || 0;
            const wattage = product.wattage || 'N/A';
            const image = product.visual_image || product.illustrative_details || product.photometrics || null;

            return `
                <div class="product-browse-item ${isSelected ? 'already-selected' : ''}" 
                     data-product-id="${product.prod_id}"
                     style="cursor: ${!isSelected ? 'pointer' : 'not-allowed'};">
                    
                    <!-- Image Column -->
                    <div>
                        ${image
                    ? `<img src="${image}" class="browse-product-img" loading="lazy" alt="${Utils.escapeHtml(make)}">`
                    : `<div class="browse-product-img" style="display:flex;align-items:center;justify-content:center;color:var(--text-muted);"><i class="fa-solid fa-image"></i></div>`
                }
                    </div>

                    <div>
                        <div class="browse-product-name">${Utils.escapeHtml(make)}</div>
                        <div class="browse-product-code">${Utils.escapeHtml(orderCode)}</div>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-muted);">
                        ${Utils.escapeHtml(String(wattage))}W
                    </div>
                    <div class="browse-product-price">${basePrice.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</div>
                </div>
            `;
        }).filter(Boolean).join('');
    },

    async fetchContext() {
        try {
            // Fetch Project with nested areas
            const project = await API.get(`/projects/${this.state.projectId}/`);

            // Defensive: Ensure project exists
            if (!project) {
                throw new Error('Project not found');
            }

            this.state.projectInfo = project;

            // Defensive: Check if areas array exists
            if (!Array.isArray(project.areas)) {
                console.warn('[ConfigBuilder] Project has no areas array, fetching separately...');
                // Fallback: Try to fetch areas separately
                try {
                    const areasResponse = await API.get(`/projects/${this.state.projectId}/areas/`);
                    project.areas = Array.isArray(areasResponse) ? areasResponse : [];
                } catch (err) {
                    console.error('[ConfigBuilder] Failed to fetch areas:', err);
                    project.areas = [];
                }
            }

            // Defensive: Find the specific area
            const area = project.areas.find(a => a.id == this.state.areaId);

            if (!area) {
                console.error(`[ConfigBuilder] Area ${this.state.areaId} not found in project areas`);
                Utils.showToast("Area not found in project", "error");
                // Set minimal area info to prevent crashes
                this.state.areaInfo = {
                    id: this.state.areaId,
                    name: 'Unknown Area',
                    area_code: 'N/A'
                };
            } else {
                this.state.areaInfo = area;
            }

            this.renderContext();
        } catch (error) {
            console.error("[ConfigBuilder] Context fetch error:", error);
            Utils.showToast("Failed to load context", "error");

            // Set fallback context to prevent blank screen
            this.state.projectInfo = { name: 'Loading failed...' };
            this.state.areaInfo = { name: 'Error', area_code: 'N/A' };
            this.renderContext();
        }
    },

    renderContext() {
        // Defensive: Check DOM elements exist
        if (!this.dom.ctxProject || !this.dom.ctxAreaName || !this.dom.ctxAreaCode) {
            console.error('[ConfigBuilder] Context DOM elements not found');
            return;
        }

        // Defensive: Safe access to project data
        if (this.state.projectInfo) {
            this.dom.ctxProject.textContent = this.state.projectInfo.name || 'Unnamed Project';
            this.dom.ctxProject.classList.remove('skeleton-text');
        }

        // Defensive: Safe access to area data
        if (this.state.areaInfo) {
            this.dom.ctxAreaName.textContent = this.state.areaInfo.name || 'Unnamed Area';
            this.dom.ctxAreaCode.textContent = this.state.areaInfo.area_code || 'N/A';
            this.dom.ctxAreaName.classList.remove('skeleton-text');
            this.dom.ctxAreaCode.classList.remove('skeleton-text');
        }
    },

    // ================= PRODUCT LOGIC =================

    handleSearch(query) {
        if (!query) {
            this.renderProductBrowseList(this.state.masterProducts);
            this.dom.searchResults.style.display = 'none';
            return;
        }

        const q = query.toLowerCase();
        // Local filtering against already fetched data
        const results = this.state.masterProducts.filter(p => {
            const make = (p.make || '').toLowerCase();
            const code = (p.order_code || '').toLowerCase();
            return make.includes(q) || code.includes(q);
        });

        // If strict "search dropdown" behavior is desired, we can use renderSearchResults
        // But the requirement says "Filter against already fetched data" and "Realtime filtering in JS".
        // It might be better to filter the main list.
        // Let's filter the main list AND show the dropdown if needed, or just the main list.
        // The prompt says "Center pane: Product list... Filter against already fetched data".
        // Let's update the main browse list.
        this.renderProductBrowseList(results);

        // Also hide the dropdown if we are filtering the main list
        this.dom.searchResults.style.display = 'none';
    },

    renderSearchResults(results) {
        // Defensive: Ensure results is an array
        if (!Array.isArray(results) || results.length === 0) {
            this.dom.searchResults.innerHTML = '<div class="p-3 text-muted text-center">No products found</div>';
            this.dom.searchResults.style.display = 'block';
            return;
        }

        const html = results.map(p => `
            <div class="search-result-item" data-product-id="${p.prod_id}" style="cursor: pointer;">
                <div>
                    <div style="font-weight:600; color:var(--text-main);">${p.make || 'Unnamed Product'}</div>
                    <div style="font-size:0.8rem; color:var(--text-muted);">${p.order_code || '-'}</div>
                </div>
                <div style="font-weight:700; color:var(--accent);">${(p.base_price || 0).toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</div>
            </div>
        `).join('');

        this.dom.searchResults.innerHTML = html;
        this.dom.searchResults.style.display = 'block';
    },

    addProduct(id) {
        // Retrieve product from map for safety (no JSON parsing in onclick)
        let product = this.state.masterProductsMap[id];

        // Fallback: If not in map, search in masterProducts array
        if (!product) {
            product = this.state.masterProducts.find(p => p && p.prod_id === id);
        }

        if (!product) {
            Utils.showToast("Error adding product. Try again.", "error");
            return;
        }

        // Defensive: Check if product already added (use prod_id)
        if (this.state.products.find(x => x && x.prod_id === id)) {
            Utils.showToast("Product already added", "warning");
            return;
        }

        // Defensive: Ensure product has required fields (backend uses prod_id as primary key)
        if (!product || typeof product.prod_id === 'undefined') {
            console.error('[ConfigBuilder] Invalid product object - missing prod_id:', product);
            Utils.showToast("Invalid product data", "error");
            return;
        }

        // Add product to selected list (store prod_id as product identifier)
        this.state.products.push({
            prod_id: id,
            data: product,
            qty: 1,
            price: product.base_price || 0
        });

        // Hide search results
        this.dom.searchResults.style.display = 'none';
        this.dom.searchInput.value = '';

        // Re-render both product browse list (to gray out selected) and selected products list
        this.renderProductBrowseList();
        this.renderProducts();

        // Update compatibility
        this.updateCompatibility();

        // Show success message
        Utils.showToast(`Added ${Utils.escapeHtml(product.make || 'Product')}`, "success");
    },

    removeProduct(id) {
        // Remove from selected products (use prod_id)
        this.state.products = this.state.products.filter(p => p && p.prod_id !== id);

        // Re-render both product browse list and selected products list
        this.renderProductBrowseList();
        this.renderProducts();

        // Update compatibility
        this.updateCompatibility();
    },

    updateProductQty(id, qty) {
        // Defensive: Find product in selected list (use prod_id)
        const prod = this.state.products.find(p => p && p.prod_id === id);
        if (prod) {
            prod.qty = Math.max(1, parseInt(qty) || 1); // Ensure minimum qty of 1
            this.updateTotals();

            // Qty change triggers compatibility check per requirements
            // "When product quantity changed -> Frontend must call compatibility API"
            this.updateCompatibility();
        }
    },

    updateProductPrice(id, price) {
        // Defensive: Find product in selected list (use prod_id)
        const prod = this.state.products.find(p => p && p.prod_id === id);
        if (prod) {
            prod.price = Math.max(0, parseFloat(price) || 0); // Ensure non-negative price
            this.updateTotals();

            // Price change doesn't affect compatibility, just total calculation
        }
    },

    renderProducts() {
        // Defensive: Check if products array exists and is valid
        if (!Array.isArray(this.state.products) || this.state.products.length === 0) {
            this.dom.productList.innerHTML = `
                <div class="empty-state-placeholder">
                    <i class="fa-solid fa-basket-shopping"></i>
                    <p>No products selected</p>
                    <small>Click products above to add them</small>
                </div>`;
            this.dom.saveBtn.disabled = true;
            return;
        }

        this.dom.saveBtn.disabled = false;

        // Build HTML for each product row
        const html = this.state.products.map(p => {
            // Defensive: Check if product object is valid (use prod_id)
            if (!p || typeof p.prod_id === 'undefined' || !p.data) {
                console.warn('[ConfigBuilder] Invalid product in selected list:', p);
                return '';
            }

            const make = p.data.make || 'Unnamed Product';
            const orderCode = p.data.order_code || 'N/A';
            const qty = Math.max(1, parseInt(p.qty) || 1);
            const price = Math.max(0, parseFloat(p.price) || 0);

            return `
                <div class="product-row">
                    <div>
                        <div style="font-weight:600; color:var(--text-main);">${Utils.escapeHtml(make)}</div>
                        <div style="font-size:0.8rem; color:var(--text-muted);">${Utils.escapeHtml(p.data.description || '')}</div>
                    </div>
                    <div style="color:var(--text-secondary); font-family:monospace;">${Utils.escapeHtml(orderCode)}</div>
                    <div>
                        <input type="number" class="qty-input" data-product-qty="${p.prod_id}" value="${qty}" min="1">
                    </div>
                    <div>
                        <input type="number" class="price-input" data-product-price="${p.prod_id}" value="${price}" min="0">
                    </div>
                    <div style="text-align:center;">
                        <button class="btn-icon text-error" data-remove-product="${p.prod_id}">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).filter(Boolean).join('');

        this.dom.productList.innerHTML = html;
        this.updateTotals();
    },

    // ================= COMPATIBILITY LOGIC =================

    async updateCompatibility() {
        // Defensive: Check if we have products
        if (!Array.isArray(this.state.products) || this.state.products.length === 0) {
            this.dom.driversList.innerHTML = '<div class="empty-comp">Select products to see drivers</div>';
            this.dom.accessoriesList.innerHTML = '<div class="empty-comp">Select products to see accessories</div>';
            this.dom.driverCount.textContent = '0';
            this.dom.accessoryCount.textContent = '0';

            // Clear state
            this.state.compatibleDrivers = [];
            this.state.compatibleAccessories = [];
            return;
        }

        // Build product IDs array with strict filtering
        // - Only include prod_id values that are integers
        // - Filter out undefined, null, NaN, etc.
        const productIds = this.state.products
            .map(p => {
                // Ensure product object exists
                if (!p) return null;

                // Get prod_id and ensure it's an integer
                const prodId = p.prod_id;

                // Validate: must be integer (not string, not float, not undefined)
                if (typeof prodId !== 'number' || !Number.isInteger(prodId)) {
                    console.warn('[ConfigBuilder] Filtering out invalid prod_id:', prodId, 'type:', typeof prodId);
                    return null;
                }

                return prodId;
            })
            .filter(id => id !== null && id !== undefined);

        // CRITICAL: Do NOT call API if product_ids array is empty
        if (productIds.length === 0) {
            console.warn('[ConfigBuilder] No valid product IDs found. Skipping compatibility API call.');
            this.dom.driversList.innerHTML = '<div class="empty-comp">Select valid products to see drivers</div>';
            this.dom.accessoriesList.innerHTML = '<div class="empty-comp">Select valid products to see accessories</div>';
            this.dom.driverCount.textContent = '0';
            this.dom.accessoryCount.textContent = '0';
            this.state.compatibleDrivers = [];
            this.state.compatibleAccessories = [];
            return;
        }

        // Build the exact payload format required by backend
        const payload = { product_ids: productIds };

        // DEBUG: Log the exact payload being sent
        console.log('[ConfigBuilder] Compatibility payload:', JSON.stringify(payload));
        console.log('[ConfigBuilder] Payload details:', {
            product_ids_count: payload.product_ids.length,
            product_ids_values: payload.product_ids,
            content_type: 'application/json'
        });

        // Show loading state
        this.dom.driversList.innerHTML = '<div style="padding:1rem; text-align:center;"><i class="fa-solid fa-spinner fa-spin"></i> Checking compatibility...</div>';
        this.dom.accessoriesList.innerHTML = '<div style="padding:1rem; text-align:center;"><i class="fa-solid fa-spinner fa-spin"></i> Loading...</div>';

        try {
            // Make API request with proper payload
            console.log('[ConfigBuilder] Sending POST /api/configurations/compatibility/', payload);
            const response = await API.post('/configurations/compatibility/', payload);

            // Log response
            console.log('[ConfigBuilder] Compatibility API response:', response);

            // Defensive: Validate response structure
            if (!response) {
                throw new Error('Empty response from compatibility API');
            }

            // Extract drivers and accessories from response
            this.state.compatibleDrivers = Array.isArray(response.drivers) ? response.drivers : [];
            this.state.compatibleAccessories = Array.isArray(response.accessories) ? response.accessories : [];

            // IMPORTANT: when products change, remove any now-incompatible selections
            this.pruneIncompatibleSelections();

            console.log(`[ConfigBuilder] Found ${this.state.compatibleDrivers.length} drivers, ${this.state.compatibleAccessories.length} accessories`);

            this.renderCompatibility();

        } catch (error) {
            console.error("[ConfigBuilder] Compat check failed:", error);
            console.error("[ConfigBuilder] Error response:", error.response);

            // Provide detailed error message
            let errorMsg = 'Failed to load drivers and accessories';
            if (error.response && error.response.data) {
                console.error('[ConfigBuilder] Error details:', error.response.data);
                errorMsg += `: ${JSON.stringify(error.response.data)}`;
            }

            this.dom.driversList.innerHTML = `<div class="text-error" style="padding:1rem;"><i class="fa-solid fa-exclamation-triangle"></i> ${errorMsg}</div>`;
            this.dom.accessoriesList.innerHTML = '<div class="text-error" style="padding:1rem;">Failed to load accessories</div>';

            // Set empty arrays
            this.state.compatibleDrivers = [];
            this.state.compatibleAccessories = [];
            this.dom.driverCount.textContent = '0';
            this.dom.accessoryCount.textContent = '0';
        }
    },


    pruneIncompatibleSelections() {
        const validDriverIds = new Set((this.state.compatibleDrivers || []).map(d => d.id));
        const validAccessoryIds = new Set((this.state.compatibleAccessories || []).map(a => a.id));

        if (this.state.selectedDrivers && typeof this.state.selectedDrivers === 'object') {
            Object.keys(this.state.selectedDrivers).forEach((id) => {
                if (!validDriverIds.has(parseInt(id, 10))) {
                    delete this.state.selectedDrivers[id];
                }
            });
        }

        if (this.state.selectedAccessories && typeof this.state.selectedAccessories === 'object') {
            Object.keys(this.state.selectedAccessories).forEach((id) => {
                if (!validAccessoryIds.has(parseInt(id, 10))) {
                    delete this.state.selectedAccessories[id];
                }
            });
        }

        this.updateTotals();
    },

    renderCompatibility() {
        // Defensive: Check if products array exists and has items
        if (!Array.isArray(this.state.products) || this.state.products.length === 0) {
            console.warn('[ConfigBuilder] renderCompatibility called with no products');
            return;
        }

        // Integrated Logic - check if all products have integrated drivers
        const allIntegrated = this.state.products.every(p =>
            p.data && p.data.driver_integration === 'INTEGRATED'
        );

        if (allIntegrated) {
            this.dom.driversList.innerHTML = `
                <div class="badge-integrated">
                    <i class="fa-solid fa-check-circle"></i>
                    All selected products have INTEGRATED drivers.
                    <br>No external driver selection needed.
                </div>`;
            this.dom.driverCount.textContent = '-';
        } else {
            this.renderDriversList();
        }

        this.renderAccessoriesList();
    },

    renderDriversList() {
        // Defensive: Ensure drivers array exists
        const drivers = Array.isArray(this.state.compatibleDrivers) ? this.state.compatibleDrivers : [];
        this.dom.driverCount.textContent = drivers.length;

        if (drivers.length === 0) {
            this.dom.driversList.innerHTML = '<div class="empty-comp text-error">No compatible drivers found for this combination!</div>';
            return;
        }

        // Build HTML for each driver
        const html = drivers.map(d => {
            // Defensive: Ensure driver object is valid
            if (!d || !d.id) {
                console.warn('[ConfigBuilder] Invalid driver object:', d);
                return '';
            }

            const isSelected = this.state.selectedDrivers && this.state.selectedDrivers[d.id];
            const driverMake = d.driver_make || 'Unknown';
            const driverCode = d.driver_code || 'N/A';
            const constantType = d.constant_type || 'N/A';
            const maxWattage = d.max_wattage || 0;
            const dimmingProtocol = d.dimming_protocol || 'N/A';
            const basePrice = d.base_price || 0;

            let qtyHtml = '';
            if (isSelected && this.state.selectedDrivers[d.id]) {
                qtyHtml = `
                    <div class="comp-qty-row">
                        <span style="font-size:0.8rem;">Qty:</span>
                        <input type="number" class="qty-input" data-driver-qty="${d.id}" value="${Math.max(1, parseInt(this.state.selectedDrivers[d.id].qty) || 1)}" min="1">
                    </div>
                `;
            }

            return `
                <div class="comp-item ${isSelected ? 'selected' : ''}" data-driver-id="${d.id}" style="cursor: pointer;">
                    <div class="comp-item-header">
                        <span>${Utils.escapeHtml(driverMake)}</span>
                        <span style="font-family:monospace;">${Utils.escapeHtml(driverCode)}</span>
                    </div>
                    <div class="comp-specs">
                        <span>${Utils.escapeHtml(constantType)}</span>
                        <span>${maxWattage}W</span>
                        <span>${Utils.escapeHtml(dimmingProtocol)}</span>
                        <span style="margin-left:auto; color:var(--accent); font-weight:700;">${basePrice.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</span>
                    </div>
                    ${qtyHtml}
                </div>
            `;
        }).filter(Boolean).join('');

        this.dom.driversList.innerHTML = html || '<div class="empty-comp">No drivers available</div>';
    },

    renderAccessoriesList() {
        // Defensive: Ensure accessories array exists
        const accs = Array.isArray(this.state.compatibleAccessories) ? this.state.compatibleAccessories : [];
        this.dom.accessoryCount.textContent = accs.length;

        if (accs.length === 0) {
            this.dom.accessoriesList.innerHTML = '<div class="empty-comp">No compatible accessories found</div>';
            return;
        }

        // Build HTML for each accessory
        const html = accs.map(a => {
            // Defensive: Ensure accessory object is valid
            if (!a || !a.id) {
                console.warn('[ConfigBuilder] Invalid accessory object:', a);
                return '';
            }

            const isSelected = this.state.selectedAccessories && this.state.selectedAccessories[a.id];
            const accessoryName = a.accessory_name || 'Unknown';
            const accessoryCategory = a.accessory_category || 'N/A';
            const basePrice = a.base_price || 0;

            let qtyHtml = '';
            if (isSelected && this.state.selectedAccessories[a.id]) {
                qtyHtml = `
                    <div class="comp-qty-row">
                        <span style="font-size:0.8rem;">Qty:</span>
                        <input type="number" class="qty-input" data-accessory-qty="${a.id}" value="${Math.max(1, parseInt(this.state.selectedAccessories[a.id].qty) || 1)}" min="1">
                    </div>
                `;
            }

            return `
                <div class="comp-item ${isSelected ? 'selected' : ''}" data-accessory-id="${a.id}" style="cursor: pointer;">
                    <div class="comp-item-header">
                        <span>${Utils.escapeHtml(accessoryName)}</span>
                    </div>
                    <div class="comp-specs">
                        <span>${Utils.escapeHtml(accessoryCategory)}</span>
                        <span style="margin-left:auto; color:var(--accent); font-weight:700;">${basePrice.toLocaleString('en-IN', { style: 'currency', currency: 'INR' })}</span>
                    </div>
                    ${qtyHtml}
                </div>
            `;
        }).filter(Boolean).join('');

        this.dom.accessoriesList.innerHTML = html || '<div class="empty-comp">No accessories available</div>';
    },

    toggleDriver(id) {
        // Defensive: Initialize selectedDrivers if needed
        if (!this.state.selectedDrivers) {
            this.state.selectedDrivers = {};
        }

        if (this.state.selectedDrivers[id]) {
            delete this.state.selectedDrivers[id];
        } else {
            // Find driver in compatible list
            const driver = Array.isArray(this.state.compatibleDrivers)
                ? this.state.compatibleDrivers.find(d => d && d.id === id)
                : null;

            if (!driver) {
                console.error('[ConfigBuilder] Driver not found in compatible list:', id);
                Utils.showToast("Cannot select this driver", "error");
                return;
            }

            this.state.selectedDrivers[id] = { qty: 1, data: driver };
        }
        this.renderDriversList();
        this.updateTotals();
    },

    updateDriverQty(id, qty) {
        // Defensive: Check if driver is selected
        if (!this.state.selectedDrivers || !this.state.selectedDrivers[id]) {
            console.error('[ConfigBuilder] Trying to update qty of unselected driver:', id);
            return;
        }

        this.state.selectedDrivers[id].qty = Math.max(1, parseInt(qty) || 1);
        this.updateTotals();
    },

    toggleAccessory(id) {
        // Defensive: Initialize selectedAccessories if needed
        if (!this.state.selectedAccessories) {
            this.state.selectedAccessories = {};
        }

        if (this.state.selectedAccessories[id]) {
            delete this.state.selectedAccessories[id];
        } else {
            // Find accessory in compatible list
            const acc = Array.isArray(this.state.compatibleAccessories)
                ? this.state.compatibleAccessories.find(a => a && a.id === id)
                : null;

            if (!acc) {
                console.error('[ConfigBuilder] Accessory not found in compatible list:', id);
                Utils.showToast("Cannot select this accessory", "error");
                return;
            }

            this.state.selectedAccessories[id] = { qty: 1, data: acc };
        }
        this.renderAccessoriesList();
        this.updateTotals();
    },

    updateAccessoryQty(id, qty) {
        // Defensive: Check if accessory is selected
        if (!this.state.selectedAccessories || !this.state.selectedAccessories[id]) {
            console.error('[ConfigBuilder] Trying to update qty of unselected accessory:', id);
            return;
        }

        this.state.selectedAccessories[id].qty = Math.max(1, parseInt(qty) || 1);
        this.updateTotals();
    },

    updateTotals() {
        let total = 0;

        // Add product totals
        if (Array.isArray(this.state.products)) {
            this.state.products.forEach(p => {
                if (p && p.data) {
                    const qty = Math.max(1, parseInt(p.qty) || 1);
                    const price = Math.max(0, parseFloat(p.price) || 0);
                    total += (qty * price);
                }
            });
        }

        // Add driver totals
        if (this.state.selectedDrivers && typeof this.state.selectedDrivers === 'object') {
            Object.values(this.state.selectedDrivers).forEach(d => {
                if (d && d.data) {
                    const qty = Math.max(1, parseInt(d.qty) || 1);
                    const price = Math.max(0, parseFloat(d.data.base_price) || 0);
                    total += (qty * price);
                }
            });
        }

        // Add accessory totals
        if (this.state.selectedAccessories && typeof this.state.selectedAccessories === 'object') {
            Object.values(this.state.selectedAccessories).forEach(a => {
                if (a && a.data) {
                    const qty = Math.max(1, parseInt(a.qty) || 1);
                    const price = Math.max(0, parseFloat(a.data.base_price) || 0);
                    total += (qty * price);
                }
            });
        }

        // Defensive: Update DOM if element exists
        if (this.dom && this.dom.totalPrice) {
            this.dom.totalPrice.textContent = total.toLocaleString('en-IN', { style: 'currency', currency: 'INR' });
        }
    },

    async saveConfiguration() {
        // Defensive: Validate that we have products selected
        if (!Array.isArray(this.state.products) || this.state.products.length === 0) {
            Utils.showToast("Please select at least one product", "warning");
            return;
        }

        // Construct payload with defensive guards
        const products = this.state.products
            .filter(p => p && p.prod_id && p.data)
            .map(p => ({
                product_id: p.prod_id,
                quantity: Math.max(1, parseInt(p.qty) || 1),
                base_price: Math.max(0, parseFloat(p.price) || 0)
            }));

        if (products.length === 0) {
            Utils.showToast("Invalid product data. Please review selections.", "error");
            return;
        }

        const drivers = this.state.selectedDrivers && typeof this.state.selectedDrivers === 'object'
            ? Object.values(this.state.selectedDrivers)
                .filter(d => d && d.data && d.data.id)
                .map(d => ({
                    driver_id: d.data.id,
                    quantity: Math.max(1, parseInt(d.qty) || 1)
                }))
            : [];

        const accessories = this.state.selectedAccessories && typeof this.state.selectedAccessories === 'object'
            ? Object.values(this.state.selectedAccessories)
                .filter(a => a && a.data && a.data.id)
                .map(a => ({
                    accessory_id: a.data.id,
                    quantity: Math.max(1, parseInt(a.qty) || 1)
                }))
            : [];

        // Link selected compatible drivers/accessories to each selected product.
        // This keeps product->driver/accessory relationships explicit for BOQ/PDF.
        const productsWithLinks = products.map((product) => ({
            ...product,
            drivers: drivers,
            accessories: accessories,
        }));

        const payload = {
            area_id: this.state.areaId,
            products: productsWithLinks,
            drivers: drivers,
            accessories: accessories
        };

        try {
            // Defensive: Check DOM elements before manipulating
            if (this.dom && this.dom.saveBtn) {
                this.dom.saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
                this.dom.saveBtn.disabled = true;
            }

            // Call batch save endpoint
            const response = await API.post('/configurations/save_batch/', payload);

            // Defensive: Validate response
            if (!response) {
                throw new Error("Empty response from server");
            }

            Utils.showToast("Configuration saved successfully!", "success");

            // Redirect after success
            setTimeout(() => {
                window.location.href = `/projects/${this.state.projectId}/areas/${this.state.areaId}/`;
            }, 1000);

        } catch (error) {
            console.error("[ConfigBuilder] Save failed:", error);
            Utils.showToast("Failed to save configuration: " + (error.message || 'Unknown error'), "error");

            // Restore button state
            if (this.dom && this.dom.saveBtn) {
                this.dom.saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save Configuration';
                this.dom.saveBtn.disabled = false;
            }
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ConfigurationBuilder.init();
});
