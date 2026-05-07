// PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.189/pdf.worker.min.js';

// API URL
const API_URL = 'http://localhost:8000';

// Estado de la aplicación
let sessionId = null;
let pdfDoc = null;
let currentPage = 1;
let scale = 1.5;
let canvas = document.getElementById('pdfCanvas');
let ctx = canvas.getContext('2d');
let firmaPosition = { x: 50, y: 80, page: 0 };
let pdfDimensions = { width: 0, height: 0 };
let isDrawingPreview = false;

// Elementos DOM
const certInput = document.getElementById('certInput');
const selectCertBtn = document.getElementById('selectCertBtn');
const certName = document.getElementById('certName');
const passwordInput = document.getElementById('passwordInput');
const verifyBtn = document.getElementById('verifyBtn');
const certInfo = document.getElementById('certInfo');
const pdfInput = document.getElementById('pdfInput');
const selectPdfBtn = document.getElementById('selectPdfBtn');
const pdfName = document.getElementById('pdfName');
const signBtn = document.getElementById('signBtn');
const previewBtn = document.getElementById('previewBtn');
const positionInfo = document.getElementById('positionInfo');
const statusDiv = document.getElementById('status');
const zoomInBtn = document.getElementById('zoomInBtn');
const zoomOutBtn = document.getElementById('zoomOutBtn');
const pageNumSpan = document.getElementById('pageNum');
const pageCountSpan = document.getElementById('pageCount');
const previewModal = document.getElementById('previewModal');
const previewImage = document.getElementById('previewImage');
const confirmPositionBtn = document.getElementById('confirmPositionBtn');
const closeModal = document.querySelector('.close');

// Mostrar mensaje de estado
function showStatus(message, type = 'info') {
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    setTimeout(() => {
        if (statusDiv.className === `status-message ${type}`) {
            statusDiv.style.display = 'none';
            statusDiv.style.display = 'block';
        }
    }, 5000);
}

// Paso 1: Seleccionar certificado
selectCertBtn.addEventListener('click', () => certInput.click());

certInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    certName.textContent = file.name;
    
    const formData = new FormData();
    formData.append('cert', file);
    
    showStatus('Subiendo certificado...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/upload-cert`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            sessionId = data.session_id;
            showStatus('Certificado cargado correctamente', 'success');
            passwordInput.disabled = false;
            verifyBtn.disabled = false;
        } else {
            showStatus(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`Error de conexión: ${error.message}`, 'error');
    }
});

// Paso 2: Verificar certificado
verifyBtn.addEventListener('click', async () => {
    const password = passwordInput.value;
    
    if (!password) {
        showStatus('Ingrese la contraseña', 'error');
        return;
    }
    
    if (!sessionId) {
        showStatus('Primero cargue el certificado', 'error');
        return;
    }
    
    showStatus('Verificando certificado...', 'info');
    
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('password', password);
    
    try {
        const response = await fetch(`${API_URL}/verify-cert`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showStatus(`✅ Certificado válido - ${data.firmante}`, 'success');
            certInfo.innerHTML = `
                <strong>${data.firmante}</strong><br>
                Vigente hasta: ${data.expiracion}<br>
                ${data.vigente ? '✅ VIGENTE' : '❌ VENCIDO'}
            `;
            selectPdfBtn.disabled = false;
        } else {
            showStatus(`Error: ${data.detail || 'Contraseña incorrecta'}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
});

// Paso 3: Seleccionar PDF
selectPdfBtn.addEventListener('click', () => pdfInput.click());

pdfInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    pdfName.textContent = file.name;
    
    if (!sessionId) {
        showStatus('Primero cargue el certificado', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('pdf', file);
    formData.append('session_id', sessionId);
    
    showStatus('Cargando PDF...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/upload-pdf`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showStatus('PDF cargado correctamente', 'success');
            
            // Cargar PDF en el visor
            const arrayBuffer = await file.arrayBuffer();
            pdfDoc = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
            pageCountSpan.textContent = pdfDoc.numPages;
            currentPage = 1;
            pageNumSpan.textContent = currentPage;
            
            renderPage(currentPage);
            
            zoomInBtn.disabled = false;
            zoomOutBtn.disabled = false;
            previewBtn.disabled = false;
            signBtn.disabled = false;
        } else {
            showStatus(`Error: ${data.detail}`, 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
});

// Renderizar página del PDF
async function renderPage(pageNum) {
    if (!pdfDoc) return;
    
    const page = await pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: scale });
    
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    
    pdfDimensions.width = viewport.width;
    pdfDimensions.height = viewport.height;
    
    const renderContext = {
        canvasContext: ctx,
        viewport: viewport
    };
    
    await page.render(renderContext).promise;
    
    // Actualizar posición de la firma (conversión de coordenadas)
    firmaPosition.page = pageNum - 1;
}

// Evento de clic en el canvas para posicionar la firma
canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    let x = (e.clientX - rect.left) * scaleX;
    let y = canvas.height - ((e.clientY - rect.top) * scaleY);
    
    // Ajustar límites
    x = Math.max(20, Math.min(x, canvas.width - 300));
    y = Math.max(20, Math.min(y, canvas.height - 120));
    
    firmaPosition = {
        x: x / scale,
        y: y / scale,
        page: currentPage - 1
    };
    
    positionInfo.innerHTML = `📍 Posición: X=${Math.round(firmaPosition.x)}, Y=${Math.round(firmaPosition.y)}, Página=${currentPage}`;
    
    // Mostrar preview
    showSignaturePreview();
    
    // Enviar posición al backend
    updatePositionBackend();
});

function showSignaturePreview() {
    // Eliminar preview anterior
    const oldPreview = document.getElementById('dynamicPreview');
    if (oldPreview) oldPreview.remove();
    
    // Crear nuevo preview
    const preview = document.createElement('div');
    preview.id = 'dynamicPreview';
    preview.className = 'signature-preview';
    preview.style.left = `${(firmaPosition.x * scale)}px`;
    preview.style.bottom = `${(firmaPosition.y * scale)}px`;
    preview.style.width = '280px';
    preview.style.height = '100px';
    preview.innerHTML = '<div class="preview-content">📍 Firma aquí</div>';
    
    document.getElementById('pdfCanvasContainer').appendChild(preview);
}

async function updatePositionBackend() {
    if (!sessionId) return;
    
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('x', firmaPosition.x);
    formData.append('y', firmaPosition.y);
    formData.append('page', firmaPosition.page);
    
    try {
        await fetch(`${API_URL}/set-position`, {
            method: 'POST',
            body: formData
        });
    } catch (error) {
        console.error('Error al actualizar posición:', error);
    }
}

// Zoom
zoomInBtn.addEventListener('click', () => {
    scale = Math.min(scale + 0.25, 3);
    renderPage(currentPage);
});

zoomOutBtn.addEventListener('click', () => {
    scale = Math.max(scale - 0.25, 0.5);
    renderPage(currentPage);
});

// Vista previa de la firma
previewBtn.addEventListener('click', async () => {
    if (!sessionId) return;
    
    showStatus('Generando vista previa...', 'info');
    
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('password', passwordInput.value);
    
    try {
        const response = await fetch(`${API_URL}/preview-signature`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            previewImage.innerHTML = `<img src="${data.image}" style="max-width:100%; border-radius:8px;">`;
            previewModal.style.display = 'block';
        } else {
            showStatus('Error al generar vista previa', 'error');
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    }
});

confirmPositionBtn.addEventListener('click', () => {
    previewModal.style.display = 'none';
    showStatus('Posición confirmada', 'success');
});

closeModal.addEventListener('click', () => {
    previewModal.style.display = 'none';
});

// Firmar documento
signBtn.addEventListener('click', async () => {
    if (!sessionId) {
        showStatus('Sesión no válida', 'error');
        return;
    }
    
    signBtn.disabled = true;
    signBtn.textContent = '⏳ Firmando...';
    showStatus('Aplicando firma digital...', 'info');
    
    try {
        const response = await fetch(`${API_URL}/sign`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: sessionId,
                password: passwordInput.value,
                position: firmaPosition
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showStatus('✅ Documento firmado exitosamente. Descargando...', 'success');
            
            const downloadUrl = `${API_URL}/download/${sessionId}`;
            window.open(downloadUrl, '_blank');
        } else {
            showStatus(`Error: ${data.detail}`, 'error');
            signBtn.disabled = false;
            signBtn.textContent = '🔐 FIRMAR DOCUMENTO';
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
        signBtn.disabled = false;
        signBtn.textContent = '🔐 FIRMAR DOCUMENTO';
    }
});

// Keyboard shortcuts for zoom
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === '+') {
        e.preventDefault();
        zoomInBtn.click();
    } else if (e.ctrlKey && e.key === '-') {
        e.preventDefault();
        zoomOutBtn.click();
    }
});

// Registrar Service Worker
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
        .then(reg => console.log('Service Worker registrado', reg))
        .catch(err => console.error('Error Service Worker:', err));
}