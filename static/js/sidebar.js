import { makeDraggable } from './drag.js';

class SidebarController {
    constructor() {
        this.minWidth = 200;
        this.maxWidth = 420;
        this.defaultWidth = 260;
        this.storageKey = 'nas_sidebar_state_v4';

        // Elements
        this.sidebar = document.getElementById('sidebar-container');
        this.resizer = document.querySelector('.sidebar-resizer');
        this.root = document.documentElement;
        this.floatingIcon = document.getElementById('sidebar-floating-icon');

        // State init
        this.state = this.loadState();
        this.isResizing = false;

        this.init();
    }

    loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) return JSON.parse(saved);
        } catch (e) {
            console.error(e);
        }
        return {
            width: this.defaultWidth, // The docked width preference
            mode: 'docked', // docked | floating | minimized
            winPos: { x: 100, y: 100 },
            iconPos: { x: 20, y: 100 }
        };
    }

    saveState() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.state));
    }

    init() {
        // Initial render matches state
        this.refreshLayout();

        // --- Window Drag ---
        if (this.sidebar) {
            makeDraggable(this.sidebar, {
                handle: '.window-controls',
                onDragEnd: (info) => {
                    this.state.winPos = { x: info.x, y: info.y };
                    this.saveState();
                }
            });
        }

        // --- Icon Drag ---
        if (this.floatingIcon) {
            this.floatingIcon.style.left = `${this.state.iconPos.x}px`;
            this.floatingIcon.style.top = `${this.state.iconPos.y}px`;

            makeDraggable(this.floatingIcon, {
                onDragEnd: (info) => {
                    this.state.iconPos = { x: info.x, y: info.y };
                    this.saveState();
                }
            });

            this.floatingIcon.addEventListener('dblclick', () => {
                this.restore();
            });
        }

        // --- Mobile Overlay & Toggle ---
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.toggleMobile(false));
        }

        const toggleBtn = document.getElementById('mobile-menu-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent immediate close triggers if any
                this.toggleMobile();
            });
        }

        // --- Resizer ---
        if (this.resizer) {
            this.resizer.addEventListener('mousedown', (e) => this.startResize(e));
        }

        window.sidebarAPI = {
            undock: () => this.undock(),
            dock: () => this.dock(),
            minimize: () => this.minimize(),
            restore: () => this.restore(),
            toggleMobile: (force) => this.toggleMobile(force)
        };
    }

    // --- Core Logic ---

    toggleMobile(forceState) {
        const isOpen = forceState !== undefined
            ? forceState
            : !this.sidebar.classList.contains('mobile-open');

        if (isOpen) {
            this.sidebar.classList.add('mobile-open');
            if (this.overlay) {
                this.overlay.classList.remove('hidden');
                requestAnimationFrame(() => {
                    this.overlay.classList.remove('opacity-0');
                });
            }
        } else {
            this.sidebar.classList.remove('mobile-open');
            if (this.overlay) {
                this.overlay.classList.add('opacity-0');
                setTimeout(() => {
                    this.overlay.classList.add('hidden');
                }, 300);
            }
        }
    }

    refreshLayout() {
        const mode = this.state.mode;

        // classes
        this.sidebar.classList.remove('mode-docked', 'mode-floating', 'mode-minimized');
        document.body.classList.remove('sidebar-docked', 'sidebar-floating', 'sidebar-minimized');
        this.floatingIcon.classList.remove('visible');

        this.sidebar.classList.add(`mode-${mode}`);
        document.body.classList.add(`sidebar-${mode}`);

        // Variables update
        if (mode === 'docked') {
            // Synced: Offset = Panel Width
            this.setCSSVar('--sidebar-panel-width', `${this.state.width}px`);
            this.setCSSVar('--layout-offset', `${this.state.width}px`);

            // Reset position styles from floating
            this.sidebar.style.left = '0';
            this.sidebar.style.top = '0';
            this.sidebar.style.height = '100vh';
            this.sidebar.style.transform = '';

        } else if (mode === 'floating') {
            // Window gets standard width (280px) or previous logic? 
            // Implementation plan says 280px fixed for now.
            // Layout Offset is 0
            this.setCSSVar('--layout-offset', `0px`);

            this.sidebar.style.height = '600px';
            this.sidebar.style.left = `${this.state.winPos.x}px`;
            this.sidebar.style.top = `${this.state.winPos.y}px`;
            // width controlled by css !important for now, or we can set var
            this.setCSSVar('--sidebar-panel-width', `280px`);

        } else if (mode === 'minimized') {
            this.floatingIcon.classList.add('visible');
            this.setCSSVar('--layout-offset', `0px`);
        }
    }

    setMode(mode) {
        this.state.mode = mode;
        this.saveState();
        this.refreshLayout();
    }

    undock() { this.setMode('floating'); }
    dock() { this.setMode('docked'); }
    minimize() { this.setMode('minimized'); }
    restore() { this.setMode('floating'); }


    // --- Resizing (Docked only) ---
    startResize(e) {
        if (this.state.mode !== 'docked') return;

        this.isResizing = true;
        document.body.classList.add('resizing', 'no-transition');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        const moveHandler = (moveEvent) => {
            if (!this.isResizing) return;
            let newWidth = moveEvent.clientX;
            if (newWidth < this.minWidth) newWidth = this.minWidth;
            if (newWidth > this.maxWidth) newWidth = this.maxWidth;

            // Update BOTH variables instantly
            this.setCSSVar('--sidebar-panel-width', `${newWidth}px`);
            this.setCSSVar('--layout-offset', `${newWidth}px`);
        };

        const stopHandler = () => {
            this.isResizing = false;
            document.body.classList.remove('resizing', 'no-transition');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';

            window.removeEventListener('mousemove', moveHandler);
            window.removeEventListener('mouseup', stopHandler);

            // Save state
            this.state.width = parseInt(getComputedStyle(this.root).getPropertyValue('--sidebar-panel-width'));
            this.saveState();
        };

        window.addEventListener('mousemove', moveHandler);
        window.addEventListener('mouseup', stopHandler);
    }

    setCSSVar(name, value) {
        this.root.style.setProperty(name, value);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SidebarController();
});
