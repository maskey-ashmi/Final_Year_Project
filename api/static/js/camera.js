const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const emptyState = document.getElementById('scan-empty');
const startBtn = document.getElementById('start-camera');
const captureBtn = document.getElementById('capture');
const loadingEl = document.getElementById('scan-loading');
const shimmerEl = document.getElementById('scan-shimmer');
const resultSection = document.getElementById('result-section');
const resultPlaceholder = document.getElementById('result-placeholder');
const acneTypeEl = document.getElementById('acne-type');
const confidenceText = document.getElementById('confidence-text');
const lesionCountText = document.getElementById('lesion-count');
const rfPredictionEl = document.getElementById('rf-prediction');
const classScoresList = document.getElementById('class-scores');
const recommendedRoutineList = document.getElementById('recommended-routine-list');
const uploadInput = document.getElementById('upload-image');
const uploadBtn = document.getElementById('upload-analyze');

// Detection visualization elements
const detectionImage = document.getElementById('detection-image');
const detectionCanvas = document.getElementById('detection-canvas');
const detectionList = document.getElementById('detection-list');

let activeStream = null;
function setBusy(isBusy) {
  if (loadingEl) {
    loadingEl.classList.toggle('d-none', !isBusy);
  }
  if (shimmerEl) {
    shimmerEl.classList.toggle('d-none', !isBusy);
  }
  if (captureBtn) {
    captureBtn.disabled = isBusy || !activeStream;
  }
  if (startBtn) {
    startBtn.disabled = isBusy;
  }
  if (uploadBtn) {
    uploadBtn.disabled = isBusy || !uploadInput || !uploadInput.files || uploadInput.files.length === 0;
  }
}

function clearPreviewState() {
  if (emptyState) {
    emptyState.classList.remove('d-none');
  }
}

async function startCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert('Camera not supported in this browser.');
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { 
        width: { ideal: 1920 },
        height: { ideal: 1080 },
        facingMode: "user"
      } 
    });
    activeStream = stream;
    video.srcObject = stream;
    await video.play();
    video.classList.add('is-live');
    clearPreviewState();
    captureBtn.disabled = false;
  } catch (error) {
    console.error('Unable to access camera', error);
    alert('Could not access your camera.');
  }
}

function stopCameraPreview() {
  if (!activeStream) {
    return;
  }
  activeStream.getTracks().forEach((track) => track.stop());
  activeStream = null;
  if (video) {
    video.srcObject = null;
    video.classList.remove('is-live');
  }
  if (captureBtn) {
    captureBtn.disabled = true;
  }
}

function dataURLToBlob(dataUrl) {
  const [header, body] = dataUrl.split(',');
  const mimeMatch = header.match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : 'image/jpeg';
  const binary = atob(body);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return new Blob([bytes], { type: mime });
}

function renderDetectionVisualization(data) {
  if (!detectionImage || !detectionCanvas || !detectionList) return;

  // Clear previous detections
  detectionList.innerHTML = '';
  const ctx = detectionCanvas.getContext('2d');
  ctx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);

  const detections = data.detections || [];

  // Prefer the server-side annotated image (face ellipse + red acne boxes already burned in)
  const imageToShow = data.annotated_image || data.image_path;

  if (imageToShow) {
    detectionImage.src = '/' + imageToShow;

    if (!data.annotated_image) {
      // Canvas fallback: draw green face ellipse + red acne boxes
      detectionImage.onload = function() {
        const rect = detectionImage.getBoundingClientRect();
        detectionCanvas.width = rect.width || detectionImage.naturalWidth;
        detectionCanvas.height = rect.height || detectionImage.naturalHeight;

        const scaleX = detectionImage.naturalWidth / (rect.width || detectionImage.naturalWidth);
        const scaleY = detectionImage.naturalHeight / (rect.height || detectionImage.naturalHeight);

        ctx.clearRect(0, 0, detectionCanvas.width, detectionCanvas.height);

        // ── Green ellipse around detected face ──────────────────────────────
        if (data.face_bbox) {
          const [fx, fy, fw, fh] = data.face_bbox;
          const centerX = (fx + fw / 2) / scaleX;
          const centerY = (fy + fh / 2) / scaleY;
          const radiusX = (fw / 2) / scaleX;
          const radiusY = (fh / 2) / scaleY;

          ctx.beginPath();
          ctx.ellipse(centerX, centerY, radiusX, radiusY, 0, 0, 2 * Math.PI);
          ctx.strokeStyle = '#00cc44';
          ctx.lineWidth = 3;
          ctx.stroke();

          // Face label
          const faceLabelX = (fx / scaleX);
          const faceLabelY = (fy / scaleY) - 6;
          ctx.fillStyle = '#00cc44';
          const faceLabelW = ctx.measureText('Face').width + 8;
          ctx.fillRect(faceLabelX, faceLabelY - 16, faceLabelW, 18);
          ctx.fillStyle = '#000';
          ctx.font = 'bold 12px Arial';
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          ctx.fillText('Face', faceLabelX + 4, faceLabelY - 14);
        }

        // ── Red rectangles around each acne lesion ──────────────────────────
        detections.forEach((detection) => {
          const [x1, y1, x2, y2] = detection.bbox;
          const sx1 = x1 / scaleX;
          const sy1 = y1 / scaleY;
          const sw  = (x2 - x1) / scaleX;
          const sh  = (y2 - y1) / scaleY;

          ctx.strokeStyle = '#e53e3e';
          ctx.lineWidth = 2;
          ctx.strokeRect(sx1, sy1, sw, sh);

          ctx.fillStyle = 'rgba(229, 62, 62, 0.15)';
          ctx.fillRect(sx1, sy1, sw, sh);

          const labelText = `${detection.type} ${(detection.confidence * 100).toFixed(0)}%`;
          ctx.font = '11px Arial';
          const labelW = ctx.measureText(labelText).width + 6;
          ctx.fillStyle = '#e53e3e';
          ctx.fillRect(sx1, sy1 - 18, labelW, 18);
          ctx.fillStyle = '#fff';
          ctx.textAlign = 'left';
          ctx.textBaseline = 'top';
          ctx.fillText(labelText, sx1 + 3, sy1 - 16);
        });
      };
    } else {
      // Annotated image already has everything burned in — hide canvas overlay
      detectionImage.onload = function() {
        detectionCanvas.width = 0;
        detectionCanvas.height = 0;
      };
    }
  }

  // Build detection list
  if (detections.length === 0) {
    const item = document.createElement('div');
    item.className = 'detection-item';
    item.innerHTML = '<span class="detection-type">No lesions detected</span>';
    detectionList.appendChild(item);
  } else {
    detections.forEach((detection) => {
      const item = document.createElement('div');
      item.className = 'detection-item';

      const typeSpan = document.createElement('span');
      typeSpan.className = 'detection-type';
      typeSpan.textContent = detection.type;

      const confidenceSpan = document.createElement('span');
      confidenceSpan.className = 'detection-confidence';
      confidenceSpan.textContent = `${(detection.confidence * 100).toFixed(1)}%`;

      item.appendChild(typeSpan);
      item.appendChild(confidenceSpan);
      detectionList.appendChild(item);
    });
  }
}

function getDetectionColor(type) {
  const colors = {
    'Acne': { border: '#dc3545', background: 'rgba(220, 53, 69, 0.1)' },
    'unknown': { border: '#808080', background: 'rgba(128, 128, 128, 0.1)' }
  };
  return colors[type] || colors['unknown'];
}

function appendRoutineGroup(targetList, title, steps) {
  if (!targetList || !Array.isArray(steps) || steps.length === 0) {
    return;
  }

  const titleItem = document.createElement('li');
  titleItem.className = 'result-group-title';
  titleItem.textContent = title;
  targetList.appendChild(titleItem);

  steps.forEach((step) => {
    const item = document.createElement('li');
    item.textContent = step;
    targetList.appendChild(item);
  });
}

function renderResult(data) {
  // primary_insight comes from the API; fall back to status field
  acneTypeEl.textContent = data.primary_insight || data.status || data.acne_type || 'Unknown';

  // primary_confidence is a 0-1 float from the API
  // data.confidence is a pre-formatted string like "43.9%" – parse it if needed
  let displayConfidence;
  if (typeof data.primary_confidence === 'number') {
    displayConfidence = data.primary_confidence * 100;
  } else if (typeof data.confidence === 'string' && data.confidence.endsWith('%')) {
    displayConfidence = parseFloat(data.confidence);
  } else {
    displayConfidence = Number(data.primary_confidence ?? data.confidence ?? 0);
    if (displayConfidence <= 1) displayConfidence *= 100;
  }
  confidenceText.textContent = isNaN(displayConfidence) ? '0%' : `${displayConfidence.toFixed(1)}%`;

  // Update lesion count
  if (lesionCountText) {
    lesionCountText.textContent = data.count || 0;
  }

  // Update Random Forest prediction
  if (rfPredictionEl && data.random_forest_prediction) {
    rfPredictionEl.textContent = data.random_forest_prediction;
  } else if (rfPredictionEl) {
    rfPredictionEl.textContent = 'Not available';
  }

  classScoresList.innerHTML = '';
  // Key insights for single class
  const classScores = data.class_scores || {};
  const yoloDisplayOrder = ['Acne'];
  yoloDisplayOrder.forEach((label) => {
    const score = Number(classScores[label] ?? 0);
    const item = document.createElement('span');
    const tone = score >= 55 ? 'attention' : 'healthy';
    item.className = `insight-tag ${tone}`;
    item.innerHTML = `<i class="bi bi-record-circle"></i><span>${label} ${score.toFixed(1)}%</span>`;
    classScoresList.appendChild(item);
  });

  // Render detection visualization
  renderDetectionVisualization(data);

  // Render Recommended Routine
  if (recommendedRoutineList) {
    recommendedRoutineList.innerHTML = '';
    if (data.routine) {
      appendRoutineGroup(recommendedRoutineList, 'Morning', data.routine.morning);
      appendRoutineGroup(recommendedRoutineList, 'Evening', data.routine.evening);
      appendRoutineGroup(recommendedRoutineList, 'Weekly', data.routine.weekly);
    }
  }

  resultPlaceholder.classList.add('d-none');
  resultSection.classList.remove('d-none');
}

async function sendImage(fileOrBlob, filename) {
  const formData = new FormData();
  formData.append('image', fileOrBlob, filename);

  setBusy(true);
  resultSection.classList.add('d-none');
  resultPlaceholder.classList.remove('d-none');

  try {
    const response = await fetch('/api/predict', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin', // Include cookies for session
      headers: {
        'X-Requested-With': 'XMLHttpRequest' // Mark as AJAX request
      }
    });
    
    // Handle redirects (session expiry)
    if (response.redirected) {
      window.location.href = response.url;
      return;
    }
    
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : { error: 'Invalid response from server.' };

    if (!response.ok) {
      if (response.status === 401) {
        // Session expired - redirect to login
        window.location.href = '/login';
        return;
      }
      // Show the server's descriptive message if available
      const errMsg = payload.message || payload.error || 'Prediction failed.';
      alert(errMsg);
      return;
    }

    renderResult(payload);
  } catch (error) {
    console.error(error);
    alert('Something went wrong while analyzing the image.');
  } finally {
    setBusy(false);
  }
}

function requireSkinType() {
  // Check if skin type has been saved (selector hidden means saved)
  const skinSelectionDiv = document.getElementById('skin-type-selection');
  if (skinSelectionDiv && !skinSelectionDiv.classList.contains('d-none')) {
    // Selector still visible – skin type not yet saved
    const skinSelect = document.getElementById('select-skin-type');
    if (!skinSelect || !skinSelect.value) {
      alert('Please select and save your skin type before scanning.');
      skinSelect && skinSelect.focus();
      return false;
    }
    // Value chosen but not saved – remind user to click Save
    alert('Please click "Save Skin Type" before starting the scan.');
    return false;
  }
  return true;
}

async function captureAndSend() {
  if (!requireSkinType()) return;
  if (!activeStream || !video.videoWidth || !video.videoHeight) {
    alert('Camera is not ready yet.');
    return;
  }

  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext('2d');
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const blob = dataURLToBlob(canvas.toDataURL('image/jpeg', 1.0));
  await sendImage(blob, 'capture.jpg');
}

async function uploadAndSend() {
  if (!requireSkinType()) return;
  if (!uploadInput || !uploadInput.files || uploadInput.files.length === 0) {
    alert('Please choose an image first.');
    return;
  }

  const file = uploadInput.files[0];
  await sendImage(file, file.name || 'upload.jpg');
}

if (startBtn) {
  startBtn.addEventListener('click', (event) => {
    event.preventDefault();
    startCamera();
  });
}

if (captureBtn) {
  captureBtn.addEventListener('click', (event) => {
    event.preventDefault();
    captureAndSend();
  });
}

if (uploadInput) {
  uploadInput.addEventListener('change', () => {
    if (uploadBtn) {
      uploadBtn.disabled = !uploadInput.files || uploadInput.files.length === 0;
    }
  });
}

if (uploadBtn) {
  uploadBtn.addEventListener('click', (event) => {
    event.preventDefault();
    uploadAndSend();
  });
}

window.addEventListener('beforeunload', stopCameraPreview);

