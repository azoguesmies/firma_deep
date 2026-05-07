#!/usr/bin/env python3
"""
Generador de iconos para la PWA de Firma Electrónica Ecuador
"""

import os
from PIL import Image, ImageDraw, ImageFont

def crear_icono(tamaño, ruta_salida):
    """Crea un icono PNG con el diseño de la aplicación"""
    
    # Colores
    bg_color = "#2c7da0"  # Color principal
    text_color = "#ffffff"
    
    # Crear imagen
    img = Image.new("RGB", (tamaño, tamaño), bg_color)
    draw = ImageDraw.Draw(img)
    
    # Dibujar un marco blanco
    borde = int(tamaño * 0.05)
    for i in range(3):
        offset = borde + i * 2
        draw.rectangle(
            [(offset, offset), (tamaño - offset, tamaño - offset)],
            outline="#ffffff",
            width=max(1, int(tamaño * 0.02))
        )
    
    # Dibujar un círculo interior
    circulo_radio = int(tamaño * 0.35)
    centro = tamaño // 2
    draw.ellipse(
        [(centro - circulo_radio, centro - circulo_radio),
         (centro + circulo_radio, centro + circulo_radio)],
        fill="#ffffff",
        outline="#1a5a7a",
        width=3
    )
    
    # Dibujar un candado estilizado (símbolo de seguridad)
    candado_ancho = int(tamaño * 0.25)
    candado_alto = int(tamaño * 0.3)
    candado_x = centro - candado_ancho // 2
    candado_y = centro - candado_alto // 2 + int(tamaño * 0.05)
    
    # Arco del candado
    arco_ancho = candado_ancho - 4
    arco_alto = int(candado_alto * 0.4)
    draw.arc(
        [(candado_x + 2, candado_y - arco_alto + 4),
         (candado_x + candado_ancho - 2, candado_y + 4)],
        start=0, end=180,
        fill=bg_color,
        width=3
    )
    
    # Cuerpo del candado
    draw.rectangle(
        [(candado_x + 2, candado_y),
         (candado_x + candado_ancho - 2, candado_y + candado_alto)],
        fill=bg_color,
        outline=bg_color,
        width=2
    )
    
    # Agregar texto "F" (Firma) en el candado
    try:
        # Intentar usar una fuente si está disponible
        font_size = int(tamaño * 0.3)
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        draw.text(
            (centro - int(font_size * 0.2), centro - int(font_size * 0.3)),
            "F",
            fill="#ffffff",
            font=font
        )
    except:
        pass
    
    # Guardar imagen
    img.save(ruta_salida, "PNG", quality=95)
    print(f"  ✅ Icono generado: {ruta_salida} ({tamaño}x{tamaño})")


def generar_todos_los_iconos():
    """Genera todos los iconos necesarios para la PWA"""
    
    # Crear directorio icons si no existe
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    os.makedirs(icons_dir, exist_ok=True)
    
    # Tamaños de iconos requeridos
    tamanos = [72, 96, 128, 144, 152, 192, 384, 512]
    
    print("\n" + "=" * 50)
    print("  GENERANDO ICONOS PARA PWA")
    print("=" * 50)
    
    for tamaño in tamanos:
        ruta = os.path.join(icons_dir, f"icon-{tamaño}.png")
        crear_icono(tamaño, ruta)
    
    # También crear favicon.ico (versión 32x32)
    favicon_path = os.path.join(icons_dir, "favicon.ico")
    crear_icono(32, favicon_path)
    
    print("\n" + "=" * 50)
    print(f"  ✅ Todos los iconos generados en: {icons_dir}")
    print("=" * 50)


if __name__ == "__main__":
    generar_todos_los_iconos()