# Sidebar Component Documentation

## Resumen
El sidebar implementa un comportamiento **Docked / Floating / Minimized**, permitiendo al usuario desacoplar el menú en una ventana flotante independiente.

## Estados (Modos)

1.  **Docked (Estático)**:
    *   Anclado a la izquierda.
    *   Redimensionable (borde derecho).
    *   Contenido principal se ajusta (`margin-left`).
    *   **Acción**: Botón "Desacoplar" (icono columnas) -> Cambia a Floating.

2.  **Floating (Ventana)**:
    *   Ventana flotante draggable (por la cabecera).
    *   Contenido principal se expande al 100% de ancho.
    *   **Acción**:
        *   Botón `[-]` (Minimizar) -> Cambia a Minimized.
        *   Botón `[x]` (Acoplar) -> Vuelve a Docked.

3.  **Minimized (Icono)**:
    *   Icono flotante (burbuja).
    *   **Acción**: Click/Doble Click -> Vuelve a Floating.

## API JavaScript (`window.sidebarAPI`)

```javascript
// Desacoplar (Static -> Floating)
sidebarAPI.undock();

// Acoplar (Floating -> Static)
sidebarAPI.dock();

// Minimizar (Floating -> Icon)
sidebarAPI.minimize();

// Restaurar (Icon -> Floating)
sidebarAPI.restore();
```

## LocalStorage

Key: `nas_sidebar_state_v2`
```json
{
  "width": 260,
  "mode": "docked", // docked | floating | minimized
  "winPos": { "x": 100, "y": 100 },
  "iconPos": { "x": 20, "y": 100 }
}
```

## CSS Clases Importantes

- `body.sidebar-docked`: Aplica margen al contenido main.
- `body.sidebar-floating`: Quita margen al contenido.
- `aside.mode-docked`: Fijo a la izquierda. Oculta window-controls.
- `aside.mode-floating`: Posición absoluta/fixed configurable. Muestra window-controls.
