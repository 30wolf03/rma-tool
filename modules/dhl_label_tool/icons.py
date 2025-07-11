from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize, QByteArray, Qt
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QImage

def create_simple_eye_icon(is_open: bool, size: int = 20) -> QIcon:
    """Erstellt ein einfaches Auge-Icon ohne SVG."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Zeichne ein einfaches Auge-Icon
    if is_open:
        # Offenes Auge: Kreis mit kleinerem Kreis in der Mitte
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(2, 2, size-4, size-4)
        
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.setBrush(Qt.GlobalColor.darkGray)
        painter.drawEllipse(size//2-2, size//2-2, 4, 4)
    else:
        # Geschlossenes Auge: Linie durch das Auge
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.setBrush(Qt.GlobalColor.white)
        painter.drawEllipse(2, 2, size-4, size-4)
        
        # Schrägstrich durch das Auge
        painter.setPen(Qt.GlobalColor.darkGray)
        painter.drawLine(3, 3, size-3, size-3)
    
    painter.end()
    
    icon = QIcon()
    icon.addPixmap(pixmap)
    return icon

def get_eye_icon(is_open: bool) -> QIcon:
    """Gibt das entsprechende Auge-Icon zurück."""
    return create_simple_eye_icon(is_open)

def create_animated_svg(progress: float, is_closing: bool = True) -> str:
    """Erstellt ein SVG mit animiertem Schrägstrich."""
    if is_closing:
        # Der Strich wandert von unten rechts nach oben links
        start_x = 19
        start_y = 19
        end_x = 1 + (19 - 1) * progress
        end_y = 1 + (19 - 1) * progress
        slash_path = f"M{start_x} {start_y}L{end_x} {end_y}"
    else:
        # Der Strich wandert von oben links nach unten rechts
        start_x = 1
        start_y = 1
        end_x = 19 - (19 - 1) * progress
        end_y = 19 - (19 - 1) * progress
        slash_path = f"M{start_x} {start_y}L{end_x} {end_y}"

    return f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#666666" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 10s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6z"></path>
        <circle cx="10" cy="10" r="2.5"></circle>
        <path d="{slash_path}"></path>
    </svg>
    """

def svg_to_pixmap(svg_str: str, size: int = 20) -> QPixmap:
    """Konvertiert einen SVG-String in ein QPixmap (PyQt6-kompatibel)."""
    try:
        renderer = QSvgRenderer()
        renderer.load(QByteArray(svg_str.encode('utf-8')))
        
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(0)
        
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        
        return QPixmap.fromImage(image)
    except Exception:
        # Fallback: Erstelle ein einfaches Icon
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        return pixmap 