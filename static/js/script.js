// Auto-hide flash messages
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s ease';
            message.style.opacity = '0';
            setTimeout(() => message.remove(), 500);
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let valid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    valid = false;
                    field.style.borderColor = '#e74c3c';
                } else {
                    field.style.borderColor = '';
                }
            });

            if (!valid) {
                e.preventDefault();
                alert('Please fill in all required fields.');
            }
        });
    });

    // Payment modal functionality
    const payButton = document.getElementById('payButton');
    const paymentModal = document.getElementById('paymentModal');
    const confirmPayment = document.getElementById('confirmPayment');
    const cancelPayment = document.getElementById('cancelPayment');
    const paymentForm = document.getElementById('paymentForm');

    if (payButton && paymentModal) {
        // Show modal when pay button is clicked
        payButton.addEventListener('click', function() {
            paymentModal.style.display = 'flex';
        });

        // Hide modal when cancel is clicked
        if (cancelPayment) {
            cancelPayment.addEventListener('click', function() {
                paymentModal.style.display = 'none';
            });
        }

        // Submit form when payment is confirmed
        if (confirmPayment && paymentForm) {
            confirmPayment.addEventListener('click', function() {
                paymentForm.submit();
            });
        }

        // Close modal when clicking outside the modal content
        paymentModal.addEventListener('click', function(e) {
            if (e.target === paymentModal) {
                paymentModal.style.display = 'none';
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && paymentModal.style.display === 'flex') {
                paymentModal.style.display = 'none';
            }
        });
    }
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-IN');
}

// Modal utility functions
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
    }
}
