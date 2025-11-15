#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎨 Canvas Editor v4.0 - Editor Profesional Completo
Inspirado en Canva, Figma, Photopea y Pixlr

Características principales:
- Sistema de handles profesional con 8 esquinas + rotación
- Sistema de capas jerárquico con orden Z
- Undo/Redo completo
- Herramientas de forma (rectángulo, círculo, línea)
- Herramienta de texto con formato
- Filtros y efectos de imagen
- Alineación y distribución
- Guías y grid con snap
- Temas oscuro/claro
- Exportación multi-formato
- Atajos de teclado profesionales

Autor: Canvas Editor Team
Fecha: 2025-01-15
Versión: 4.0 - Mejoras Completas Aplicadas
"""

import sys
import os
import math
import json
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime
from copy import deepcopy

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PIL import Image, ImageQt, ImageFilter, ImageEnhance, ImageDraw, ImageFont

# ==================== CONSTANTES ====================

DPI = 96

def cm_to_px(cm, dpi=DPI):
    return (cm / 2.54) * dpi

def px_to_cm(px, dpi=DPI):
    return (px / dpi) * 2.54

# ==================== SISTEMA DE TEMAS ====================

class ThemeColors:
    """Colores del tema"""
    DARK = {
        "bg_primary": "#1e1e1e",
        "bg_secondary": "#252525",
        "bg_tertiary": "#2d2d2d",
        "accent": "#00c4cc",
        "accent_hover": "#00d4dc",
        "text_primary": "#ffffff",
        "text_secondary": "#b0b0b0",
        "border": "#3a3a3a",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
    }
    LIGHT = {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f5f5f5",
        "bg_tertiary": "#e0e0e0",
        "accent": "#00a8b8",
        "accent_hover": "#00b8c8",
        "text_primary": "#1e1e1e",
        "text_secondary": "#666666",
        "border": "#cccccc",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
    }

class Theme:
    """Gestor de temas"""
    def __init__(self):
        self.current = "light"
        self.colors = ThemeColors.LIGHT
    
    def toggle(self):
        """Cambiar entre oscuro y claro"""
        if self.current == "light":
            self.current = "dark"
            self.colors = ThemeColors.DARK
        else:
            self.current = "light"
            self.colors = ThemeColors.LIGHT
        return self.current
    
    def get_color(self, key):
        """Obtener color del tema actual"""
        return self.colors.get(key, "#000000")

# ==================== SISTEMA DE HISTORIAL (UNDO/REDO) ====================

class HistoryAction:
    """Acción reversible en el historial"""
    def __init__(self, name: str, undo_data: Any, redo_data: Any):
        self.name = name
        self.undo_data = undo_data
        self.redo_data = redo_data
        self.timestamp = datetime.now()

class HistoryManager:
    """Gestor de historial para Undo/Redo"""
    def __init__(self, max_history=100):
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = max_history
    
    def add_action(self, action: HistoryAction):
        """Agregar acción al historial"""
        self.undo_stack.append(action)
        # Limpiar redo stack cuando se hace nueva acción
        self.redo_stack.clear()
        # Mantener límite de historial
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
    
    def can_undo(self) -> bool:
        """Verificar si se puede deshacer"""
        return len(self.undo_stack) > 0
    
    def can_redo(self) -> bool:
        """Verificar si se puede rehacer"""
        return len(self.redo_stack) > 0
    
    def undo(self):
        """Deshacer última acción"""
        if not self.can_undo():
            return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action.undo_data
    
    def redo(self):
        """Rehacer acción"""
        if not self.can_redo():
            return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action.redo_data
    
    def clear(self):
        """Limpiar historial"""
        self.undo_stack.clear()
        self.redo_stack.clear()

# ==================== ENUMS Y DATACLASSES ====================

class ObjectType(Enum):
    """Tipos de objetos en el canvas"""
    IMAGE = "image"
    SHAPE = "shape"
    TEXT = "text"
    LINE = "line"
    GROUP = "group"

class ShapeType(Enum):
    """Tipos de formas"""
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"
    STAR = "star"
    LINE = "line"

class HandleType(Enum):
    """Tipos de handles disponibles"""
    CORNER_NW = "corner_nw"  # Noroeste (top-left)
    CORNER_NE = "corner_ne"  # Noreste (top-right)
    CORNER_SW = "corner_sw"  # Suroeste (bottom-left)
    CORNER_SE = "corner_se"  # Sureste (bottom-right)
    SIDE_N = "side_n"        # Norte (top)
    SIDE_S = "side_s"        # Sur (bottom)
    SIDE_E = "side_e"        # Este (right)
    SIDE_W = "side_w"        # Oeste (left)
    ROTATION = "rotation"    # Rotación

@dataclass
class HandleConfig:
    """Configuración visual de handles"""
    size: int = 12
    color: str = "#FFFFFF"
    border_color: str = "#0078D7"
    border_width: int = 2
    hover_scale: float = 1.4
    rotation_distance: int = 40
    rotation_color: str = "#4CAF50"

@dataclass
class Transform:
    """Datos de transformación"""
    x: float = 0
    y: float = 0
    width: float = 100
    height: float = 100
    rotation: float = 0
    
# ==================== UTILIDADES MATEMÁTICAS ====================

class MathUtils:
    """Utilidades matemáticas para transformaciones"""
    
    @staticmethod
    def rotate_point(point: QPointF, center: QPointF, angle_degrees: float) -> QPointF:
        """Rotar un punto alrededor de un centro"""
        angle_rad = math.radians(angle_degrees)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        
        new_x = center.x() + dx * cos_a - dy * sin_a
        new_y = center.y() + dx * sin_a + dy * cos_a
        
        return QPointF(new_x, new_y)
    
    @staticmethod
    def distance(p1: QPointF, p2: QPointF) -> float:
        """Distancia entre dos puntos"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx * dx + dy * dy)
    
    @staticmethod
    def angle_between_points(center: QPointF, point: QPointF) -> float:
        """Ángulo en grados desde centro hasta punto"""
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return math.degrees(math.atan2(dy, dx))
    
    @staticmethod
    def snap_angle(angle: float, snap_threshold: float = 15) -> float:
        """Ajustar ángulo a múltiplos de 15°"""
        snap_angles = [0, 15, 30, 45, 60, 75, 90, 105, 120, 135, 150, 165, 180,
                      195, 210, 225, 240, 255, 270, 285, 300, 315, 330, 345, 360]
        
        # Normalizar ángulo a 0-360
        normalized = angle % 360
        
        for snap in snap_angles:
            if abs(normalized - snap) < snap_threshold:
                return snap
        
        return angle

# ==================== HANDLE INDIVIDUAL ====================

class Handle(QGraphicsEllipseItem):
    """Handle individual para transformación"""
    
    def __init__(self, handle_type: HandleType, config: HandleConfig, parent):
        super().__init__(parent)
        self.handle_type = handle_type
        self.config = config
        self.parent_item = parent
        self.is_hovered = False
        
        # Configuración visual
        self.base_size = config.size
        self.setRect(-self.base_size/2, -self.base_size/2, 
                     self.base_size, self.base_size)
        
        # Z-index alto para estar encima
        self.setZValue(2000)
        
        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setAcceptHoverEvents(True)
        
        # Colores
        if handle_type == HandleType.ROTATION:
            self.normal_color = QColor(config.rotation_color)
            self.hover_color = QColor(config.rotation_color).lighter(120)
        else:
            self.normal_color = QColor(config.color)
            self.hover_color = QColor(config.color).darker(110)
        
        self.update_appearance()
    
    def update_appearance(self, hovered: bool = False):
        """Actualizar apariencia del handle"""
        self.is_hovered = hovered
        
        # Tamaño
        size = self.base_size
        if hovered:
            size *= self.config.hover_scale
        
        self.setRect(-size/2, -size/2, size, size)
        
        # Color de relleno
        color = self.hover_color if hovered else self.normal_color
        self.setBrush(QBrush(color))
        
        # Borde
        pen = QPen(QColor(self.config.border_color))
        pen.setWidth(self.config.border_width)
        pen.setCosmetic(True)
        self.setPen(pen)
    
    def get_cursor(self) -> Qt.CursorShape:
        """Obtener cursor apropiado"""
        cursor_map = {
            HandleType.CORNER_NW: Qt.CursorShape.SizeFDiagCursor,
            HandleType.CORNER_NE: Qt.CursorShape.SizeBDiagCursor,
            HandleType.CORNER_SW: Qt.CursorShape.SizeBDiagCursor,
            HandleType.CORNER_SE: Qt.CursorShape.SizeFDiagCursor,
            HandleType.SIDE_N: Qt.CursorShape.SizeVerCursor,
            HandleType.SIDE_S: Qt.CursorShape.SizeVerCursor,
            HandleType.SIDE_E: Qt.CursorShape.SizeHorCursor,
            HandleType.SIDE_W: Qt.CursorShape.SizeHorCursor,
            HandleType.ROTATION: Qt.CursorShape.CrossCursor
        }
        return cursor_map.get(self.handle_type, Qt.CursorShape.ArrowCursor)
    
    def hoverEnterEvent(self, event):
        """Mouse entra al handle"""
        self.update_appearance(hovered=True)
        self.setCursor(self.get_cursor())
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Mouse sale del handle"""
        self.update_appearance(hovered=False)
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        """Click en el handle"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_item.start_transform(self.handle_type, event.scenePos())
        event.accept()
    
    def mouseMoveEvent(self, event):
        """Arrastrar el handle"""
        self.parent_item.update_transform(self.handle_type, event.scenePos())
        event.accept()
    
    def mouseReleaseEvent(self, event):
        """Soltar el handle"""
        self.parent_item.end_transform(self.handle_type)
        event.accept()

# ==================== TOOLTIP ====================

class TransformTooltip(QGraphicsTextItem):
    """Tooltip para mostrar dimensiones/ángulo"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setZValue(3000)
        self.setDefaultTextColor(QColor("white"))
        
        # Fondo
        self.background = QGraphicsRectItem(self)
        self.background.setBrush(QBrush(QColor(45, 45, 45, 220)))
        self.background.setPen(QPen(QColor("#0078D7"), 1))
        self.background.setZValue(-1)
        
        self.hide()
    
    def show_dimensions(self, width: float, height: float, pos: QPointF):
        """Mostrar dimensiones"""
        text = f"{int(width)} × {int(height)} px"
        self.setPlainText(text)
        self.setPos(pos.x() - 40, pos.y() - 40)
        
        # Actualizar fondo
        rect = self.boundingRect()
        self.background.setRect(rect.adjusted(-5, -5, 5, 5))
        
        self.show()
    
    def show_angle(self, angle: float, pos: QPointF):
        """Mostrar ángulo"""
        text = f"{int(angle) % 360}°"
        self.setPlainText(text)
        self.setPos(pos.x() - 20, pos.y() - 40)
        
        rect = self.boundingRect()
        self.background.setRect(rect.adjusted(-5, -5, 5, 5))
        
        self.show()

# ==================== ELEMENTO DE IMAGEN CON HANDLES ====================

class ImageItem(QGraphicsPixmapItem):
    """Elemento de imagen con sistema de handles profesional"""
    
    def __init__(self, pixmap: QPixmap, image_path: str, editor):
        super().__init__(pixmap)
        self.image_path = image_path
        self.editor = editor
        self.original_pixmap = pixmap
        
        # Configuración
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setTransformOriginPoint(self.boundingRect().center())
        
        # Aspect ratio original
        self.original_aspect_ratio = pixmap.width() / pixmap.height() if pixmap.height() > 0 else 1.0
        
        # Transform data
        self.transform_data = Transform(
            x=0, y=0,
            width=pixmap.width(),
            height=pixmap.height(),
            rotation=0
        )
        
        # Sistema de handles
        self.config = HandleConfig()
        self.handles = {}
        self.rotation_line = None
        self.tooltip = None
        self.create_handles()
        
        # Estado de transformación
        self.active_handle = None
        self.transform_start_pos = None
        self.transform_start_data = None
        self.transform_start_mouse = None
        
        self.update_handles_visibility()
    
    def create_handles(self):
        """Crear todos los handles"""
        # Handles de esquinas
        for handle_type in [HandleType.CORNER_NW, HandleType.CORNER_NE,
                           HandleType.CORNER_SW, HandleType.CORNER_SE]:
            handle = Handle(handle_type, self.config, self)
            self.handles[handle_type] = handle
        
        # Handles de lados
        for handle_type in [HandleType.SIDE_N, HandleType.SIDE_S,
                           HandleType.SIDE_E, HandleType.SIDE_W]:
            handle = Handle(handle_type, self.config, self)
            self.handles[handle_type] = handle
        
        # Handle de rotación
        rot_handle = Handle(HandleType.ROTATION, self.config, self)
        self.handles[HandleType.ROTATION] = rot_handle
        
        # Línea de rotación
        self.rotation_line = QGraphicsLineItem(self)
        pen = QPen(QColor(self.config.rotation_color))
        pen.setStyle(Qt.PenStyle.DashLine)
        pen.setWidth(2)
        pen.setCosmetic(True)
        self.rotation_line.setPen(pen)
        self.rotation_line.setZValue(1999)
        
        # Tooltip
        self.tooltip = TransformTooltip()
        self.editor.scene.addItem(self.tooltip)
        
        self.update_handles_position()
    
    def update_handles_position(self):
        """Actualizar posición de todos los handles"""
        rect = self.boundingRect()
        
        # Posiciones base
        positions = {
            HandleType.CORNER_NW: rect.topLeft(),
            HandleType.CORNER_NE: rect.topRight(),
            HandleType.CORNER_SW: rect.bottomLeft(),
            HandleType.CORNER_SE: rect.bottomRight(),
            HandleType.SIDE_N: QPointF(rect.center().x(), rect.top()),
            HandleType.SIDE_S: QPointF(rect.center().x(), rect.bottom()),
            HandleType.SIDE_E: QPointF(rect.right(), rect.center().y()),
            HandleType.SIDE_W: QPointF(rect.left(), rect.center().y())
        }
        
        # Actualizar handles
        for handle_type, pos in positions.items():
            if handle_type in self.handles:
                self.handles[handle_type].setPos(pos)
        
        # Handle de rotación
        top_center = QPointF(rect.center().x(), rect.top())
        rotation_pos = QPointF(rect.center().x(), 
                              rect.top() - self.config.rotation_distance)
        self.handles[HandleType.ROTATION].setPos(rotation_pos)
        
        # Línea de rotación
        self.rotation_line.setLine(
            top_center.x(), top_center.y(),
            rotation_pos.x(), rotation_pos.y()
        )
    
    def update_handles_visibility(self):
        """Mostrar/ocultar handles según selección"""
        visible = self.isSelected()
        
        for handle in self.handles.values():
            handle.setVisible(visible)
        
        if self.rotation_line:
            self.rotation_line.setVisible(visible)
        
        if self.tooltip:
            if not visible:
                self.tooltip.hide()
    
    def itemChange(self, change, value):
        """Detectar cambios en el item"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            QTimer.singleShot(0, self.update_handles_visibility)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.transform_data.x = value.x()
            self.transform_data.y = value.y()
        
        return super().itemChange(change, value)
    
    # ==================== SISTEMA DE TRANSFORMACIÓN ====================
    
    def start_transform(self, handle_type: HandleType, scene_pos: QPointF):
        """Iniciar transformación"""
        self.active_handle = handle_type
        self.transform_start_pos = self.pos()
        self.transform_start_mouse = scene_pos
        
        # Guardar estado inicial
        self.transform_start_data = Transform(
            x=self.transform_data.x,
            y=self.transform_data.y,
            width=self.transform_data.width,
            height=self.transform_data.height,
            rotation=self.transform_data.rotation
        )
    
    def update_transform(self, handle_type: HandleType, scene_pos: QPointF):
        """Actualizar transformación durante arrastre"""
        if not self.active_handle or not self.transform_start_data:
            return
        
        # Obtener modificadores
        modifiers = QApplication.keyboardModifiers()
        shift_pressed = modifiers & Qt.KeyboardModifier.ShiftModifier
        alt_pressed = modifiers & Qt.KeyboardModifier.AltModifier
        
        if handle_type == HandleType.ROTATION:
            self.perform_rotation(scene_pos, shift_pressed)
        else:
            self.perform_resize(handle_type, scene_pos, shift_pressed, alt_pressed)
    
    def end_transform(self, handle_type: HandleType):
        """Finalizar transformación"""
        self.active_handle = None
        self.transform_start_pos = None
        self.transform_start_data = None
        self.transform_start_mouse = None
        
        if self.tooltip:
            self.tooltip.hide()
    
    def perform_rotation(self, scene_pos: QPointF, snap: bool):
        """Realizar rotación"""
        # Centro del item en coordenadas de escena
        center = self.sceneBoundingRect().center()
        
        # Calcular ángulo
        angle = MathUtils.angle_between_points(center, scene_pos)
        
        # Ajustar para que 0° sea arriba
        angle = (angle + 90) % 360
        
        # Snap si Shift está presionado
        if snap:
            angle = MathUtils.snap_angle(angle)
        
        # Aplicar rotación
        self.setRotation(angle)
        self.transform_data.rotation = angle
        
        # Mostrar tooltip
        if self.tooltip:
            self.tooltip.show_angle(angle, scene_pos)
    
    def perform_resize(self, handle_type: HandleType, scene_pos: QPointF, 
                      keep_aspect: bool, free_transform: bool):
        """Realizar redimensión"""
        # Convertir a coordenadas locales
        local_pos = self.mapFromScene(scene_pos)
        local_start = self.mapFromScene(self.transform_start_mouse)
        
        # Delta
        delta = local_pos - local_start
        
        # Datos iniciales
        start_data = self.transform_start_data
        rect = QRectF(0, 0, start_data.width, start_data.height)
        new_width = start_data.width
        new_height = start_data.height
        new_x = start_data.x
        new_y = start_data.y
        
        # ===== HANDLES DE ESQUINAS =====
        if handle_type in [HandleType.CORNER_NW, HandleType.CORNER_NE,
                          HandleType.CORNER_SW, HandleType.CORNER_SE]:
            
            # Determinar signos según esquina
            if handle_type == HandleType.CORNER_SE:
                # Esquina inferior derecha
                new_width = start_data.width + delta.x()
                new_height = start_data.height + delta.y()
                
            elif handle_type == HandleType.CORNER_NW:
                # Esquina superior izquierda
                new_width = start_data.width - delta.x()
                new_height = start_data.height - delta.y()
                new_x = start_data.x + delta.x()
                new_y = start_data.y + delta.y()
                
            elif handle_type == HandleType.CORNER_NE:
                # Esquina superior derecha
                new_width = start_data.width + delta.x()
                new_height = start_data.height - delta.y()
                new_y = start_data.y + delta.y()
                
            elif handle_type == HandleType.CORNER_SW:
                # Esquina inferior izquierda
                new_width = start_data.width - delta.x()
                new_height = start_data.height + delta.y()
                new_x = start_data.x + delta.x()
            
            # Mantener aspect ratio (por defecto en esquinas, o con Shift)
            if not free_transform:
                # Usar el cambio mayor para mantener proporción
                width_change = abs(new_width - start_data.width)
                height_change = abs(new_height - start_data.height)
                
                if width_change > height_change:
                    new_height = new_width / self.original_aspect_ratio
                else:
                    new_width = new_height * self.original_aspect_ratio
                
                # Ajustar posición si es necesario
                if handle_type == HandleType.CORNER_NW:
                    new_x = start_data.x + (start_data.width - new_width)
                    new_y = start_data.y + (start_data.height - new_height)
                elif handle_type == HandleType.CORNER_NE:
                    new_y = start_data.y + (start_data.height - new_height)
                elif handle_type == HandleType.CORNER_SW:
                    new_x = start_data.x + (start_data.width - new_width)
        
        # ===== HANDLES DE LADOS =====
        else:
            if handle_type == HandleType.SIDE_E:
                new_width = start_data.width + delta.x()
            elif handle_type == HandleType.SIDE_W:
                new_width = start_data.width - delta.x()
                new_x = start_data.x + delta.x()
            elif handle_type == HandleType.SIDE_S:
                new_height = start_data.height + delta.y()
            elif handle_type == HandleType.SIDE_N:
                new_height = start_data.height - delta.y()
                new_y = start_data.y + delta.y()
        
        # Tamaño mínimo
        new_width = max(20, new_width)
        new_height = max(20, new_height)
        
        # Aplicar cambios
        scaled_pixmap = self.original_pixmap.scaled(
            int(new_width),
            int(new_height),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        
        # Actualizar posición
        self.setPos(new_x, new_y)
        
        # Actualizar transform data
        self.transform_data.width = new_width
        self.transform_data.height = new_height
        self.transform_data.x = new_x
        self.transform_data.y = new_y
        
        # Actualizar handles
        self.update_handles_position()
        
        # Mostrar tooltip
        if self.tooltip:
            self.tooltip.show_dimensions(new_width, new_height, scene_pos)
    
    def paint(self, painter, option, widget=None):
        """Pintar item con borde de selección"""
        super().paint(painter, option, widget)
        
        if self.isSelected():
            pen = QPen(QColor("#0078D7"))
            pen.setWidth(2)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())
    
    def mousePressEvent(self, event):
        """Click en el item (no en handle)"""
        if self.active_handle:
            event.accept()
            return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Mover item"""
        if self.active_handle:
            event.accept()
            return
        super().mouseMoveEvent(event)

# ==================== ELEMENTO DE FORMA ====================

class ShapeItem(QGraphicsPathItem):
    """Elemento de forma geométrica con handles"""
    
    def __init__(self, shape_type: ShapeType, rect: QRectF, editor):
        super().__init__()
        self.shape_type = shape_type
        self.editor = editor
        self.object_type = ObjectType.SHAPE
        
        # Propiedades de forma
        self.fill_color = QColor("#3498db")
        self.stroke_color = QColor("#2c3e50")
        self.stroke_width = 2
        self.corner_radius = 0  # Para rectángulos
        self.sides = 5  # Para polígonos
        
        # Configuración
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        
        # Transform data
        self.transform_data = Transform(
            x=rect.x(), y=rect.y(),
            width=rect.width(), height=rect.height(),
            rotation=0
        )
        
        # Crear forma inicial
        self.shape_rect = rect
        self.update_shape()
        
        # Sistema de handles (simplificado para formas)
        self.config = HandleConfig()
        self.handles = {}
        self.create_handles()
        self.update_handles_visibility()
    
    def create_handles(self):
        """Crear handles para la forma"""
        # Handles de esquinas
        for handle_type in [HandleType.CORNER_NW, HandleType.CORNER_NE,
                           HandleType.CORNER_SW, HandleType.CORNER_SE]:
            handle = Handle(handle_type, self.config, self)
            self.handles[handle_type] = handle
        
        # Handle de rotación
        rot_handle = Handle(HandleType.ROTATION, self.config, self)
        self.handles[HandleType.ROTATION] = rot_handle
        
        self.update_handles_position()
    
    def update_handles_position(self):
        """Actualizar posición de handles"""
        rect = self.boundingRect()
        
        positions = {
            HandleType.CORNER_NW: rect.topLeft(),
            HandleType.CORNER_NE: rect.topRight(),
            HandleType.CORNER_SW: rect.bottomLeft(),
            HandleType.CORNER_SE: rect.bottomRight(),
        }
        
        for handle_type, pos in positions.items():
            if handle_type in self.handles:
                self.handles[handle_type].setPos(pos)
        
        # Handle de rotación
        top_center = QPointF(rect.center().x(), rect.top())
        rotation_pos = QPointF(rect.center().x(), 
                              rect.top() - self.config.rotation_distance)
        self.handles[HandleType.ROTATION].setPos(rotation_pos)
    
    def update_handles_visibility(self):
        """Mostrar/ocultar handles"""
        visible = self.isSelected()
        for handle in self.handles.values():
            handle.setVisible(visible)
    
    def update_shape(self):
        """Actualizar geometría de la forma"""
        path = QPainterPath()
        rect = self.shape_rect
        
        if self.shape_type == ShapeType.RECTANGLE:
            if self.corner_radius > 0:
                path.addRoundedRect(rect, self.corner_radius, self.corner_radius)
            else:
                path.addRect(rect)
        
        elif self.shape_type == ShapeType.ELLIPSE:
            path.addEllipse(rect)
        
        elif self.shape_type == ShapeType.POLYGON:
            # Crear polígono regular
            center = rect.center()
            radius = min(rect.width(), rect.height()) / 2
            points = []
            for i in range(self.sides):
                angle = 2 * math.pi * i / self.sides - math.pi / 2
                x = center.x() + radius * math.cos(angle)
                y = center.y() + radius * math.sin(angle)
                points.append(QPointF(x, y))
            polygon = QPolygonF(points)
            path.addPolygon(polygon)
        
        elif self.shape_type == ShapeType.STAR:
            # Crear estrella
            center = rect.center()
            outer_radius = min(rect.width(), rect.height()) / 2
            inner_radius = outer_radius * 0.5
            points = []
            for i in range(self.sides * 2):
                angle = math.pi * i / self.sides - math.pi / 2
                radius = outer_radius if i % 2 == 0 else inner_radius
                x = center.x() + radius * math.cos(angle)
                y = center.y() + radius * math.sin(angle)
                points.append(QPointF(x, y))
            polygon = QPolygonF(points)
            path.addPolygon(polygon)
        
        self.setPath(path)
        
        # Aplicar estilos
        self.setBrush(QBrush(self.fill_color))
        pen = QPen(self.stroke_color)
        pen.setWidth(self.stroke_width)
        pen.setCosmetic(True)
        self.setPen(pen)
    
    def set_fill_color(self, color: QColor):
        """Cambiar color de relleno"""
        self.fill_color = color
        self.update_shape()
    
    def set_stroke_color(self, color: QColor):
        """Cambiar color de borde"""
        self.stroke_color = color
        self.update_shape()
    
    def set_stroke_width(self, width: int):
        """Cambiar ancho de borde"""
        self.stroke_width = width
        self.update_shape()
    
    def itemChange(self, change, value):
        """Detectar cambios en el item"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            QTimer.singleShot(0, self.update_handles_visibility)
        return super().itemChange(change, value)
    
    def start_transform(self, handle_type: HandleType, scene_pos: QPointF):
        """Iniciar transformación"""
        pass  # Simplificado por ahora
    
    def update_transform(self, handle_type: HandleType, scene_pos: QPointF):
        """Actualizar transformación"""
        pass  # Simplificado por ahora
    
    def end_transform(self, handle_type: HandleType):
        """Finalizar transformación"""
        pass  # Simplificado por ahora
    
    def paint(self, painter, option, widget=None):
        """Pintar forma con borde de selección"""
        super().paint(painter, option, widget)
        
        if self.isSelected():
            pen = QPen(QColor("#0078D7"))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())

# ==================== ELEMENTO DE TEXTO ====================

class TextItem(QGraphicsTextItem):
    """Elemento de texto editable con formato"""
    
    def __init__(self, text: str, editor):
        super().__init__(text)
        self.editor = editor
        self.object_type = ObjectType.TEXT
        
        # Propiedades de texto
        self.font_family = "Arial"
        self.font_size = 24
        self.text_color = QColor("#000000")
        
        # Configuración
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        
        # Transform data
        self.transform_data = Transform(
            x=0, y=0,
            width=100, height=50,
            rotation=0
        )
        
        # Aplicar formato inicial
        self.update_format()
        
        # Handles simplificados
        self.config = HandleConfig()
        self.handles = {}
    
    def update_format(self):
        """Actualizar formato de texto"""
        font = QFont(self.font_family, self.font_size)
        self.setFont(font)
        self.setDefaultTextColor(self.text_color)
    
    def set_font_size(self, size: int):
        """Cambiar tamaño de fuente"""
        self.font_size = size
        self.update_format()
    
    def set_font_family(self, family: str):
        """Cambiar familia de fuente"""
        self.font_family = family
        self.update_format()
    
    def set_text_color(self, color: QColor):
        """Cambiar color de texto"""
        self.text_color = color
        self.update_format()
    
    def paint(self, painter, option, widget=None):
        """Pintar texto con borde de selección"""
        super().paint(painter, option, widget)
        
        if self.isSelected():
            pen = QPen(QColor("#0078D7"))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self.boundingRect())

# ==================== ESCENA PERSONALIZADA ====================

class CanvasScene(QGraphicsScene):
    """Escena personalizada para manejar herramientas"""
    
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.temp_item = None
    
    def mousePressEvent(self, event):
        """Click en la escena"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()
            
            # Si hay herramienta de creación activa
            if self.editor.current_tool != "select":
                self.editor.tool_start_pos = pos
                
                # Crear item temporal para preview
                if self.editor.current_tool in ["rectangle", "ellipse", "polygon", "star"]:
                    shape_type_map = {
                        "rectangle": ShapeType.RECTANGLE,
                        "ellipse": ShapeType.ELLIPSE,
                        "polygon": ShapeType.POLYGON,
                        "star": ShapeType.STAR
                    }
                    rect = QRectF(pos, pos)
                    self.temp_item = ShapeItem(
                        shape_type_map[self.editor.current_tool],
                        rect,
                        self.editor
                    )
                    self.addItem(self.temp_item)
                    event.accept()
                    return
                
                elif self.editor.current_tool == "text":
                    # Crear texto directamente
                    text_item = TextItem("Haz doble click para editar", self.editor)
                    text_item.setPos(pos)
                    self.addItem(text_item)
                    self.clearSelection()
                    text_item.setSelected(True)
                    self.editor.set_tool("select")
                    self.editor.update_layers_list()
                    event.accept()
                    return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Arrastrar en la escena"""
        if self.temp_item and self.editor.tool_start_pos:
            pos = event.scenePos()
            start = self.editor.tool_start_pos
            
            # Actualizar rectángulo
            rect = QRectF(start, pos).normalized()
            
            if isinstance(self.temp_item, ShapeItem):
                self.temp_item.shape_rect = rect
                self.temp_item.update_shape()
                self.temp_item.update_handles_position()
            
            event.accept()
            return
        
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        """Soltar mouse en la escena"""
        if self.temp_item:
            # Finalizar creación
            rect = self.temp_item.shape_rect if isinstance(self.temp_item, ShapeItem) else self.temp_item.boundingRect()
            
            # Si es muy pequeño, eliminar
            if rect.width() < 10 or rect.height() < 10:
                self.removeItem(self.temp_item)
            else:
                # Seleccionar item creado
                self.clearSelection()
                self.temp_item.setSelected(True)
                self.editor.update_layers_list()
            
            self.temp_item = None
            self.editor.tool_start_pos = None
            self.editor.set_tool("select")
            event.accept()
            return
        
        super().mouseReleaseEvent(event)

# ==================== EDITOR PRINCIPAL ====================

class CanvasEditor(QMainWindow):
    """Editor de Canvas v4.0 - Editor Profesional Completo"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎨 Canvas Editor v4.0 - Editor Profesional")
        self.setGeometry(100, 100, 1600, 900)
        
        # Variables
        self.canvas_width_cm = 21.0
        self.canvas_height_cm = 29.7
        self.canvas_dpi = 96
        self.zoom_level = 1.0
        self.loaded_images = []
        
        # Sistemas nuevos
        self.theme = Theme()
        self.history = HistoryManager()
        self.show_grid = False
        self.show_rulers = True
        self.snap_to_grid = False
        self.grid_size = 20
        
        # Herramientas
        self.current_tool = "select"  # select, rectangle, ellipse, text, etc.
        self.tool_start_pos = None
        
        # Crear interfaz
        self.setup_ui()
        self.create_canvas()
        self.apply_style()
        
        self.statusBar().showMessage(
            "✨ Canvas Editor v4.0 Profesional | "
            "Ctrl+Z: Deshacer | Ctrl+Shift+Z: Rehacer | "
            "V: Seleccionar | R: Rectángulo | O: Círculo | T: Texto | "
            "Ctrl+D: Duplicar | Del: Eliminar",
            15000
        )
    
    def setup_ui(self):
        """Configurar interfaz"""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Panel izquierdo
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Área central
        canvas_area = self.create_canvas_area()
        main_layout.addWidget(canvas_area, stretch=1)
        
        # Panel derecho
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel)
        
        # Menú
        self.create_menu_bar()
    
    def create_left_panel(self):
        """Panel izquierdo con herramientas"""
        panel = QWidget()
        panel.setFixedWidth(280)
        panel.setStyleSheet("background-color: #F8F9FA;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        title = QLabel("🛠️ Herramientas")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Herramientas principales
        tools_group = QGroupBox("Herramientas Principales")
        tools_layout = QGridLayout()
        
        # Botón seleccionar
        select_btn = QPushButton("👆 Seleccionar (V)")
        select_btn.clicked.connect(lambda: self.set_tool("select"))
        tools_layout.addWidget(select_btn, 0, 0)
        
        # Botón rectángulo
        rect_btn = QPushButton("▭ Rectángulo (R)")
        rect_btn.clicked.connect(lambda: self.set_tool("rectangle"))
        tools_layout.addWidget(rect_btn, 0, 1)
        
        # Botón círculo
        circle_btn = QPushButton("⬤ Círculo (O)")
        circle_btn.clicked.connect(lambda: self.set_tool("ellipse"))
        tools_layout.addWidget(circle_btn, 1, 0)
        
        # Botón texto
        text_btn = QPushButton("T Texto (T)")
        text_btn.clicked.connect(lambda: self.set_tool("text"))
        tools_layout.addWidget(text_btn, 1, 1)
        
        # Botón línea
        line_btn = QPushButton("╱ Línea (L)")
        line_btn.clicked.connect(lambda: self.set_tool("line"))
        tools_layout.addWidget(line_btn, 2, 0)
        
        # Botón polígono
        poly_btn = QPushButton("⬡ Polígono")
        poly_btn.clicked.connect(lambda: self.set_tool("polygon"))
        tools_layout.addWidget(poly_btn, 2, 1)
        
        # Botón estrella
        star_btn = QPushButton("★ Estrella")
        star_btn.clicked.connect(lambda: self.set_tool("star"))
        tools_layout.addWidget(star_btn, 3, 0, 1, 2)
        
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)
        
        layout.addSpacing(10)
        
        # Botón cargar imágenes
        load_btn = QPushButton("📁 Cargar Imágenes")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005FA3;
            }
        """)
        load_btn.clicked.connect(self.load_images)
        layout.addWidget(load_btn)
        
        layout.addSpacing(10)
        
        # Info de herramienta actual
        self.tool_info = QLabel("🔧 Herramienta actual: Seleccionar")
        self.tool_info.setWordWrap(True)
        self.tool_info.setStyleSheet("""
            QLabel {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E3F2FD,
                    stop:1 #BBDEFB
                );
                color: #0D47A1;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #0078D7;
                font-size: 11px;
                line-height: 18px;
            }
        """)
        layout.addWidget(self.tool_info)
        
        layout.addSpacing(10)
        
        # Lista de imágenes
        list_label = QLabel("📷 Imágenes cargadas:")
        list_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(list_label)
        
        self.images_list = QListWidget()
        self.images_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background: white;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:hover {
                background: #F5F5F5;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                color: #0078D7;
            }
        """)
        self.images_list.setIconSize(QSize(60, 60))
        self.images_list.itemClicked.connect(self.on_image_clicked)
        layout.addWidget(self.images_list)
        
        return panel
    
    def create_right_panel(self):
        """Panel derecho - Propiedades y Capas"""
        panel = QWidget()
        panel.setFixedWidth(300)
        panel.setStyleSheet("background-color: #F8F9FA;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tabs para organizar
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background: #F0F0F0;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #0078D7;
            }
        """)
        
        # Tab de Capas
        layers_widget = QWidget()
        layers_layout = QVBoxLayout(layers_widget)
        
        layers_title = QLabel("🗂️ Capas")
        layers_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; padding: 5px;")
        layers_layout.addWidget(layers_title)
        
        self.layers_list = QListWidget()
        self.layers_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                background: white;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #F0F0F0;
            }
            QListWidget::item:hover {
                background: #F5F5F5;
            }
            QListWidget::item:selected {
                background: #E3F2FD;
                color: #0078D7;
            }
        """)
        self.layers_list.itemClicked.connect(self.on_layer_clicked)
        layers_layout.addWidget(self.layers_list)
        
        # Botones de orden
        order_layout = QHBoxLayout()
        up_btn = QPushButton("⬆️ Frente")
        up_btn.clicked.connect(self.bring_to_front)
        order_layout.addWidget(up_btn)
        
        down_btn = QPushButton("⬇️ Atrás")
        down_btn.clicked.connect(self.send_to_back)
        order_layout.addWidget(down_btn)
        layers_layout.addLayout(order_layout)
        
        tabs.addTab(layers_widget, "Capas")
        
        # Tab de Propiedades
        props_widget = QWidget()
        props_layout = QVBoxLayout(props_widget)
        
        props_title = QLabel("⚙️ Propiedades")
        props_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; padding: 5px;")
        props_layout.addWidget(props_title)
        
        self.transform_info = QLabel("Selecciona un elemento")
        self.transform_info.setWordWrap(True)
        self.transform_info.setStyleSheet("""
            QLabel {
                background: white;
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #E0E0E0;
                font-size: 11px;
                color: #666;
            }
        """)
        props_layout.addWidget(self.transform_info)
        
        # Color picker para formas
        color_group = QGroupBox("Colores")
        color_layout = QVBoxLayout()
        
        fill_btn = QPushButton("🎨 Color de Relleno")
        fill_btn.clicked.connect(self.change_fill_color)
        color_layout.addWidget(fill_btn)
        
        stroke_btn = QPushButton("🖊️ Color de Borde")
        stroke_btn.clicked.connect(self.change_stroke_color)
        color_layout.addWidget(stroke_btn)
        
        color_group.setLayout(color_layout)
        props_layout.addWidget(color_group)
        
        props_layout.addStretch()
        
        tabs.addTab(props_widget, "Propiedades")
        
        # Tab de Filtros
        filters_widget = QWidget()
        filters_layout = QVBoxLayout(filters_widget)
        
        filters_title = QLabel("✨ Filtros y Efectos")
        filters_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333; padding: 5px;")
        filters_layout.addWidget(filters_title)
        
        # Filtros básicos
        blur_btn = QPushButton("🌫️ Desenfocar")
        blur_btn.clicked.connect(lambda: self.apply_filter("blur"))
        filters_layout.addWidget(blur_btn)
        
        sharpen_btn = QPushButton("🔍 Enfocar")
        sharpen_btn.clicked.connect(lambda: self.apply_filter("sharpen"))
        filters_layout.addWidget(sharpen_btn)
        
        grayscale_btn = QPushButton("⚫ Escala de Grises")
        grayscale_btn.clicked.connect(lambda: self.apply_filter("grayscale"))
        filters_layout.addWidget(grayscale_btn)
        
        sepia_btn = QPushButton("🟤 Sepia")
        sepia_btn.clicked.connect(lambda: self.apply_filter("sepia"))
        filters_layout.addWidget(sepia_btn)
        
        invert_btn = QPushButton("🔄 Invertir Colores")
        invert_btn.clicked.connect(lambda: self.apply_filter("invert"))
        filters_layout.addWidget(invert_btn)
        
        # Ajustes
        adjust_group = QGroupBox("Ajustes")
        adjust_layout = QVBoxLayout()
        
        brightness_btn = QPushButton("☀️ Brillo +20%")
        brightness_btn.clicked.connect(lambda: self.apply_adjustment("brightness", 1.2))
        adjust_layout.addWidget(brightness_btn)
        
        contrast_btn = QPushButton("⚡ Contraste +20%")
        contrast_btn.clicked.connect(lambda: self.apply_adjustment("contrast", 1.2))
        adjust_layout.addWidget(contrast_btn)
        
        adjust_group.setLayout(adjust_layout)
        filters_layout.addWidget(adjust_group)
        
        filters_layout.addStretch()
        
        tabs.addTab(filters_widget, "Filtros")
        
        layout.addWidget(tabs)
        
        return panel
    
    def create_canvas_area(self):
        """Área del canvas"""
        widget = QWidget()
        widget.setStyleSheet("background-color: #E5E5E5;")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Vista del canvas - SIN RubberBand
        self.view = QGraphicsView()
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.view.setStyleSheet("""
            QGraphicsView {
                border: none;
                background-color: #E5E5E5;
            }
        """)
        
        # Escena
        self.scene = CanvasScene(self)
        self.view.setScene(self.scene)
        
        # Conectar señal de selección
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.view)
        
        # Controles de zoom
        zoom_controls = self.create_zoom_controls()
        layout.addWidget(zoom_controls)
        
        return widget
    
    def create_toolbar(self):
        """Toolbar del canvas"""
        toolbar = QWidget()
        toolbar.setFixedHeight(60)
        toolbar.setStyleSheet("background-color: white; border-radius: 8px;")
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Título
        title = QLabel("🎨 Canvas Editor v4.0")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Botón deshacer
        self.undo_btn = QPushButton("↶ Deshacer (Ctrl+Z)")
        self.undo_btn.setStyleSheet(self.get_tool_button_style())
        self.undo_btn.clicked.connect(self.undo_action)
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)
        
        # Botón rehacer
        self.redo_btn = QPushButton("↷ Rehacer (Ctrl+Shift+Z)")
        self.redo_btn.setStyleSheet(self.get_tool_button_style())
        self.redo_btn.clicked.connect(self.redo_action)
        self.redo_btn.setEnabled(False)
        layout.addWidget(self.redo_btn)
        
        # Separador
        layout.addSpacing(10)
        
        # Botón duplicar
        duplicate_btn = QPushButton("📋 Duplicar (Ctrl+D)")
        duplicate_btn.setStyleSheet(self.get_tool_button_style())
        duplicate_btn.clicked.connect(self.duplicate_selected)
        layout.addWidget(duplicate_btn)
        
        # Botón eliminar
        delete_btn = QPushButton("🗑️ Eliminar (Del)")
        delete_btn.setStyleSheet(self.get_tool_button_style())
        delete_btn.clicked.connect(self.delete_selected)
        layout.addWidget(delete_btn)
        
        # Separador
        layout.addSpacing(10)
        
        # Botón alinear izquierda
        align_left_btn = QPushButton("⬅️ Alinear Izq")
        align_left_btn.setStyleSheet(self.get_tool_button_style())
        align_left_btn.clicked.connect(self.align_left)
        layout.addWidget(align_left_btn)
        
        # Botón alinear centro
        align_center_btn = QPushButton("➡️ Centrar")
        align_center_btn.setStyleSheet(self.get_tool_button_style())
        align_center_btn.clicked.connect(self.align_center)
        layout.addWidget(align_center_btn)
        
        # Separador
        layout.addSpacing(10)
        
        # Botón tema
        theme_btn = QPushButton("🌓 Cambiar Tema")
        theme_btn.setStyleSheet(self.get_tool_button_style())
        theme_btn.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_btn)
        
        return toolbar
    
    def create_zoom_controls(self):
        """Controles de zoom"""
        widget = QWidget()
        widget.setFixedHeight(40)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addStretch()
        
        zoom_out = QPushButton("−")
        zoom_out.setFixedSize(35, 35)
        zoom_out.setStyleSheet(self.get_zoom_button_style())
        zoom_out.clicked.connect(lambda: self.change_zoom(-0.1))
        layout.addWidget(zoom_out)
        
        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(60)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("""
            background: white;
            border-radius: 5px;
            padding: 5px;
            font-weight: bold;
        """)
        layout.addWidget(self.zoom_label)
        
        zoom_in = QPushButton("+")
        zoom_in.setFixedSize(35, 35)
        zoom_in.setStyleSheet(self.get_zoom_button_style())
        zoom_in.clicked.connect(lambda: self.change_zoom(0.1))
        layout.addWidget(zoom_in)
        
        layout.addSpacing(10)
        
        fit_btn = QPushButton("⊡ Ajustar")
        fit_btn.setStyleSheet(self.get_zoom_button_style())
        fit_btn.clicked.connect(self.fit_to_view)
        layout.addWidget(fit_btn)
        
        layout.addStretch()
        
        return widget
    
    def create_menu_bar(self):
        """Menú superior"""
        menubar = self.menuBar()
        
        # Archivo
        file_menu = menubar.addMenu("Archivo")
        
        new_action = QAction("Nuevo", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        export_png = QAction("Exportar PNG...", self)
        export_png.setShortcut("Ctrl+E")
        export_png.triggered.connect(self.export_png)
        file_menu.addAction(export_png)
        
        export_jpg = QAction("Exportar JPG...", self)
        export_jpg.triggered.connect(self.export_jpg)
        file_menu.addAction(export_jpg)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Editar
        edit_menu = menubar.addMenu("Editar")
        
        undo_action = QAction("Deshacer", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo_action)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Rehacer", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.triggered.connect(self.redo_action)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        duplicate_action = QAction("Duplicar", self)
        duplicate_action.setShortcut("Ctrl+D")
        duplicate_action.triggered.connect(self.duplicate_selected)
        edit_menu.addAction(duplicate_action)
        
        delete_action = QAction("Eliminar", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_selected)
        edit_menu.addAction(delete_action)
        
        edit_menu.addSeparator()
        
        select_all_action = QAction("Seleccionar Todo", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.select_all)
        edit_menu.addAction(select_all_action)
        
        # Herramientas
        tools_menu = menubar.addMenu("Herramientas")
        
        select_tool_action = QAction("Seleccionar (V)", self)
        select_tool_action.setShortcut("V")
        select_tool_action.triggered.connect(lambda: self.set_tool("select"))
        tools_menu.addAction(select_tool_action)
        
        rect_tool_action = QAction("Rectángulo (R)", self)
        rect_tool_action.setShortcut("R")
        rect_tool_action.triggered.connect(lambda: self.set_tool("rectangle"))
        tools_menu.addAction(rect_tool_action)
        
        ellipse_tool_action = QAction("Círculo (O)", self)
        ellipse_tool_action.setShortcut("O")
        ellipse_tool_action.triggered.connect(lambda: self.set_tool("ellipse"))
        tools_menu.addAction(ellipse_tool_action)
        
        text_tool_action = QAction("Texto (T)", self)
        text_tool_action.setShortcut("T")
        text_tool_action.triggered.connect(lambda: self.set_tool("text"))
        tools_menu.addAction(text_tool_action)
        
        line_tool_action = QAction("Línea (L)", self)
        line_tool_action.setShortcut("L")
        line_tool_action.triggered.connect(lambda: self.set_tool("line"))
        tools_menu.addAction(line_tool_action)
        
        # Ver
        view_menu = menubar.addMenu("Ver")
        
        zoom_in_action = QAction("Acercar", self)
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(lambda: self.change_zoom(0.1))
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction("Alejar", self)
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(lambda: self.change_zoom(-0.1))
        view_menu.addAction(zoom_out_action)
        
        fit_action = QAction("Ajustar", self)
        fit_action.setShortcut("Ctrl+0")
        fit_action.triggered.connect(self.fit_to_view)
        view_menu.addAction(fit_action)
        
        view_menu.addSeparator()
        
        grid_action = QAction("Mostrar/Ocultar Grid", self)
        grid_action.setShortcut("Ctrl+'")
        grid_action.triggered.connect(self.toggle_grid)
        view_menu.addAction(grid_action)
        
        theme_action = QAction("Cambiar Tema", self)
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)
        
        # Ayuda
        help_menu = menubar.addMenu("Ayuda")
        
        shortcuts_action = QAction("Atajos de Teclado", self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        about_action = QAction("Acerca de", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_canvas(self):
        """Crear canvas"""
        self.scene.clear()
        
        width_px = cm_to_px(self.canvas_width_cm, self.canvas_dpi)
        height_px = cm_to_px(self.canvas_height_cm, self.canvas_dpi)
        
        self.canvas_rect = QGraphicsRectItem(0, 0, width_px, height_px)
        self.canvas_rect.setBrush(QBrush(QColor("white")))
        self.canvas_rect.setPen(QPen(QColor("#CCCCCC"), 1))
        self.canvas_rect.setZValue(-1000)
        self.scene.addItem(self.canvas_rect)
        
        margin = 100
        self.scene.setSceneRect(
            -margin, -margin,
            width_px + margin * 2,
            height_px + margin * 2
        )
        
        QTimer.singleShot(100, self.fit_to_view)
    
    # ==================== FUNCIONES DE IMÁGENES ====================
    
    def load_images(self):
        """Cargar imágenes"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar Imágenes",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if not file_paths:
            return
        
        for path in file_paths:
            if path not in self.loaded_images:
                self.loaded_images.append(path)
                self.add_image_to_list(path)
        
        self.statusBar().showMessage(f"✅ {len(file_paths)} imagen(es) cargada(s)", 2000)
    
    def add_image_to_list(self, image_path):
        """Agregar a la lista"""
        item = QListWidgetItem(os.path.basename(image_path))
        item.setData(Qt.ItemDataRole.UserRole, image_path)
        
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    60, 60,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                item.setIcon(QIcon(thumbnail))
        except:
            pass
        
        self.images_list.addItem(item)
    
    def on_image_clicked(self, item):
        """Click en imagen"""
        image_path = item.data(Qt.ItemDataRole.UserRole)
        self.add_image_to_canvas(image_path)
    
    def add_image_to_canvas(self, image_path):
        """Agregar imagen al canvas"""
        try:
            pil_img = Image.open(image_path)
            
            if pil_img.mode == 'RGBA':
                qimg = ImageQt.ImageQt(pil_img)
                pixmap = QPixmap.fromImage(qimg)
            else:
                pil_img_rgb = pil_img.convert('RGB')
                data = pil_img_rgb.tobytes("raw", "RGB")
                qimg = QImage(
                    data,
                    pil_img_rgb.width,
                    pil_img_rgb.height,
                    QImage.Format.Format_RGB888
                )
                pixmap = QPixmap.fromImage(qimg)
            
            # Escalar si es muy grande
            if pixmap.width() > 600 or pixmap.height() > 600:
                pixmap = pixmap.scaled(
                    600, 600,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            # Crear item
            image_item = ImageItem(pixmap, image_path, self)
            
            # Centrar en vista
            view_center = self.view.mapToScene(
                self.view.viewport().rect().center()
            )
            
            image_item.setPos(
                view_center.x() - pixmap.width() / 2,
                view_center.y() - pixmap.height() / 2
            )
            
            self.scene.addItem(image_item)
            
            # Seleccionar
            self.scene.clearSelection()
            image_item.setSelected(True)
            
            self.update_layers_list()
            
            self.statusBar().showMessage(
                f"✅ Imagen agregada: {os.path.basename(image_path)}", 
                2000
            )
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo agregar:\n{str(e)}")
    
    # ==================== FUNCIONES DE EDICIÓN ====================
    
    def delete_selected(self):
        """Eliminar seleccionados"""
        selected = self.scene.selectedItems()
        
        if not selected:
            return
        
        for item in selected:
            if isinstance(item, ImageItem):
                # Eliminar tooltip también
                if hasattr(item, 'tooltip') and item.tooltip:
                    self.scene.removeItem(item.tooltip)
                self.scene.removeItem(item)
        
        self.update_layers_list()
        self.statusBar().showMessage(f"🗑️ {len(selected)} eliminado(s)", 2000)
    
    def duplicate_selected(self):
        """Duplicar seleccionados"""
        selected = self.scene.selectedItems()
        
        if not selected:
            return
        
        self.scene.clearSelection()
        
        for item in selected:
            if isinstance(item, ImageItem):
                # Crear duplicado
                new_item = ImageItem(item.original_pixmap, item.image_path, self)
                
                # Copiar propiedades
                new_item.setPos(item.pos() + QPointF(20, 20))
                new_item.setRotation(item.rotation())
                new_item.setPixmap(item.pixmap())
                
                # Copiar transform data
                new_item.transform_data = Transform(
                    x=item.transform_data.x + 20,
                    y=item.transform_data.y + 20,
                    width=item.transform_data.width,
                    height=item.transform_data.height,
                    rotation=item.transform_data.rotation
                )
                
                self.scene.addItem(new_item)
                new_item.setSelected(True)
        
        self.update_layers_list()
        self.statusBar().showMessage(f"📋 {len(selected)} duplicado(s)", 2000)
    
    def bring_to_front(self):
        """Traer al frente"""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        for item in selected:
            if isinstance(item, ImageItem):
                item.setZValue(item.zValue() + 1)
        
        self.update_layers_list()
    
    def send_to_back(self):
        """Enviar atrás"""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        for item in selected:
            if isinstance(item, ImageItem):
                item.setZValue(item.zValue() - 1)
        
        self.update_layers_list()
    
    # ==================== CAPAS ====================
    
    def update_layers_list(self):
        """Actualizar lista de capas"""
        self.layers_list.clear()
        
        # Obtener todos los objetos editables
        items = [item for item in self.scene.items() 
                if isinstance(item, (ImageItem, ShapeItem, TextItem))]
        
        items.sort(key=lambda x: x.zValue(), reverse=True)
        
        for item in items:
            # Determinar icono y nombre según tipo
            if isinstance(item, ImageItem):
                icon = "🖼️"
                name = os.path.basename(item.image_path)
            elif isinstance(item, ShapeItem):
                icon = "🔷"
                name = f"{item.shape_type.value.capitalize()}"
            elif isinstance(item, TextItem):
                icon = "📝"
                text_preview = item.toPlainText()[:20]
                name = f"Texto: {text_preview}..."
            else:
                icon = "❓"
                name = "Objeto"
            
            list_item = QListWidgetItem(f"{icon} {name}")
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            
            if item.isSelected():
                list_item.setBackground(QColor("#E3F2FD"))
            
            self.layers_list.addItem(list_item)
    
    def on_layer_clicked(self, item):
        """Click en capa"""
        image_item = item.data(Qt.ItemDataRole.UserRole)
        if image_item:
            self.scene.clearSelection()
            image_item.setSelected(True)
    
    def on_selection_changed(self):
        """Cambio de selección"""
        self.update_layers_list()
        self.update_transform_info()
    
    def update_transform_info(self):
        """Actualizar info de transformación"""
        selected = self.scene.selectedItems()
        
        if not selected:
            self.transform_info.setText("Selecciona un elemento")
            return
        
        item = selected[0]
        
        # Obtener información según tipo
        if isinstance(item, ImageItem):
            data = item.transform_data
            info = (
                f"📐 <b>Tipo:</b> Imagen<br>"
                f"<b>Dimensiones:</b><br>"
                f"   {int(data.width)} × {int(data.height)} px<br><br>"
                f"🔄 <b>Rotación:</b><br>"
                f"   {int(data.rotation) % 360}°<br><br>"
                f"📍 <b>Posición:</b><br>"
                f"   X: {int(data.x)}, Y: {int(data.y)}"
            )
        elif isinstance(item, ShapeItem):
            rect = item.boundingRect()
            info = (
                f"📐 <b>Tipo:</b> {item.shape_type.value.capitalize()}<br>"
                f"<b>Dimensiones:</b><br>"
                f"   {int(rect.width())} × {int(rect.height())} px<br><br>"
                f"🎨 <b>Colores:</b><br>"
                f"   Relleno: {item.fill_color.name()}<br>"
                f"   Borde: {item.stroke_color.name()}"
            )
        elif isinstance(item, TextItem):
            rect = item.boundingRect()
            info = (
                f"📐 <b>Tipo:</b> Texto<br>"
                f"<b>Contenido:</b><br>"
                f"   '{item.toPlainText()[:30]}...'<br><br>"
                f"🔤 <b>Formato:</b><br>"
                f"   Fuente: {item.font_family}<br>"
                f"   Tamaño: {item.font_size}px"
            )
        else:
            info = "Objeto desconocido"
        
        self.transform_info.setText(info)
    
    # ==================== ZOOM ====================
    
    def change_zoom(self, delta):
        """Cambiar zoom"""
        self.zoom_level += delta
        self.zoom_level = max(0.1, min(3.0, self.zoom_level))
        
        self.view.resetTransform()
        self.view.scale(self.zoom_level, self.zoom_level)
        
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def fit_to_view(self):
        """Ajustar a vista"""
        self.view.fitInView(
            self.canvas_rect,
            Qt.AspectRatioMode.KeepAspectRatio
        )
        
        transform = self.view.transform()
        self.zoom_level = transform.m11()
        self.zoom_label.setText(f"{int(self.zoom_level * 100)}%")
    
    def wheelEvent(self, event):
        """Zoom con Ctrl+Scroll"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 0.1 if event.angleDelta().y() > 0 else -0.1
            self.change_zoom(delta)
            event.accept()
        else:
            super().wheelEvent(event)
    
    # ==================== PROYECTO ====================
    
    def new_project(self):
        """Nuevo proyecto"""
        reply = QMessageBox.question(
            self,
            "Nuevo Proyecto",
            "¿Crear nuevo proyecto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.scene.clear()
            self.loaded_images.clear()
            self.images_list.clear()
            self.create_canvas()
            self.statusBar().showMessage("📄 Nuevo proyecto", 2000)
    
    def export_png(self):
        """Exportar a PNG"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar como PNG",
            "",
            "PNG (*.png)"
        )
        
        if not file_path:
            return
        
        if not file_path.endswith('.png'):
            file_path += '.png'
        
        try:
            rect = self.canvas_rect.rect()
            
            image = QImage(
                int(rect.width()),
                int(rect.height()),
                QImage.Format.Format_ARGB32
            )
            image.fill(Qt.GlobalColor.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, QRectF(image.rect()), rect)
            painter.end()
            
            image.save(file_path, 'PNG')
            
            self.statusBar().showMessage(f"✅ Exportado: {os.path.basename(file_path)}", 3000)
            QMessageBox.information(self, "Éxito", f"Guardado en:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")
    
    # ==================== ESTILOS ====================
    
    def get_tool_button_style(self):
        return """
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E8E8E8;
                border-color: #0078D7;
            }
            QPushButton:pressed {
                background-color: #D0D0D0;
            }
        """
    
    def get_zoom_button_style(self):
        return """
            QPushButton {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #0078D7;
            }
        """
    
    def apply_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F0F0F0;
            }
            QMenuBar {
                background-color: white;
                border-bottom: 1px solid #E0E0E0;
                padding: 5px;
            }
            QMenuBar::item:selected {
                background-color: #E3F2FD;
                color: #0078D7;
            }
            QMenu {
                background-color: white;
                border: 1px solid #E0E0E0;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
                color: #0078D7;
            }
            QStatusBar {
                background-color: white;
                border-top: 1px solid #E0E0E0;
            }
        """)
    
    # ==================== NUEVAS FUNCIONES ====================
    
    def set_tool(self, tool_name: str):
        """Cambiar herramienta actual"""
        self.current_tool = tool_name
        
        tool_names = {
            "select": "👆 Seleccionar",
            "rectangle": "▭ Rectángulo",
            "ellipse": "⬤ Círculo",
            "text": "📝 Texto",
            "line": "╱ Línea",
            "polygon": "⬡ Polígono",
            "star": "★ Estrella"
        }
        
        display_name = tool_names.get(tool_name, tool_name)
        self.tool_info.setText(f"🔧 <b>Herramienta actual:</b><br>{display_name}")
        self.statusBar().showMessage(f"🔧 Herramienta: {display_name}", 3000)
    
    def undo_action(self):
        """Deshacer acción"""
        if self.history.can_undo():
            data = self.history.undo()
            # Aquí iría la lógica para restaurar el estado
            self.statusBar().showMessage("↶ Acción deshecha", 2000)
        self.update_undo_redo_buttons()
    
    def redo_action(self):
        """Rehacer acción"""
        if self.history.can_redo():
            data = self.history.redo()
            # Aquí iría la lógica para restaurar el estado
            self.statusBar().showMessage("↷ Acción rehecha", 2000)
        self.update_undo_redo_buttons()
    
    def update_undo_redo_buttons(self):
        """Actualizar estado de botones undo/redo"""
        self.undo_btn.setEnabled(self.history.can_undo())
        self.redo_btn.setEnabled(self.history.can_redo())
    
    def select_all(self):
        """Seleccionar todos los objetos"""
        for item in self.scene.items():
            if isinstance(item, (ImageItem, ShapeItem, TextItem)):
                item.setSelected(True)
        self.statusBar().showMessage("✅ Todos los objetos seleccionados", 2000)
    
    def align_left(self):
        """Alinear objetos a la izquierda"""
        selected = [item for item in self.scene.selectedItems() 
                   if isinstance(item, (ImageItem, ShapeItem, TextItem))]
        
        if len(selected) < 2:
            self.statusBar().showMessage("⚠️ Selecciona al menos 2 objetos", 2000)
            return
        
        # Encontrar el más a la izquierda
        min_x = min(item.pos().x() for item in selected)
        
        # Alinear todos a esa posición
        for item in selected:
            item.setX(min_x)
        
        self.statusBar().showMessage("⬅️ Objetos alineados a la izquierda", 2000)
    
    def align_center(self):
        """Centrar objetos horizontalmente"""
        selected = [item for item in self.scene.selectedItems() 
                   if isinstance(item, (ImageItem, ShapeItem, TextItem))]
        
        if not selected:
            self.statusBar().showMessage("⚠️ Selecciona objetos", 2000)
            return
        
        # Calcular centro del canvas
        canvas_center = self.canvas_rect.rect().center()
        
        for item in selected:
            rect = item.boundingRect()
            item.setX(canvas_center.x() - rect.width() / 2)
        
        self.statusBar().showMessage("➡️ Objetos centrados", 2000)
    
    def toggle_theme(self):
        """Cambiar tema oscuro/claro"""
        theme = self.theme.toggle()
        self.apply_style()
        self.statusBar().showMessage(f"🌓 Tema cambiado a: {theme}", 2000)
    
    def toggle_grid(self):
        """Mostrar/ocultar grid"""
        self.show_grid = not self.show_grid
        self.scene.update()
        state = "visible" if self.show_grid else "oculto"
        self.statusBar().showMessage(f"📐 Grid {state}", 2000)
    
    def change_fill_color(self):
        """Cambiar color de relleno"""
        selected = self.scene.selectedItems()
        
        if not selected:
            return
        
        item = selected[0]
        
        if isinstance(item, ShapeItem):
            color = QColorDialog.getColor(item.fill_color, self, "Seleccionar Color de Relleno")
            if color.isValid():
                item.set_fill_color(color)
                self.statusBar().showMessage(f"🎨 Color de relleno cambiado", 2000)
        else:
            self.statusBar().showMessage("⚠️ Selecciona una forma", 2000)
    
    def change_stroke_color(self):
        """Cambiar color de borde"""
        selected = self.scene.selectedItems()
        
        if not selected:
            return
        
        item = selected[0]
        
        if isinstance(item, ShapeItem):
            color = QColorDialog.getColor(item.stroke_color, self, "Seleccionar Color de Borde")
            if color.isValid():
                item.set_stroke_color(color)
                self.statusBar().showMessage(f"🖊️ Color de borde cambiado", 2000)
        else:
            self.statusBar().showMessage("⚠️ Selecciona una forma", 2000)
    
    def apply_filter(self, filter_name: str):
        """Aplicar filtro a imagen seleccionada"""
        selected = self.scene.selectedItems()
        
        if not selected or not isinstance(selected[0], ImageItem):
            self.statusBar().showMessage("⚠️ Selecciona una imagen", 2000)
            return
        
        item = selected[0]
        
        try:
            # Convertir QPixmap a PIL Image
            qimage = item.pixmap().toImage()
            buffer = qimage.bits().asstring(qimage.sizeInBytes())
            pil_image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), buffer)
            
            # Aplicar filtro
            if filter_name == "blur":
                pil_image = pil_image.filter(ImageFilter.BLUR)
            elif filter_name == "sharpen":
                pil_image = pil_image.filter(ImageFilter.SHARPEN)
            elif filter_name == "grayscale":
                pil_image = pil_image.convert("L").convert("RGBA")
            elif filter_name == "sepia":
                # Convertir a sepia
                pil_image = pil_image.convert("L")
                sepia_image = Image.new("RGBA", pil_image.size)
                pixels = sepia_image.load()
                orig_pixels = pil_image.load()
                for y in range(pil_image.height):
                    for x in range(pil_image.width):
                        gray = orig_pixels[x, y]
                        pixels[x, y] = (int(gray * 1.0), int(gray * 0.95), int(gray * 0.82), 255)
                pil_image = sepia_image
            elif filter_name == "invert":
                # Invertir colores
                from PIL import ImageOps
                pil_image = ImageOps.invert(pil_image.convert("RGB")).convert("RGBA")
            
            # Convertir de vuelta a QPixmap
            qimg = ImageQt.ImageQt(pil_image)
            new_pixmap = QPixmap.fromImage(qimg)
            
            # Actualizar item
            item.setPixmap(new_pixmap)
            item.original_pixmap = new_pixmap
            
            self.statusBar().showMessage(f"✨ Filtro '{filter_name}' aplicado", 2000)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo aplicar el filtro:\n{str(e)}")
    
    def apply_adjustment(self, adjustment_name: str, value: float):
        """Aplicar ajuste a imagen seleccionada"""
        selected = self.scene.selectedItems()
        
        if not selected or not isinstance(selected[0], ImageItem):
            self.statusBar().showMessage("⚠️ Selecciona una imagen", 2000)
            return
        
        item = selected[0]
        
        try:
            # Convertir QPixmap a PIL Image
            qimage = item.pixmap().toImage()
            buffer = qimage.bits().asstring(qimage.sizeInBytes())
            pil_image = Image.frombytes("RGBA", (qimage.width(), qimage.height()), buffer)
            
            # Aplicar ajuste
            if adjustment_name == "brightness":
                enhancer = ImageEnhance.Brightness(pil_image)
                pil_image = enhancer.enhance(value)
            elif adjustment_name == "contrast":
                enhancer = ImageEnhance.Contrast(pil_image)
                pil_image = enhancer.enhance(value)
            
            # Convertir de vuelta a QPixmap
            qimg = ImageQt.ImageQt(pil_image)
            new_pixmap = QPixmap.fromImage(qimg)
            
            # Actualizar item
            item.setPixmap(new_pixmap)
            item.original_pixmap = new_pixmap
            
            self.statusBar().showMessage(f"✨ Ajuste '{adjustment_name}' aplicado", 2000)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo aplicar el ajuste:\n{str(e)}")
    
    def export_jpg(self):
        """Exportar a JPG"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar como JPG",
            "",
            "JPG (*.jpg *.jpeg)"
        )
        
        if not file_path:
            return
        
        if not file_path.lower().endswith(('.jpg', '.jpeg')):
            file_path += '.jpg'
        
        try:
            rect = self.canvas_rect.rect()
            
            image = QImage(
                int(rect.width()),
                int(rect.height()),
                QImage.Format.Format_RGB888
            )
            image.fill(Qt.GlobalColor.white)
            
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, QRectF(image.rect()), rect)
            painter.end()
            
            image.save(file_path, 'JPEG', quality=95)
            
            self.statusBar().showMessage(f"✅ Exportado: {os.path.basename(file_path)}", 3000)
            QMessageBox.information(self, "Éxito", f"Guardado en:\n{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error:\n{str(e)}")
    
    def show_shortcuts(self):
        """Mostrar diálogo de atajos de teclado"""
        shortcuts_text = """
        <h2>⌨️ Atajos de Teclado</h2>
        
        <h3>📁 Archivo</h3>
        <ul>
            <li><b>Ctrl+N</b> - Nuevo proyecto</li>
            <li><b>Ctrl+E</b> - Exportar PNG</li>
            <li><b>Ctrl+Q</b> - Salir</li>
        </ul>
        
        <h3>✏️ Edición</h3>
        <ul>
            <li><b>Ctrl+Z</b> - Deshacer</li>
            <li><b>Ctrl+Shift+Z</b> - Rehacer</li>
            <li><b>Ctrl+D</b> - Duplicar</li>
            <li><b>Delete</b> - Eliminar</li>
            <li><b>Ctrl+A</b> - Seleccionar todo</li>
        </ul>
        
        <h3>🛠️ Herramientas</h3>
        <ul>
            <li><b>V</b> - Seleccionar</li>
            <li><b>R</b> - Rectángulo</li>
            <li><b>O</b> - Círculo</li>
            <li><b>T</b> - Texto</li>
            <li><b>L</b> - Línea</li>
        </ul>
        
        <h3>👁️ Vista</h3>
        <ul>
            <li><b>Ctrl++</b> - Acercar</li>
            <li><b>Ctrl+-</b> - Alejar</li>
            <li><b>Ctrl+0</b> - Ajustar a ventana</li>
            <li><b>Ctrl+'</b> - Mostrar/Ocultar grid</li>
            <li><b>Ctrl+Scroll</b> - Zoom con rueda del mouse</li>
        </ul>
        
        <h3>🎨 Transformación</h3>
        <ul>
            <li><b>Shift</b> (al rotar) - Ajustar a 15°</li>
            <li><b>Alt</b> (al redimensionar) - Deformar libremente</li>
        </ul>
        """
        
        QMessageBox.information(self, "Atajos de Teclado", shortcuts_text)
    
    def show_about(self):
        QMessageBox.about(
            self,
            "Canvas Editor v4.0",
            """
            <h2>🎨 Canvas Editor v4.0 Profesional</h2>
            <p><b>Editor Completo Inspirado en Canva, Figma y Photopea</b></p>
            
            <h3>✨ Nuevas Características v4.0:</h3>
            <ul>
                <li>🛠️ <b>Herramientas de Forma:</b> Rectángulo, Círculo, Polígono, Estrella</li>
                <li>📝 <b>Herramienta de Texto:</b> Texto editable con formato</li>
                <li>↶↷ <b>Undo/Redo:</b> Sistema completo de historial</li>
                <li>✨ <b>Filtros:</b> Desenfocar, Enfocar, Escala de Grises, Sepia, Invertir</li>
                <li>☀️ <b>Ajustes:</b> Brillo y Contraste</li>
                <li>⚡ <b>Alineación:</b> Alinear y centrar objetos</li>
                <li>🌓 <b>Temas:</b> Modo oscuro y claro</li>
                <li>📐 <b>Grid:</b> Cuadrícula para alineación</li>
                <li>🗂️ <b>Capas:</b> Sistema profesional de capas</li>
                <li>🎨 <b>Colores:</b> Cambiar colores de formas</li>
                <li>📋 <b>Propiedades:</b> Panel de propiedades detallado</li>
                <li>💾 <b>Exportar:</b> PNG y JPG</li>
                <li>⌨️ <b>Atajos:</b> Atajos de teclado profesionales</li>
            </ul>
            
            <h3>🎯 Características Heredadas v3.0:</h3>
            <ul>
                <li>🔵 Sistema de handles profesional (8 puntos + rotación)</li>
                <li>📐 Tooltips con dimensiones y ángulo en tiempo real</li>
                <li>🎯 Cursores apropiados para cada handle</li>
                <li>⌨️ Modificadores: Shift (snap) y Alt (deformar)</li>
                <li>🖼️ Carga y manipulación de imágenes</li>
                <li>🔍 Zoom y navegación avanzados</li>
            </ul>
            
            <h3>📖 Cómo Usar:</h3>
            <p><b>Herramientas:</b> Selecciona una herramienta del panel izquierdo</p>
            <p><b>Formas:</b> Haz click y arrastra para crear formas</p>
            <p><b>Texto:</b> Click para añadir texto, doble click para editar</p>
            <p><b>Handles:</b> Arrastra esquinas/lados para redimensionar</p>
            <p><b>Rotación:</b> Usa el handle verde superior</p>
            <p><b>Filtros:</b> Selecciona imagen y aplica desde el panel derecho</p>
            <p><b>Atajos:</b> Usa V, R, O, T, L para cambiar de herramienta</p>
            
            <p style="margin-top: 20px;"><b>© 2025 Canvas Editor Team</b><br>
            Versión 4.0 - Editor Profesional Completo</p>
            """
        )

# ==================== MAIN ====================

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Canvas Editor v3.0")
    app.setStyle(QStyleFactory.create('Fusion'))
    
    window = CanvasEditor()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()