/**
 * Lightweight drag utility for Sidebar Floating Icon & Windows
 */
export function makeDraggable(element, options = {}) {
    let isDragging = false;
    let startX, startY, initialLeft, initialTop;
    let hasMoved = false; // Track if movement occurred
    const MOVE_THRESHOLD = 3; // Pixels to consider "dragging"

    const { onDragEnd, onDragStart } = options;

    const handleStart = (e) => {
        if (e.target.closest('.no-drag')) return;
        // If we are dragging a window via header, element might be the window, 
        // but we only want to trigger if target is header.
        // This check usually belongs closer to invocation, but:
        if (options.handle && !e.target.closest(options.handle)) return;

        isDragging = true;
        hasMoved = false;

        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        startX = clientX;
        startY = clientY;

        const rect = element.getBoundingClientRect();
        initialLeft = rect.left;
        initialTop = rect.top;

        if (!e.type.startsWith('touch')) e.preventDefault();

        element.style.transition = 'none'; // Disable transition during drag

        if (onDragStart) onDragStart();
    };

    const handleMove = (e) => {
        if (!isDragging) return;

        const clientX = e.type.startsWith('touch') ? e.touches[0].clientX : e.clientX;
        const clientY = e.type.startsWith('touch') ? e.touches[0].clientY : e.clientY;

        const dx = clientX - startX;
        const dy = clientY - startY;

        // Check threshold
        if (Math.abs(dx) > MOVE_THRESHOLD || Math.abs(dy) > MOVE_THRESHOLD) {
            hasMoved = true;
        }

        let newLeft = initialLeft + dx;
        let newTop = initialTop + dy;

        const maxX = window.innerWidth - element.offsetWidth;
        const maxY = window.innerHeight - element.offsetHeight;

        newLeft = Math.max(0, Math.min(newLeft, maxX));
        newTop = Math.max(0, Math.min(newTop, maxY));

        element.style.left = `${newLeft}px`;
        element.style.top = `${newTop}px`;
        element.style.transform = 'none';
        element.style.bottom = 'auto';
        element.style.right = 'auto';
    };

    const handleEnd = () => {
        if (!isDragging) return;
        isDragging = false;
        element.style.transition = ''; // Restore transition

        if (onDragEnd) onDragEnd({
            x: parseFloat(element.style.left),
            y: parseFloat(element.style.top),
            wasDragged: hasMoved
        });
    };

    // Mouse events
    element.addEventListener('mousedown', handleStart);
    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleEnd);

    // Touch events
    element.addEventListener('touchstart', handleStart, { passive: false });
    window.addEventListener('touchmove', handleMove, { passive: false });
    window.addEventListener('touchend', handleEnd);

    return {
        destroy: () => {
            element.removeEventListener('mousedown', handleStart);
            window.removeEventListener('mousemove', handleMove);
            window.removeEventListener('mouseup', handleEnd);
            element.removeEventListener('touchstart', handleStart);
            window.removeEventListener('touchmove', handleMove);
            window.removeEventListener('touchend', handleEnd);
        }
    };
}
