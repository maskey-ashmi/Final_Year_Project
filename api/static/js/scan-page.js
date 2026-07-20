document.addEventListener('DOMContentLoaded', async () => {
  try {
    const session = await window.loadAppSession();
    const user = session.user || {};
    const profileReady = Boolean(user.age);

    // Update profile display
    document.getElementById('scan-profile-name').textContent = user.name || 'Skin profile';
    const ageLabel = user.age ?? 'N/A';
    const skinTypeLabel = user.skin_type ? user.skin_type[0].toUpperCase() + user.skin_type.slice(1) : 'Not set';
    document.getElementById('scan-profile-meta').textContent = `Age ${ageLabel} • ${skinTypeLabel}`;

    const alertEl = document.getElementById('scan-profile-alert');
    const startBtn = document.getElementById('start-camera');
    const uploadBtn = document.getElementById('upload-analyze');
    const skinSelectionDiv = document.getElementById('skin-type-selection');
    const saveBtn = document.getElementById('save-skin-type');
    const skinSelect = document.getElementById('select-skin-type');

    if (!profileReady) {
      // Missing age – show alert and disable scanning
      alertEl.classList.remove('d-none');
      startBtn.disabled = true;
      if (uploadBtn) uploadBtn.disabled = true;
      skinSelectionDiv.classList.remove('d-none');
    } else {
      alertEl.classList.add('d-none');
      if (user.skin_type) {
        // If they already have a skin type, show it as saved instead of requiring again on page load
        // Wait, the user said "do this after skin type is saved... and it can be changed acc to the user of they again wanna change and do analysis"
        // Also "no matter how much i click on save skin type it says alert" - this is because the selector wasn't hidden.
        skinSelectionDiv.classList.add('d-none');
        startBtn.disabled = false;
        if (uploadBtn) uploadBtn.disabled = false;
        
        const displayContainer = document.getElementById('saved-skin-type-display');
        const displaySpan = document.getElementById('display-skin-type');
        if (displayContainer && displaySpan) {
          displaySpan.textContent = user.skin_type[0].toUpperCase() + user.skin_type.slice(1);
          displayContainer.classList.remove('d-none');
        }
      } else {
        skinSelectionDiv.classList.remove('d-none');
        startBtn.disabled = true;
        if (uploadBtn) uploadBtn.disabled = true;
      }
    }

    // Pre-fill selector if user already has a skin type
    if (user.skin_type && skinSelect) {
      skinSelect.value = user.skin_type;
    }

    // Handle saving skin type
    if (saveBtn) {
      saveBtn.addEventListener('click', async () => {
        const selected = skinSelect ? skinSelect.value : '';
        if (!selected) {
          alert('Please select a skin type before continuing.');
          if (skinSelect) skinSelect.focus();
          return;
        }
        try {
          const response = await fetch('/api/update_skin_type', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ skin_type: selected }),
          });
          if (!response.ok) {
            const err = await response.json();
            alert(err.error || 'Failed to update skin type');
            return;
          }
          const data = await response.json();
          const updatedUser = data.user || data;
          const newAgeLabel = updatedUser.age ?? 'N/A';
          const newSkinLabel = updatedUser.skin_type
            ? updatedUser.skin_type[0].toUpperCase() + updatedUser.skin_type.slice(1)
            : 'Not set';
          document.getElementById('scan-profile-name').textContent = updatedUser.name || 'Skin profile';
          document.getElementById('scan-profile-meta').textContent = `Age ${newAgeLabel} • ${newSkinLabel}`;

          // Hide selector, enable scanning, show saved display
          skinSelectionDiv.classList.add('d-none');
          alertEl.classList.add('d-none');
          startBtn.disabled = false;
          if (uploadBtn) uploadBtn.disabled = false;
          
          const displayContainer = document.getElementById('saved-skin-type-display');
          const displaySpan = document.getElementById('display-skin-type');
          if (displayContainer && displaySpan) {
            displaySpan.textContent = newSkinLabel;
            displayContainer.classList.remove('d-none');
          }
          
          // Also enable capture if video is running
          const captureBtn = document.getElementById('capture');
          const video = document.getElementById('video');
          if (captureBtn && video && video.srcObject) {
            captureBtn.disabled = false;
          }
        } catch (e) {
          console.error(e);
          alert('Error updating skin type');
        }
      });
    }

    const changeBtn = document.getElementById('change-skin-type');
    if (changeBtn) {
      changeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const displayContainer = document.getElementById('saved-skin-type-display');
        if (displayContainer) displayContainer.classList.add('d-none');
        skinSelectionDiv.classList.remove('d-none');
        startBtn.disabled = true;
        if (uploadBtn) uploadBtn.disabled = true;
        const captureBtn = document.getElementById('capture');
        if (captureBtn) captureBtn.disabled = true;
      });
    }
  } catch (error) {
    console.error(error);
  }
});
