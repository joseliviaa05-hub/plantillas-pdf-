PROMPT:

Quiero que analices completamente mi proyecto, especialmente el archivo canvas_editor.py, que usa QGraphicsScene (CanvasScene) y QGraphicsView (CanvasView) para renderizar el canvas de edición.

Tu tarea es agregar guías inteligentes (smart guides) al estilo Canva/Figma/Illustrator.

🎯 OBJETIVO PRINCIPAL

Implementar en mi editor un sistema completo de guías inteligentes que muestre líneas visuales temporales cuando el usuario mueve un objeto en el canvas, ayudándolo a alinear elementos entre sí y con el canvas.

Debe incluir:

Guías verticales y horizontales

Guías de centrado (center alignment)

Alineación de bordes (left / right / top / bottom)

Alineación por centros de objetos

Guías cuando la distancia entre elementos es igual

Snap suave (imantación) cuando un objeto se acerca a una alineación

Todo debe funcionar mientras el usuario arrastra un objeto.

🧠 REQUISITOS TÉCNICOS DETALLADOS
1. Detección de alineación entre objetos

Durante un movimiento (mouseMoveEvent de los items o tracking en CanvasScene):

Detectar si el objeto que se está moviendo está cerca de:

Centros de otros objetos:

centerX

centerY

Bordes de otros objetos:

left

right

top

bottom

Líneas guías del canvas:

centro vertical del canvas

centro horizontal del canvas

Establecer un umbral configurable (por defecto 5–10 px).

Si la distancia es menor al umbral → disparar una guía.

2. Mostrar líneas guías temporales

Agregar dentro de CanvasScene:

Lista que contenga QGraphicsLineItem para las guías activas

Método:

showGuideLine(line)

clearGuides()

Las guías deben ser:

color: #ff4dd4 (como Canva) o similar

opacidad: 0.6

grosor: 1–2 px

no seleccionables

no interferir con eventos del usuario

Las líneas se dibujan en coordenadas de escena.

3. Implementar Snap / Imantación

Cuando se detecte una alineación válida:

Ajustar automáticamente x o y del objeto movido para que coincida exactamente con la guía.

El snap debe sentirse suave, no rígido.

Debe activarse sólo cuando el usuario esté muy cerca (umbral configurable).

4. Integración con tus clases reales

El código debe integrarse correctamente con:

CanvasScene

CanvasView

Clases de items existentes (imágenes, formas, texto, etc.)

Si es necesario:

crear una clase nueva SmartGuideManager

mover la lógica repetida a métodos utilitarios

No romper el zoom, pan, selección múltiple, ni las herramientas actuales.

🔄 FLUJO COMPLETO ESPERADO

Usuario mueve un objeto en el canvas.

El sistema analiza la posición del objeto contra otros items y el canvas.

Si encuentra alineación potencial → muestra guía visual inmediatamente.

Si el objeto está cerca → aplicar snap.

Al soltar (mouseReleaseEvent) →

eliminar todas las guías

mantener la posición final correcta

🧩 ARQUITECTURA SUGERIDA

Si hace falta, crear estos métodos dentro de CanvasScene:

updateSmartGuides(movingItem)
detectAlignment(movingItem, otherItem)
drawVerticalGuide(x)
drawHorizontalGuide(y)
clearGuides()
applySnap(movingItem, alignmentInfo)


Y si es necesario:

añadir un override elegante en mouseMoveEvent de los items

o manejarlo directamente desde CanvasScene mediante itemChange si tus items lo permiten.

🧪 VERIFICACIÓN Y ENTREGA

Antes de finalizar:

Mostrame un plan de implementación detallado, paso por paso.

Luego aplicá los cambios en una nueva rama.

Mostrame el diff completo.

Explicá brevemente la arquitectura implementada.

Asegurate de que las guías NO queden pegadas permanentemente en la escena.

Confirmá que no se rompen las herramientas existentes.

📌 NOTAS IMPORTANTES

Respetá el estilo y arquitectura del proyecto.

Podés crear archivos nuevos si hace falta.

Usá nombres claros como SmartGuide, AlignmentInfo, etc.

No mezclar lógica de UI con lógica de alineación.

Prioridad máxima: precisión y suavidad del comportamiento, estilo Canva 1:1.

FIN DEL PROMPT