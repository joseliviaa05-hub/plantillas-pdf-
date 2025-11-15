#!/usr/bin/env python3
"""
Editor de Canvas Profesional - Versión Completa
Sistema completo de edición de imágenes con canvas profesional
"""

import json
import math
import os
import random
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PIL import Image, ImageQt
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as pdf_canvas

POINTS_PER_CM = 28.346456692913385

def cm_to_points(value_cm: float) -> float:
    return value_cm * POINTS_PER_CM

def cm_to_pixels(cm: float, dpi: int = 96) -> float:
    inches = cm / 2.54
    return inches * dpi

def pixels_to_cm(pixels: float, dpi: int = 96) -> float:
    inches = pixels / dpi
    return inches * 2.54

# ==================== Clases de Datos ====================

@dataclass
class CanvasImageItem:
    """Imagen en el canvas con todas sus propiedades"""
    image_path: str
    x: float  # posición en cm
    y: float
    width: float  # tamaño en cm
    height: float
    rotation: float = 0
    z_index: int = 0
    locked: bool = False
    visible: bool = True
    opacity: float = 1.0
    original_aspect_ratio: float = 1.0
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class TemplatePreset:
    """Plantilla rápida personalizable"""
    name: str
    cols: int
    rows: int
    photo_width_cm: float
    photo_height_cm: float
    margin_cm: float
    spacing_cm: float = 0.5

# ==================== Item Gráfico Arrastrable ====================

class DraggableImageItem(QGraphicsPixmapItem):
    """Item de imagen arrastrable y redimensionable en el canvas - Estilo Canva"""
    
    def __init__(self, pixmap: QPixmap, canvas_item: CanvasImageItem, canvas_editor, parent=None):
        super().__init__(pixmap, parent)
        self.canvas_item = canvas_item
        self.canvas_editor = canvas_editor
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not canvas_item.locked)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setOpacity(canvas_item.opacity)
        self.setZValue(canvas_item.z_index)
        
        # Configuración de handles (estilo Canva)
        self.handle_size = 12
        self.handle_color = QColor(255, 255, 255)
        self.handle_border_color = QColor(0, 196, 204)  # Cyan de Canva
        self.handle_border_width = 2
        self.handle_hover_scale = 1.3
        self.rotation_handle_distance = 40  # Distancia del handle de rotación
        
        # Estado de interacción
        self.is_resizing = False
        self.is_rotating = False
        self.resize_corner = None
        self.resize_side = None
        self.resize_start_pos = None
        self.resize_start_rect = None
        self.resize_start_pixmap = None
        self.hovered_handle = None
        
        # Transformación
        self.setTransformOriginPoint(self.boundingRect().center())
        self.setRotation(canvas_item.rotation)
        self.setAcceptHoverEvents(True)
        
    def boundingRect(self):
        rect = super().boundingRect()
        # Expandir para incluir handles y handle de rotación
        margin = max(self.handle_size + 5, self.rotation_handle_distance + 15)
        return rect.adjusted(-margin, -margin, margin, margin)
    
    def paint(self, painter, option, widget):
        # Dibujar la imagen
        super().paint(painter, option, widget)
        
        # Dibujar controles si está seleccionado
        if self.isSelected():
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = self.pixmap().rect()
            
            # Borde de selección (estilo Canva)
            pen = QPen(self.handle_border_color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            
            # Dibujar handles en las esquinas (circulares, estilo Canva)
            corners = [
                ('tl', rect.left(), rect.top()),
                ('tr', rect.right(), rect.top()),
                ('bl', rect.left(), rect.bottom()),
                ('br', rect.right(), rect.bottom()),
            ]
            
            for corner_id, x, y in corners:
                self._draw_handle(painter, x, y, corner_id)
            
            # Dibujar handles en los lados
            sides = [
                ('t', (rect.left() + rect.right()) / 2, rect.top()),
                ('b', (rect.left() + rect.right()) / 2, rect.bottom()),
                ('l', rect.left(), (rect.top() + rect.bottom()) / 2),
                ('r', rect.right(), (rect.top() + rect.bottom()) / 2),
            ]
            
            for side_id, x, y in sides:
                self._draw_handle(painter, x, y, side_id)
            
            # Dibujar handle de rotación (arriba, estilo Canva)
            rotation_x = (rect.left() + rect.right()) / 2
            rotation_y = rect.top() - self.rotation_handle_distance
            
            # Línea punteada de conexión
            pen = QPen(self.handle_border_color, 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(
                QPointF(rotation_x, rect.top()),
                QPointF(rotation_x, rotation_y)
            )
            
            # Handle de rotación circular
            self._draw_rotation_handle(painter, rotation_x, rotation_y)
    
    def _draw_handle(self, painter, x, y, handle_id):
        """Dibuja un handle individual (estilo Canva)"""
        size = self.handle_size
        if self.hovered_handle == handle_id:
            size = int(size * self.handle_hover_scale)
        
        # Sombra sutil
        shadow_offset = 1
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QPointF(x + shadow_offset, y + shadow_offset),
            size / 2, size / 2
        )
        
        # Handle principal
        painter.setBrush(QBrush(self.handle_color))
        painter.setPen(QPen(self.handle_border_color, self.handle_border_width))
        painter.drawEllipse(QPointF(x, y), size / 2, size / 2)
    
    def _draw_rotation_handle(self, painter, x, y):
        """Dibuja el handle de rotación (estilo Canva)"""
        size = self.handle_size
        if self.hovered_handle == 'rotation':
            size = int(size * self.handle_hover_scale)
        
        # Sombra
        shadow_offset = 1
        painter.setBrush(QBrush(QColor(0, 0, 0, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QPointF(x + shadow_offset, y + shadow_offset),
            size / 2, size / 2
        )
        
        # Handle con ícono de rotación
        painter.setBrush(QBrush(self.handle_color))
        painter.setPen(QPen(self.handle_border_color, self.handle_border_width))
        painter.drawEllipse(QPointF(x, y), size / 2, size / 2)
        
        # Dibujar símbolo de rotación (flechas curvas)
        painter.setPen(QPen(self.handle_border_color, 1.5))
        arrow_size = size * 0.4
        painter.drawArc(
            QRectF(x - arrow_size, y - arrow_size, arrow_size * 2, arrow_size * 2),
            30 * 16, 300 * 16
        )
    
    def get_handle_at_pos(self, pos):
        """Determinar qué handle se clickeó"""
        rect = self.pixmap().rect()
        handle_size = self.handle_size
        
        # Handle de rotación (comprobar primero)
        rotation_x = (rect.left() + rect.right()) / 2
        rotation_y = rect.top() - self.rotation_handle_distance
        rotation_rect = QRectF(
            rotation_x - handle_size, rotation_y - handle_size,
            handle_size * 2, handle_size * 2
        )
        if rotation_rect.contains(pos):
            return ('rotation', 'rotation')
        
        # Esquinas (redimensionar proporcional)
        corners = {
            'tl': QRectF(rect.left() - handle_size, rect.top() - handle_size, handle_size * 2, handle_size * 2),
            'tr': QRectF(rect.right() - handle_size, rect.top() - handle_size, handle_size * 2, handle_size * 2),
            'bl': QRectF(rect.left() - handle_size, rect.bottom() - handle_size, handle_size * 2, handle_size * 2),
            'br': QRectF(rect.right() - handle_size, rect.bottom() - handle_size, handle_size * 2, handle_size * 2),
        }
        
        for corner, handle_rect in corners.items():
            if handle_rect.contains(pos):
                return ('corner', corner)
        
        # Lados (deformar)
        sides = {
            't': QRectF((rect.left() + rect.right())/2 - handle_size, rect.top() - handle_size, handle_size * 2, handle_size * 2),
            'b': QRectF((rect.left() + rect.right())/2 - handle_size, rect.bottom() - handle_size, handle_size * 2, handle_size * 2),
            'l': QRectF(rect.left() - handle_size, (rect.top() + rect.bottom())/2 - handle_size, handle_size * 2, handle_size * 2),
            'r': QRectF(rect.right() - handle_size, (rect.top() + rect.bottom())/2 - handle_size, handle_size * 2, handle_size * 2),
        }
        
        for side, handle_rect in sides.items():
            if handle_rect.contains(pos):
                return ('side', side)
        
        return (None, None)
    
    def hoverMoveEvent(self, event):
        """Actualizar handle hover y cursor"""
        if not self.isSelected():
            super().hoverMoveEvent(event)
            return
        
        pos = event.pos()
        handle_type, handle_pos = self.get_handle_at_pos(pos)
        
        # Actualizar handle hover
        old_hover = self.hovered_handle
        self.hovered_handle = handle_pos if handle_type else None
        
        if old_hover != self.hovered_handle:
            self.update()
        
        # Actualizar cursor
        if handle_type == 'rotation':
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif handle_type == 'corner':
            cursors = {
                'tl': Qt.CursorShape.SizeFDiagCursor,
                'tr': Qt.CursorShape.SizeBDiagCursor,
                'bl': Qt.CursorShape.SizeBDiagCursor,
                'br': Qt.CursorShape.SizeFDiagCursor,
            }
            self.setCursor(cursors.get(handle_pos, Qt.CursorShape.ArrowCursor))
        elif handle_type == 'side':
            cursors = {
                't': Qt.CursorShape.SizeVerCursor,
                'b': Qt.CursorShape.SizeVerCursor,
                'l': Qt.CursorShape.SizeHorCursor,
                'r': Qt.CursorShape.SizeHorCursor,
            }
            self.setCursor(cursors.get(handle_pos, Qt.CursorShape.ArrowCursor))
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor if not self.canvas_item.locked else Qt.CursorShape.ArrowCursor)
        
        super().hoverMoveEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Limpiar hover state"""
        self.hovered_handle = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.canvas_item.locked:
            pos = event.pos()
            handle_type, handle_pos = self.get_handle_at_pos(pos)
            
            if handle_type == 'rotation':
                self.is_rotating = True
                self.resize_start_pos = event.scenePos()
                event.accept()
                return
            elif handle_type:
                self.is_resizing = True
                self.resize_corner = handle_pos if handle_type == 'corner' else None
                self.resize_side = handle_pos if handle_type == 'side' else None
                self.resize_start_pos = event.scenePos()
                self.resize_start_rect = self.boundingRect()
                self.resize_start_pixmap = self.pixmap()
                event.accept()
                return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if self.is_rotating:
            # Calcular ángulo de rotación desde el centro
            center = self.boundingRect().center()
            scene_pos = event.scenePos()
            local_center = self.mapToScene(center)
            
            import math
            angle = math.degrees(math.atan2(
                scene_pos.y() - local_center.y(),
                scene_pos.x() - local_center.x()
            ))
            
            # Normalizar ángulo
            angle = (angle + 90) % 360
            
            # Snap a ángulos cardinales con Shift
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                snap_angles = [0, 45, 90, 135, 180, 225, 270, 315]
                snap_threshold = 10
                for snap_angle in snap_angles:
                    if abs(angle - snap_angle) < snap_threshold:
                        angle = snap_angle
                        break
            
            self.setRotation(angle)
            self.canvas_item.rotation = angle
            event.accept()
            
        elif self.is_resizing:
            delta = event.scenePos() - self.resize_start_pos
            current_pixmap = self.resize_start_pixmap
            
            if self.resize_corner:
                # Redimensionar desde esquina
                new_width = max(20, current_pixmap.width())
                new_height = max(20, current_pixmap.height())
                
                if self.resize_corner == 'br':
                    new_width = max(20, current_pixmap.width() + delta.x())
                    new_height = max(20, current_pixmap.height() + delta.y())
                elif self.resize_corner == 'bl':
                    new_width = max(20, current_pixmap.width() - delta.x())
                    new_height = max(20, current_pixmap.height() + delta.y())
                elif self.resize_corner == 'tr':
                    new_width = max(20, current_pixmap.width() + delta.x())
                    new_height = max(20, current_pixmap.height() - delta.y())
                elif self.resize_corner == 'tl':
                    new_width = max(20, current_pixmap.width() - delta.x())
                    new_height = max(20, current_pixmap.height() - delta.y())
                
                # Mantener proporción con Shift
                if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    aspect_ratio = current_pixmap.width() / current_pixmap.height()
                    new_height = new_width / aspect_ratio
                
                scaled_pixmap = current_pixmap.scaled(
                    int(new_width), int(new_height),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
                
            elif self.resize_side:
                # Deformar desde lado
                new_width = current_pixmap.width()
                new_height = current_pixmap.height()
                
                if self.resize_side == 'r':
                    new_width = max(20, current_pixmap.width() + delta.x())
                elif self.resize_side == 'l':
                    new_width = max(20, current_pixmap.width() - delta.x())
                elif self.resize_side == 'b':
                    new_height = max(20, current_pixmap.height() + delta.y())
                elif self.resize_side == 't':
                    new_height = max(20, current_pixmap.height() - delta.y())
                
                scaled_pixmap = current_pixmap.scaled(
                    int(new_width), int(new_height),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.setPixmap(scaled_pixmap)
            
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        if self.is_rotating:
            self.is_rotating = False
            self.canvas_editor.update_properties_from_selection()
            self.canvas_editor.save_history_state()
            event.accept()
        elif self.is_resizing:
            self.is_resizing = False
            # Actualizar canvas_item con nuevo tamaño
            dpi = self.canvas_editor.canvas_dpi
            self.canvas_item.width = pixels_to_cm(self.pixmap().width(), dpi)
            self.canvas_item.height = pixels_to_cm(self.pixmap().height(), dpi)
            self.canvas_editor.update_properties_from_selection()
            self.canvas_editor.save_history_state()
            event.accept()
        else:
            super().mouseReleaseEvent(event)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Aplicar smart guides durante el movimiento
            if hasattr(self.canvas_editor, 'show_smart_guides') and self.canvas_editor.show_smart_guides:
                if self.canvas_editor.smart_guides:
                    snap_x, snap_y = self.canvas_editor.smart_guides.find_snap_positions(self)
                    
                    new_pos = value
                    rect = self.sceneBoundingRect()
                    center_offset_x = rect.width() / 2
                    center_offset_y = rect.height() / 2
                    
                    if snap_x is not None:
                        new_pos.setX(snap_x - center_offset_x)
                    if snap_y is not None:
                        new_pos.setY(snap_y - center_offset_y)
                    
                    return new_pos
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Actualizar posición en canvas_item
            if hasattr(self, 'canvas_item') and hasattr(self.canvas_editor, 'canvas_dpi'):
                dpi = self.canvas_editor.canvas_dpi
                pos = self.pos()
                self.canvas_item.x = pixels_to_cm(pos.x(), dpi)
                self.canvas_item.y = pixels_to_cm(pos.y(), dpi)
                self.canvas_editor.update_properties_from_selection()
            
            # Limpiar guías cuando termina el movimiento
            if hasattr(self.canvas_editor, 'smart_guides') and self.canvas_editor.smart_guides:
                self.canvas_editor.smart_guides.clear_guides()
        
        return super().itemChange(change, value)
    
    def contextMenuEvent(self, event):
        """Menú contextual sobre la imagen"""
        if self.canvas_item.locked:
            return
        
        menu = QMenu()
        
        # Panel de transformación
        transform_menu = menu.addMenu("🔄 Transformar")
        
        rotate_free = transform_menu.addAction("🔄 Rotar Libremente...")
        rotate_90_cw = transform_menu.addAction("↷ Rotar +90°")
        rotate_90_ccw = transform_menu.addAction("↶ Rotar -90°")
        transform_menu.addSeparator()
        flip_h = transform_menu.addAction("↔️ Voltear Horizontal")
        flip_v = transform_menu.addAction("↕️ Voltear Vertical")
        
        # Recortar
        crop_action = menu.addAction("✂️ Recortar...")
        
        menu.addSeparator()
        
        # Acciones básicas
        duplicate_action = menu.addAction("📋 Duplicar")
        delete_action = menu.addAction("🗑️ Eliminar")
        
        menu.addSeparator()
        
        # Orden Z
        to_front = menu.addAction("⬆️ Traer al frente")
        to_back = menu.addAction("⬇️ Enviar atrás")
        
        action = menu.exec(event.screenPos())
        
        if action == rotate_free:
            self.canvas_editor.rotate_selected_free()
        elif action == rotate_90_cw:
            self.canvas_editor.rotate_selected(90)
        elif action == rotate_90_ccw:
            self.canvas_editor.rotate_selected(-90)
        elif action == flip_h:
            self.canvas_editor.flip_selected_horizontal()
        elif action == flip_v:
            self.canvas_editor.flip_selected_vertical()
        elif action == crop_action:
            self.canvas_editor.crop_selected()
        elif action == duplicate_action:
            self.canvas_editor.duplicate_selected()
        elif action == delete_action:
            self.canvas_editor.delete_selected()
        elif action == to_front:
            self.canvas_editor.bring_to_front()
        elif action == to_back:
            self.canvas_editor.send_to_back()

# ==================== Editor de Plantillas ====================

class TemplateEditorDialog(QDialog):
    """Diálogo para crear/editar plantillas rápidas"""
    
    def __init__(self, template: TemplatePreset = None, parent=None):
        super().__init__(parent)
        self.template = template
        self.setWindowTitle("✏️ Editar Plantilla" if template else "➕ Nueva Plantilla")
        self.resize(500, 400)
        self.setup_ui()
        
        if template:
            self.load_template(template)
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        form = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Ej: DNI 4x4, Instagram Grid, etc.")
        
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(2)
        
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setValue(2)
        
        self.width_spin = QDoubleSpinBox()
        self.width_spin.setRange(0.5, 30)
        self.width_spin.setValue(3.5)
        self.width_spin.setSuffix(" cm")
        self.width_spin.setDecimals(2)
        
        self.height_spin = QDoubleSpinBox()
        self.height_spin.setRange(0.5, 30)
        self.height_spin.setValue(4.5)
        self.height_spin.setSuffix(" cm")
        self.height_spin.setDecimals(2)
        
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0, 5)
        self.margin_spin.setValue(0.5)
        self.margin_spin.setSuffix(" cm")
        self.margin_spin.setDecimals(2)
        
        self.spacing_spin = QDoubleSpinBox()
        self.spacing_spin.setRange(0, 5)
        self.spacing_spin.setValue(0.5)
        self.spacing_spin.setSuffix(" cm")
        self.spacing_spin.setDecimals(2)
        
        form.addRow("📝 Nombre:", self.name_edit)
        form.addRow("📊 Columnas:", self.cols_spin)
        form.addRow("📊 Filas:", self.rows_spin)
        form.addRow("↔️ Ancho foto:", self.width_spin)
        form.addRow("↕️ Alto foto:", self.height_spin)
        form.addRow("📏 Margen:", self.margin_spin)
        form.addRow("↔️ Espaciado:", self.spacing_spin)
        
        # Preview
        preview_group = QGroupBox("👁️ Vista Previa")
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; background: white; min-height: 150px;")
        preview_layout.addWidget(self.preview_label)
        preview_group.setLayout(preview_layout)
        
        # Conectar cambios para preview
        self.cols_spin.valueChanged.connect(self.update_preview)
        self.rows_spin.valueChanged.connect(self.update_preview)
        self.width_spin.valueChanged.connect(self.update_preview)
        self.height_spin.valueChanged.connect(self.update_preview)
        self.margin_spin.valueChanged.connect(self.update_preview)
        self.spacing_spin.valueChanged.connect(self.update_preview)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addLayout(form)
        layout.addWidget(preview_group)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
        self.update_preview()
    
    def load_template(self, template: TemplatePreset):
        """Cargar datos de plantilla existente"""
        self.name_edit.setText(template.name)
        self.cols_spin.setValue(template.cols)
        self.rows_spin.setValue(template.rows)
        self.width_spin.setValue(template.photo_width_cm)
        self.height_spin.setValue(template.photo_height_cm)
        self.margin_spin.setValue(template.margin_cm)
        self.spacing_spin.setValue(template.spacing_cm)
    
    def update_preview(self):
        """Actualizar vista previa de la plantilla"""
        cols = self.cols_spin.value()
        rows = self.rows_spin.value()
        w = self.width_spin.value()
        h = self.height_spin.value()
        margin = self.margin_spin.value()
        spacing = self.spacing_spin.value()
        
        # Calcular tamaño total
        total_w = margin * 2 + cols * w + (cols - 1) * spacing
        total_h = margin * 2 + rows * h + (rows - 1) * spacing
        
        # Crear preview simple
        preview_w = 300
        preview_h = 200
        
        pixmap = QPixmap(preview_w, preview_h)
        pixmap.fill(Qt.GlobalColor.white)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Escalar para que quepa
        scale = min((preview_w - 20) / total_w, (preview_h - 20) / total_h) * 10  # 10 es factor arbitrario
        
        # Dibujar grid
        painter.setPen(QPen(QColor(0, 120, 215), 2))
        painter.setBrush(QBrush(QColor(200, 230, 255)))
        
        offset_x = (preview_w - cols * w * scale - (cols-1) * spacing * scale) / 2
        offset_y = (preview_h - rows * h * scale - (rows-1) * spacing * scale) / 2
        
        for row in range(rows):
            for col in range(cols):
                x = offset_x + col * (w + spacing) * scale
                y = offset_y + row * (h + spacing) * scale
                painter.drawRect(int(x), int(y), int(w * scale), int(h * scale))
        
        painter.end()
        
        self.preview_label.setPixmap(pixmap)
        
        # Mostrar info
        info = f"Total: {total_w:.1f} x {total_h:.1f} cm | {cols * rows} fotos"
        self.preview_label.setToolTip(info)
    
    def get_template(self) -> TemplatePreset:
        """Obtener la plantilla configurada"""
        return TemplatePreset(
            name=self.name_edit.text(),
            cols=self.cols_spin.value(),
            rows=self.rows_spin.value(),
            photo_width_cm=self.width_spin.value(),
            photo_height_cm=self.height_spin.value(),
            margin_cm=self.margin_spin.value(),
            spacing_cm=self.spacing_spin.value()
        )

# ==================== Sistema de Guías Inteligentes ====================

class SmartGuides:
    """Sistema de guías de alineación inteligentes (estilo Canva)"""
    
    def __init__(self, canvas_editor, snap_threshold=5):
        self.canvas_editor = canvas_editor
        self.snap_threshold = snap_threshold
        self.active_guides = []  # Lista de líneas de guía activas
    
    def find_snap_positions(self, moving_item):
        """Encuentra posiciones de snap para alineación"""
        self.clear_guides()
        
        if not moving_item or not hasattr(moving_item, 'canvas_item'):
            return None, None
        
        moving_rect = moving_item.sceneBoundingRect()
        moving_center_x = moving_rect.center().x()
        moving_center_y = moving_rect.center().y()
        
        snap_x = None
        snap_y = None
        
        # Comparar con otros objetos
        for item in self.canvas_editor.scene.items():
            if not isinstance(item, DraggableImageItem) or item == moving_item:
                continue
            
            other_rect = item.sceneBoundingRect()
            other_center_x = other_rect.center().x()
            other_center_y = other_rect.center().y()
            
            # Alineación vertical (centros)
            if abs(moving_center_x - other_center_x) < self.snap_threshold:
                snap_x = other_center_x
                self.add_vertical_guide(other_center_x)
            
            # Alineación horizontal (centros)
            if abs(moving_center_y - other_center_y) < self.snap_threshold:
                snap_y = other_center_y
                self.add_horizontal_guide(other_center_y)
            
            # Alineación de bordes
            if abs(moving_rect.left() - other_rect.left()) < self.snap_threshold:
                snap_x = other_rect.left() + moving_rect.width() / 2
                self.add_vertical_guide(other_rect.left())
            
            if abs(moving_rect.right() - other_rect.right()) < self.snap_threshold:
                snap_x = other_rect.right() - moving_rect.width() / 2
                self.add_vertical_guide(other_rect.right())
            
            if abs(moving_rect.top() - other_rect.top()) < self.snap_threshold:
                snap_y = other_rect.top() + moving_rect.height() / 2
                self.add_horizontal_guide(other_rect.top())
            
            if abs(moving_rect.bottom() - other_rect.bottom()) < self.snap_threshold:
                snap_y = other_rect.bottom() - moving_rect.height() / 2
                self.add_horizontal_guide(other_rect.bottom())
        
        # Alineación con canvas
        scene_rect = self.canvas_editor.scene.sceneRect()
        canvas_center_x = scene_rect.center().x()
        canvas_center_y = scene_rect.center().y()
        
        if abs(moving_center_x - canvas_center_x) < self.snap_threshold:
            snap_x = canvas_center_x
            self.add_vertical_guide(canvas_center_x)
        
        if abs(moving_center_y - canvas_center_y) < self.snap_threshold:
            snap_y = canvas_center_y
            self.add_horizontal_guide(canvas_center_y)
        
        return snap_x, snap_y
    
    def add_vertical_guide(self, x):
        """Añade guía vertical"""
        scene_rect = self.canvas_editor.scene.sceneRect()
        line = self.canvas_editor.scene.addLine(
            x, scene_rect.top(),
            x, scene_rect.bottom(),
            QPen(QColor(0, 196, 204), 1, Qt.PenStyle.DashLine)
        )
        line.setZValue(9999)
        self.active_guides.append(line)
    
    def add_horizontal_guide(self, y):
        """Añade guía horizontal"""
        scene_rect = self.canvas_editor.scene.sceneRect()
        line = self.canvas_editor.scene.addLine(
            scene_rect.left(), y,
            scene_rect.right(), y,
            QPen(QColor(0, 196, 204), 1, Qt.PenStyle.DashLine)
        )
        line.setZValue(9999)
        self.active_guides.append(line)
    
    def clear_guides(self):
        """Limpia todas las guías activas"""
        for guide in self.active_guides:
            self.canvas_editor.scene.removeItem(guide)
        self.active_guides.clear()

# ==================== Lista de Capas con Drag & Drop ====================

class LayersListWidget(QListWidget):
    """Lista de capas con drag & drop para reordenar"""
    
    layerOrderChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.model().rowsMoved.connect(self.on_rows_moved)
    
    def on_rows_moved(self):
        """Emitir señal cuando se reordenan las capas"""
        self.layerOrderChanged.emit()

# ==================== Canvas Principal ====================

class CanvasEditor(QMainWindow):
    """Editor de Canvas Profesional para trabajar con imágenes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # Estado del canvas
        self.canvas_width_cm = 21.0  # A4 por defecto
        self.canvas_height_cm = 29.7
        self.canvas_dpi = 96
        self.canvas_color = QColor(255, 255, 255)
        self.show_grid = True
        self.show_rulers = True
        self.snap_to_grid = False
        self.show_smart_guides = True  # Guías inteligentes activadas por defecto
        
        # Imágenes en el canvas
        self.canvas_images: List[CanvasImageItem] = []
        self.loaded_images: List[str] = []
        
        # Sistema de guías inteligentes
        self.smart_guides = None  # Se inicializa después de crear scene
        
        # Zoom
        self.zoom_factor = 1.0
        
        # Historial (Undo/Redo)
        self.history: List[str] = []  # JSON states
        self.history_index = -1
        self.max_history = 50
        
        # Plantillas personalizadas
        self.custom_templates: List[TemplatePreset] = []
        self.load_custom_templates()
        
        # Clipboard
        self.clipboard_items: List[CanvasImageItem] = []
        
        self.setWindowTitle("🎨 Canvas Editor Profesional")
        self.resize(1600, 900)
        
        self.setup_ui()
        self.create_canvas()
        self.setup_shortcuts()
        
        # Guardar estado inicial
        self.save_history_state()
    
    def setup_shortcuts(self):
        """Configurar atajos de teclado"""
        # Undo/Redo
        QShortcut(QKeySequence.StandardKey.Undo, self, self.undo)
        QShortcut(QKeySequence.StandardKey.Redo, self, self.redo)
        
        # Selección
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self.select_all)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, self.deselect_all)
        
        # Edición
        QShortcut(QKeySequence.StandardKey.Delete, self, self.delete_selected)
        QShortcut(QKeySequence("Ctrl+D"), self, self.duplicate_selected)
        QShortcut(QKeySequence.StandardKey.Copy, self, self.copy_selected)
        QShortcut(QKeySequence.StandardKey.Paste, self, self.paste_from_clipboard)
        
        # Capas
        QShortcut(QKeySequence("Ctrl+]"), self, self.bring_to_front)
        QShortcut(QKeySequence("Ctrl+["), self, self.send_to_back)
        
        # Zoom
        QShortcut(QKeySequence.StandardKey.ZoomIn, self, lambda: self.change_zoom(0.2))
        QShortcut(QKeySequence.StandardKey.ZoomOut, self, lambda: self.change_zoom(-0.2))
    
    def setup_ui(self):
        """Setup main UI layout"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        
        # Create three main panels
        left_widget = self._create_left_panel()
        center_widget = self._create_center_panel()
        right_widget = self._create_right_panel()
        
        # Assemble main layout
        main_layout.addWidget(left_widget)
        main_layout.addWidget(center_widget, 1)
        main_layout.addWidget(right_widget)
        
        central.setLayout(main_layout)
        self.statusBar().showMessage("Canvas listo ✓")
    
    def _create_left_panel(self):
        """Create left panel with canvas configuration and templates"""
        left_widget = QWidget()
        left_widget.setMaximumWidth(320)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)
        
        # Add components
        config_group = self._create_canvas_config_group()
        apply_canvas_btn = self._create_apply_canvas_button()
        images_group = self._create_images_group()
        templates_group = self._create_templates_group()
        view_group = self._create_view_options_group()
        
        left_panel.addWidget(config_group)
        left_panel.addWidget(apply_canvas_btn)
        left_panel.addWidget(images_group)
        left_panel.addWidget(templates_group)
        left_panel.addWidget(view_group)
        left_panel.addStretch()
        
        left_widget.setLayout(left_panel)
        return left_widget
    
    def _create_canvas_config_group(self):
        """Create canvas configuration group"""
        config_group = QGroupBox("📄 Configuración del Canvas")
        config_layout = QFormLayout()
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "A4 (21 x 29.7 cm)",
            "Carta (21.6 x 27.9 cm)",
            "Instagram Post (1080x1080)",
            "Instagram Story (1080x1920)",
            "10x15 cm (Foto)",
            "13x18 cm",
            "20x25 cm",
            "Personalizado"
        ])
        self.size_combo.currentTextChanged.connect(self.on_size_changed)
        
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Vertical", "Horizontal"])
        self.orientation_combo.currentTextChanged.connect(self.on_orientation_changed)
        
        self.custom_width = QDoubleSpinBox()
        self.custom_width.setRange(5, 100)
        self.custom_width.setValue(21.0)
        self.custom_width.setSuffix(" cm")
        self.custom_width.hide()
        
        self.custom_height = QDoubleSpinBox()
        self.custom_height.setRange(5, 100)
        self.custom_height.setValue(29.7)
        self.custom_height.setSuffix(" cm")
        self.custom_height.hide()
        
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["96 DPI (Pantalla)", "150 DPI (Estándar)", "300 DPI (Impresión)"])
        self.dpi_combo.currentTextChanged.connect(self.on_dpi_changed)
        
        config_layout.addRow("Tamaño:", self.size_combo)
        config_layout.addRow("Orientación:", self.orientation_combo)
        config_layout.addRow("Ancho:", self.custom_width)
        config_layout.addRow("Alto:", self.custom_height)
        config_layout.addRow("Calidad:", self.dpi_combo)
        
        config_group.setLayout(config_layout)
        return config_group
    
    def _create_apply_canvas_button(self):
        """Create apply canvas configuration button"""
        apply_canvas_btn = QPushButton("🔄 Aplicar Configuración")
        apply_canvas_btn.clicked.connect(self.recreate_canvas)
        apply_canvas_btn.setStyleSheet("background: #0078d7; color: white; font-weight: bold; padding: 8px;")
        return apply_canvas_btn
    
    def _create_images_group(self):
        """Create images group for loading images"""
        images_group = QGroupBox("🖼️ Imágenes Disponibles")
        images_layout = QVBoxLayout()
    def _create_images_group(self):
        """Create images group for loading images"""
        images_group = QGroupBox("🖼️ Imágenes Disponibles")
        images_layout = QVBoxLayout()
        
        self.images_list = QListWidget()
        self.images_list.setMaximumHeight(180)
        self.images_list.setDragEnabled(True)
        self.images_list.setAcceptDrops(False)
        
        load_btn = QPushButton("📁 Cargar Imágenes")
        load_btn.clicked.connect(self.load_images)
        
        images_layout.addWidget(self.images_list)
        images_layout.addWidget(load_btn)
        images_group.setLayout(images_layout)
        return images_group
    
    def _create_templates_group(self):
        """Create templates group for quick layouts"""
        templates_group = QGroupBox("📋 Plantillas Rápidas")
        templates_layout = QVBoxLayout()
        
        # Scroll area for templates
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(200)
        
        templates_widget = QWidget()
        templates_inner = QVBoxLayout()
        
        # Predefined templates
        btn_4x4 = QPushButton("📸 4x4 DNI (4 fotos)")
        btn_4x4.clicked.connect(lambda: self.apply_predefined_template("4x4"))
        
        btn_2x3 = QPushButton("📸 2x3 (6 fotos)")
        btn_2x3.clicked.connect(lambda: self.apply_predefined_template("2x3"))
        
        btn_collage = QPushButton("🎨 Collage Libre")
        btn_collage.clicked.connect(lambda: self.apply_predefined_template("collage"))
        
        templates_inner.addWidget(btn_4x4)
        templates_inner.addWidget(btn_2x3)
        templates_inner.addWidget(btn_collage)
        
        # Custom templates
        for template in self.custom_templates:
            btn = QPushButton(f"⭐ {template.name}")
            btn.clicked.connect(lambda checked, t=template: self.apply_custom_template(t))
            templates_inner.addWidget(btn)
        
        templates_inner.addStretch()
        templates_widget.setLayout(templates_inner)
        scroll.setWidget(templates_widget)
        
        # Template management buttons
        template_btns = QHBoxLayout()
        edit_template_btn = QPushButton("✏️ Editar")
        edit_template_btn.clicked.connect(self.edit_template)
        add_template_btn = QPushButton("➕ Nueva")
        add_template_btn.clicked.connect(self.add_new_template)
        template_btns.addWidget(edit_template_btn)
        template_btns.addWidget(add_template_btn)
        
        templates_layout.addWidget(scroll)
        templates_layout.addLayout(template_btns)
        templates_group.setLayout(templates_layout)
        return templates_group
    
    def _create_view_options_group(self):
        """Create view options group"""
        view_group = QGroupBox("👁️ Vista")
        view_layout = QVBoxLayout()
        
        self.grid_check = QCheckBox("Mostrar cuadrícula")
        self.grid_check.setChecked(True)
        self.grid_check.stateChanged.connect(self.toggle_grid)
        self.apply_checkbox_style(self.grid_check)
        
        self.snap_check = QCheckBox("Ajustar a cuadrícula")
        self.snap_check.stateChanged.connect(self.toggle_snap)
        self.apply_checkbox_style(self.snap_check)
        
        self.guides_check = QCheckBox("Guías inteligentes")
        self.guides_check.setChecked(True)
        self.guides_check.stateChanged.connect(self.toggle_smart_guides)
        self.apply_checkbox_style(self.guides_check)
        
        view_layout.addWidget(self.grid_check)
        view_layout.addWidget(self.snap_check)
        view_layout.addWidget(self.guides_check)
        view_group.setLayout(view_layout)
        return view_group
    
    def _create_center_panel(self):
        """Create center panel with canvas view"""
        center_widget = QWidget()
        center_layout = QVBoxLayout()
        
        # Toolbar
        toolbar = self._create_toolbar()
        
        # Graphics View for canvas
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setStyleSheet("background: #cccccc;")
        self.view.setAcceptDrops(True)
        self.view.viewport().installEventFilter(self)
        
        # Inicializar sistema de guías inteligentes
        self.smart_guides = SmartGuides(self)
        
        center_layout.addLayout(toolbar)
        center_layout.addWidget(self.view)
        center_widget.setLayout(center_layout)
        return center_widget
    
    def _create_toolbar(self):
        """Create toolbar with zoom and undo/redo controls"""
        toolbar = QHBoxLayout()
        
        # Zoom controls
        zoom_out_btn = QPushButton("🔍-")
        zoom_out_btn.clicked.connect(lambda: self.change_zoom(-0.2))
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(60)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        zoom_in_btn = QPushButton("🔍+")
        zoom_in_btn.clicked.connect(lambda: self.change_zoom(0.2))
        
        fit_btn = QPushButton("🔲 Ajustar")
        fit_btn.clicked.connect(self.fit_to_view)
        
        toolbar.addWidget(QLabel("<b>Zoom:</b>"))
        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(zoom_in_btn)
        toolbar.addWidget(fit_btn)
        toolbar.addStretch()
        
        # Undo/Redo
        undo_btn = QPushButton("↶ Deshacer")
        undo_btn.clicked.connect(self.undo)
        redo_btn = QPushButton("↷ Rehacer")
        redo_btn.clicked.connect(self.redo)
        
        toolbar.addWidget(undo_btn)
        toolbar.addWidget(redo_btn)
        
        return toolbar
    
    def _create_right_panel(self):
        """Create right panel with properties and actions"""
        right_widget = QWidget()
        right_widget.setMaximumWidth(300)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)
        
        # Add components
        props_group = self._create_properties_group()
        actions_group = self._create_actions_group()
        layers_group = self._create_layers_group()
        export_group = self._create_export_group()
        
        right_panel.addWidget(props_group)
        right_panel.addWidget(actions_group)
        right_panel.addWidget(layers_group)
        right_panel.addWidget(export_group)
        right_panel.addStretch()
        
        right_widget.setLayout(right_panel)
        return right_widget
    
    def _create_properties_group(self):
        """Create properties group for selected images"""
        props_group = QGroupBox("⚙️ Propiedades de Imagen")
        props_layout = QFormLayout()
        
        self.prop_x = QDoubleSpinBox()
        self.prop_x.setRange(-100, 100)
        self.prop_x.setSuffix(" cm")
        self.prop_x.valueChanged.connect(self.update_selected_position)
        
        self.prop_y = QDoubleSpinBox()
        self.prop_y.setRange(-100, 100)
        self.prop_y.setSuffix(" cm")
        self.prop_y.valueChanged.connect(self.update_selected_position)
        
        self.prop_width = QDoubleSpinBox()
        self.prop_width.setRange(0.1, 100)
        self.prop_width.setSuffix(" cm")
        self.prop_width.setDecimals(2)
        self.prop_width.valueChanged.connect(self.update_selected_size)
        
        self.prop_height = QDoubleSpinBox()
        self.prop_height.setRange(0.1, 100)
        self.prop_height.setSuffix(" cm")
        self.prop_height.setDecimals(2)
        self.prop_height.valueChanged.connect(self.update_selected_size)
        
        self.prop_rotation = QSpinBox()
        self.prop_rotation.setRange(0, 359)
        self.prop_rotation.setSuffix("°")
        self.prop_rotation.valueChanged.connect(self.update_selected_rotation)
        
        self.prop_opacity = QSlider(Qt.Orientation.Horizontal)
        self.prop_opacity.setRange(0, 100)
        self.prop_opacity.setValue(100)
        self.prop_opacity.valueChanged.connect(self.update_selected_opacity)
        self.opacity_label = QLabel("100%")
        
        props_layout.addRow("X:", self.prop_x)
        props_layout.addRow("Y:", self.prop_y)
        props_layout.addRow("Ancho:", self.prop_width)
        props_layout.addRow("Alto:", self.prop_height)
        props_layout.addRow("Rotación:", self.prop_rotation)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.prop_opacity)
        opacity_layout.addWidget(self.opacity_label)
        props_layout.addRow("Opacidad:", opacity_layout)
        
        self.lock_aspect = QCheckBox("🔒 Mantener proporción")
        self.lock_aspect.setChecked(True)
        self.apply_checkbox_style(self.lock_aspect)
        props_layout.addRow("", self.lock_aspect)
        
        props_group.setLayout(props_layout)
        return props_group
    
    def _create_actions_group(self):
        """Create actions group for image manipulation"""
        actions_group = QGroupBox("🔧 Acciones")
        actions_layout = QVBoxLayout()
        
        btn_duplicate = QPushButton("📋 Duplicar (Ctrl+D)")
        btn_duplicate.clicked.connect(self.duplicate_selected)
        
        btn_delete = QPushButton("🗑️ Eliminar (Del)")
        btn_delete.clicked.connect(self.delete_selected)
        
        btn_to_front = QPushButton("⬆️ Traer al frente")
        btn_to_front.clicked.connect(self.bring_to_front)
        
        btn_to_back = QPushButton("⬇️ Enviar atrás")
        btn_to_back.clicked.connect(self.send_to_back)
        
        btn_lock = QPushButton("🔒 Bloquear/Desbloquear")
        btn_lock.clicked.connect(self.toggle_lock_selected)
        
        actions_layout.addWidget(btn_duplicate)
        actions_layout.addWidget(btn_delete)
        actions_layout.addWidget(btn_to_front)
        actions_layout.addWidget(btn_to_back)
        actions_layout.addWidget(btn_lock)
        actions_group.setLayout(actions_layout)
        return actions_group
    
    def _create_layers_group(self):
        """Create layers group for layer management"""
        layers_group = QGroupBox("📚 Capas")
        layers_layout = QVBoxLayout()
        
        self.layers_list = LayersListWidget()
        self.layers_list.itemClicked.connect(self.select_layer)
        self.layers_list.layerOrderChanged.connect(self.on_layer_order_changed)
        self.layers_list.setMaximumHeight(250)
        
        layers_layout.addWidget(QLabel("<i>Arrastra para reordenar</i>"))
        layers_layout.addWidget(self.layers_list)
        layers_group.setLayout(layers_layout)
        return layers_group
    
    def _create_export_group(self):
        """Create export group for canvas export"""
        export_group = QGroupBox("💾 Exportar")
        export_layout = QVBoxLayout()
        
        self.export_format = QComboBox()
        self.export_format.addItems(["PDF", "PNG", "JPG", "TIFF"])
        
        btn_export = QPushButton("📥 Exportar Canvas")
        btn_export.clicked.connect(self.export_canvas)
        btn_export.setStyleSheet("background: #4caf50; color: white; font-weight: bold; padding: 10px;")
        
        export_layout.addWidget(QLabel("Formato:"))
        export_layout.addWidget(self.export_format)
        export_layout.addWidget(btn_export)
        export_group.setLayout(export_layout)
        return export_group
    
    def apply_checkbox_style(self, checkbox):
        """Aplicar estilo mejorado a checkbox"""
        checkbox.setStyleSheet("""
            QCheckBox {
                spacing: 8px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #999;
                border-radius: 3px;
                background: white;
            }
            QCheckBox::indicator:checked {
                background: #0078d7;
                border: 2px solid #0078d7;
            }
            QCheckBox::indicator:hover {
                border: 2px solid #0078d7;
            }
        """)
    
    def eventFilter(self, obj, event):
        """Filtrar eventos para drag & drop de imágenes al canvas"""
        if obj == self.view.viewport():
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasUrls() or self.images_list.currentItem():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Type.Drop:
                pos = self.view.mapToScene(event.position().toPoint())
                
                # Drag desde lista de imágenes
                if self.images_list.currentItem():
                    item = self.images_list.currentItem()
                    path = item.data(Qt.ItemDataRole.UserRole)
                    self.add_image_to_canvas_at_pos(path, pos.x(), pos.y())
                    return True
                
                # Drag desde archivos externos
                if event.mimeData().hasUrls():
                    for url in event.mimeData().urls():
                        path = url.toLocalFile()
                        if path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')):
                            self.add_image_to_canvas_at_pos(path, pos.x(), pos.y())
                    return True
        
        return super().eventFilter(obj, event)
    
    def create_canvas(self):
        """Crear el canvas con el tamaño configurado"""
        self.scene.clear()
        
        # Calcular tamaño en píxeles
        width_px = cm_to_pixels(self.canvas_width_cm, self.canvas_dpi)
        height_px = cm_to_pixels(self.canvas_height_cm, self.canvas_dpi)
        
        # Fondo del canvas
        self.canvas_rect = self.scene.addRect(
            0, 0, width_px, height_px,
            QPen(QColor(100, 100, 100)),
            QBrush(self.canvas_color)
        )
        self.canvas_rect.setZValue(-1000)
        
        # Agregar cuadrícula si está habilitada
        if self.show_grid:
            self.draw_grid(width_px, height_px)
        
        # Reglas
        if self.show_rulers:
            self.draw_rulers(width_px, height_px)
        
        self.scene.setSceneRect(0, 0, width_px, height_px)
        self.statusBar().showMessage(
            f"Canvas: {self.canvas_width_cm} x {self.canvas_height_cm} cm "
            f"({int(width_px)} x {int(height_px)} px) @ {self.canvas_dpi} DPI"
        )
    
    def draw_grid(self, width_px, height_px):
        """Dibujar cuadrícula en el canvas"""
        grid_spacing_cm = 1.0
        grid_spacing_px = cm_to_pixels(grid_spacing_cm, self.canvas_dpi)
        
        pen = QPen(QColor(220, 220, 220), 0.5, Qt.PenStyle.DotLine)
        
        # Líneas verticales
        x = grid_spacing_px
        while x < width_px:
            line = self.scene.addLine(x, 0, x, height_px, pen)
            line.setZValue(-999)
            x += grid_spacing_px
        
        # Líneas horizontales
        y = grid_spacing_px
        while y < height_px:
            line = self.scene.addLine(0, y, width_px, y, pen)
            line.setZValue(-999)
            y += grid_spacing_px
    
    def draw_rulers(self, width_px, height_px):
        """Dibujar reglas en los bordes"""
        ruler_size = 20
        font = QFont("Arial", 7)
        
        # Regla horizontal (superior)
        pen = QPen(QColor(150, 150, 150))
        cm_px = cm_to_pixels(1, self.canvas_dpi)
        
        for i in range(int(self.canvas_width_cm) + 1):
            x = i * cm_px
            if x <= width_px:
                line = self.scene.addLine(x, -ruler_size, x, 0, pen)
                line.setZValue(-998)
                text = self.scene.addText(f"{i}", font)
                text.setPos(x - 5, -ruler_size - 2)
                text.setZValue(-998)
        
        # Regla vertical (izquierda)
        for i in range(int(self.canvas_height_cm) + 1):
            y = i * cm_px
            if y <= height_px:
                line = self.scene.addLine(-ruler_size, y, 0, y, pen)
                line.setZValue(-998)
                text = self.scene.addText(f"{i}", font)
                text.setPos(-ruler_size - 5, y - 10)
                text.setZValue(-998)
    
    def load_images(self):
        """Cargar imágenes desde archivos"""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar Imágenes",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp)"
        )
        
        for path in paths:
            if path not in self.loaded_images:
                self.loaded_images.append(path)
                
                # Crear thumbnail
                try:
                    pil_img = Image.open(path)
                    pil_img.thumbnail((64, 64))
                    
                    # Convertir a QPixmap
                    if pil_img.mode == 'RGBA':
                        qimg = ImageQt.ImageQt(pil_img)
                    else:
                        pil_img = pil_img.convert('RGB')
                        data = pil_img.tobytes("raw", "RGB")
                        qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGB888)
                    
                    icon = QIcon(QPixmap.fromImage(qimg))
                    
                    item = QListWidgetItem(icon, os.path.basename(path))
                    item.setData(Qt.ItemDataRole.UserRole, path)
                    self.images_list.addItem(item)
                except Exception as e:
                    print(f"Error cargando {path}: {e}")
        
        self.statusBar().showMessage(f"{len(paths)} imagen(es) cargada(s)", 3000)
    
    def add_image_to_canvas_at_pos(self, path: str, scene_x: float, scene_y: float):
        """Agregar imagen al canvas en posición específica"""
        try:
            # Cargar imagen con soporte de transparencia
            pil_img = Image.open(path)
            
            # Calcular aspect ratio original
            aspect_ratio = pil_img.height / pil_img.width
            
            # Tamaño inicial (5 cm de ancho)
            initial_width_cm = 5.0
            initial_height_cm = initial_width_cm * aspect_ratio
            
            # Convertir posición de píxeles a cm
            x_cm = pixels_to_cm(scene_x, self.canvas_dpi)
            y_cm = pixels_to_cm(scene_y, self.canvas_dpi)
            
            # Crear CanvasImageItem
            canvas_item = CanvasImageItem(
                image_path=path,
                x=x_cm,
                y=y_cm,
                width=initial_width_cm,
                height=initial_height_cm,
                z_index=len(self.canvas_images),
                original_aspect_ratio=aspect_ratio
            )
            
            # Convertir PIL a QPixmap preservando transparencia
            if pil_img.mode == 'RGBA':
                qimg = ImageQt.ImageQt(pil_img)
                pixmap = QPixmap.fromImage(qimg)
            else:
                pil_img_rgb = pil_img.convert('RGB')
                data = pil_img_rgb.tobytes("raw", "RGB")
                qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
            
            # Escalar pixmap
            width_px = cm_to_pixels(initial_width_cm, self.canvas_dpi)
            height_px = cm_to_pixels(initial_height_cm, self.canvas_dpi)
            scaled_pixmap = pixmap.scaled(
                int(width_px), int(height_px),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Crear item gráfico
            graphic_item = DraggableImageItem(scaled_pixmap, canvas_item, self)
            graphic_item.setPos(scene_x, scene_y)
            
            self.scene.addItem(graphic_item)
            self.canvas_images.append(canvas_item)
            
            self.update_layers_list()
            self.save_history_state()
            self.statusBar().showMessage(f"Imagen agregada: {os.path.basename(path)}", 2000)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo cargar la imagen:\n{e}")
    
    def update_layers_list(self):
        """Actualizar lista de capas con thumbnails"""
        self.layers_list.clear()
        
        for idx, img_item in enumerate(reversed(self.canvas_images)):
            try:
                # Crear thumbnail
                pil_img = Image.open(img_item.image_path)
                pil_img.thumbnail((32, 32))
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                else:
                    pil_img = pil_img.convert('RGB')
                    data = pil_img.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGB888)
                
                icon = QIcon(QPixmap.fromImage(qimg))
                
                name = f"Capa {len(self.canvas_images) - idx}"
                list_item = QListWidgetItem(icon, name)
                
                # Guardar índice real (no invertido)
                real_idx = len(self.canvas_images) - 1 - idx
                list_item.setData(Qt.ItemDataRole.UserRole, real_idx)
                
                # Indicadores visuales
                flags = []
                if not img_item.visible:
                    flags.append("👁️‍🗨️")
                if img_item.locked:
                    flags.append("🔒")
                if flags:
                    list_item.setText(f"{name} {' '.join(flags)}")
                
                self.layers_list.addItem(list_item)
            except:
                list_item = QListWidgetItem(f"Capa {len(self.canvas_images) - idx}")
                list_item.setData(Qt.ItemDataRole.UserRole, len(self.canvas_images) - 1 - idx)
                self.layers_list.addItem(list_item)
    
    def on_layer_order_changed(self):
        """Reordenar capas cuando se arrastra en la lista"""
        new_order = []
        for i in range(self.layers_list.count()):
            item = self.layers_list.item(i)
            idx = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(self.canvas_images[idx])
        
        # Invertir porque la lista muestra al revés
        self.canvas_images = list(reversed(new_order))
        
        # Actualizar z-index en el scene
        for idx, canvas_item in enumerate(self.canvas_images):
            canvas_item.z_index = idx
            for item in self.scene.items():
                if isinstance(item, DraggableImageItem) and item.canvas_item == canvas_item:
                    item.setZValue(idx)
        
        self.save_history_state()
        self.statusBar().showMessage("Orden de capas actualizado", 2000)
    
    def select_layer(self, item):
        """Seleccionar capa desde la lista"""
        idx = item.data(Qt.ItemDataRole.UserRole)
        if 0 <= idx < len(self.canvas_images):
            canvas_item = self.canvas_images[idx]
            
            # Deseleccionar todo
            for scene_item in self.scene.items():
                if isinstance(scene_item, DraggableImageItem):
                    scene_item.setSelected(scene_item.canvas_item == canvas_item)
            
            self.update_properties_from_selection()
    
    def update_properties_from_selection(self):
        """Actualizar panel de propiedades desde selección"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if len(selected) == 1:
            canvas_item = selected[0].canvas_item
            
            self.prop_x.blockSignals(True)
            self.prop_y.blockSignals(True)
            self.prop_width.blockSignals(True)
            self.prop_height.blockSignals(True)
            self.prop_rotation.blockSignals(True)
            self.prop_opacity.blockSignals(True)
            
            self.prop_x.setValue(canvas_item.x)
            self.prop_y.setValue(canvas_item.y)
            self.prop_width.setValue(canvas_item.width)
            self.prop_height.setValue(canvas_item.height)
            self.prop_rotation.setValue(int(canvas_item.rotation))
            self.prop_opacity.setValue(int(canvas_item.opacity * 100))
            self.opacity_label.setText(f"{int(canvas_item.opacity * 100)}%")
            
            self.prop_x.blockSignals(False)
            self.prop_y.blockSignals(False)
            self.prop_width.blockSignals(False)
            self.prop_height.blockSignals(False)
            self.prop_rotation.blockSignals(False)
            self.prop_opacity.blockSignals(False)
    
    def update_selected_position(self):
        """Actualizar posición de imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if selected:
            x_cm = self.prop_x.value()
            y_cm = self.prop_y.value()
            
            for item in selected:
                item.canvas_item.x = x_cm
                item.canvas_item.y = y_cm
                
                x_px = cm_to_pixels(x_cm, self.canvas_dpi)
                y_px = cm_to_pixels(y_cm, self.canvas_dpi)
                item.setPos(x_px, y_px)
            
            self.save_history_state()
    
    def update_selected_size(self):
        """Actualizar tamaño de imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        new_width = self.prop_width.value()
        new_height = self.prop_height.value()
        
        for item in selected:
            # Si mantener proporción está activo
            if self.lock_aspect.isChecked():
                # Calcular nuevo alto basado en ancho
                new_height = new_width * item.canvas_item.original_aspect_ratio
                
                self.prop_height.blockSignals(True)
                self.prop_height.setValue(new_height)
                self.prop_height.blockSignals(False)
            
            item.canvas_item.width = new_width
            item.canvas_item.height = new_height
            
            # Reescalar pixmap
            try:
                pil_img = Image.open(item.canvas_item.image_path)
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(new_width, self.canvas_dpi)
                height_px = cm_to_pixels(new_height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                item.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"Error reescalando: {e}")
        
        self.save_history_state()
    
    def update_selected_rotation(self):
        """Actualizar rotación de imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if selected:
            rotation = self.prop_rotation.value()
            
            for item in selected:
                item.canvas_item.rotation = rotation
                item.setRotation(rotation)
            
            self.save_history_state()
    
    def update_selected_opacity(self):
        """Actualizar opacidad de imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if selected:
            opacity = self.prop_opacity.value() / 100.0
            self.opacity_label.setText(f"{self.prop_opacity.value()}%")
            
            for item in selected:
                item.canvas_item.opacity = opacity
                item.setOpacity(opacity)
            
            self.save_history_state()
    
    def rotate_selected_free(self):
        """Rotar libremente imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            QMessageBox.information(self, "Info", "Selecciona una imagen primero")
            return
        
        angle, ok = QInputDialog.getInt(self, "Rotar Libremente", 
                                        "Ángulo de rotación (0-359):", 
                                        0, 0, 359)
        if ok:
            for item in selected:
                item.canvas_item.rotation = angle
                item.setRotation(angle)
                
                self.prop_rotation.blockSignals(True)
                self.prop_rotation.setValue(angle)
                self.prop_rotation.blockSignals(False)
            
            self.save_history_state()
            self.statusBar().showMessage(f"Rotado {angle}°", 2000)
    
    def rotate_selected(self, angle):
        """Rotar imagen seleccionada por ángulo específico"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        for item in selected:
            new_rotation = (item.canvas_item.rotation + angle) % 360
            item.canvas_item.rotation = new_rotation
            item.setRotation(new_rotation)
            
            self.prop_rotation.blockSignals(True)
            self.prop_rotation.setValue(int(new_rotation))
            self.prop_rotation.blockSignals(False)
        
        self.save_history_state()
        self.statusBar().showMessage(f"Rotado {angle}°", 2000)
    
    def flip_selected_horizontal(self):
        """Voltear imagen seleccionada horizontalmente"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        for item in selected:
            try:
                pil_img = Image.open(item.canvas_item.image_path)
                pil_img = pil_img.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Guardar temporalmente
                temp_path = os.path.join(tempfile.gettempdir(), f"flipped_{uuid.uuid4()}.png")
                pil_img.save(temp_path)
                item.canvas_item.image_path = temp_path
                
                # Actualizar pixmap
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(item.canvas_item.width, self.canvas_dpi)
                height_px = cm_to_pixels(item.canvas_item.height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                item.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"Error volteando: {e}")
        
        self.save_history_state()
        self.statusBar().showMessage("Volteado horizontalmente", 2000)
    
    def flip_selected_vertical(self):
        """Voltear imagen seleccionada verticalmente"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        for item in selected:
            try:
                pil_img = Image.open(item.canvas_item.image_path)
                pil_img = pil_img.transpose(Image.FLIP_TOP_BOTTOM)
                
                # Guardar temporalmente
                temp_path = os.path.join(tempfile.gettempdir(), f"flipped_{uuid.uuid4()}.png")
                pil_img.save(temp_path)
                item.canvas_item.image_path = temp_path
                
                # Actualizar pixmap
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(item.canvas_item.width, self.canvas_dpi)
                height_px = cm_to_pixels(item.canvas_item.height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                item.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"Error volteando: {e}")
        
        self.save_history_state()
        self.statusBar().showMessage("Volteado verticalmente", 2000)
    
    def crop_selected(self):
        """Recortar imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            QMessageBox.information(self, "Info", "Selecciona una imagen primero")
            return
        
        QMessageBox.information(self, "Recortar", 
                               "Usa los handles laterales para ajustar el tamaño y recortar la imagen.\n\n"
                               "Tip: Los handles naranjas en los lados permiten estirar/comprimir.")
    
    def duplicate_selected(self):
        """Duplicar imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            QMessageBox.information(self, "Info", "Selecciona una imagen primero")
            return
        
        for item in selected:
            # Crear copia
            new_canvas_item = CanvasImageItem(
                image_path=item.canvas_item.image_path,
                x=item.canvas_item.x + 1.0,
                y=item.canvas_item.y + 1.0,
                width=item.canvas_item.width,
                height=item.canvas_item.height,
                rotation=item.canvas_item.rotation,
                z_index=len(self.canvas_images),
                opacity=item.canvas_item.opacity,
                original_aspect_ratio=item.canvas_item.original_aspect_ratio
            )
            
            new_graphic_item = DraggableImageItem(item.pixmap(), new_canvas_item, self)
            new_graphic_item.setPos(item.pos().x() + 20, item.pos().y() + 20)
            new_graphic_item.setRotation(item.rotation())
            new_graphic_item.setOpacity(item.opacity())
            
            self.scene.addItem(new_graphic_item)
            self.canvas_images.append(new_canvas_item)
        
        self.update_layers_list()
        self.save_history_state()
        self.statusBar().showMessage(f"{len(selected)} imagen(es) duplicada(s)", 2000)
    
    def delete_selected(self):
        """Eliminar imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        for item in selected:
            if not item.canvas_item.locked:
                self.scene.removeItem(item)
                if item.canvas_item in self.canvas_images:
                    self.canvas_images.remove(item.canvas_item)
        
        self.update_layers_list()
        self.save_history_state()
        self.statusBar().showMessage(f"{len(selected)} imagen(es) eliminada(s)", 2000)
    
    def bring_to_front(self):
        """Traer imagen al frente"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        max_z = max([img.z_index for img in self.canvas_images]) if self.canvas_images else 0
        
        for item in selected:
            max_z += 1
            item.canvas_item.z_index = max_z
            item.setZValue(max_z)
        
        self.save_history_state()
        self.statusBar().showMessage("Traído al frente", 2000)
    
    def send_to_back(self):
        """Enviar imagen atrás"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        min_z = min([img.z_index for img in self.canvas_images]) if self.canvas_images else 0
        
        for item in selected:
            min_z -= 1
            item.canvas_item.z_index = min_z
            item.setZValue(min_z)
        
        self.save_history_state()
        self.statusBar().showMessage("Enviado atrás", 2000)
    
    def toggle_lock_selected(self):
        """Bloquear/desbloquear imagen seleccionada"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            QMessageBox.information(self, "Info", "Selecciona una imagen primero")
            return
        
        for item in selected:
            item.canvas_item.locked = not item.canvas_item.locked
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not item.canvas_item.locked)
        
        self.update_layers_list()
        self.save_history_state()
        
        status = "bloqueada(s)" if selected[0].canvas_item.locked else "desbloqueada(s)"
        self.statusBar().showMessage(f"Imagen(es) {status}", 2000)
    
    def select_all(self):
        """Seleccionar todas las imágenes"""
        for item in self.scene.items():
            if isinstance(item, DraggableImageItem):
                item.setSelected(True)
        
        self.statusBar().showMessage("Todas las imágenes seleccionadas", 2000)
    
    def deselect_all(self):
        """Deseleccionar todo"""
        for item in self.scene.items():
            if isinstance(item, DraggableImageItem):
                item.setSelected(False)
        
        self.statusBar().showMessage("Deseleccionado", 2000)
    
    def copy_selected(self):
        """Copiar imágenes seleccionadas al clipboard"""
        selected = [item for item in self.scene.selectedItems() if isinstance(item, DraggableImageItem)]
        
        if not selected:
            return
        
        self.clipboard_items = []
        for item in selected:
            # Copiar canvas_item
            copied = CanvasImageItem(
                image_path=item.canvas_item.image_path,
                x=item.canvas_item.x,
                y=item.canvas_item.y,
                width=item.canvas_item.width,
                height=item.canvas_item.height,
                rotation=item.canvas_item.rotation,
                z_index=item.canvas_item.z_index,
                opacity=item.canvas_item.opacity,
                original_aspect_ratio=item.canvas_item.original_aspect_ratio
            )
            self.clipboard_items.append(copied)
        
        self.statusBar().showMessage(f"{len(selected)} imagen(es) copiada(s)", 2000)
    
    def paste_from_clipboard(self):
        """Pegar imágenes desde clipboard"""
        if not self.clipboard_items:
            return
        
        for canvas_item in self.clipboard_items:
            # Crear nueva instancia con offset
            new_item = CanvasImageItem(
                image_path=canvas_item.image_path,
                x=canvas_item.x + 1.0,
                y=canvas_item.y + 1.0,
                width=canvas_item.width,
                height=canvas_item.height,
                rotation=canvas_item.rotation,
                z_index=len(self.canvas_images),
                opacity=canvas_item.opacity,
                original_aspect_ratio=canvas_item.original_aspect_ratio
            )
            
            # Cargar imagen
            try:
                pil_img = Image.open(canvas_item.image_path)
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(new_item.width, self.canvas_dpi)
                height_px = cm_to_pixels(new_item.height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                graphic_item = DraggableImageItem(scaled_pixmap, new_item, self)
                x_px = cm_to_pixels(new_item.x, self.canvas_dpi)
                y_px = cm_to_pixels(new_item.y, self.canvas_dpi)
                graphic_item.setPos(x_px, y_px)
                graphic_item.setRotation(new_item.rotation)
                graphic_item.setOpacity(new_item.opacity)
                
                self.scene.addItem(graphic_item)
                self.canvas_images.append(new_item)
            except Exception as e:
                print(f"Error pegando: {e}")
        
        self.update_layers_list()
        self.save_history_state()
        self.statusBar().showMessage(f"{len(self.clipboard_items)} imagen(es) pegada(s)", 2000)
    
    def save_history_state(self):
        """Guardar estado actual en el historial"""
        # Serializar estado
        state = {
            'canvas_width': self.canvas_width_cm,
            'canvas_height': self.canvas_height_cm,
            'canvas_dpi': self.canvas_dpi,
            'images': [
                {
                    'path': img.image_path,
                    'x': img.x,
                    'y': img.y,
                    'width': img.width,
                    'height': img.height,
                    'rotation': img.rotation,
                    'z_index': img.z_index,
                    'opacity': img.opacity,
                    'locked': img.locked,
                    'visible': img.visible,
                    'aspect_ratio': img.original_aspect_ratio,
                    'uuid': img.uuid
                }
                for img in self.canvas_images
            ]
        }
        
        state_json = json.dumps(state)
        
        # Eliminar estados futuros si estamos en medio del historial
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        self.history.append(state_json)
        
        # Limitar tamaño del historial
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1
    
    def undo(self):
        """Deshacer última acción"""
        if self.history_index > 0:
            self.history_index -= 1
            self.restore_state(self.history[self.history_index])
            self.statusBar().showMessage("Deshacer", 2000)
    
    def redo(self):
        """Rehacer acción"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.restore_state(self.history[self.history_index])
            self.statusBar().showMessage("Rehacer", 2000)
    
    def restore_state(self, state_json: str):
        """Restaurar estado desde JSON"""
        try:
            state = json.loads(state_json)
            
            # Limpiar canvas actual
            for item in self.scene.items():
                if isinstance(item, DraggableImageItem):
                    self.scene.removeItem(item)
            
            self.canvas_images.clear()
            
            # Restaurar imágenes
            for img_data in state['images']:
                canvas_item = CanvasImageItem(
                    image_path=img_data['path'],
                    x=img_data['x'],
                    y=img_data['y'],
                    width=img_data['width'],
                    height=img_data['height'],
                    rotation=img_data['rotation'],
                    z_index=img_data['z_index'],
                    opacity=img_data['opacity'],
                    locked=img_data['locked'],
                    visible=img_data['visible'],
                    original_aspect_ratio=img_data['aspect_ratio']
                )
                canvas_item.uuid = img_data['uuid']
                
                # Cargar imagen
                pil_img = Image.open(canvas_item.image_path)
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(canvas_item.width, self.canvas_dpi)
                height_px = cm_to_pixels(canvas_item.height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                graphic_item = DraggableImageItem(scaled_pixmap, canvas_item, self)
                x_px = cm_to_pixels(canvas_item.x, self.canvas_dpi)
                y_px = cm_to_pixels(canvas_item.y, self.canvas_dpi)
                graphic_item.setPos(x_px, y_px)
                graphic_item.setRotation(canvas_item.rotation)
                graphic_item.setOpacity(canvas_item.opacity)
                graphic_item.setZValue(canvas_item.z_index)
                graphic_item.setVisible(canvas_item.visible)
                
                self.scene.addItem(graphic_item)
                self.canvas_images.append(canvas_item)
            
            self.update_layers_list()
            
        except Exception as e:
            print(f"Error restaurando estado: {e}")
    
    def load_custom_templates(self):
        """Cargar plantillas personalizadas desde archivo"""
        config_file = os.path.join(os.path.expanduser("~"), ".canvas_templates.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    for t in data:
                        template = TemplatePreset(
                            name=t['name'],
                            cols=t['cols'],
                            rows=t['rows'],
                            photo_width_cm=t['width'],
                            photo_height_cm=t['height'],
                            margin_cm=t['margin'],
                            spacing_cm=t.get('spacing', 0.5)
                        )
                        self.custom_templates.append(template)
            except Exception as e:
                print(f"Error cargando plantillas: {e}")
    
    def save_custom_templates(self):
        """Guardar plantillas personalizadas a archivo"""
        config_file = os.path.join(os.path.expanduser("~"), ".canvas_templates.json")
        
        try:
            data = [
                {
                    'name': t.name,
                    'cols': t.cols,
                    'rows': t.rows,
                    'width': t.photo_width_cm,
                    'height': t.photo_height_cm,
                    'margin': t.margin_cm,
                    'spacing': t.spacing_cm
                }
                for t in self.custom_templates
            ]
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error guardando plantillas: {e}")
    
    def edit_template(self):
        """Editar plantilla seleccionada"""
        # Mostrar diálogo para seleccionar qué plantilla editar
        if not self.custom_templates:
            QMessageBox.information(self, "Info", "No hay plantillas personalizadas para editar")
            return
        
        names = [t.name for t in self.custom_templates]
        name, ok = QInputDialog.getItem(self, "Editar Plantilla", 
                                        "Selecciona plantilla a editar:", 
                                        names, 0, False)
        
        if ok and name:
            template = next((t for t in self.custom_templates if t.name == name), None)
            if template:
                dialog = TemplateEditorDialog(template, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    edited = dialog.get_template()
                    # Reemplazar
                    idx = self.custom_templates.index(template)
                    self.custom_templates[idx] = edited
                    self.save_custom_templates()
                    QMessageBox.information(self, "Éxito", "Plantilla actualizada. Reinicia el editor para ver los cambios.")
    
    def add_new_template(self):
        """Agregar nueva plantilla personalizada"""
        dialog = TemplateEditorDialog(None, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_template = dialog.get_template()
            
            if not new_template.name:
                QMessageBox.warning(self, "Error", "El nombre no puede estar vacío")
                return
            
            self.custom_templates.append(new_template)
            self.save_custom_templates()
            QMessageBox.information(self, "Éxito", f"Plantilla '{new_template.name}' creada. Reinicia el editor para verla en la lista.")
    
    def apply_predefined_template(self, template_name):
        """Aplicar plantilla predefinida"""
        if not self.loaded_images:
            QMessageBox.information(self, "Info", "Carga imágenes primero")
            return
        
        # Limpiar canvas
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Aplicar plantilla? Se eliminarán las imágenes actuales en el canvas.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        for item in self.scene.items():
            if isinstance(item, DraggableImageItem):
                self.scene.removeItem(item)
        
        self.canvas_images.clear()
        
        if template_name == "4x4":
            self.apply_photo_grid_template(2, 2, 3.5, 4.5, 0.5, 0.5)
        elif template_name == "2x3":
            self.apply_photo_grid_template(2, 3, 5.0, 7.0, 0.5, 0.5)
        elif template_name == "collage":
            self.apply_collage_template()
        
        self.update_layers_list()
        self.save_history_state()
        self.statusBar().showMessage(f"Plantilla '{template_name}' aplicada", 2000)
    
    def apply_custom_template(self, template: TemplatePreset):
        """Aplicar plantilla personalizada"""
        if not self.loaded_images:
            QMessageBox.information(self, "Info", "Carga imágenes primero")
            return
        
        reply = QMessageBox.question(
            self, "Confirmar",
            f"¿Aplicar plantilla '{template.name}'? Se eliminarán las imágenes actuales.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        for item in self.scene.items():
            if isinstance(item, DraggableImageItem):
                self.scene.removeItem(item)
        
        self.canvas_images.clear()
        
        self.apply_photo_grid_template(
            template.cols,
            template.rows,
            template.photo_width_cm,
            template.photo_height_cm,
            template.margin_cm,
            template.spacing_cm
        )
        
        self.update_layers_list()
        self.save_history_state()
        self.statusBar().showMessage(f"Plantilla '{template.name}' aplicada", 2000)
    
    def apply_photo_grid_template(self, cols, rows, photo_w_cm, photo_h_cm, margin_cm, spacing_cm):
        """Aplicar plantilla de grid de fotos"""
        if not self.loaded_images:
            return
        
        img_path = self.loaded_images[0]
        
        x_start = margin_cm
        y_start = margin_cm
        
        for row in range(rows):
            for col in range(cols):
                x = x_start + col * (photo_w_cm + spacing_cm)
                y = y_start + row * (photo_h_cm + spacing_cm)
                
                # Cargar imagen
                try:
                    pil_img = Image.open(img_path)
                    aspect_ratio = pil_img.height / pil_img.width
                    
                    canvas_item = CanvasImageItem(
                        image_path=img_path,
                        x=x,
                        y=y,
                        width=photo_w_cm,
                        height=photo_h_cm,
                        z_index=len(self.canvas_images),
                        original_aspect_ratio=aspect_ratio
                    )
                    
                    if pil_img.mode == 'RGBA':
                        qimg = ImageQt.ImageQt(pil_img)
                        pixmap = QPixmap.fromImage(qimg)
                    else:
                        pil_img_rgb = pil_img.convert('RGB')
                        data = pil_img_rgb.tobytes("raw", "RGB")
                        qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                    
                    width_px = cm_to_pixels(photo_w_cm, self.canvas_dpi)
                    height_px = cm_to_pixels(photo_h_cm, self.canvas_dpi)
                    scaled_pixmap = pixmap.scaled(
                        int(width_px), int(height_px),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    
                    graphic_item = DraggableImageItem(scaled_pixmap, canvas_item, self)
                    x_px = cm_to_pixels(x, self.canvas_dpi)
                    y_px = cm_to_pixels(y, self.canvas_dpi)
                    graphic_item.setPos(x_px, y_px)
                    
                    self.scene.addItem(graphic_item)
                    self.canvas_images.append(canvas_item)
                except Exception as e:
                    print(f"Error en grid: {e}")
    
    def apply_collage_template(self):
        """Aplicar template de collage libre"""
        for idx, img_path in enumerate(self.loaded_images[:9]):
            x = random.uniform(1, max(1, self.canvas_width_cm - 6))
            y = random.uniform(1, max(1, self.canvas_height_cm - 6))
            w = random.uniform(4, 8)
            h = random.uniform(4, 8)
            
            try:
                pil_img = Image.open(img_path)
                aspect_ratio = pil_img.height / pil_img.width
                
                canvas_item = CanvasImageItem(
                    image_path=img_path,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    rotation=random.randint(-15, 15),
                    z_index=idx,
                    original_aspect_ratio=aspect_ratio
                )
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(w, self.canvas_dpi)
                height_px = cm_to_pixels(h, self.canvas_dpi)
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                graphic_item = DraggableImageItem(scaled_pixmap, canvas_item, self)
                x_px = cm_to_pixels(x, self.canvas_dpi)
                y_px = cm_to_pixels(y, self.canvas_dpi)
                graphic_item.setPos(x_px, y_px)
                graphic_item.setRotation(canvas_item.rotation)
                
                self.scene.addItem(graphic_item)
                self.canvas_images.append(canvas_item)
            except Exception as e:
                print(f"Error en collage: {e}")
    
    def on_size_changed(self, size_text):
        """Cambiar tamaño del canvas"""
        if "A4" in size_text:
            self.canvas_width_cm = 21.0
            self.canvas_height_cm = 29.7
            self.custom_width.hide()
            self.custom_height.hide()
        elif "Carta" in size_text:
            self.canvas_width_cm = 21.6
            self.canvas_height_cm = 27.9
            self.custom_width.hide()
            self.custom_height.hide()
        elif "Instagram Post" in size_text:
            # 1080x1080 px a 96 DPI
            self.canvas_width_cm = pixels_to_cm(1080, 96)
            self.canvas_height_cm = pixels_to_cm(1080, 96)
            self.custom_width.hide()
            self.custom_height.hide()
        elif "Instagram Story" in size_text:
            # 1080x1920 px a 96 DPI
            self.canvas_width_cm = pixels_to_cm(1080, 96)
            self.canvas_height_cm = pixels_to_cm(1920, 96)
            self.custom_width.hide()
            self.custom_height.hide()
        elif "10x15" in size_text:
            self.canvas_width_cm = 10.0
            self.canvas_height_cm = 15.0
            self.custom_width.hide()
            self.custom_height.hide()
        elif "13x18" in size_text:
            self.canvas_width_cm = 13.0
            self.canvas_height_cm = 18.0
            self.custom_width.hide()
            self.custom_height.hide()
        elif "20x25" in size_text:
            self.canvas_width_cm = 20.0
            self.canvas_height_cm = 25.0
            self.custom_width.hide()
            self.custom_height.hide()
        elif "Personalizado" in size_text:
            self.custom_width.show()
            self.custom_height.show()
            self.canvas_width_cm = self.custom_width.value()
            self.canvas_height_cm = self.custom_height.value()
    
    def on_orientation_changed(self, orientation):
        """Cambiar orientación del canvas"""
        if orientation == "Horizontal":
            self.canvas_width_cm, self.canvas_height_cm = self.canvas_height_cm, self.canvas_width_cm
    
    def on_dpi_changed(self, dpi_text):
        """Cambiar DPI del canvas"""
        if "96" in dpi_text:
            self.canvas_dpi = 96
        elif "150" in dpi_text:
            self.canvas_dpi = 150
        elif "300" in dpi_text:
            self.canvas_dpi = 300
    
    def recreate_canvas(self):
        """Recrear canvas con nueva configuración"""
        if "Personalizado" in self.size_combo.currentText():
            self.canvas_width_cm = self.custom_width.value()
            self.canvas_height_cm = self.custom_height.value()
        
        reply = QMessageBox.question(
            self, "Confirmar",
            "¿Recrear canvas? Se perderán las imágenes actuales.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.canvas_images.clear()
            self.create_canvas()
            self.update_layers_list()
            self.save_history_state()
    
    def toggle_grid(self, state):
        """Mostrar/ocultar cuadrícula"""
        self.show_grid = state == Qt.CheckState.Checked.value
        self.create_canvas()
        
        # Re-agregar todas las imágenes
        items_copy = self.canvas_images.copy()
        self.canvas_images.clear()
        
        for item in self.scene.items():
            if isinstance(item, DraggableImageItem):
                self.scene.removeItem(item)
        
        for canvas_item in items_copy:
            try:
                pil_img = Image.open(canvas_item.image_path)
                
                if pil_img.mode == 'RGBA':
                    qimg = ImageQt.ImageQt(pil_img)
                    pixmap = QPixmap.fromImage(qimg)
                else:
                    pil_img_rgb = pil_img.convert('RGB')
                    data = pil_img_rgb.tobytes("raw", "RGB")
                    qimg = QImage(data, pil_img_rgb.width, pil_img_rgb.height, QImage.Format.Format_RGB888)
                    pixmap = QPixmap.fromImage(qimg)
                
                width_px = cm_to_pixels(canvas_item.width, self.canvas_dpi)
                height_px = cm_to_pixels(canvas_item.height, self.canvas_dpi)
                
                scaled_pixmap = pixmap.scaled(
                    int(width_px), int(height_px),
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                graphic_item = DraggableImageItem(scaled_pixmap, canvas_item, self)
                x_px = cm_to_pixels(canvas_item.x, self.canvas_dpi)
                y_px = cm_to_pixels(canvas_item.y, self.canvas_dpi)
                graphic_item.setPos(x_px, y_px)
                graphic_item.setRotation(canvas_item.rotation)
                graphic_item.setOpacity(canvas_item.opacity)
                graphic_item.setZValue(canvas_item.z_index)
                
                self.scene.addItem(graphic_item)
                self.canvas_images.append(canvas_item)
            except Exception as e:
                print(f"Error re-agregando imagen: {e}")
    
    def toggle_snap(self, state):
        """Activar/desactivar ajuste a cuadrícula"""
        self.snap_to_grid = state == Qt.CheckState.Checked.value
    
    def toggle_smart_guides(self, state):
        """Activar/desactivar guías inteligentes"""
        self.show_smart_guides = state == Qt.CheckState.Checked.value
        if not self.show_smart_guides and self.smart_guides:
            self.smart_guides.clear_guides()
    
    def change_zoom(self, delta):
        """Cambiar zoom"""
        self.zoom_factor = max(0.1, min(5.0, self.zoom_factor + delta))
        self.view.resetTransform()
        self.view.scale(self.zoom_factor, self.zoom_factor)
        self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
    
    def fit_to_view(self):
        """Ajustar canvas a la vista"""
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = self.view.transform().m11()
        self.zoom_label.setText(f"{int(self.zoom_factor * 100)}%")
    
    def export_canvas(self):
        """Exportar canvas a archivo"""
        format_map = {
            "PDF": "*.pdf",
            "PNG": "*.png",
            "JPG": "*.jpg",
            "TIFF": "*.tiff"
        }
        
        format_sel = self.export_format.currentText()
        filter_str = f"{format_sel} Files ({format_map[format_sel]})"
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar Canvas",
            f"canvas.{format_sel.lower()}",
            filter_str
        )
        
        if not path:
            return
        
        try:
            if format_sel == "PDF":
                self.export_to_pdf(path)
            else:
                self.export_to_image(path, format_sel)
            
            QMessageBox.information(self, "Éxito", f"Canvas exportado a:\n{path}")
            self.statusBar().showMessage("Canvas exportado ✓", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo exportar: {e}")
    
    def export_to_pdf(self, output_path):
        """Exportar canvas a PDF"""
        width_pt = cm_to_points(self.canvas_width_cm)
        height_pt = cm_to_points(self.canvas_height_cm)
        
        c = pdf_canvas.Canvas(output_path, pagesize=(width_pt, height_pt))
        
        # Ordenar por z-index
        sorted_images = sorted(self.canvas_images, key=lambda x: x.z_index)
        
        for canvas_img in sorted_images:
            if not canvas_img.visible:
                continue
            
            try:
                img = Image.open(canvas_img.image_path)
                
                # Guardar temporalmente
                temp_path = os.path.join(tempfile.gettempdir(), f"temp_{uuid.uuid4()}.png")
                
                # Aplicar rotación si es necesario
                if canvas_img.rotation != 0:
                    img = img.rotate(-canvas_img.rotation, expand=True)
                
                img.save(temp_path)
                
                # Convertir posición y tamaño a puntos
                x_pt = cm_to_points(canvas_img.x)
                y_pt = height_pt - cm_to_points(canvas_img.y) - cm_to_points(canvas_img.height)
                w_pt = cm_to_points(canvas_img.width)
                h_pt = cm_to_points(canvas_img.height)
                
                # Dibujar imagen
                c.drawImage(temp_path, x_pt, y_pt, width=w_pt, height=h_pt, 
                           preserveAspectRatio=False, mask='auto')
                
                # Limpiar archivo temporal
                os.remove(temp_path)
            except Exception as e:
                print(f"Error exportando imagen a PDF: {e}")
        
        c.save()
    
    def export_to_image(self, output_path, format_name):
        """Exportar canvas a imagen"""
        width_px = int(cm_to_pixels(self.canvas_width_cm, self.canvas_dpi))
        height_px = int(cm_to_pixels(self.canvas_height_cm, self.canvas_dpi))
        
        # Determinar formato de imagen
        if format_name == "PNG":
            image = QImage(width_px, height_px, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
        else:
            image = QImage(width_px, height_px, QImage.Format.Format_RGB32)
            image.fill(self.canvas_color)
        
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Renderizar solo el canvas y las imágenes
        self.canvas_rect.setVisible(format_name != "PNG")  # Ocultar fondo en PNG
        self.scene.render(painter, QRectF(0, 0, width_px, height_px), 
                         QRectF(0, 0, width_px, height_px))
        self.canvas_rect.setVisible(True)
        
        painter.end()
        
        # Guardar
        if format_name == "JPG":
            image.save(output_path, "JPEG", 95)
        else:
            image.save(output_path, format_name)
    
    def wheelEvent(self, event):
        """Zoom con rueda del mouse (Ctrl + Scroll)"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            zoom_delta = 0.1 if delta > 0 else -0.1
            self.change_zoom(zoom_delta)
            event.accept()
        else:
            super().wheelEvent(event)
    
    def closeEvent(self, event):
        """Guardar configuración al cerrar"""
        # Guardar plantillas personalizadas
        self.save_custom_templates()
        event.accept()

# ==================== DEMO STANDALONE ====================

def main():
    """Ejecutar Canvas Editor standalone"""
    app = QApplication(sys.argv)
    app.setApplicationName("Canvas Editor Profesional")
    app.setStyle("Fusion")
    
    window = CanvasEditor()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()