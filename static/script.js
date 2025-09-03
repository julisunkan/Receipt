// Smart Receipt Generator JavaScript

let itemCounter = 0;
let signaturePad;
let currentCurrencySymbol = '$';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Set current date
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('receiptDate').value = today;
    
    // Initialize signature pad
    initializeSignaturePad();
    
    // Add first item row
    addItem();
    
    // Initialize currency symbol
    updateCurrencySymbol();
    
    // Load saved business settings from localStorage
    loadBusinessSettings();
    
    // Enable Bootstrap form validation
    enableFormValidation();
});

// Initialize signature pad
function initializeSignaturePad() {
    const canvas = document.getElementById('signatureCanvas');
    signaturePad = new SignaturePad(canvas, {
        backgroundColor: 'rgba(255, 255, 255, 1)',
        penColor: 'rgb(0, 0, 0)',
        velocityFilterWeight: 0.7,
        minWidth: 0.5,
        maxWidth: 2.5,
        throttle: 16,
        minPointDistance: 5,
    });

    // Resize canvas for responsiveness
    function resizeCanvas() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const rect = canvas.getBoundingClientRect();
        canvas.width = rect.width * ratio;
        canvas.height = rect.height * ratio;
        canvas.getContext('2d').scale(ratio, ratio);
        signaturePad.clear();
    }

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();
}

// Clear signature
function clearSignature() {
    signaturePad.clear();
}

// Add item to the items table
function addItem() {
    itemCounter++;
    const tbody = document.getElementById('itemsBody');
    const row = document.createElement('tr');
    row.id = `item-${itemCounter}`;
    
    row.innerHTML = `
        <td>
            <input type="text" class="form-control" name="item_name_${itemCounter}" placeholder="Enter item name" required onchange="calculateTotals()">
        </td>
        <td>
            <input type="number" class="form-control" name="item_quantity_${itemCounter}" min="1" step="1" value="1" required onchange="calculateTotals()">
        </td>
        <td>
            <input type="number" class="form-control" name="item_price_${itemCounter}" min="0" step="0.01" placeholder="0.00" required onchange="calculateTotals()">
        </td>
        <td class="text-end">
            <span class="item-total">${currentCurrencySymbol}0.00</span>
        </td>
        <td class="text-center">
            <button type="button" class="btn btn-outline-danger btn-sm" onclick="removeItem(${itemCounter})" title="Remove item">
                <i class="fas fa-trash"></i>
            </button>
        </td>
    `;
    
    tbody.appendChild(row);
    calculateTotals();
}

// Remove item from the items table
function removeItem(itemId) {
    const row = document.getElementById(`item-${itemId}`);
    if (row) {
        row.remove();
        calculateTotals();
    }
    
    // Ensure at least one item row exists
    const tbody = document.getElementById('itemsBody');
    if (tbody.children.length === 0) {
        addItem();
    }
}

// Calculate totals
function calculateTotals() {
    const tbody = document.getElementById('itemsBody');
    const rows = tbody.querySelectorAll('tr');
    let subtotal = 0;
    
    // Calculate subtotal
    rows.forEach(row => {
        const quantityInput = row.querySelector('input[name*="quantity"]');
        const priceInput = row.querySelector('input[name*="price"]');
        const totalSpan = row.querySelector('.item-total');
        
        if (quantityInput && priceInput && totalSpan) {
            const quantity = parseFloat(quantityInput.value) || 0;
            const price = parseFloat(priceInput.value) || 0;
            const itemTotal = quantity * price;
            
            totalSpan.textContent = `${currentCurrencySymbol}${formatCurrency(itemTotal)}`;
            subtotal += itemTotal;
        }
    });
    
    // Get tax and discount values
    const taxRate = parseFloat(document.getElementById('taxRate').value) || 0;
    const discount = parseFloat(document.getElementById('discount').value) || 0;
    
    // Calculate tax and grand total
    const taxAmount = (subtotal * taxRate) / 100;
    const grandTotal = subtotal + taxAmount - discount;
    
    // Update display
    document.getElementById('subtotal').textContent = `${currentCurrencySymbol}${formatCurrency(subtotal)}`;
    document.getElementById('taxAmount').textContent = `${currentCurrencySymbol}${formatCurrency(taxAmount)}`;
    document.getElementById('discountAmount').textContent = `${currentCurrencySymbol}${formatCurrency(discount)}`;
    document.getElementById('grandTotal').textContent = `${currentCurrencySymbol}${formatCurrency(Math.max(0, grandTotal))}`;
}

// Update currency symbol when currency changes
function updateCurrencySymbol() {
    const currencySelect = document.getElementById('currency');
    const selectedOption = currencySelect.options[currencySelect.selectedIndex];
    currentCurrencySymbol = selectedOption.getAttribute('data-symbol') || '$';
    calculateTotals();
}

// Currency selector change handler
document.getElementById('currency').addEventListener('change', updateCurrencySymbol);

// Upload business logo
async function uploadLogo(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('logo', input.files[0]);
        
        try {
            const response = await fetch('/upload_logo', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.filename) {
                document.getElementById('logoPreview').style.display = 'block';
                document.getElementById('logoImg').src = result.url;
                document.getElementById('logoFilename').value = result.filename;
                showToast('Logo uploaded successfully!', 'success');
            } else {
                showToast('Error uploading logo: ' + result.error, 'danger');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showToast('Error uploading logo', 'danger');
        }
    }
}

// Generate receipt PDF
async function generateReceipt() {
    // Validate form
    const form = document.getElementById('receiptForm');
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        showToast('Please fill in all required fields', 'warning');
        return;
    }
    
    // Check if there are items
    const itemRows = document.getElementById('itemsBody').querySelectorAll('tr');
    if (itemRows.length === 0) {
        showToast('Please add at least one item', 'warning');
        return;
    }
    
    // Validate items
    let hasValidItems = false;
    for (let row of itemRows) {
        const name = row.querySelector('input[name*="name"]').value.trim();
        const quantity = parseFloat(row.querySelector('input[name*="quantity"]').value) || 0;
        const price = parseFloat(row.querySelector('input[name*="price"]').value) || 0;
        
        if (name && quantity > 0 && price >= 0) {
            hasValidItems = true;
            break;
        }
    }
    
    if (!hasValidItems) {
        showToast('Please add at least one valid item with name, quantity, and price', 'warning');
        return;
    }
    
    // Show loading modal
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    loadingModal.show();
    
    try {
        // Collect form data
        const formData = collectFormData();
        
        // Generate receipt
        const response = await fetch('/generate_receipt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Save receipt to history
            saveToHistory(formData);
            
            // Save business settings
            saveBusinessSettings(formData);
            
            // Trigger server-side download
            const downloadLink = document.createElement('a');
            downloadLink.href = `/download_receipt/${result.receipt_id}`;
            downloadLink.download = `receipt_${result.receipt_id}.pdf`;
            downloadLink.style.display = 'none';
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
            
            showToast('Receipt generated successfully!<br><small class="text-muted mt-2 d-block"><i class="fas fa-clock me-1"></i>Note: Files will be automatically deleted after 1 minute for security.</small>', 'success');
            
            // Generate new receipt ID for next receipt
            document.getElementById('receiptId').value = generateReceiptId();
        } else {
            showToast('Error generating receipt: ' + result.error, 'danger');
        }
    } catch (error) {
        console.error('Generation error:', error);
        showToast('Error generating receipt', 'danger');
    } finally {
        loadingModal.hide();
    }
}

// Collect form data
function collectFormData() {
    const data = {
        // Business details
        business_name: document.getElementById('businessName').value,
        business_address: document.getElementById('businessAddress').value,
        business_email: document.getElementById('businessEmail').value,
        business_phone: document.getElementById('businessPhone').value,
        logo_filename: document.getElementById('logoFilename').value,
        
        // Client details
        client_name: document.getElementById('clientName').value,
        client_address: document.getElementById('clientAddress').value,
        client_email: document.getElementById('clientEmail').value,
        client_phone: document.getElementById('clientPhone').value,
        
        // Receipt details
        receipt_id: document.getElementById('receiptId').value,
        date: document.getElementById('receiptDate').value,
        currency_code: document.getElementById('currency').value,
        currency_symbol: currentCurrencySymbol,
        tax_rate: document.getElementById('taxRate').value,
        discount: document.getElementById('discount').value,
        payment_status: document.getElementById('paymentStatus').value,
        notes: document.getElementById('notes').value,
        
        // Items
        items: [],
        
        // Signature
        signature: signaturePad.isEmpty() ? null : signaturePad.toDataURL()
    };
    
    // Collect items
    const itemRows = document.getElementById('itemsBody').querySelectorAll('tr');
    itemRows.forEach(row => {
        const name = row.querySelector('input[name*="name"]').value.trim();
        const quantity = parseFloat(row.querySelector('input[name*="quantity"]').value) || 0;
        const price = parseFloat(row.querySelector('input[name*="price"]').value) || 0;
        
        if (name && quantity > 0) {
            data.items.push({ name, quantity, price });
        }
    });
    
    // Calculate totals
    const subtotal = data.items.reduce((sum, item) => sum + (item.quantity * item.price), 0);
    const taxAmount = (subtotal * parseFloat(data.tax_rate)) / 100;
    const discount = parseFloat(data.discount) || 0;
    const grandTotal = subtotal + taxAmount - discount;
    
    data.subtotal = subtotal.toFixed(2);
    data.tax_amount = taxAmount.toFixed(2);
    data.grand_total = Math.max(0, grandTotal).toFixed(2);
    
    return data;
}

// Generate receipt ID
function generateReceiptId() {
    const timestamp = Date.now().toString(36);
    const random = Math.random().toString(36).substr(2, 5);
    return `RCP-${timestamp}${random}`.toUpperCase();
}

// Export business settings
function exportBusinessSettings() {
    const businessData = {
        business_name: document.getElementById('businessName').value,
        business_address: document.getElementById('businessAddress').value,
        business_email: document.getElementById('businessEmail').value,
        business_phone: document.getElementById('businessPhone').value,
        logo_filename: document.getElementById('logoFilename').value
    };
    
    fetch('/export_business_settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(businessData)
    })
    .then(response => response.blob())
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'business_settings.json';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showToast('Business settings exported successfully!', 'success');
    })
    .catch(error => {
        console.error('Export error:', error);
        showToast('Error exporting business settings', 'danger');
    });
}

// Import business settings
function importBusinessSettings(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const settings = JSON.parse(e.target.result);
            
            // Fill business fields
            document.getElementById('businessName').value = settings.business_name || '';
            document.getElementById('businessAddress').value = settings.business_address || '';
            document.getElementById('businessEmail').value = settings.business_email || '';
            document.getElementById('businessPhone').value = settings.business_phone || '';
            
            if (settings.logo_filename) {
                document.getElementById('logoFilename').value = settings.logo_filename;
                document.getElementById('logoPreview').style.display = 'block';
                document.getElementById('logoImg').src = `/static/uploads/${settings.logo_filename}`;
            }
            
            showToast('Business settings imported successfully!', 'success');
        } catch (error) {
            console.error('Import error:', error);
            showToast('Error importing business settings: Invalid file format', 'danger');
        }
    };
    reader.readAsText(file);
}

// Save business settings to localStorage
function saveBusinessSettings(data) {
    const businessSettings = {
        business_name: data.business_name,
        business_address: data.business_address,
        business_email: data.business_email,
        business_phone: data.business_phone,
        logo_filename: data.logo_filename
    };
    
    localStorage.setItem('businessSettings', JSON.stringify(businessSettings));
}

// Load business settings from localStorage
function loadBusinessSettings() {
    const saved = localStorage.getItem('businessSettings');
    if (saved) {
        try {
            const settings = JSON.parse(saved);
            document.getElementById('businessName').value = settings.business_name || '';
            document.getElementById('businessAddress').value = settings.business_address || '';
            document.getElementById('businessEmail').value = settings.business_email || '';
            document.getElementById('businessPhone').value = settings.business_phone || '';
            
            if (settings.logo_filename) {
                document.getElementById('logoFilename').value = settings.logo_filename;
                document.getElementById('logoPreview').style.display = 'block';
                document.getElementById('logoImg').src = `/static/uploads/${settings.logo_filename}`;
            }
        } catch (error) {
            console.error('Error loading saved settings:', error);
        }
    }
}

// Save receipt to history
function saveToHistory(receiptData) {
    let history = JSON.parse(localStorage.getItem('receiptHistory') || '[]');
    
    // Add current receipt to history
    history.unshift({
        id: receiptData.receipt_id,
        date: receiptData.date,
        client: receiptData.client_name,
        total: receiptData.grand_total,
        currency: receiptData.currency_symbol,
        status: receiptData.payment_status,
        timestamp: new Date().toISOString()
    });
    
    // Keep only last 50 receipts
    history = history.slice(0, 50);
    
    localStorage.setItem('receiptHistory', JSON.stringify(history));
}

// Show toast notification
function showToast(message, type = 'info') {
    // Remove any existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create toast element
    const toastHtml = `
        <div class="toast position-fixed top-0 end-0 m-3" role="alert" style="z-index: 9999;">
            <div class="toast-header">
                <strong class="me-auto text-${type}">
                    <i class="fas ${getToastIcon(type)} me-2"></i>
                    ${getToastTitle(type)}
                </strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">${message}</div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', toastHtml);
    
    const toastElement = document.querySelector('.toast:last-child');
    const toast = new bootstrap.Toast(toastElement);
    toast.show();
    
    // Auto remove after showing
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Get toast icon based on type
function getToastIcon(type) {
    const icons = {
        success: 'fa-check-circle',
        warning: 'fa-exclamation-triangle',
        danger: 'fa-times-circle',
        info: 'fa-info-circle'
    };
    return icons[type] || icons.info;
}

// Get toast title based on type
function getToastTitle(type) {
    const titles = {
        success: 'Success',
        warning: 'Warning',
        danger: 'Error',
        info: 'Information'
    };
    return titles[type] || titles.info;
}

// Enable Bootstrap form validation
function enableFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// Print receipt functionality
function printReceipt() {
    window.print();
}

// Format currency with thousand separators
function formatCurrency(amount) {
    return parseFloat(amount).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+Enter to generate receipt
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        generateReceipt();
    }
    
    // Ctrl+N to add new item
    if (e.ctrlKey && e.key === 'n') {
        e.preventDefault();
        addItem();
    }
});
