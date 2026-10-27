/**
 * Face Enrollment for Face Login
 */

let modelsLoaded = false;
let videoStream = null;
let enrollmentSession = 0;

function enrollmentActive(session) {
    return session === enrollmentSession &&
        document.getElementById('faceEnrollModal')?.classList.contains('active');
}

// Load face-api models
async function loadFaceModels() {
    if (modelsLoaded) return;
    
    const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';
    
    try {
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
            faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
        ]);
        modelsLoaded = true;
        console.log('Face recognition models loaded');
    } catch (error) {
        console.error('Error loading face models:', error);
        throw new Error('Failed to load face recognition models');
    }
}

// Open face enrollment modal
async function openFaceEnrollModal() {
    const modal = document.getElementById('faceEnrollModal');
    if (!modal || modal.classList.contains('active')) return;
    
    window.MediConnectDialog.open(modal);
    const session = ++enrollmentSession;
    document.getElementById('captureFaceBtn').disabled = false;
    
    try {
        showEnrollStatus('Loading face recognition models...', 'info');
        await loadFaceModels();
        if (!enrollmentActive(session)) return;
        
        showEnrollStatus('Starting camera...', 'info');
        await startEnrollCamera(session);
        if (!enrollmentActive(session)) return;
        
        showEnrollStatus('Position your face in the center', 'info');
        
    } catch (error) {
        console.error('Enrollment error:', error);
        if (enrollmentActive(session)) showEnrollStatus(error.message, 'error');
    }
}

// Start camera for enrollment
async function startEnrollCamera(session) {
    const video = document.getElementById('faceEnrollVideo');
    if (!video) throw new Error('Video element not found');
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 }
        });
        if (!enrollmentActive(session)) {
            stream.getTracks().forEach(track => track.stop());
            return;
        }
        videoStream = stream;
        
        video.srcObject = videoStream;
        await video.play();
        
    } catch (error) {
        throw new Error('Camera access denied. Please allow camera access.');
    }
}

// Capture face and enroll
async function captureFace() {
    const session = enrollmentSession;
    const video = document.getElementById('faceEnrollVideo');
    const canvas = document.getElementById('faceEnrollCanvas');
    const captureBtn = document.getElementById('captureFaceBtn');
    
    if (!video || !canvas || !enrollmentActive(session)) return;
    
    try {
        captureBtn.disabled = true;
        showEnrollStatus('Detecting face...', 'info');
        
        // Detect face and get descriptor
        const detection = await faceapi
            .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks()
            .withFaceDescriptor();
        if (!enrollmentActive(session)) return;
        
        if (!detection) {
            throw new Error('No face detected. Please ensure your face is clearly visible.');
        }
        
        showEnrollStatus('Face detected! Processing...', 'info');
        
        // Capture image
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        
        // Draw un-mirrored image
        ctx.save();
        ctx.scale(-1, 1);
        ctx.drawImage(video, -canvas.width, 0, canvas.width, canvas.height);
        ctx.restore();
        
        const imageData = canvas.toDataURL('image/jpeg', 0.9);
        const descriptor = Array.from(detection.descriptor);
        
        // Send to server
        showEnrollStatus('Saving face data...', 'info');
        await enrollFaceOnServer(descriptor, imageData);
        if (!enrollmentActive(session)) return;
        
        showEnrollStatus('Face enrolled successfully! ✓', 'success');
        
        setTimeout(() => {
            if (!enrollmentActive(session)) return;
            closeFaceEnrollModal();
            location.reload(); // Refresh to show enrolled status
        }, 2000);
        
    } catch (error) {
        if (enrollmentActive(session)) showEnrollStatus(error.message, 'error');
        console.error('Capture error:', error);
    } finally {
        if (enrollmentActive(session)) captureBtn.disabled = false;
    }
}

// Send face data to server
async function enrollFaceOnServer(descriptor, imageData) {
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const response = await fetch('/accounts/api/enroll-face/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            descriptor: descriptor,
            image_data: imageData
        })
    });
    
    const data = await response.json();
    
    if (!data.success) {
        throw new Error(data.error || 'Failed to enroll face');
    }
}

// Close enrollment modal
function closeFaceEnrollModal() {
    const modal = document.getElementById('faceEnrollModal');
    if (modal) {
        window.MediConnectDialog.close(modal);
    }
}

// Stop camera stream
function stopEnrollCamera() {
    const video = document.getElementById('faceEnrollVideo');
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
}

// Show status message
function showEnrollStatus(message, type = 'info') {
    const statusEl = document.getElementById('faceEnrollStatus');
    const errorEl = document.getElementById('faceEnrollError');
    if (statusEl) {
        statusEl.textContent = type === 'error' ? '' : message;
        statusEl.className = `face-login-status ${type}`;
    }
    if (errorEl) errorEl.textContent = type === 'error' ? message : '';
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('faceEnrollModal')?.addEventListener('mc:dialog-close', () => {
        enrollmentSession++;
        stopEnrollCamera();
    });
    const enrollBtn = document.getElementById('enrollFaceBtn');
    const updateBtn = document.getElementById('updateFaceBtn');
    const captureBtn = document.getElementById('captureFaceBtn');
    const closeBtn = document.getElementById('closeFaceEnrollModal');
    
    if (enrollBtn) {
        enrollBtn.addEventListener('click', openFaceEnrollModal);
    }
    
    if (updateBtn) {
        updateBtn.addEventListener('click', openFaceEnrollModal);
    }
    
    if (captureBtn) {
        captureBtn.addEventListener('click', captureFace);
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeFaceEnrollModal);
    }
});
