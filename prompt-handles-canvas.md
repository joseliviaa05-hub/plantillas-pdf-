# Prompt para Generar Sistema de Handles de Canvas

Genera un sistema completo y profesional de handles (manejadores) para un editor de canvas similar a Canva web, con las siguientes características:

## Requisitos Funcionales

### 1. Tipos de Handles
- **Handles de esquina (4)**: Para redimensionar manteniendo o no las proporciones
- **Handles de borde (4)**: Para redimensionar en una sola dirección (arriba, abajo, izquierda, derecha)
- **Handle de rotación (1)**: Ubicado en la parte superior central, con línea de conexión al objeto
- **Indicador de bloqueo**: Visual para proporciones bloqueadas

### 2. Comportamiento de Redimensionamiento
- **Sin tecla modificadora**: Redimensionar libre
- **Con Shift presionado**: Mantener proporciones (aspect ratio)
- **Con Alt presionado**: Redimensionar desde el centro
- **Con Shift + Alt**: Mantener proporciones y redimensionar desde el centro
- Límites mínimos de tamaño (ej: 10x10px)
- Snap to grid opcional cuando está cerca de líneas guía

### 3. Comportamiento de Rotación
- Rotación suave desde el handle superior
- Mostrar ángulo actual en un tooltip mientras se rota
- Snap a 15° cuando se presiona Shift
- Snap a 0°, 90°, 180°, 270° cuando está cerca (±5°)
- Cursor personalizado durante la rotación

### 4. Características Visuales (estilo Canva)
```javascript
// Especificaciones de diseño:
const handleStyles = {
  size: 12, // px
  borderRadius: '50%', // circular
  backgroundColor: '#ffffff',
  border: '2px solid #00c4cc', // color turquesa de Canva
  boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
  cursor: {
    corners: ['nwse-resize', 'nesw-resize'],
    sides: ['ns-resize', 'ew-resize'],
    rotation: 'url(rotate-cursor.png), auto'
  }
};

const selectionBox = {
  border: '2px solid #00c4cc',
  backgroundColor: 'transparent'
};
```

### 5. Interactividad UX
- **Hover**: Handles aumentan de tamaño (scale 1.2) y cambian opacidad
- **Active**: Feedback visual claro del handle activo
- **Tooltips**: Mostrar dimensiones durante redimensión y ángulo durante rotación
- **Smooth animations**: Transiciones suaves CSS (150ms ease)
- **Touch support**: Handles más grandes en dispositivos táctiles (16px)

### 6. Funcionalidades Avanzadas
- **Multi-selección**: Permitir transformar múltiples objetos
- **Grupos**: Tratar grupos como una sola unidad
- **Proporciones bloqueadas**: Toggle para bloquear aspect ratio
- **Historial (undo/redo)**: Guardar estados antes/después de transformaciones
- **Guías inteligentes**: Mostrar alineación con otros objetos
- **Magnetismo**: Snap a bordes de otros objetos

## Requisitos Técnicos

### Stack Tecnológico
```javascript
// Preferiblemente usar:
- Canvas nativo HTML5 o
- Fabric.js / Konva.js / Paper.js para manejo de canvas
- TypeScript para type safety
- React/Vue/Vanilla JS según preferencia
```

### Estructura del Código
```typescript
// Interfaces principales que debe incluir:

interface Handle {
  id: string;
  type: 'corner' | 'side' | 'rotation';
  position: { x: number; y: number };
  cursor: string;
  onDrag: (e: MouseEvent) => void;
}

interface TransformableObject {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  scaleX: number;
  scaleY: number;
  lockAspectRatio: boolean;
}

interface TransformManager {
  selectedObjects: TransformableObject[];
  handles: Handle[];
  renderHandles: () => void;
  updateTransform: (handle: Handle, delta: {x: number, y: number}) => void;
  applyTransform: () => void;
  cancelTransform: () => void;
}
```

### Optimización
- Usar `requestAnimationFrame` para actualizaciones de render
- Debounce para eventos de mouse/touch intensivos
- Calcular bounding boxes eficientemente
- Lazy rendering de handles solo cuando hay selección

## Entregables Esperados

1. **Código principal**:
   - Sistema de handles completo
   - Lógica de transformación (resize, rotate)
   - Event handlers (mouse, touch, keyboard)
   
2. **Utilidades**:
   - Funciones matemáticas (cálculo de ángulos, transformaciones)
   - Detección de colisiones para snap
   - Sistema de guías y magnetismo

3. **Estilos**:
   - CSS/estilos para handles y selection box
   - Cursores personalizados
   - Animaciones y transiciones

4. **Demo funcional**:
   - Ejemplo de uso con algunos objetos
   - Controles para probar todas las funcionalidades

## Ejemplo Visual de Referencia

```
       [rotation-handle]
              |
              | (línea punteada)
              |
    [•]------[•]------[•]
     |                 |
     |   OBJETO        |
     |   SELECTED      |
     |                 |
    [•]------[•]------[•]

Leyenda:
[•] = handles de esquina y borde
[rotation] = handle de rotación con ícono
```

## Casos de Uso a Soportar
1. Usuario selecciona imagen y la redimensiona desde esquina
2. Usuario rota texto usando handle superior
3. Usuario redimensiona forma geométrica manteniendo proporciones con Shift
4. Usuario alinea múltiples objetos usando guías inteligentes
5. Usuario en tablet/móvil manipula objetos con touch

## Consideraciones de Accesibilidad
- Soporte para navegación por teclado (arrow keys + Shift/Ctrl)
- Alto contraste para handles
- Anuncios ARIA para cambios de estado
- Tamaños touch-friendly (mínimo 44x44px en móvil)

---

**Nota**: El código debe ser modular, extensible y bien documentado con comentarios explicativos. Prioriza la experiencia de usuario fluida y profesional similar a Canva.