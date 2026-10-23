/**
 * Face Login with Face-API.js
 * 
 * Uses TensorFlow.js face-api for face detection and recognition
 * in the browser - no server-side dependencies needed.
 */

let modelsLoaded = false;
let faceDescriptors = [];

// Initialize face-api models
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

// Fetch all registered face descriptors from server
async function fetchFaceDescriptors() {
    try {
        const response = await fetch('/accounts/api/face-descriptors/');
        const data = await response.json();
        faceDescriptors = data.descriptors;
        console.log(`Loaded ${faceDescriptors.length} face descriptors`);
        return faceDescriptors;
    } catch (error) {
        console.error('Error fetching face descriptors:', error);
        throw error;
    }
}

// Extract face descriptor from video element
async function getFaceDescriptorFromVideo(videoElement) {
    const detection = await faceapi
        .detectSingleFace(videoElement, new faceapi.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceDescriptor();
    
    if (!detection) {
        throw new Error('No face detected');
    }
    
    return detection.descriptor;
}

// Find matching user by comparing face descriptors
function findMatchingUser(currentDescriptor, threshold = 0.6) {
    let bestMatch = null;
    let bestDistance = Infinity;
    
    for (const user of faceDescriptors) {
        const storedDescriptor = new Float32Array(user.descriptor);
        const distance = faceapi.euclideanDistance(currentDescriptor, storedDescriptor);
        
        if (distance < threshold && distance < bestDistance) {
            bestDistance = distance;
            bestMatch = user;
        }
    }
    
    return bestMatch ? { user: bestMatch, distance: bestDistance } : null;
}

// Open face login modal
async function openFaceLoginModal() {
    const modal = document.getElementById('faceLoginModal');
    if (!modal) {
        console.error('Face login modal not found');
        return;
    }
    
    modal.classList.add('active');
    
    try {
        // Load models and descriptors
        showFaceLoginStatus('Loading face recognition models...', 'info');
        await loadFaceModels();
        
        showFaceLoginStatus('Loading registered faces...', 'info');
        await fetchFaceDescriptors();
        
        if (faceDescriptors.length === 0) {
            showFaceLoginStatus('No faces registered yet. Please sign up first.', 'error');
            return;
        }
        
        // Start camera
        showFaceLoginStatus('Starting camera...', 'info');
        await startFaceLoginCamera();
        
        showFaceLoginStatus('Look at the camera', 'success');
        
    } catch (error) {
        console.error('Face login error:', error);
        showFaceLoginStatus(error.message, 'error');
    }
}

// Start camera for face login
async function startFaceLoginCamera() {
    const video = document.getElementById('faceLoginVideo');
    if (!video) {
        throw new Error('Video element not found');
    }
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user', width: 640, height: 480 }
        });
        
        video.srcObject = stream;
        await video.play();
        
        // Start face detection loop
        detectAndMatchFace(video);
        
    } catch (error) {
        throw new Error('Camera access denied. Please allow camera access.');
    }
}

// Continuously detect and match faces
async function detectAndMatchFace(video) {
    const modal = document.getElementById('faceLoginModal');
    
    // Check if modal is still active
    if (!modal || !modal.classList.contains('active')) {
        stopFaceLoginCamera();
        return;
    }
    
    try {
        const descriptor = await getFaceDescriptorFromVideo(video);
        const match = findMatchingUser(descriptor);
        
        if (match) {
            showFaceLoginStatus(`Recognized: ${match.user.name}`, 'success');
            await performFaceLogin(match.user.user_id);
            return; // Stop detection after successful login
        }
    } catch (error) {
        // No face detected or error - continue trying
        if (error.message !== 'No face detected') {
            console.error('Detection error:', error);
        }
    }
    
    // Continue detection
    setTimeout(() => detectAndMatchFace(video), 1000);
}

// Perform login with matched user
async function performFaceLogin(userId) {
    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        const response = await fetch('/accounts/api/face-login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ user_id: userId })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showFaceLoginStatus('Login successful! Redirecting...', 'success');
            setTimeout(() => {
                window.location.href = data.redirect_url;
            }, 1000);
        } else {
            showFaceLoginStatus(`Login failed: ${data.error}`, 'error');
            closeFaceLoginModal();
        }
    } catch (error) {
        showFaceLoginStatus('Login failed. Please try again.', 'error');
        console.error('Login error:', error);
    }
}

// Close face login modal
function closeFaceLoginModal() {
    const modal = document.getElementById('faceLoginModal');
    if (modal) {
        modal.classList.remove('active');
        stopFaceLoginCamera();
    }
}

// Stop camera stream
function stopFaceLoginCamera() {
    const video = document.getElementById('faceLoginVideo');
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
}

// Show status message in modal
function showFaceLoginStatus(message, type = 'info') {
    const statusEl = document.getElementById('faceLoginStatus');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `face-login-status ${type}`;
    }
}

// Initialize face login button
document.addEventListener('DOMContentLoaded', () => {
    const faceLoginBtn = document.getElementById('faceLoginBtn');
    if (faceLoginBtn) {
        faceLoginBtn.addEventListener('click', openFaceLoginModal);
    }
    
    const closeModalBtn = document.getElementById('closeFaceLoginModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeFaceLoginModal);
    }
});
