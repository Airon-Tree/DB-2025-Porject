// Wait for DOM to load
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Image preview for pin creation
    const imageInput = document.getElementById('image');
    if (imageInput) {
        imageInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    // Create preview element if it doesn't exist
                    let preview = document.getElementById('image-preview');
                    if (!preview) {
                        preview = document.createElement('div');
                        preview.id = 'image-preview';
                        preview.className = 'mt-3 text-center';
                        preview.innerHTML = '<img src="" class="img-fluid" style="max-height: 300px;" />';
                        imageInput.parentNode.appendChild(preview);
                    }
                    // Update preview image
                    const img = preview.querySelector('img');
                    img.src = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // Confirm before deleting
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                event.preventDefault();
            }
        });
    });

    // Toggle URL/Upload input based on selection
    const pinSourceRadios = document.querySelectorAll('input[name="pin_source"]');
    if (pinSourceRadios.length > 0) {
        pinSourceRadios.forEach(function(radio) {
            radio.addEventListener('change', function() {
                const uploadSection = document.getElementById('upload-section');
                const urlSection = document.getElementById('url-section');

                if (this.value === 'upload') {
                    uploadSection.style.display = 'block';
                    urlSection.style.display = 'none';
                } else {
                    uploadSection.style.display = 'none';
                    urlSection.style.display = 'block';
                }
            });
        });
    }

    // Masonry layout for pins (simple implementation)
    const pinsContainer = document.getElementById('pins-container');
    if (pinsContainer) {
        // Simple masonry-like layout adjustment
        window.addEventListener('load', function() {
            const pins = pinsContainer.querySelectorAll('.col-lg-3');
            const columnCount = 4;

            // Only apply on larger screens
            if (window.innerWidth >= 992 && pins.length > columnCount) {
                // Arrange pins in columns
                for (let i = 0; i < pins.length; i++) {
                    pins[i].style.order = (i % columnCount) + Math.floor(i / columnCount) * columnCount;
                }
            }
        });
    }
});