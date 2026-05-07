from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
import tempfile
import uuid
import os
import io
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont
import qrcode
from endesive.pdf import cms

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

TEMP_DIR = Path(tempfile.gettempdir()) / "firma_ec"
TEMP_DIR.mkdir(exist_ok=True)

sessions = {}

TZ_ECUADOR = timezone(timedelta(hours=-5))

def ahora_ecuador():
    return datetime.now(TZ_ECUADOR)

def generar_imagen_firma(nombre_firmante: str, fecha_firma: str) -> bytes:
    """Genera imagen con QR + nombre + fecha (tamaño 280x100)"""
    size = (280, 100)
    img = Image.new("RGB", size, "#FFFFFF")
    draw = ImageDraw.Draw(img)
    
    # QR code
    datos_qr = f"Documento firmado digitalmente\nFirmante: {nombre_firmante}\nFecha: {fecha_firma}\nPAdES Ecuador"
    
    qr = qrcode.QRCode(version=2, box_size=3, border=1)
    qr.add_data(datos_qr)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")
    img_qr = img_qr.resize((75, 75))
    
    img.paste(img_qr, (8, 12))
    
    # Texto
    try:
        font_bold = ImageFont.truetype("arialbd.ttf", 10)
        font_normal = ImageFont.truetype("arial.ttf", 9)
    except:
        font_bold = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    draw.text((92, 15), "Firmado digitalmente por:", fill="#555555", font=font_normal)
    draw.text((92, 32), nombre_firmante[:32], fill="#000000", font=font_bold)
    draw.text((92, 52), fecha_firma, fill="#333333", font=font_normal)
    draw.text((92, 72), "PAdES - Ecuador", fill="#999999", font=font_normal)
    
    draw.line([(85, 8), (85, size[1]-8)], fill="#CCCCCC", width=1)
    draw.rectangle([(3, 3), (size[0]-3, size[1]-3)], outline="#2c7da0", width=2)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG", quality=95)
    return img_bytes.getvalue()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/upload-cert")
async def upload_cert(cert: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    path = TEMP_DIR / f"{session_id}.p12"
    with open(path, "wb") as f:
        f.write(await cert.read())
    sessions[session_id] = {"cert_path": str(path)}
    return {"session_id": session_id}

@app.post("/verify-cert")
async def verify_cert(session_id: str = Form(...), password: str = Form(...)):
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_key_and_certificates
    from cryptography.x509.oid import NameOID
    
    with open(sessions[session_id]["cert_path"], "rb") as f:
        data = f.read()
    
    try:
        clave, cert, cadena = load_key_and_certificates(data, password.encode())
        if cert is None:
            raise Exception()
        
        nombre = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        if isinstance(nombre, bytes):
            nombre = nombre.decode('utf-8', errors='ignore')
        
        emi = cert.not_valid_before_utc.astimezone(TZ_ECUADOR)
        exp = cert.not_valid_after_utc.astimezone(TZ_ECUADOR)
        ahora = ahora_ecuador()
        vigente = emi <= ahora <= exp
        dias = (exp - ahora).days if vigente else 0
        
        sessions[session_id]["nombre"] = nombre
        sessions[session_id]["password"] = password
        sessions[session_id]["clave"] = clave
        sessions[session_id]["certificado"] = cert
        sessions[session_id]["cadena"] = cadena or []
        
        return {
            "success": True,
            "firmante": nombre,
            "emision": emi.strftime("%d/%m/%Y"),
            "expiracion": exp.strftime("%d/%m/%Y"),
            "vigente": vigente,
            "dias_restantes": dias
        }
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(401, "Contraseña incorrecta o certificado inválido")

@app.post("/upload-pdf")
async def upload_pdf(pdf: UploadFile = File(...), session_id: str = Form(...)):
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    path = TEMP_DIR / f"{session_id}_doc.pdf"
    with open(path, "wb") as f:
        f.write(await pdf.read())
    sessions[session_id]["pdf_path"] = str(path)
    return {"success": True, "num_pages": 1}

@app.post("/set-position")
async def set_position(session_id: str = Form(...), x: float = Form(...), y: float = Form(...), page: int = Form(0)):
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    sessions[session_id]["position"] = {"x": x, "y": y, "page": page}
    return {"success": True}

@app.post("/preview-signature")
async def preview(session_id: str = Form(...), password: str = Form(...)):
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    
    nombre = sessions[session_id].get("nombre", "Firmante")
    fecha = ahora_ecuador().strftime("%d/%m/%Y %H:%M:%S")
    img_bytes = generar_imagen_firma(nombre, fecha)
    
    import base64
    b64 = base64.b64encode(img_bytes).decode()
    
    return {"success": True, "image": f"data:image/png;base64,{b64}"}

@app.post("/sign")
async def sign(request: Request):
    body = await request.json()
    session_id = body.get("session_id")
    password = body.get("password")
    position = body.get("position", {"x": 50, "y": 80, "page": 0})
    
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    
    session = sessions[session_id]
    
    # Verificar contraseña
    if session.get("password") != password:
        raise HTTPException(401, "Contraseña incorrecta")
    
    # Leer PDF
    with open(session["pdf_path"], "rb") as f:
        pdf_bytes = f.read()
    
    # Generar imagen de firma
    nombre = session.get("nombre", "Firmante")
    fecha_firma = ahora_ecuador().strftime("%d/%m/%Y %H:%M:%S")
    img_bytes = generar_imagen_firma(nombre, fecha_firma)
    
    # Guardar imagen temporal
    img_path = TEMP_DIR / f"{session_id}_sig.png"
    with open(img_path, "wb") as f:
        f.write(img_bytes)
    
    # Configuración de la firma
    fecha_adobe = ahora_ecuador().strftime("D:%Y%m%d%H%M%S-05'00'")
    
    udct = {
        "sigflags": 3,
        "sigpage": position.get("page", 0),
        "sigbutton": True,
        "sigfield": f"Signature_{uuid.uuid4().hex[:8]}",
        "auto_sigfield": True,
        "signaturebox": (
            position.get("x", 50),
            position.get("y", 80),
            position.get("x", 50) + 280,
            position.get("y", 80) + 100
        ),
        "signature_img": str(img_path),
        "signature_img_width": 280,
        "signature_img_height": 100,
        "contact": nombre,
        "location": "Ecuador",
        "signingdate": fecha_adobe,
        "reason": f"Documento firmado por {nombre}",
    }
    
    # Firmar con endesive
    try:
        datas = cms.sign(
            datau=pdf_bytes,
            udct=udct,
            key=session["clave"],
            cert=session["certificado"],
            othercerts=session.get("cadena") or [],
            algomd="sha256"
        )
        pdf_firmado = pdf_bytes + datas
    except Exception as e:
        print(f"Error al firmar: {e}")
        return {"success": False, "error": str(e)}
    
    # Guardar resultado
    output = TEMP_DIR / f"{session_id}_signed.pdf"
    with open(output, "wb") as f:
        f.write(pdf_firmado)
    
    # Limpiar imagen temporal
    if img_path.exists():
        img_path.unlink()
    
    session["output"] = str(output)
    
    return {"success": True, "message": "Documento firmado exitosamente"}

@app.get("/download/{session_id}")
async def download(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Sesión no encontrada")
    if "output" not in sessions[session_id]:
        raise HTTPException(404, "Documento no firmado aún")
    return FileResponse(sessions[session_id]["output"], filename="documento_firmado.pdf")

if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("Servidor iniciado en http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)