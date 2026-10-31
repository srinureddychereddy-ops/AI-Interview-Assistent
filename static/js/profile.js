document.addEventListener('DOMContentLoaded', function () {
    // Profile Picture Preview
    const container = document.querySelector('.profile-picture-container');
    const preview = document.getElementById('profilePicturePreview');
    const input = document.getElementById('profilePictureInput');
    const removeBtn = document.getElementById('removeProfilePictureBtn');
    const removeInput = document.getElementById('removeProfilePictureInput');

    if (container && input && preview) {
        container.addEventListener('click', () => input.click());

        input.addEventListener('change', function() {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.src = e.target.result;
                    // If a new image is selected, ensure the 'remove' flag is not set
                    if(removeInput) removeInput.value = '0';
                }
                reader.readAsDataURL(input.files[0]);
            }
        });
    }
    
    if (removeBtn && preview && removeInput) {
        removeBtn.addEventListener('click', () => {
            // Revert to default image on the frontend
            preview.src = '/static/uploads/profile/default.png';
            // Clear the file input
            input.value = '';
            // Set hidden input to signal removal on the backend
            removeInput.value = '1';
        });
    }

    // Resume Filename Display
    const resumeInput = document.getElementById('resumeUploadInput');
    const resumeFilenameEl = document.getElementById('resumeFilename');

    if (resumeInput && resumeFilenameEl) {
        resumeInput.addEventListener('change', function() {
            if (this.files && this.files.length > 0) {
                resumeFilenameEl.textContent = this.files[0].name;
            }
        });
    }

    // Bootstrap form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});