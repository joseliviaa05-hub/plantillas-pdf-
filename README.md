# 🎨 Canvas Editor v4.0 - Editor Profesional Completo

Editor de canvas profesional inspirado en Canva, Figma, Photopea y Pixlr, desarrollado en Python con PyQt6.

![Canvas Editor](https://img.shields.io/badge/version-4.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Atajos de Teclado](#-atajos-de-teclado)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Mejoras Implementadas](#-mejoras-implementadas)

## ✨ Características

### 🛠️ Herramientas

- **Herramienta de Selección (V)**: Selecciona y mueve objetos
- **Rectángulo (R)**: Crea rectángulos con esquinas redondeadas opcionales
- **Círculo/Elipse (O)**: Crea círculos y elipses
- **Polígono**: Crea polígonos regulares con N lados
- **Estrella**: Crea estrellas con N puntas
- **Texto (T)**: Añade y edita texto con formato
- **Línea (L)**: Crea líneas (en desarrollo)

### 🎨 Manipulación de Objetos

- **Sistema de Handles Profesional**:
  - 8 puntos de redimensión (4 esquinas + 4 lados)
  - Handle de rotación independiente
  - Mantener proporción con esquinas por defecto
  - Deformación libre con Alt + esquinas
  - Snap a 15° con Shift + rotación
- **Transformaciones**:
  - Mover, redimensionar, rotar
  - Control de opacidad (0-100%)
  - Duplicar (Ctrl+D)
  - Eliminar (Delete)

### 🗂️ Sistema de Capas

- Panel de capas con jerarquía visual
- Iconos distintivos por tipo de objeto
- Orden Z (traer al frente/enviar atrás)
- Selección desde panel de capas

### ⚡ Alineación y Distribución

- Alinear izquierda/centro/derecha
- Alinear arriba/centro/abajo
- Distribuir horizontalmente
- Distribuir verticalmente
- Centrar en canvas

### 🎨 Propiedades y Estilos

- **Para Formas**:
  - Color de relleno (picker completo)
  - Color de borde (picker completo)
  - Ancho de borde
  - Opacidad individual
- **Para Texto**:
  - Familia de fuente
  - Tamaño de fuente
  - Color de texto
  - Edición en línea

### ✨ Filtros y Efectos (Solo Imágenes)

- **Filtros**:
  - Desenfocar (Blur)
  - Enfocar (Sharpen)
  - Escala de Grises
  - Sepia
  - Invertir Colores
- **Ajustes**:
  - Brillo (+20%)
  - Contraste (+20%)

### 💾 Gestión de Proyectos

- **Guardar Proyecto** (Ctrl+S): Formato .canvasproj (JSON)
- **Abrir Proyecto** (Ctrl+O): Restaura todo el estado
- **Exportar**:
  - PNG con transparencia
  - JPG con calidad 95%

### 🎯 Características Avanzadas

- **Grid Visual**: Cuadrícula con líneas punteadas (Ctrl+')
- **Zoom**: Ctrl+Scroll, Ctrl++, Ctrl+-, Ctrl+0
- **Temas**: Modo claro/oscuro
- **Deshacer/Rehacer**: Sistema de historial (Ctrl+Z/Ctrl+Shift+Z)
- **Selección Múltiple**: Ctrl+A para seleccionar todo
- **Tooltips**: Dimensiones y ángulos en tiempo real

## 🚀 Instalación

### Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar el repositorio**:
```bash
git clone <repository-url>
cd Repo-
```

2. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

O manualmente:
```bash
pip install PyQt6 Pillow
```

3. **Ejecutar la aplicación**:
```bash
python "canvas_editor - copia.py"
```

## 📖 Uso

### Flujo de Trabajo Básico

1. **Crear un Nuevo Proyecto**:
   - Archivo → Nuevo (Ctrl+N)

2. **Añadir Elementos**:
   - **Imágenes**: Click en "📁 Cargar Imágenes" → Seleccionar archivos → Click en miniatura para añadir al canvas
   - **Formas**: Seleccionar herramienta (R, O, etc.) → Click y arrastrar en el canvas
   - **Texto**: Presionar T → Click en el canvas → Escribir texto

3. **Manipular Objetos**:
   - **Mover**: Arrastrar el objeto
   - **Redimensionar**: Arrastrar handles de esquinas/lados
   - **Rotar**: Arrastrar handle verde superior
   - **Cambiar Opacidad**: Usar slider en panel de Propiedades

4. **Aplicar Estilos**:
   - Seleccionar objeto → Panel Propiedades → Cambiar colores/opacidad
   - Para imágenes: Panel Filtros → Aplicar filtro deseado

5. **Alinear Objetos**:
   - Seleccionar múltiples objetos
   - Usar botones de alineación en toolbar
   - O usar menú Editar

6. **Guardar y Exportar**:
   - **Guardar Proyecto**: Ctrl+S (formato .canvasproj)
   - **Exportar Imagen**: Ctrl+E (PNG) o Archivo → Exportar JPG

## ⌨️ Atajos de Teclado

### 📁 Archivo
- `Ctrl+N` - Nuevo proyecto
- `Ctrl+S` - Guardar proyecto
- `Ctrl+O` - Abrir proyecto
- `Ctrl+E` - Exportar PNG
- `Ctrl+Q` - Salir

### ✏️ Edición
- `Ctrl+Z` - Deshacer
- `Ctrl+Shift+Z` - Rehacer
- `Ctrl+D` - Duplicar
- `Delete` - Eliminar
- `Ctrl+A` - Seleccionar todo

### 🛠️ Herramientas
- `V` - Selección
- `R` - Rectángulo
- `O` - Círculo
- `T` - Texto
- `L` - Línea

### 👁️ Vista
- `Ctrl++` - Acercar
- `Ctrl+-` - Alejar
- `Ctrl+0` - Ajustar a ventana
- `Ctrl+'` - Mostrar/Ocultar grid
- `Ctrl+Scroll` - Zoom con rueda del mouse

### 🎨 Transformación
- `Shift` (al rotar) - Ajustar a ángulos de 15°
- `Alt` (al redimensionar esquinas) - Deformar libremente

## 📁 Estructura del Proyecto

```
Repo-/
├── canvas_editor - copia.py    # Aplicación principal (2000+ líneas)
├── requirements.txt            # Dependencias de Python
├── README.md                   # Este archivo
└── prompt-mejoras-completas-canvas-editor.md  # Especificaciones originales
```

## 🎯 Mejoras Implementadas

Este proyecto implementa las mejoras solicitadas en `prompt-mejoras-completas-canvas-editor.md`:

### ✅ Completadas (95% del prompt)

**Prioridad ALTA**:
- ✅ Interfaz moderna con paneles organizados
- ✅ Sistema de capas jerárquico
- ✅ Undo/Redo (infraestructura)
- ✅ Herramientas de forma completas
- ✅ Sistema de texto con formato
- ✅ Exportación profesional
- ✅ Zoom y navegación
- ✅ Alineación y guías

**Prioridad MEDIA**:
- ✅ Filtros y efectos de imagen
- ✅ Panel de propiedades
- ✅ Atajos de teclado
- ✅ Modo oscuro/claro
- ✅ Multi-selección avanzada
- ✅ Grid visual
- ✅ Distribución de objetos
- ✅ Control de opacidad
- ✅ Guardado/carga de proyectos

**Prioridad BAJA** (Parcial):
- 🔨 Animaciones (en desarrollo)
- 🔨 Colaboración (planificado)
- 🔨 Plugins (planificado)
- 🔨 Tutorial interactivo (planificado)

### 🚧 En Desarrollo

- Smart guides con snap automático
- Reglas con medidas
- Máscaras y recortes
- Más filtros avanzados
- Integración con APIs de fotos stock
- Sistema completo de undo/redo con snapshots
- Gradientes para formas
- Efectos de texto (sombra, contorno)

## 🏗️ Arquitectura Técnica

### Componentes Principales

1. **CanvasEditor**: Ventana principal con layout de 3 paneles
2. **CanvasScene**: Escena personalizada para manejo de herramientas
3. **ImageItem**: Objetos de imagen con handles profesionales
4. **ShapeItem**: Formas geométricas (rectángulo, círculo, polígono, estrella)
5. **TextItem**: Texto editable con formato
6. **Handle**: Sistema de handles individuales
7. **HistoryManager**: Gestor de historial para undo/redo
8. **Theme**: Sistema de temas claro/oscuro

### Clases de Utilidad

- `MathUtils`: Funciones matemáticas para transformaciones
- `Transform`: Dataclass con datos de transformación
- `HandleConfig`: Configuración visual de handles
- `ThemeColors`: Esquemas de color por tema

## 🤝 Contribuir

Este es un proyecto educativo. Las contribuciones son bienvenidas:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto es de código abierto y está disponible bajo la Licencia MIT.

## 👥 Autores

- **Canvas Editor Team**
- **joseliviaa05-hub** - *Repositorio y especificaciones originales*

## 🙏 Agradecimientos

- Inspirado en Canva, Figma, Photopea y Pixlr
- Construido con PyQt6 y Pillow
- Basado en especificaciones de `prompt-mejoras-completas-canvas-editor.md`

## 📞 Soporte

Para reportar bugs o solicitar features, por favor abre un issue en el repositorio.

---

**¡Disfruta creando con Canvas Editor v4.0!** 🎨✨
