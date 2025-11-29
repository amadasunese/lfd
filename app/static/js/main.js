// static/js/main.js

(function () {
    // === Utility helpers ===
    function formatCurrency(amount) {
        return new Intl.NumberFormat('en-NG', {
            style: 'currency',
            currency: 'NGN'
        }).format(amount);
    }

    function formatDate(dateString) {
        return new Date(dateString).toLocaleDateString('en-NG', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }

    function debounce(func, wait = 300) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // === Notifications & cart count ===
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        const bsType = type === 'error' ? 'danger' : type;

        notification.className = `
            alert alert-${bsType} alert-dismissible fade show
            position-fixed top-0 end-0 m-3
        `.replace(/\s+/g, ' ').trim();
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification && notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    function animateCartBadge(cartBadge) {
        if (!cartBadge) return;
        cartBadge.classList.add('cart-pulse');
        setTimeout(() => cartBadge.classList.remove('cart-pulse'), 300);
    }

    function updateCartCount(newCount) {
        const cartBadge = document.querySelector('.cart-count');
        if (!cartBadge) return;

        // If backend sent cart_count, use it directly
        if (typeof newCount === 'number') {
            cartBadge.textContent = newCount;
            animateCartBadge(cartBadge);
            return;
        }

        // Fallback: fetch cart_count from server
        fetch('/orders/cart_count', {
            headers: { 'Accept': 'application/json' }
        })
            .then(response => response.json())
            .then(data => {
                if (typeof data.count === 'number') {
                    cartBadge.textContent = data.count;
                    animateCartBadge(cartBadge);
                }
            })
            .catch(err => console.error('Cart count error:', err));
    }

    // === Add to cart (API-style, for other pages) ===
    async function addToCart(itemId, quantity = 1) {
        try {
            const response = await fetch('/orders/add_to_cart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: `item_id=${encodeURIComponent(itemId)}&quantity=${encodeURIComponent(quantity)}`
            });

            const result = await response.json().catch(() => ({}));

            if (result.success) {
                updateCartCount(typeof result.cart_count === 'number' ? result.cart_count : undefined);
                showNotification(result.message || 'Item added to cart!', 'success');
            } else {
                showNotification(result.message || 'Error adding item to cart', 'error');
            }
        } catch (error) {
            console.error(error);
            showNotification('Network error. Please try again.', 'error');
        }
    }

    // === Delegated Add-to-cart for forms on menu/home pages ===
    async function handleAddToCartFormSubmit(form) {
        const submitBtn = form.querySelector('button[type="submit"]');

        if (submitBtn && submitBtn.disabled) return;

        const data = new FormData(form);
        const action = form.action || '/orders/add_to_cart';

        let originalHtml = '';
        if (submitBtn) {
            originalHtml = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Adding...';
        }

        try {
            const response = await fetch(action, {
                method: 'POST',
                body: data,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            });

            const result = await response.json().catch(() => ({}));

            if (result.success) {
                // Turn the button into "View Cart"
                if (submitBtn) {
                    submitBtn.outerHTML = `
                        <a href="/orders/cart" class="btn btn-success btn-add-cart">
                            <i class="fas fa-check me-2"></i> View Cart
                        </a>
                    `;
                }

                updateCartCount(typeof result.cart_count === 'number' ? result.cart_count : undefined);
                showNotification(result.message || 'Item added to cart!', 'success');
            } else {
                showNotification(result.message || 'Error adding item to cart', 'error');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalHtml || 'Add to Cart';
                }
            }
        } catch (error) {
            console.error(error);
            showNotification('Network error. Please try again.', 'error');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalHtml || 'Add to Cart';
            }
        }
    }

    // === Initializers ===
    function initAutoHideAlerts() {
        // Only for alerts already on page load (e.g., flashed messages)
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.parentNode) alert.remove();
            }, 5000);
        });
    }

    function initFormsLoadingState() {
        // Global submit listener but skip add-to-cart forms (handled separately)
        document.addEventListener('submit', function (e) {
            const form = e.target;
            if (!form || form.classList.contains('add-to-cart-form')) return;

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Processing...';
            }
        }, true);
    }

    function initDeleteConfirmation() {
        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.btn-danger[data-confirm="delete"], .btn-delete');
            if (!btn) return;

            const message = btn.dataset.confirmText || 'Are you sure you want to delete this item?';
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    }

    function initFilePreview() {
        document.addEventListener('change', function (e) {
            const input = e.target;
            if (!input.matches('input[type="file"][data-preview]')) return;

            const preview = document.getElementById(input.dataset.preview);
            if (preview && input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function (ev) {
                    preview.src = ev.target.result;
                };
                reader.readAsDataURL(input.files[0]);
            }
        });
    }

    function initSearchInput() {
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;

        const handleSearch = debounce(function (event) {
            // In future we can auto-submit or use AJAX here
            console.log('Searching for:', event.target.value);
        }, 300);

        searchInput.addEventListener('input', handleSearch);
    }

    function initSmoothScroll() {
        document.addEventListener('click', function (e) {
            const link = e.target.closest('a[href^="#"]');
            if (!link) return;

            const href = link.getAttribute('href');
            if (!href || href === '#') return;

            const target = document.querySelector(href);
            if (!target) return;

            e.preventDefault();
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        });
    }

    function initNavbarToggle() {
        const navbarToggler = document.querySelector('.navbar-toggler');
        const navbarCollapse = document.querySelector('.navbar-collapse');
        if (!navbarToggler || !navbarCollapse) return;

        navbarToggler.addEventListener('click', () => {
            navbarCollapse.classList.toggle('show');
        });
    }

    function initPriceRange() {
        const priceRange = document.getElementById('price-range');
        const priceDisplay = document.getElementById('price-display');
        if (!priceRange || !priceDisplay) return;

        priceRange.addEventListener('input', function () {
            priceDisplay.textContent = `₦0 - ₦${this.value}`;
        });
    }

    function initFeatureCardsReveal() {
        const featureCards = document.querySelectorAll('.feature-card');
        if (!featureCards.length) return;

        const revealOnScroll = () => {
            featureCards.forEach(card => {
                const rect = card.getBoundingClientRect();
                if (rect.top < window.innerHeight - 100) {
                    card.classList.add('visible');
                }
            });
        };

        document.addEventListener('scroll', revealOnScroll, { passive: true });
        revealOnScroll(); // run once on load
    }

    function initAddToCartDelegation() {
        document.addEventListener('submit', function (e) {
            const form = e.target.closest('.add-to-cart-form');
            if (!form) return;
            e.preventDefault();
            handleAddToCartFormSubmit(form);
        });
    }

    function initQuantityButtons() {
        // Delegated click listener for all quantity buttons
        document.addEventListener('click', function (e) {
            const btn = e.target.closest('.quantity-btn');
            if (!btn) return;

            const input = btn.parentElement.querySelector('input[type="number"]');
            if (!input) return;

            const action = btn.dataset.action;
            let value = parseInt(input.value, 10) || 0;
            const min = parseInt(input.min, 10) || 0;
            const max = parseInt(input.max, 10) || Infinity;

            if (action === 'increase' && value < max) {
                input.value = value + 1;
            } else if (action === 'decrease' && value > min) {
                input.value = value - 1;
            }

            input.dispatchEvent(new Event('change'));
        });
    }

    // === Init all ===
    function init() {
        initAutoHideAlerts();
        initFormsLoadingState();
        initDeleteConfirmation();
        initFilePreview();
        initSearchInput();
        initSmoothScroll();
        initNavbarToggle();
        initPriceRange();
        initFeatureCardsReveal();
        initAddToCartDelegation();
        initQuantityButtons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose helpers globally for other scripts/pages
    window.LauraciousFoodies = {
        addToCart,
        showNotification,
        updateCartCount,
        formatCurrency,
        formatDate,
        debounce
    };
})();


document.addEventListener("click", function (e) {
    const btn = e.target.closest(".load-modal");
    if (!btn) return;

    const orderId = btn.dataset.id;
    const type = btn.dataset.type; // items | details
    const url = type === "items"
        ? `/admin/order_items/${orderId}`
        : `/admin/order_details/${orderId}`;

    fetch(url)
        .then(res => res.text())
        .then(html => {
            document.getElementById("modalContent").innerHTML = html;
            const modal = new bootstrap.Modal(document.getElementById("globalModal"));
            modal.show();
        })
        .catch(err => alert("Error loading modal"));
});
