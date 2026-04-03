import os
import sys
import subprocess
import threading
import time
import json
from pathlib import Path
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QComboBox, QSlider, QCheckBox,
    QFileDialog, QProgressBar, QSplitter, QScrollArea, QSizePolicy,
    QMessageBox, QGroupBox, QSpacerItem, QStyle, QMenu, QAction,
    QStackedWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, QRectF,
    QPropertyAnimation, QEasingCurve, QUrl, QRect
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QColor, QPen, QBrush, QFont,
    QLinearGradient, QRadialGradient, QPalette, QTransform,
    QMovie, QWheelEvent, QIcon
)

# --- Frozen binary support (PyInstaller) ---
def _get_app_dir():
    """Return the directory where the binary (or script) lives."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def _get_klarity_cmd():
    """Return the command prefix for invoking klarity."""
    if getattr(sys, 'frozen', False):
        return [sys.executable]
    return [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'klarity.py')]

THEME = {
    'background': '#0A0A0A',
    'surface': '#1a1a1a',
    'surface_hover': '#2a2a2a',
    'surface_active': '#3a3a3a',
    'text': '#E5E5E5',
    'text_secondary': '#A0A0A0',
    'accent': '#4CAF50',
    'accent_hover': '#45a049',
    'accent_pressed': '#3d8b40',
    'accent_disabled': '#2d5a30',
    'border': '#404040',
    'border_light': '#E5E5E5',
    'border_disabled': '#555555',
    'error': '#f44336',
    'warning': '#ff9800',
    'success': '#4CAF50',
    'panel_background': '#121212',
    'panel_border': '#E5E5E5',
}

def get_main_button_style():
    return """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #121212, stop:0.3 #121212, stop:0.7 #1a1a1a, stop:1 #121212);
            border: 2px solid #E5E5E5;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            padding: 10px 20px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #121212, stop:0.3 #161616, stop:0.7 #1e1e1e, stop:1 #121212);
            border: 2px solid #4CAF50;
            color: #4CAF50;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #0e0e0e, stop:0.3 #121212, stop:0.7 #161616, stop:1 #0e0e0e);
            border: 2px solid #4CAF50;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            border: 2px solid #555555;
            color: #666666;
        }
    """

def get_secondary_button_style():
    return """
        QPushButton {
            background-color: #1a1a1a;
            color: #E5E5E5;
            border: 1px solid #404040;
            border-radius: 6px;
            font-size: 12px;
            padding: 8px 16px;
        }
        QPushButton:hover {
            background-color: #2a2a2a;
            border: 1px solid #E5E5E5;
        }
        QPushButton:pressed {
            background-color: #3a3a3a;
        }
        QPushButton:disabled {
            background-color: #1a1a1a;
            border: 1px solid #404040;
            color: #666666;
        }
    """

def get_accent_button_style():
    return """
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2d5a30, stop:0.5 #4CAF50, stop:1 #2d5a30);
            border: 2px solid #4CAF50;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            color: white;
            padding: 10px 20px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #3d8b40, stop:0.5 #5CBF60, stop:1 #3d8b40);
            border: 2px solid #5CBF60;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1d4a20, stop:0.5 #3CAF40, stop:1 #1d4a20);
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            border: 2px solid #555555;
            color: #666666;
        }
    """

def get_accent_button_disabled_style():
    return """
        QPushButton {
            background-color: #2a2a2a;
            border: 2px solid #555555;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            color: #666666;
            padding: 10px 20px;
        }
    """

def get_surface_button_style():
    return """
        QPushButton {
            background-color: #2a2a2a;
            color: white;
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            font-size: 12px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #3a3a3a;
            border: 1px solid #E5E5E5;
        }
        QPushButton:pressed {
            background-color: #4a4a4a;
            border: 1px solid #E5E5E5;
        }
        QPushButton:disabled {
            background-color: #2a2a2a;
            border: 1px solid #404040;
            color: #666666;
        }
    """

def get_panel_style():
    return f"""
        QFrame {{
            background-color: {THEME['panel_background']};
            border: 2px solid {THEME['panel_border']};
            border-radius: 8px;
        }}
    """

def get_combo_box_style():
    return f"""
        QComboBox {{
            background-color: {THEME['surface']};
            color: {THEME['text']};
            border: 2px solid {THEME['border_light']};
            border-radius: 6px;
            padding: 6px 12px;
            min-width: 100px;
            font-size: 12px;
        }}
        QComboBox::drop-down {{
            border: none;
            subcontrol-origin: padding;
            subcontrol-position: right center;
            width: 24px;
        }}
        QComboBox::down-arrow {{
            image: none();
            width: 0px;
            height: 0px;
        }}
        QComboBox:hover {{
            border: 2px solid #4CAF50;
        }}
        QComboBox:disabled {{
            background-color: #2a2a2a;
            border: 2px solid #555555;
            color: #666666;
        }}
        QComboBox QAbstractItemView {{
            background-color: {THEME['surface']};
            color: {THEME['text']};
            border: 1px solid {THEME['border_light']};
            selection-background-color: {THEME['surface_hover']};
            selection-color: {THEME['text']};
        }}
    """

def get_progress_bar_style():
    return f"""
        QProgressBar {{
            border: 1px solid {THEME['border']};
            background-color: {THEME['surface']};
            height: 20px;
            border-radius: 10px;
            text-align: center;
            color: {THEME['text']};
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2d5a30, stop:0.5 #4CAF50, stop:1 #2d5a30);
            border-radius: 9px;
        }}
    """

def get_slider_style():
    return f"""
        QSlider::groove:horizontal {{
            border: 1px solid {THEME['border']};
            height: 8px;
            background: {THEME['surface']};
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {THEME['accent']};
            border: 2px solid {THEME['text']};
            width: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: #5CBF60;
        }}
        QSlider::sub-page:horizontal {{
            background: {THEME['accent']};
            border-radius: 4px;
        }}
    """

def get_group_box_style():
    return f"""
        QGroupBox {{
            font-weight: bold;
            font-size: 13px;
            color: {THEME['text']};
            border: 1px solid {THEME['border']};
            border-radius: 6px;
            margin-top: 10px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            color: {THEME['text']};
        }}
    """

def get_checkbox_style():
    return f"""
        QCheckBox {{
            color: {THEME['text']};
            font-size: 12px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {THEME['border_light']};
            border-radius: 4px;
            background-color: {THEME['surface']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {THEME['accent']};
            border: 2px solid {THEME['accent']};
        }}
        QCheckBox::indicator:hover {{
            border: 2px solid {THEME['accent']};
        }}
        QCheckBox:disabled {{
            color: #666666;
        }}
        QCheckBox::indicator:disabled {{
            background-color: #2a2a2a;
            border: 2px solid #555555;
        }}
    """

class ProcessingThread(QThread):
    progress_update = pyqtSignal(int, str)
    processing_complete = pyqtSignal(str, bool)
    download_status = pyqtSignal(str, str)

    def __init__(self, command, input_path, output_path, mode):
        super().__init__()
        self.command = command
        self.input_path = input_path
        self.output_path = output_path
        self.mode = mode
        self.cancelled = False

    def run(self):
        try:
            self.download_status.emit("Checking models...", "checking")

            process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=_get_app_dir()
            )

            output_file = None
            while True:
                if self.cancelled:
                    process.terminate()
                    self.processing_complete.emit("Cancelled", False)
                    return

                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break

                line = line.strip()
                if not line:
                    continue

                if line.startswith('{') and line.endswith('}'):
                    try:
                        data = json.loads(line)
                        percent = data.get('percent', 0)
                        step = data.get('step', '')
                        self.progress_update.emit(percent, step)

                        if 'output' in data:
                            output_file = data['output']
                    except json.JSONDecodeError:
                        pass
                elif 'downloading' in line.lower():
                    self.download_status.emit(line, "downloading")
                elif 'loaded' in line.lower() or 'downloaded' in line.lower():
                    self.download_status.emit(line, "done")
                elif '%' in line:
                    try:
                        import re
                        match = re.search(r'(\d+)%', line)
                        if match:
                            percent = int(match.group(1))
                            self.progress_update.emit(percent, line)
                    except:
                        pass

            if process.returncode == 0:
                final_output = self.output_path
                self.processing_complete.emit(final_output, True)
            else:
                self.processing_complete.emit(f"Error: Process failed with code {process.returncode}", False)

        except Exception as e:
            self.processing_complete.emit(f"Error: {str(e)}", False)

    def cancel(self):
        self.cancelled = True


class ScrollableImageViewer(QScrollArea):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.pixmap = None

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"background-color: {THEME['surface']};")
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.setWidget(self.image_label)
        self.setWidgetResizable(True)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            QScrollArea {{
                background-color: {THEME['surface']};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {THEME['surface']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {THEME['border']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {THEME['accent']};
            }}
            QScrollBar:add-line:vertical, QScrollBar:sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background-color: {THEME['surface']};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {THEME['border']};
                border-radius: 6px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {THEME['accent']};
            }}
            QScrollBar:add-line:horizontal, QScrollBar:sub-line:horizontal {{
                width: 0px;
            }}
        """)

        self.setMouseTracking(True)

    def setPixmap(self, pixmap):
        self.pixmap = pixmap
        if pixmap:
            self.updateImage()
        else:
            self.image_label.clear()
            self.image_label.setText("No media loaded")
            self.image_label.setStyleSheet(f"""
                background-color: {THEME['surface']};
                color: {THEME['text_secondary']};
                font-size: 14px;
            """)

    def updateImage(self):
        if self.pixmap:
            new_width = int(self.pixmap.width() * self.zoom_level)
            new_height = int(self.pixmap.height() * self.zoom_level)
            scaled = self.pixmap.scaled(new_width, new_height,
                                        Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled)
            self.image_label.resize(scaled.size())

    def setZoomLevel(self, level):
        self.zoom_level = max(self.min_zoom, min(self.max_zoom, level))
        self.updateImage()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1
            self.zoom_level = max(self.min_zoom, min(self.max_zoom, self.zoom_level))
            self.updateImage()
            parent = self.parent()
            while parent:
                if hasattr(parent, 'onZoomChanged'):
                    parent.onZoomChanged(self.zoom_level)
                    break
                parent = parent.parent()
        else:
            super().wheelEvent(event)


class ImageComparisonSlider(QWidget):

    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_pixmap = None
        self.after_pixmap = None
        self.slider_pos = 0.5
        self.zoom_level = 1.0
        self.dragging_slider = False
        self.dragging_pan = False
        self.showing_result = True

        self.pan_x = 0
        self.pan_y = 0
        self.last_mouse_pos = None

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

    def setBeforeImage(self, pixmap):
        self.before_pixmap = pixmap
        self.resetView()

    def setAfterImage(self, pixmap):
        self.after_pixmap = pixmap
        self.update()

    def setZoomLevel(self, level):
        self.zoom_level = max(0.1, min(10.0, level))
        self.update()

    def setSliderPosition(self, pos):
        self.slider_pos = max(0.0, min(1.0, pos))
        self.update()

    def resetView(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.pos()

            old_rect = self.getScaledRect(self.before_pixmap or self.after_pixmap)
            if not old_rect:
                return

            rel_x = (cursor_pos.x() - old_rect.x()) / old_rect.width()
            rel_y = (cursor_pos.y() - old_rect.y()) / old_rect.height()

            if rel_x < 0 or rel_x > 1 or rel_y < 0 or rel_y > 1:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_level *= 1.1
                else:
                    self.zoom_level /= 1.1
                self.zoom_level = max(0.1, min(10.0, self.zoom_level))
                self.update()
                self.zoomChanged.emit(self.zoom_level)
                return

            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))

            new_rect = self.getScaledRectNoPan(self.before_pixmap or self.after_pixmap)
            if new_rect:
                new_cursor_x = new_rect.x() + rel_x * new_rect.width()
                new_cursor_y = new_rect.y() + rel_y * new_rect.height()
                self.pan_x = cursor_pos.x() - new_cursor_x
                self.pan_y = cursor_pos.y() - new_cursor_y

            self.update()
            self.zoomChanged.emit(self.zoom_level)
        else:
            super().wheelEvent(event)

    def getScaledRectNoPan(self, pixmap):
        if not pixmap:
            return None
        base_size = self.rect().size()
        scaled = pixmap.scaled(base_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        w = int(scaled.width() * self.zoom_level)
        h = int(scaled.height() * self.zoom_level)
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        return QRect(x, y, w, h)

    def getScaledRect(self, pixmap):
        base_rect = self.getScaledRectNoPan(pixmap)
        if base_rect:
            return QRect(int(base_rect.x() + self.pan_x), int(base_rect.y() + self.pan_y),
                        base_rect.width(), base_rect.height())
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(THEME['surface']))

        if not self.before_pixmap and not self.after_pixmap:
            painter.setPen(QColor(THEME['text_secondary']))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "No media loaded\n\nDrop an image/video or click Browse")
            return

        if self.before_pixmap and not self.after_pixmap:
            rect = self.getScaledRect(self.before_pixmap)
            if rect:
                scaled = self.before_pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(rect.topLeft(), scaled)

            painter.setPen(QColor(THEME['text']))
            painter.setFont(QFont('Arial', 11, QFont.Bold))
            label_rect = QRectF(10, 10, 70, 25)
            painter.fillRect(label_rect, QColor(0, 0, 0, 180))
            painter.drawText(label_rect, Qt.AlignCenter, "ORIGINAL")
            return

        base_rect = self.getScaledRect(self.before_pixmap)
        if not base_rect:
            return

        if self.after_pixmap:
            scaled_after = self.after_pixmap.scaled(base_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(base_rect.topLeft(), scaled_after)

        if self.before_pixmap:
            slider_x = int(self.width() * self.slider_pos)

            painter.save()
            painter.setClipRect(0, 0, slider_x, self.height())

            scaled_before = self.before_pixmap.scaled(base_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(base_rect.topLeft(), scaled_before)
            painter.restore()

            pen = QPen(QColor(THEME['accent']), 3)
            painter.setPen(pen)
            painter.drawLine(slider_x, 0, slider_x, self.height())

            handle_h = 50
            handle_w = 24
            handle_rect = QRectF(slider_x - handle_w//2, self.height()//2 - handle_h//2, handle_w, handle_h)

            painter.setBrush(QBrush(QColor(THEME['accent'])))
            painter.setPen(QPen(QColor(THEME['text']), 2))
            painter.drawRoundedRect(handle_rect, 5, 5)

            painter.setPen(QPen(QColor(THEME['text']), 2))
            arrow_y = self.height() // 2
            painter.drawLine(slider_x - 6, arrow_y, slider_x - 2, arrow_y - 5)
            painter.drawLine(slider_x - 6, arrow_y, slider_x - 2, arrow_y + 5)
            painter.drawLine(slider_x + 6, arrow_y, slider_x + 2, arrow_y - 5)
            painter.drawLine(slider_x + 6, arrow_y, slider_x + 2, arrow_y + 5)

        painter.setPen(QColor(THEME['text']))
        painter.setFont(QFont('Arial', 11, QFont.Bold))

        before_label = QRectF(10, 10, 70, 25)
        painter.fillRect(before_label, QColor(0, 0, 0, 180))
        painter.drawText(before_label, Qt.AlignCenter, "BEFORE")

        after_label = QRectF(self.width() - 80, 10, 70, 25)
        painter.fillRect(after_label, QColor(0, 0, 0, 180))
        painter.drawText(after_label, Qt.AlignCenter, "AFTER")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            slider_x = int(self.width() * self.slider_pos)
            handle_rect = QRect(slider_x - 20, self.height()//2 - 30, 40, 60)

            if handle_rect.contains(event.pos()):
                self.dragging_slider = True
                self.slider_pos = event.pos().x() / self.width()
            else:
                self.dragging_pan = True
                self.last_mouse_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
            self.update()

    def mouseMoveEvent(self, event):
        if self.dragging_slider:
            self.slider_pos = max(0.0, min(1.0, event.pos().x() / self.width()))
            self.update()
        elif self.dragging_pan and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_slider = False
            self.dragging_pan = False
            self.last_mouse_pos = None
            self.setCursor(Qt.CrossCursor)


class SideBySideView(QWidget):

    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_pixmap = None
        self.after_pixmap = None
        self.zoom_level = 1.0

        self.pan_x = 0
        self.pan_y = 0
        self.dragging_pan = False
        self.last_mouse_pos = None

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def setBeforeImage(self, pixmap):
        self.before_pixmap = pixmap
        self.resetView()

    def setAfterImage(self, pixmap):
        self.after_pixmap = pixmap
        self.update()

    def setZoomLevel(self, level):
        self.zoom_level = max(0.1, min(10.0, level))
        self.update()

    def resetView(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.pos()

            half_width = self.width() // 2
            on_left = cursor_pos.x() < half_width
            target_rect = QRect(0, 0, half_width, self.height()) if on_left else QRect(half_width, 0, half_width, self.height())

            pixmap = self.before_pixmap if on_left else self.after_pixmap
            old_rect = self.getScaledRect(pixmap, target_rect)
            if not old_rect:
                return

            rel_x = (cursor_pos.x() - old_rect.x()) / old_rect.width()
            rel_y = (cursor_pos.y() - old_rect.y()) / old_rect.height()

            if rel_x < 0 or rel_x > 1 or rel_y < 0 or rel_y > 1:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_level *= 1.1
                else:
                    self.zoom_level /= 1.1
                self.zoom_level = max(0.1, min(10.0, self.zoom_level))
                self.update()
                self.zoomChanged.emit(self.zoom_level)
                return

            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))

            new_rect = self.getScaledRectNoPan(pixmap, target_rect)
            if new_rect:
                new_cursor_x = new_rect.x() + rel_x * new_rect.width()
                new_cursor_y = new_rect.y() + rel_y * new_rect.height()
                self.pan_x = cursor_pos.x() - new_cursor_x
                self.pan_y = cursor_pos.y() - new_cursor_y

            self.update()
            self.zoomChanged.emit(self.zoom_level)
        else:
            super().wheelEvent(event)

    def getScaledRectNoPan(self, pixmap, target_rect):
        if not pixmap:
            return None
        scaled = pixmap.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        w = int(scaled.width() * self.zoom_level)
        h = int(scaled.height() * self.zoom_level)
        x = target_rect.x() + (target_rect.width() - w) // 2
        y = target_rect.y() + (target_rect.height() - h) // 2
        return QRect(x, y, w, h)

    def getScaledRect(self, pixmap, target_rect):
        base_rect = self.getScaledRectNoPan(pixmap, target_rect)
        if base_rect:
            return QRect(int(base_rect.x() + self.pan_x), int(base_rect.y() + self.pan_y),
                        base_rect.width(), base_rect.height())
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(THEME['surface']))

        half_width = self.width() // 2
        left_rect = QRect(0, 0, half_width, self.height())
        right_rect = QRect(half_width, 0, half_width, self.height())

        painter.setPen(QPen(QColor(THEME['accent']), 3))
        painter.drawLine(half_width, 0, half_width, self.height())

        if not self.before_pixmap and not self.after_pixmap:
            painter.setPen(QColor(THEME['text_secondary']))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "No media loaded\n\nDrop an image/video or click Browse")
            return

        if self.before_pixmap:
            rect = self.getScaledRect(self.before_pixmap, left_rect)
            if rect:
                painter.save()
                painter.setClipRect(left_rect)
                scaled = self.before_pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(rect.topLeft(), scaled)
                painter.restore()

        if self.after_pixmap:
            rect = self.getScaledRect(self.after_pixmap, right_rect)
            if rect:
                painter.save()
                painter.setClipRect(right_rect)
                scaled = self.after_pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(rect.topLeft(), scaled)
                painter.restore()

        painter.setPen(QColor(THEME['text']))
        painter.setFont(QFont('Arial', 11, QFont.Bold))

        before_label = QRectF(10, 10, 70, 25)
        painter.fillRect(before_label, QColor(0, 0, 0, 180))
        painter.drawText(before_label, Qt.AlignCenter, "BEFORE")

        after_label = QRectF(self.width() - 80, 10, 70, 25)
        painter.fillRect(after_label, QColor(0, 0, 0, 180))
        painter.drawText(after_label, Qt.AlignCenter, "AFTER")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_pan = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.dragging_pan and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_pan = False
            self.last_mouse_pos = None
            self.setCursor(Qt.ArrowCursor)


class SingleImageView(QWidget):

    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.before_pixmap = None
        self.after_pixmap = None
        self.pixmap = None
        self.zoom_level = 1.0
        self.showing_result = True

        self.pan_x = 0
        self.pan_y = 0
        self.dragging_pan = False
        self.last_mouse_pos = None

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def setBeforeImage(self, pixmap):
        self.before_pixmap = pixmap
        self._updateCurrentPixmap()

    def setAfterImage(self, pixmap):
        self.after_pixmap = pixmap
        self._updateCurrentPixmap()

    def _updateCurrentPixmap(self):
        if self.showing_result:
            if self.after_pixmap:
                self.pixmap = self.after_pixmap
            elif self.before_pixmap:
                self.pixmap = self.before_pixmap
            else:
                self.pixmap = None
        else:
            if self.before_pixmap:
                self.pixmap = self.before_pixmap
            elif self.after_pixmap:
                self.pixmap = self.after_pixmap
            else:
                self.pixmap = None
        self.resetView()

    def setZoomLevel(self, level):
        self.zoom_level = max(0.1, min(10.0, level))
        self.update()

    def setShowingResult(self, show_result):
        self.showing_result = show_result
        self._updateCurrentPixmap()

    def resetView(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            cursor_pos = event.pos()

            old_rect = self.getScaledRect(self.pixmap)
            if not old_rect:
                return

            rel_x = (cursor_pos.x() - old_rect.x()) / old_rect.width()
            rel_y = (cursor_pos.y() - old_rect.y()) / old_rect.height()

            if rel_x < 0 or rel_x > 1 or rel_y < 0 or rel_y > 1:
                delta = event.angleDelta().y()
                if delta > 0:
                    self.zoom_level *= 1.1
                else:
                    self.zoom_level /= 1.1
                self.zoom_level = max(0.1, min(10.0, self.zoom_level))
                self.update()
                self.zoomChanged.emit(self.zoom_level)
                return

            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))

            new_rect = self.getScaledRectNoPan(self.pixmap)
            if new_rect:
                new_cursor_x = new_rect.x() + rel_x * new_rect.width()
                new_cursor_y = new_rect.y() + rel_y * new_rect.height()
                self.pan_x = cursor_pos.x() - new_cursor_x
                self.pan_y = cursor_pos.y() - new_cursor_y

            self.update()
            self.zoomChanged.emit(self.zoom_level)
        else:
            super().wheelEvent(event)

    def getScaledRectNoPan(self, pixmap):
        if not pixmap:
            return None
        base_size = self.rect().size()
        scaled = pixmap.scaled(base_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        w = int(scaled.width() * self.zoom_level)
        h = int(scaled.height() * self.zoom_level)
        x = (self.width() - w) // 2
        y = (self.height() - h) // 2
        return QRect(x, y, w, h)

    def getScaledRect(self, pixmap):
        base_rect = self.getScaledRectNoPan(pixmap)
        if base_rect:
            return QRect(int(base_rect.x() + self.pan_x), int(base_rect.y() + self.pan_y),
                        base_rect.width(), base_rect.height())
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.fillRect(self.rect(), QColor(THEME['surface']))

        if self.pixmap:
            rect = self.getScaledRect(self.pixmap)
            if rect:
                scaled = self.pixmap.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                painter.drawPixmap(rect.topLeft(), scaled)

            painter.setPen(QColor(THEME['text']))
            painter.setFont(QFont('Arial', 11, QFont.Bold))
            label = "RESULT" if self.showing_result else "ORIGINAL"
            label_rect = QRectF(10, 10, 80, 25)
            painter.fillRect(label_rect, QColor(0, 0, 0, 180))
            painter.drawText(label_rect, Qt.AlignCenter, label)
        else:
            painter.setPen(QColor(THEME['text_secondary']))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(self.rect(), Qt.AlignCenter, "No media loaded")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_pan = True
            self.last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.dragging_pan and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_pan = False
            self.last_mouse_pos = None
            self.setCursor(Qt.ArrowCursor)


class VideoComparisonWidget(QWidget):

    zoomChanged = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.video_original_path = None
        self.video_result_path = None
        self.cap_original = None
        self.cap_result = None

        self.fps_original = 30
        self.fps_result = 30
        self.frame_count_original = 0
        self.frame_count_result = 0
        self.duration_original = 0
        self.duration_result = 0
        self.duration = 0

        self.current_time = 0.0
        self.playback_speed = 1.0
        self.is_playing = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advanceTime)

        self.view_mode = 'slider'
        self.slider_pos = 0.5
        self.showing_result = True

        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

        self.dragging_slider = False
        self.dragging_pan = False
        self.last_mouse_pos = None

        self.frame_original = None
        self.frame_result = None
        self.frame_original_idx = -1
        self.frame_result_idx = -1

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)

        self.display_widget = QWidget()
        self.display_widget.setMinimumHeight(200)
        self.display_widget.setStyleSheet(f"background-color: {THEME['surface']};")
        self.display_widget.paintEvent = self._paint_display
        self.display_widget.wheelEvent = self._display_wheel
        self.display_widget.mousePressEvent = self._display_mouse_press
        self.display_widget.mouseMoveEvent = self._display_mouse_move
        self.display_widget.mouseReleaseEvent = self._display_mouse_release
        self.display_widget.setMouseTracking(True)
        main_layout.addWidget(self.display_widget, 1)

        self.timeline = QSlider(Qt.Horizontal)
        self.timeline.setStyleSheet(get_slider_style())
        self.timeline.setRange(0, 1000)
        self.timeline.setValue(0)
        self.timeline.sliderMoved.connect(self._on_timeline_moved)
        self.timeline.sliderPressed.connect(self._on_timeline_pressed)
        self.timeline.sliderReleased.connect(self._on_timeline_released)
        main_layout.addWidget(self.timeline)

        controls = QHBoxLayout()

        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet(get_surface_button_style())
        self.play_btn.clicked.connect(self.togglePlay)
        controls.addWidget(self.play_btn)

        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 12px;")
        controls.addWidget(self.time_label)

        controls.addStretch()

        controls.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["25%", "50%", "75%", "100%", "150%", "200%"])
        self.speed_combo.setCurrentIndex(3)
        self.speed_combo.setStyleSheet(get_combo_box_style())
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        controls.addWidget(self.speed_combo)

        main_layout.addLayout(controls)

        self._display = self.display_widget

    def setVideo(self, video_path):
        import cv2
        self.video_original_path = video_path

        if self.cap_original:
            self.cap_original.release()
        self.cap_original = cv2.VideoCapture(video_path)

        self.fps_original = self.cap_original.get(cv2.CAP_PROP_FPS) or 30
        self.frame_count_original = int(self.cap_original.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_original = self.frame_count_original / self.fps_original if self.fps_original > 0 else 0

        self._update_duration()
        self.current_time = 0
        self._update_frame_at_time()
        self._update_ui()

    def setResultVideo(self, video_path):
        import cv2
        self.video_result_path = video_path

        if self.cap_result:
            self.cap_result.release()
        self.cap_result = cv2.VideoCapture(video_path)

        self.fps_result = self.cap_result.get(cv2.CAP_PROP_FPS) or 30
        self.frame_count_result = int(self.cap_result.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_result = self.frame_count_result / self.fps_result if self.fps_result > 0 else 0

        self._update_duration()
        self._update_frame_at_time()
        self._update_ui()

    def _update_duration(self):
        if self.duration_original > 0 and self.duration_result > 0:
            self.duration = min(self.duration_original, self.duration_result)
        elif self.duration_original > 0:
            self.duration = self.duration_original
        elif self.duration_result > 0:
            self.duration = self.duration_result
        else:
            self.duration = 0

    def setViewMode(self, mode):
        self.view_mode = mode
        self._display.update()

    def setShowingResult(self, show_result):
        self.showing_result = show_result
        self._display.update()

    def setSliderPosition(self, pos):
        self.slider_pos = max(0.0, min(1.0, pos))
        self._display.update()

    def resetView(self):
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._display.update()
        self.zoomChanged.emit(self.zoom_level)

    def setZoomLevel(self, level):
        self.zoom_level = max(0.1, min(10.0, level))
        self._display.update()

    def _get_frame(self, cap, frame_idx, cache_attr, cache_idx_attr):
        import cv2

        if not cap:
            return None

        cached_idx = getattr(self, cache_idx_attr)
        if cached_idx == frame_idx:
            return getattr(self, cache_attr)

        cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_idx))
        ret, frame = cap.read()

        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            setattr(self, cache_attr, frame)
            setattr(self, cache_idx_attr, frame_idx)
            return frame
        return None

    def _update_frame_at_time(self):
        import cv2

        if self.current_time < 0:
            self.current_time = 0

        frame_orig = int(self.current_time * self.fps_original)
        frame_result = int(self.current_time * self.fps_result)

        frame_orig = min(frame_orig, max(0, self.frame_count_original - 1))
        frame_result = min(frame_result, max(0, self.frame_count_result - 1))

        self._get_frame(self.cap_original, frame_orig, 'frame_original', 'frame_original_idx')
        self._get_frame(self.cap_result, frame_result, 'frame_result', 'frame_result_idx')

    def _update_ui(self):
        if self.duration > 0:
            progress = int((self.current_time / self.duration) * 1000)
            self.timeline.blockSignals(True)
            self.timeline.setValue(min(1000, max(0, progress)))
            self.timeline.blockSignals(False)

        current_min = int(self.current_time // 60)
        current_sec = int(self.current_time % 60)
        total_min = int(self.duration // 60)
        total_sec = int(self.duration % 60)
        self.time_label.setText(f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}")

        self._display.update()

    def advanceTime(self):
        base_fps = 60.0
        dt = (1.0 / base_fps) * self.playback_speed
        self.current_time += dt

        if self.current_time >= self.duration:
            self.current_time = 0

        self._update_frame_at_time()
        self._update_ui()

    def togglePlay(self):
        if self.is_playing:
            self.timer.stop()
            self.play_btn.setText("▶")
        else:
            interval = int(1000 / 60)
            self.timer.start(max(1, interval))
            self.play_btn.setText("⏸")
        self.is_playing = not self.is_playing

    def _on_timeline_moved(self, value):
        if self.duration > 0:
            self.current_time = (value / 1000.0) * self.duration
            self._update_frame_at_time()
            self._update_ui()

    def _on_timeline_pressed(self):
        self._was_playing = self.is_playing
        if self.is_playing:
            self.timer.stop()

    def _on_timeline_released(self):
        if hasattr(self, '_was_playing') and self._was_playing:
            interval = int(1000 / 60)
            self.timer.start(max(1, interval))

    def _on_speed_changed(self, index):
        speeds = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        self.playback_speed = speeds[index]

    def _get_scaled_rect(self, pixmap_size, target_rect):
        base_w = target_rect.width()
        base_h = target_rect.height()

        if pixmap_size.width() > 0 and pixmap_size.height() > 0:
            scale = min(base_w / pixmap_size.width(), base_h / pixmap_size.height())
        else:
            scale = 1.0

        w = int(pixmap_size.width() * scale * self.zoom_level)
        h = int(pixmap_size.height() * scale * self.zoom_level)
        x = target_rect.x() + (target_rect.width() - w) // 2 + int(self.pan_x)
        y = target_rect.y() + (target_rect.height() - h) // 2 + int(self.pan_y)

        return QRect(x, y, w, h)

    def _paint_display(self, event):
        painter = QPainter(self.display_widget)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.display_widget.rect()
        painter.fillRect(rect, QColor(THEME['surface']))

        has_original = self.frame_original is not None
        has_result = self.frame_result is not None

        if not has_original and not has_result:
            painter.setPen(QColor(THEME['text_secondary']))
            painter.setFont(QFont('Arial', 14))
            painter.drawText(rect, Qt.AlignCenter, "No media loaded\n\nDrop a video or click Browse")
            return

        pixmap_orig = None
        pixmap_result = None
        pixmap_size = None

        if has_original:
            h, w, ch = self.frame_original.shape
            bytes_per_line = ch * w
            qimg = QImage(self.frame_original.data.tobytes(), w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap_orig = QPixmap.fromImage(qimg)
            pixmap_size = pixmap_orig.size()

        if has_result:
            h, w, ch = self.frame_result.shape
            bytes_per_line = ch * w
            qimg = QImage(self.frame_result.data.tobytes(), w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap_result = QPixmap.fromImage(qimg)
            if pixmap_size is None:
                pixmap_size = pixmap_result.size()

        if self.view_mode == 'sidebyside':
            self._paint_sidebyside(painter, rect, pixmap_orig, pixmap_result, pixmap_size)
        elif self.view_mode == 'slider':
            self._paint_slider(painter, rect, pixmap_orig, pixmap_result, pixmap_size)
        else:
            self._paint_single(painter, rect, pixmap_orig, pixmap_result, pixmap_size)

    def _paint_slider(self, painter, rect, pixmap_orig, pixmap_result, pixmap_size):
        target_rect = rect

        if not pixmap_size:
            return

        img_rect = self._get_scaled_rect(pixmap_size, target_rect)

        if pixmap_result:
            painter.drawPixmap(img_rect.topLeft(), pixmap_result.scaled(img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if pixmap_orig:
            slider_x = int(rect.width() * self.slider_pos)
            painter.save()
            painter.setClipRect(0, 0, slider_x, rect.height())
            painter.drawPixmap(img_rect.topLeft(), pixmap_orig.scaled(img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.restore()

            pen = QPen(QColor(THEME['accent']), 3)
            painter.setPen(pen)
            painter.drawLine(slider_x, 0, slider_x, rect.height())

            handle_h = 50
            handle_w = 24
            handle_rect = QRectF(slider_x - handle_w//2, rect.height()//2 - handle_h//2, handle_w, handle_h)

            painter.setBrush(QBrush(QColor(THEME['accent'])))
            painter.setPen(QPen(QColor(THEME['text']), 2))
            painter.drawRoundedRect(handle_rect, 5, 5)

            painter.setPen(QPen(QColor(THEME['text']), 2))
            arrow_y = rect.height() // 2
            painter.drawLine(slider_x - 6, arrow_y, slider_x - 2, arrow_y - 5)
            painter.drawLine(slider_x - 6, arrow_y, slider_x - 2, arrow_y + 5)
            painter.drawLine(slider_x + 6, arrow_y, slider_x + 2, arrow_y - 5)
            painter.drawLine(slider_x + 6, arrow_y, slider_x + 2, arrow_y + 5)

        painter.setPen(QColor(THEME['text']))
        painter.setFont(QFont('Arial', 11, QFont.Bold))

        before_label = QRectF(10, 10, 70, 25)
        painter.fillRect(before_label, QColor(0, 0, 0, 180))
        painter.drawText(before_label, Qt.AlignCenter, "BEFORE")

        after_label = QRectF(rect.width() - 80, 10, 70, 25)
        painter.fillRect(after_label, QColor(0, 0, 0, 180))
        painter.drawText(after_label, Qt.AlignCenter, "AFTER")

    def _paint_sidebyside(self, painter, rect, pixmap_orig, pixmap_result, pixmap_size):
        half_width = rect.width() // 2
        left_rect = QRect(0, 0, half_width, rect.height())
        right_rect = QRect(half_width, 0, half_width, rect.height())

        painter.setPen(QPen(QColor(THEME['accent']), 3))
        painter.drawLine(half_width, 0, half_width, rect.height())

        if pixmap_orig and pixmap_size:
            img_rect = self._get_scaled_rect(pixmap_size, left_rect)
            painter.save()
            painter.setClipRect(left_rect)
            painter.drawPixmap(img_rect.topLeft(), pixmap_orig.scaled(img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.restore()

        if pixmap_result and pixmap_size:
            img_rect = self._get_scaled_rect(pixmap_size, right_rect)
            painter.save()
            painter.setClipRect(right_rect)
            painter.drawPixmap(img_rect.topLeft(), pixmap_result.scaled(img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            painter.restore()

        painter.setPen(QColor(THEME['text']))
        painter.setFont(QFont('Arial', 11, QFont.Bold))

        before_label = QRectF(10, 10, 70, 25)
        painter.fillRect(before_label, QColor(0, 0, 0, 180))
        painter.drawText(before_label, Qt.AlignCenter, "BEFORE")

        after_label = QRectF(rect.width() - 80, 10, 70, 25)
        painter.fillRect(after_label, QColor(0, 0, 0, 180))
        painter.drawText(after_label, Qt.AlignCenter, "AFTER")

    def _paint_single(self, painter, rect, pixmap_orig, pixmap_result, pixmap_size):
        pixmap = pixmap_result if (self.showing_result and pixmap_result) else pixmap_orig

        if pixmap and pixmap_size:
            img_rect = self._get_scaled_rect(pixmap_size, rect)
            painter.drawPixmap(img_rect.topLeft(), pixmap.scaled(img_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

            painter.setPen(QColor(THEME['text']))
            painter.setFont(QFont('Arial', 11, QFont.Bold))
            label = "RESULT" if (self.showing_result and pixmap_result) else "ORIGINAL"
            label_rect = QRectF(10, 10, 80, 25)
            painter.fillRect(label_rect, QColor(0, 0, 0, 180))
            painter.drawText(label_rect, Qt.AlignCenter, label)

    def _display_wheel(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_level *= 1.1
            else:
                self.zoom_level /= 1.1
            self.zoom_level = max(0.1, min(10.0, self.zoom_level))
            self._display.update()
            self.zoomChanged.emit(self.zoom_level)
        else:
            pass

    def _display_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            if self.view_mode == 'slider':
                rect = self._display.rect()
                slider_x = int(rect.width() * self.slider_pos)
                handle_rect = QRect(slider_x - 20, rect.height()//2 - 30, 40, 60)

                if handle_rect.contains(event.pos()):
                    self.dragging_slider = True
                else:
                    self.dragging_pan = True
                    self.last_mouse_pos = event.pos()
                    self._display.setCursor(Qt.ClosedHandCursor)
            else:
                self.dragging_pan = True
                self.last_mouse_pos = event.pos()
                self._display.setCursor(Qt.ClosedHandCursor)

    def _display_mouse_move(self, event):
        if self.dragging_slider:
            rect = self._display.rect()
            self.slider_pos = max(0.0, min(1.0, event.pos().x() / rect.width()))
            self._display.update()
        elif self.dragging_pan and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.pan_x += delta.x()
            self.pan_y += delta.y()
            self.last_mouse_pos = event.pos()
            self._display.update()

    def _display_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging_slider = False
            self.dragging_pan = False
            self.last_mouse_pos = None
            self._display.setCursor(Qt.CrossCursor if self.view_mode == 'slider' else Qt.ArrowCursor)

    def clear(self):
        if self.cap_original:
            self.cap_original.release()
            self.cap_original = None
        if self.cap_result:
            self.cap_result.release()
            self.cap_result = None

        self.video_original_path = None
        self.video_result_path = None
        self.frame_original = None
        self.frame_result = None
        self.frame_original_idx = -1
        self.frame_result_idx = -1
        self.fps_original = 30
        self.fps_result = 30
        self.frame_count_original = 0
        self.frame_count_result = 0
        self.duration_original = 0
        self.duration_result = 0
        self.duration = 0
        self.current_time = 0

        self.timeline.setValue(0)
        self.time_label.setText("00:00 / 00:00")

        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0

        self._display.update()


class KlarityGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klarity - Image/Video Restoration")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)

        logo_path = os.path.join(_get_app_dir(), 'logo.png')
        if os.path.exists(logo_path):
            window_icon = QIcon(logo_path)
            for size in [16, 22, 32, 48, 64, 128, 256]:
                window_icon.addPixmap(QPixmap(logo_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setWindowIcon(window_icon)

        self.setStyleSheet(f"background-color: {THEME['background']}; color: {THEME['text']};")

        self.input_path = None
        self.output_path = None
        self.result_path = None
        self.processing_thread = None
        self.start_time = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateTimer)

        self.is_video = False
        self.side_by_side_mode = False
        self.current_zoom = 1.0

        self.setupUI()
        self.checkModels()
        self.updateProcessButton()

    def setupUI(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        left_panel = QFrame()
        left_panel.setFixedWidth(280)
        left_panel.setStyleSheet(get_panel_style())
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(10)

        info_layout = QHBoxLayout()
        self.info_btn = QPushButton("?")
        self.info_btn.setFixedSize(30, 30)
        self.info_btn.setStyleSheet(get_surface_button_style())
        self.info_btn.clicked.connect(self.showInfo)
        info_layout.addWidget(self.info_btn)
        info_layout.addStretch()

        title = QLabel("KLARITY")
        title.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {THEME['text']};
            letter-spacing: 3px;
        """)
        info_layout.addWidget(title)
        info_layout.addStretch()
        left_layout.addLayout(info_layout)

        mode_group = QGroupBox("Model Mode")
        mode_group.setStyleSheet(get_group_box_style())
        mode_layout = QVBoxLayout(mode_group)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Heavy (Best Quality)", "Lite (Faster)"])
        self.mode_combo.setStyleSheet(get_combo_box_style())
        self.mode_combo.currentIndexChanged.connect(self.onModeChanged)
        mode_layout.addWidget(self.mode_combo)

        self.model_status = QLabel("Checking models...")
        self.model_status.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        mode_layout.addWidget(self.model_status)

        self.download_btn = QPushButton("Download Models")
        self.download_btn.setStyleSheet(get_secondary_button_style())
        self.download_btn.clicked.connect(self.downloadModels)
        mode_layout.addWidget(self.download_btn)

        left_layout.addWidget(mode_group)

        input_group = QGroupBox("Input")
        input_group.setStyleSheet(get_group_box_style())
        input_layout = QVBoxLayout(input_group)

        self.input_label = QLabel("No file selected")
        self.input_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self.input_label.setWordWrap(True)
        input_layout.addWidget(self.input_label)

        browse_btn = QPushButton("Browse File")
        browse_btn.setStyleSheet(get_secondary_button_style())
        browse_btn.clicked.connect(self.browseInput)
        input_layout.addWidget(browse_btn)

        left_layout.addWidget(input_group)

        proc_group = QGroupBox("Processing Mode")
        proc_group.setStyleSheet(get_group_box_style())
        proc_layout = QVBoxLayout(proc_group)

        self.proc_mode_combo = QComboBox()
        self.proc_mode_combo.addItems([
            "Denoise", "Deblur", "Upscale",
            "Clean (Denoise+Deblur)", "Full (All)",
            "Frame Generation", "Clean + Frame Gen", "Full + Frame Gen"
        ])
        self.proc_mode_combo.setStyleSheet(get_combo_box_style())
        self.proc_mode_combo.currentIndexChanged.connect(self.onProcModeChanged)
        proc_layout.addWidget(self.proc_mode_combo)

        upscale_layout = QHBoxLayout()
        upscale_layout.addWidget(QLabel("Upscale:"))
        self.upscale_combo = QComboBox()
        self.upscale_combo.addItems(["2x", "4x"])
        self.upscale_combo.setStyleSheet(get_combo_box_style())
        upscale_layout.addWidget(self.upscale_combo)
        proc_layout.addLayout(upscale_layout)

        frame_layout = QHBoxLayout()
        frame_layout.addWidget(QLabel("Frame Mult:"))
        self.frame_combo = QComboBox()
        self.frame_combo.addItems(["2x", "4x"])
        self.frame_combo.setStyleSheet(get_combo_box_style())
        frame_layout.addWidget(self.frame_combo)
        proc_layout.addLayout(frame_layout)

        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["Auto", "CPU", "GPU"])
        self.device_combo.setStyleSheet(get_combo_box_style())
        device_layout.addWidget(self.device_combo)
        proc_layout.addLayout(device_layout)

        left_layout.addWidget(proc_group)

        output_group = QGroupBox("Output")
        output_group.setStyleSheet(get_group_box_style())
        output_layout = QVBoxLayout(output_group)

        output_btn = QPushButton("Choose Output Folder")
        output_btn.setStyleSheet(get_secondary_button_style())
        output_btn.clicked.connect(self.browseOutput)
        output_layout.addWidget(output_btn)

        self.output_label = QLabel("Same as input")
        self.output_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self.output_label.setWordWrap(True)
        output_layout.addWidget(self.output_label)

        left_layout.addWidget(output_group)

        left_layout.addStretch()

        progress_group = QGroupBox("Progress")
        progress_group.setStyleSheet(get_group_box_style())
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(get_progress_bar_style())
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        progress_layout.addWidget(self.status_label)

        self.timer_label = QLabel("")
        self.timer_label.setStyleSheet(f"color: {THEME['text']}; font-size: 14px; font-weight: bold;")
        progress_layout.addWidget(self.timer_label)

        left_layout.addWidget(progress_group)

        btn_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet(get_secondary_button_style())
        self.clear_btn.clicked.connect(self.clearAll)
        btn_layout.addWidget(self.clear_btn)

        self.process_btn = QPushButton("PROCESS")
        self.process_btn.setStyleSheet(get_accent_button_disabled_style())
        self.process_btn.clicked.connect(self.startProcessing)
        self.process_btn.setEnabled(False)
        btn_layout.addWidget(self.process_btn)

        left_layout.addLayout(btn_layout)

        main_layout.addWidget(left_panel)

        right_panel = QFrame()
        right_panel.setStyleSheet(get_panel_style())
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(10)

        view_controls = QHBoxLayout()

        self.compare_check = QCheckBox("Before/After")
        self.compare_check.setStyleSheet(get_checkbox_style())
        self.compare_check.setChecked(True)
        self.compare_check.stateChanged.connect(self.toggleComparison)
        view_controls.addWidget(self.compare_check)

        self.sidebyside_check = QCheckBox("Side-by-Side")
        self.sidebyside_check.setStyleSheet(get_checkbox_style())
        self.sidebyside_check.stateChanged.connect(self.toggleSideBySide)
        view_controls.addWidget(self.sidebyside_check)

        self.view_switcher = QPushButton("Show Original")
        self.view_switcher.setStyleSheet(get_surface_button_style())
        self.view_switcher.clicked.connect(self.toggleView)
        self.view_switcher.setVisible(False)
        view_controls.addWidget(self.view_switcher)

        view_controls.addStretch()

        view_controls.addWidget(QLabel("Zoom:"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setFixedWidth(120)
        self.zoom_slider.setRange(10, 1000)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setStyleSheet(get_slider_style())
        self.zoom_slider.valueChanged.connect(self.onZoomSliderChanged)
        view_controls.addWidget(self.zoom_slider)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setStyleSheet(f"color: {THEME['text_secondary']}; min-width: 50px;")
        view_controls.addWidget(self.zoom_label)

        self.reset_view_btn = QPushButton("Reset View")
        self.reset_view_btn.setStyleSheet(get_surface_button_style())
        self.reset_view_btn.clicked.connect(self.resetAllViews)
        view_controls.addWidget(self.reset_view_btn)

        right_layout.addLayout(view_controls)

        self.view_stack = QStackedWidget()

        self.slider_view = ImageComparisonSlider(self)
        self.slider_view.zoomChanged.connect(self.onZoomChanged)
        self.view_stack.addWidget(self.slider_view)

        self.sidebyside_view = SideBySideView(self)
        self.sidebyside_view.zoomChanged.connect(self.onZoomChanged)
        self.view_stack.addWidget(self.sidebyside_view)

        self.single_view = SingleImageView(self)
        self.single_view.zoomChanged.connect(self.onZoomChanged)
        self.view_stack.addWidget(self.single_view)

        self.video_view = VideoComparisonWidget(self)
        self.video_view.zoomChanged.connect(self.onZoomChanged)
        self.view_stack.addWidget(self.video_view)

        right_layout.addWidget(self.view_stack, 1)

        self.overlay_widget = QWidget(right_panel)
        self.overlay_widget.setStyleSheet(f"""
            background-color: rgba(10, 10, 10, 220);
            border-radius: 8px;
        """)
        overlay_layout = QVBoxLayout(self.overlay_widget)
        overlay_layout.setAlignment(Qt.AlignCenter)

        self.overlay_label = QLabel("Processing...")
        self.overlay_label.setStyleSheet(f"""
            color: {THEME['text']};
            font-size: 24px;
            font-weight: bold;
        """)
        self.overlay_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.overlay_label)

        self.overlay_timer = QLabel("00:00")
        self.overlay_timer.setStyleSheet(f"""
            color: {THEME['text_secondary']};
            font-size: 18px;
        """)
        self.overlay_timer.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.overlay_timer)

        self.overlay_widget.hide()

        main_layout.addWidget(right_panel, 1)

        self.right_panel = right_panel

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'overlay_widget') and hasattr(self, 'right_panel'):
            self.overlay_widget.setGeometry(self.right_panel.rect())

    def updateProcessButton(self):
        if self.input_path and os.path.exists(self.input_path):
            self.process_btn.setEnabled(True)
            self.process_btn.setStyleSheet(get_accent_button_style())
        else:
            self.process_btn.setEnabled(False)
            self.process_btn.setStyleSheet(get_accent_button_disabled_style())

    def showInfo(self):
        import torch
        import shutil

        info_text = f"""<h2>Klarity - Image/Video Restoration Tool</h2>
        <p><b>Version:</b> 1.0</p>
        <hr>
        <p><b>Python:</b> {sys.version.split()[0]}</p>
        <p><b>PyTorch:</b> {torch.__version__}</p>
        <p><b>CUDA:</b> {'Available - ' + torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'Not Available'}</p>
        <p><b>ffmpeg:</b> {'Available' if shutil.which('ffmpeg') else 'NOT FOUND'}</p>
        <hr>
        <p><b>Supported Image Formats:</b><br>
        .jpg, .jpeg, .png, .bmp, .tiff, .tif, .webp</p>
        <p><b>Supported Video Formats:</b><br>
        .mp4, .avi, .mov, .mkv, .webm, .flv, .wmv, .m4v</p>
        <hr>
        <p><b>Credits:</b></p>
        <ul>
        <li>Real-ESRGAN - Upscaling</li>
        <li>NAFNet - Denoising/Deblurring</li>
        <li>RIFE - Frame Interpolation</li>
        </ul>
        <hr>
        <p><b>Tip:</b> Use Ctrl + Mouse Wheel to zoom in/out</p>
        """

        msg = QMessageBox(self)
        msg.setWindowTitle("About Klarity")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info_text)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {THEME['background']};
            }}
            QLabel {{
                color: {THEME['text']};
                min-width: 400px;
            }}
            QPushButton {{
                {get_secondary_button_style()}
                min-width: 80px;
            }}
        """)
        msg.exec_()

    def checkModels(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(script_dir, "models")

        mode = "heavy" if self.mode_combo.currentIndex() == 0 else "lite"

        model_files = {
            'deblur': f'deblur-{mode}.pth',
            'denoise': f'denoise-{mode}.pth',
            'upscale': f'upscale-{mode}.pth',
            'rife': f'framegen-{mode}.pkl'
        }

        all_exist = True
        for name, filename in model_files.items():
            path = os.path.join(models_dir, filename)
            if not os.path.exists(path) or os.path.getsize(path) < 1000:
                all_exist = False
                break

        if all_exist:
            self.model_status.setText(f"✓ All {mode} models ready")
            self.model_status.setStyleSheet(f"color: {THEME['success']}; font-size: 11px;")
            self.download_btn.setVisible(False)
        else:
            self.model_status.setText(f"⚠ Some {mode} models missing")
            self.model_status.setStyleSheet(f"color: {THEME['warning']}; font-size: 11px;")
            self.download_btn.setVisible(True)

    def onModeChanged(self, index):
        self.checkModels()

    def onProcModeChanged(self, index):
        is_frame_mode = index >= 5
        self.frame_combo.setEnabled(is_frame_mode)

        is_upscale_mode = index in [2, 4, 7]
        self.upscale_combo.setEnabled(is_upscale_mode)

    def downloadModels(self):
        mode = "heavy" if self.mode_combo.currentIndex() == 0 else "lite"
        self.model_status.setText("Downloading models...")
        self.model_status.setStyleSheet(f"color: {THEME['warning']}; font-size: 11px;")
        self.download_btn.setEnabled(False)

        def download():
            cmd = _get_klarity_cmd() + ["download-models"]
            if mode == "lite":
                cmd.append("-lite")
            subprocess.run(cmd, cwd=_get_app_dir())

        thread = threading.Thread(target=download)
        thread.start()

        def check_done():
            if thread.is_alive():
                QTimer.singleShot(500, check_done)
            else:
                self.checkModels()
                self.download_btn.setEnabled(True)

        check_done()

    def browseInput(self):
        file_filter = "Media Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.mp4 *.avi *.mov *.mkv *.webm *.flv *.wmv *.m4v);;All Files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", file_filter)

        if path:
            self.input_path = path
            self.result_path = None
            self.input_label.setText(os.path.basename(path))
            self.input_label.setStyleSheet(f"color: {THEME['text']}; font-size: 11px;")

            video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv', '.m4v'}
            self.is_video = Path(path).suffix.lower() in video_exts

            if self.is_video:
                self.proc_mode_combo.clear()
                self.proc_mode_combo.addItems([
                    "Denoise", "Deblur", "Upscale",
                    "Clean (Denoise+Deblur)", "Full (All)",
                    "Frame Generation", "Clean + Frame Gen", "Full + Frame Gen"
                ])
            else:
                self.proc_mode_combo.clear()
                self.proc_mode_combo.addItems([
                    "Denoise", "Deblur", "Upscale",
                    "Clean (Denoise+Deblur)", "Full (All)"
                ])

            self.loadMedia(path)
            self.updateProcessButton()

    def browseOutput(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Folder")

        if path:
            if not path.endswith('/') and not path.endswith('\\'):
                path += '/'
            self.output_path = path
            self.output_label.setText(path.rstrip('/\\'))
            self.output_label.setStyleSheet(f"color: {THEME['text']}; font-size: 11px;")

    def loadMedia(self, path):
        if self.is_video:
            self.view_stack.setCurrentWidget(self.video_view)
            self.video_view.setVideo(path)
            self.compare_check.setEnabled(True)
            self.sidebyside_check.setEnabled(True)
            self.updateVideoView()
        else:
            self.updateImageView()

    def updateVideoView(self):
        if not self.is_video:
            return

        compare_enabled = self.compare_check.isChecked()
        sidebyside_enabled = self.sidebyside_check.isChecked()

        if sidebyside_enabled and compare_enabled:
            self.video_view.setViewMode('sidebyside')
        elif compare_enabled:
            self.video_view.setViewMode('slider')
        else:
            self.video_view.setViewMode('single')

        self.view_switcher.setVisible(not compare_enabled)

    def updateImageView(self):
        if self.is_video:
            return

        compare_enabled = self.compare_check.isChecked()
        sidebyside_enabled = self.sidebyside_check.isChecked()

        before_pixmap = None
        after_pixmap = None

        if self.input_path and os.path.exists(self.input_path):
            before_pixmap = QPixmap(self.input_path)

        if self.result_path and os.path.exists(self.result_path):
            after_pixmap = QPixmap(self.result_path)

        if sidebyside_enabled and compare_enabled:
            self.view_stack.setCurrentWidget(self.sidebyside_view)
            self.sidebyside_view.setBeforeImage(before_pixmap)
            self.sidebyside_view.setAfterImage(after_pixmap)
        elif compare_enabled:
            self.view_stack.setCurrentWidget(self.slider_view)
            self.slider_view.setBeforeImage(before_pixmap)
            self.slider_view.setAfterImage(after_pixmap)
        else:
            self.view_stack.setCurrentWidget(self.single_view)
            self.single_view.setBeforeImage(before_pixmap)
            self.single_view.setAfterImage(after_pixmap)

        self.view_switcher.setVisible(not compare_enabled)

    def toggleComparison(self, state):
        if self.is_video:
            self.updateVideoView()
        else:
            self.updateImageView()

    def toggleSideBySide(self, state):
        self.side_by_side_mode = state == Qt.Checked
        if self.is_video:
            self.updateVideoView()
        else:
            self.updateImageView()

    def toggleView(self):
        if self.is_video:
            self.video_view.setShowingResult(not self.video_view.showing_result)
            is_result = self.video_view.showing_result
        else:
            self.single_view.setShowingResult(not self.single_view.showing_result)
            is_result = self.single_view.showing_result

        self.view_switcher.setText("Show Original" if is_result else "Show Result")

    def onZoomSliderChanged(self, value):
        self.current_zoom = value / 100.0
        self.slider_view.setZoomLevel(self.current_zoom)
        self.sidebyside_view.setZoomLevel(self.current_zoom)
        self.single_view.setZoomLevel(self.current_zoom)
        self.video_view.setZoomLevel(self.current_zoom)
        self.zoom_label.setText(f"{value}%")

    def onZoomChanged(self, zoom_level):
        self.current_zoom = zoom_level
        zoom_percent = int(zoom_level * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(zoom_percent)
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{zoom_percent}%")

    def resetAllViews(self):
        self.current_zoom = 1.0
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(100)
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText("100%")

        self.slider_view.resetView()
        self.sidebyside_view.resetView()
        self.single_view.resetView()
        self.video_view.resetView()

    def startProcessing(self):
        if not self.input_path:
            QMessageBox.warning(self, "No Input", "Please select an input file first.")
            return

        mode = "heavy" if self.mode_combo.currentIndex() == 0 else "lite"

        proc_modes = [
            "denoise", "deblur", "upscale",
            "clean", "full",
            "frame-gen", "clean-frame-gen", "full-frame-gen"
        ]
        proc_mode = proc_modes[self.proc_mode_combo.currentIndex()]

        upscale = "2" if self.upscale_combo.currentIndex() == 0 else "4"
        frame_mult = "2" if self.frame_combo.currentIndex() == 0 else "4"
        device = self.device_combo.currentText().lower()

        cmd = _get_klarity_cmd() + [f"-{mode}", proc_mode, self.input_path, "--json-progress"]

        if proc_mode in ["upscale", "full", "full-frame-gen"]:
            cmd.extend(["--upscale", upscale])

        if proc_mode in ["frame-gen", "clean-frame-gen", "full-frame-gen"]:
            cmd.extend(["--multi", frame_mult])

        if device != "auto":
            cmd.extend(["--device", device])

        if self.output_path:
            cmd.extend(["-o", self.output_path])

        input_p = Path(self.input_path)
        suffix_map = {
            'denoise': '_denoised',
            'deblur': '_deblurred',
            'upscale': '_upscaled',
            'clean': '_cleaned',
            'full': '_enhanced',
            'frame-gen': '_generated',
            'clean-frame-gen': '_clean_generated',
            'full-frame-gen': '_full_enhanced',
        }
        suffix = suffix_map.get(proc_mode, '_processed')
        output_dir = self.output_path if self.output_path else str(input_p.parent)
        expected_output = os.path.join(output_dir, f"{input_p.stem}{suffix}{input_p.suffix}")

        self.processing_thread = ProcessingThread(cmd, self.input_path, expected_output, proc_mode)
        self.processing_thread.progress_update.connect(self.onProgressUpdate)
        self.processing_thread.processing_complete.connect(self.onProcessingComplete)
        self.processing_thread.download_status.connect(self.onDownloadStatus)

        self.process_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.start_time = time.time()
        self.timer.start(1000)

        self.overlay_label.setText("Processing...")
        self.overlay_widget.show()
        self.overlay_widget.setGeometry(self.right_panel.rect())

        self.processing_thread.start()

    def onProgressUpdate(self, percent, step):
        self.progress_bar.setValue(percent)
        self.status_label.setText(step)

    def onDownloadStatus(self, msg, status):
        if status == "downloading":
            self.model_status.setText(f"⬇ {msg[:30]}...")
            self.model_status.setStyleSheet(f"color: {THEME['warning']}; font-size: 11px;")
        elif status == "done":
            self.model_status.setText(f"✓ {msg[:30]}")
            self.model_status.setStyleSheet(f"color: {THEME['success']}; font-size: 11px;")

    def onProcessingComplete(self, result, success):
        self.timer.stop()
        self.overlay_widget.hide()
        self.clear_btn.setEnabled(True)
        self.updateProcessButton()

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Complete!")
            self.status_label.setStyleSheet(f"color: {THEME['success']}; font-size: 11px;")

            actual_result = result
            if not os.path.exists(result):
                input_p = Path(self.input_path)
                search_dir = self.output_path if self.output_path else str(input_p.parent)

                if os.path.exists(search_dir):
                    for f in os.listdir(search_dir):
                        if input_p.stem in f and f != input_p.name:
                            potential = os.path.join(search_dir, f)
                            if os.path.getmtime(potential) > os.path.getmtime(self.input_path):
                                actual_result = potential
                                break

            if os.path.exists(actual_result):
                self.result_path = actual_result

                if self.is_video:
                    self.video_view.setResultVideo(actual_result)
                    self.video_view.current_time = 0
                    self.video_view._update_frame_at_time()
                    self.video_view._update_ui()
                    self.updateVideoView()
                else:
                    self.updateImageView()

                self.view_switcher.setText("Show Original")

                self.overlay_label.setText("Complete!")
                self.overlay_timer.setText(f"Saved: {os.path.basename(actual_result)}")
                self.overlay_widget.show()
                QTimer.singleShot(2000, self.overlay_widget.hide)
            else:
                QMessageBox.warning(self, "Output Not Found",
                    f"Could not find output file.\nExpected location: {result}")
        else:
            self.status_label.setText(result)
            self.status_label.setStyleSheet(f"color: {THEME['error']}; font-size: 11px;")
            QMessageBox.critical(self, "Error", result)

    def updateTimer(self):
        if self.start_time:
            elapsed = time.time() - self.start_time
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self.timer_label.setText(f"Elapsed: {mins:02d}:{secs:02d}")
            self.overlay_timer.setText(f"{mins:02d}:{secs:02d}")

    def clearAll(self):
        self.input_path = None
        self.output_path = None
        self.result_path = None

        self.input_label.setText("No file selected")
        self.input_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self.output_label.setText("Same as input")
        self.output_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")

        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
        self.status_label.setStyleSheet(f"color: {THEME['text_secondary']}; font-size: 11px;")
        self.timer_label.setText("")

        self.slider_view.setBeforeImage(None)
        self.slider_view.setAfterImage(None)
        self.sidebyside_view.setBeforeImage(None)
        self.sidebyside_view.setAfterImage(None)
        self.single_view.setBeforeImage(None)
        self.single_view.setAfterImage(None)

        self.video_view.clear()

        self.overlay_widget.hide()

        self.updateProcessButton()

        self.view_switcher.setText("Show Original")

        self.resetAllViews()

    def closeEvent(self, event):
        if self.processing_thread and self.processing_thread.isRunning():
            reply = QMessageBox.question(
                self, 'Processing in Progress',
                'A process is running. Cancel and exit?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.processing_thread.cancel()
                self.processing_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            self.video_view.clear()
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Klarity')
    app.setApplicationDisplayName('Klarity')
    app.setDesktopFileName('klarity')

    logo_path = os.path.join(_get_app_dir(), 'logo.png')
    if os.path.exists(logo_path):
        app_icon = QIcon(logo_path)
        app.setWindowIcon(app_icon)
        for size in [16, 22, 32, 48, 64, 128, 256]:
            app_icon.addPixmap(QPixmap(logo_path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(THEME['background']))
    palette.setColor(QPalette.WindowText, QColor(THEME['text']))
    palette.setColor(QPalette.Base, QColor(THEME['surface']))
    palette.setColor(QPalette.AlternateBase, QColor(THEME['surface']))
    palette.setColor(QPalette.ToolTipBase, QColor(THEME['surface']))
    palette.setColor(QPalette.ToolTipText, QColor(THEME['text']))
    palette.setColor(QPalette.Text, QColor(THEME['text']))
    palette.setColor(QPalette.Button, QColor(THEME['surface']))
    palette.setColor(QPalette.ButtonText, QColor(THEME['text']))
    palette.setColor(QPalette.BrightText, QColor(THEME['error']))
    palette.setColor(QPalette.Highlight, QColor(THEME['accent']))
    palette.setColor(QPalette.HighlightedText, QColor(THEME['text']))
    app.setPalette(palette)

    window = KlarityGUI()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
