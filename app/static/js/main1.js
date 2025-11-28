// Add to cart functionality
function addToCart(itemId, quantity = 1) {
    fetch('/orders/add_to_cart', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `item_id=${itemId}&quantity=${quantity}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Item added to cart!', 'success');
            updateCartCount();
        } else {
            showNotification('Error adding item to cart', 'error');
        }
    });
}

// Show notification
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// Update cart count
// function updateCartCount() {
//     fetch('/orders/cart_count')
//     .then(response => response.json())
//     .then(data => {
//         const cartBadge = document.querySelector('.cart-count');
//         if (cartBadge) {
//             cartBadge.textContent = data.count;
//         }
//     });
// }

function updateCartCount() {
    fetch('/orders/cart_count')
    .then(r => r.json())
    .then(data => {
        const cartBadge = document.querySelector('.cart-count');
        if (cartBadge) {
            cartBadge.textContent = data.count;
            cartBadge.classList.add("pulse");
            setTimeout(() => cartBadge.classList.remove("pulse"), 300);
        }
    });
}

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    });

    // Add loading state to forms
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
                submitBtn.disabled = true;
            }
        });
    });

    // Confirm before deleting
    const deleteButtons = document.querySelectorAll('.btn-danger');
    deleteButtons.forEach(btn => {
        if (btn.textContent.includes('Delete')) {
            btn.addEventListener('click', function(e) {
                if (!confirm('Are you sure you want to delete this item?')) {
                    e.preventDefault();
                }
            });
        }
    });

    // Image preview for file uploads
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const preview = document.getElementById(this.dataset.preview);
            if (preview && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                };
                reader.readAsDataURL(this.files[0]);
            }
        });
    });

    // Real-time search functionality
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Implement search functionality here
                console.log('Searching for:', this.value);
            }, 300);
        });
    }

    // Smooth scrolling for anchor links
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Responsive navigation toggle
    const navbarToggler = document.querySelector('.navbar-toggler');
    const navbarCollapse = document.querySelector('.navbar-collapse');
    
    if (navbarToggler && navbarCollapse) {
        navbarToggler.addEventListener('click', function() {
            navbarCollapse.classList.toggle('show');
        });
    }

    // Price range slider (if exists)
    const priceRange = document.getElementById('price-range');
    const priceDisplay = document.getElementById('price-display');
    
    if (priceRange && priceDisplay) {
        priceRange.addEventListener('input', function() {
            priceDisplay.textContent = `$0 - $${this.value}`;
        });
    }

    // Quantity buttons functionality
    document.addEventListener("click", function (e) {
        if (!e.target.closest(".quantity-btn")) return;
    
        const btn = e.target.closest(".quantity-btn");
        const input = btn.parentElement.querySelector('input[type="number"]');
        const action = btn.dataset.action;
    
        let value = parseInt(input.value);
    
        if (action === "increase" && value < parseInt(input.max)) {
            input.value = value + 1;
        } 
        if (action === "decrease" && value > parseInt(input.min)) {
            input.value = value - 1;
        }
    
        input.dispatchEvent(new Event('change'));
    });
    

    // Add to cart animation
    const addToCartButtons = document.querySelectorAll('.add-to-cart-btn');
    addToCartButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Add animation class
            this.classList.add('btn-loading');
            
            // Create flying animation to cart
            const rect = this.getBoundingClientRect();
            const flyingItem = document.createElement('div');
            flyingItem.innerHTML = '<i class="fas fa-shopping-cart"></i>';
            flyingItem.style.position = 'fixed';
            flyingItem.style.left = rect.left + 'px';
            flyingItem.style.top = rect.top + 'px';
            flyingItem.style.zIndex = '9999';
            flyingItem.style.transition = 'all 0.8s ease-in-out';
            
            document.body.appendChild(flyingItem);
            
            // Animate to cart icon
            const cartIcon = document.querySelector('.navbar .fa-shopping-cart');
            if (cartIcon) {
                const cartRect = cartIcon.getBoundingClientRect();
                setTimeout(() => {
                    flyingItem.style.left = cartRect.left + 'px';
                    flyingItem.style.top = cartRect.top + 'px';
                    flyingItem.style.transform = 'scale(0.5)';
                    flyingItem.style.opacity = '0';
                }, 100);
                
                setTimeout(() => {
                    flyingItem.remove();
                    this.classList.remove('btn-loading');
                }, 900);
            }
        });
    });
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for use in other scripts
window.LauraciousFoodies = {
    addToCart,
    showNotification,
    updateCartCount,
    formatCurrency,
    formatDate,
    debounce
};

// document.addEventListener('DOMContentLoaded', () => {
//     document.body.addEventListener('submit', async (e) => {
//       const form = e.target.closest('.add-to-cart-form');
//       if (!form) return;
  
//       e.preventDefault();                               // stop normal submit
//       const data = new FormData(form);
//       await fetch("{{ url_for('orders.add_to_cart') }}", {
//         method: 'POST',
//         body: data
//       });
//       location.reload();                               // or update DOM manually
//     });
//   });


document.body.addEventListener('submit', async (e) => {
    const form = e.target.closest('.add-to-cart-form');
    if (!form) return;

    e.preventDefault();
    const data = new FormData(form);
    const response = await fetch(form.action, { method: 'POST', body: data });
    const result = await response.json();

    if (result.success) {
        // Change the button to "View Cart"
        const btn = form.querySelector('button');
        btn.outerHTML = `<a href="/orders/cart" class="btn btn-success btn-add-cart">
                            <i class="fas fa-check me-2"></i> View Cart
                         </a>`;
        updateCartCount();
        showNotification('Item added to cart!', 'success');
    } else {
        showNotification('Error adding item to cart', 'error');
    }
});