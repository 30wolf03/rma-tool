from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, QByteArray
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QPainter, QImage

# SVG-Icons für die Passwort-Sichtbarkeitsumschaltung
EYE_OPEN_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
    <circle cx="12" cy="12" r="3"></circle>
</svg>
"""

EYE_CLOSED_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
    <line x1="1" y1="1" x2="23" y2="23"></line>
</svg>
"""

# SVG-Pfade für die Animation
EYE_PATH = "M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"
EYE_CIRCLE = "M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"
SLASH_START = "M1 1L23 23"
SLASH_END = "M23 1L1 23"

def create_animated_svg(progress: float, is_closing: bool = True) -> str:
    """Erstellt ein SVG mit animiertem Schrägstrich."""
    if is_closing:
        # Der Strich wandert von unten rechts nach oben links
        start_x = 23
        start_y = 23
        end_x = 1 + (23 - 1) * progress
        end_y = 1 + (23 - 1) * progress
        slash_path = f"M{start_x} {start_y}L{end_x} {end_y}"
    else:
        # Der Strich wandert von oben links nach unten rechts
        start_x = 1
        start_y = 1
        end_x = 23 - (23 - 1) * progress
        end_y = 23 - (23 - 1) * progress
        slash_path = f"M{start_x} {start_y}L{end_x} {end_y}"

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="{EYE_PATH}"></path>
        <circle cx="12" cy="12" r="3"></circle>
        <path d="{slash_path}"></path>
    </svg>
    """

def svg_to_pixmap(svg_str: str, size: int = 24) -> QPixmap:
    """Konvertiert einen SVG-String in ein QPixmap."""
    renderer = QSvgRenderer()
    renderer.load(QByteArray(svg_str.encode('utf-8')))
    
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(0)
    
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    
    return QPixmap.fromImage(image)

def get_eye_icon(is_open: bool) -> QIcon:
    """Gibt das entsprechende Auge-Icon zurück."""
    svg = EYE_OPEN_SVG if is_open else EYE_CLOSED_SVG
    pixmap = svg_to_pixmap(svg)
    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon 