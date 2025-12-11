"""
Centralized styles for the Modern Pro GUI.

Premium dark theme featuring:
- Glassmorphism with backdrop blur effects
- Smooth gradient accents
- Micro-animations and transitions
- Modern typography system
- Depth through shadows and layering
"""

# Color System - Premium Dark Palette
COLORS = {
    "bg_darkest": "#05070f",
    "bg_dark": "#0a0e17",
    "bg_medium": "#111827",
    "bg_light": "#1f2937",
    "bg_elevated": "#2d3748",
    "accent_primary": "#818cf8",  # Indigo
    "accent_secondary": "#c084fc",  # Purple
    "accent_success": "#34d399",  # Emerald
    "accent_warning": "#fbbf24",  # Amber
    "accent_danger": "#f87171",  # Red
    "accent_info": "#38bdf8",  # Sky
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border_subtle": "#1e293b",
    "border_default": "#334155",
}

DARK_THEME = """
/* ==========================================================================
   🎨 MODERN PRO THEME - AgencyOS
   Premium dark theme with glassmorphism and gradients
   ========================================================================== */

/* --- BASE RESET & FOUNDATION --- */
QMainWindow, QWidget {
    background-color: #05070f;
    color: #f8fafc;
    font-family: 'Inter', 'SF Pro Display', 'Segoe UI', -apple-system, sans-serif;
    font-size: 15px;
    selection-background-color: #818cf8;
    selection-color: white;
}

/* --- TYPOGRAPHY SYSTEM --- */
QLabel#h1 {
    font-size: 36px;
    font-weight: 800;
    color: #ffffff;
    letter-spacing: -1px;
    padding-bottom: 4px;
}

QLabel#h2 {
    font-size: 26px;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: -0.5px;
}

QLabel#h3 {
    font-size: 18px;
    font-weight: 600;
    color: #e2e8f0;
}

QLabel#subtitle {
    color: #64748b;
    font-size: 15px;
    font-weight: 500;
}

QLabel#accent {
    color: #818cf8;
    font-weight: 600;
}

/* --- PREMIUM BUTTONS --- */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #374151, stop:1 #1f2937);
    border: 1px solid #4b5563;
    color: #f3f4f6;
    padding: 14px 28px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 16px;
    min-height: 24px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4b5563, stop:1 #374151);
    border-color: #6b7280;
}

QPushButton:pressed {
    background: #1f2937;
    border-color: #818cf8;
}

QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a855f7);
    border: none;
    color: white;
    font-weight: 700;
    font-size: 17px;
    padding: 16px 32px;
}

QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #818cf8, stop:0.5 #a78bfa, stop:1 #c084fc);
}

QPushButton#success {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #059669, stop:1 #10b981);
    border: none;
    color: white;
}

QPushButton#danger {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #dc2626, stop:1 #ef4444);
    border: none;
    color: white;
}

QPushButton#ghost {
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
}

QPushButton#ghost:hover {
    background: rgba(99, 102, 241, 0.1);
    border-color: #818cf8;
    color: #c7d2fe;
}

/* --- GLASS INPUT FIELDS --- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(30, 41, 59, 0.8), stop:1 rgba(15, 23, 42, 0.9));
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 18px;
    color: #f1f5f9;
    font-size: 16px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
    border: 2px solid #818cf8;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(49, 46, 129, 0.3), stop:1 rgba(30, 41, 59, 0.9));
}

QLineEdit::placeholder {
    color: #475569;
}

/* --- PREMIUM DROPDOWNS --- */
QComboBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(30, 41, 59, 0.8), stop:1 rgba(15, 23, 42, 0.9));
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px 18px;
    color: #f1f5f9;
    font-size: 16px;
    min-width: 140px;
}

QComboBox:hover {
    border-color: #475569;
}

QComboBox:focus {
    border: 2px solid #818cf8;
}

QComboBox::drop-down {
    border: none;
    padding-right: 12px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #818cf8;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: #4f46e5;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 10px 16px;
    border-radius: 6px;
    min-height: 24px;
}

QComboBox QAbstractItemView::item:hover {
    background: rgba(99, 102, 241, 0.2);
}

/* --- GLASSMORPHISM CONTAINERS --- */
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(30, 41, 59, 0.6), stop:1 rgba(15, 23, 42, 0.8));
    border: 1px solid rgba(51, 65, 85, 0.5);
    border-radius: 16px;
    margin-top: 28px;
    padding: 24px;
    padding-top: 32px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 20px;
    padding: 0 12px;
    color: #818cf8;
    font-weight: 700;
    font-size: 16px;
    background: #0a0e17;
    border-radius: 4px;
}

QFrame#card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(30, 41, 59, 0.7), stop:1 rgba(15, 23, 42, 0.85));
    border: 1px solid rgba(51, 65, 85, 0.4);
    border-radius: 20px;
    padding: 24px;
}

/* --- MODERN TABS --- */
QTabWidget::pane {
    border: 1px solid #1e293b;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0f172a, stop:1 #0a0e17);
    border-radius: 16px;
    padding: 20px;
    margin-top: -1px;
}

QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 16px 28px;
    margin-right: 4px;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    font-weight: 600;
    font-size: 16px;
    min-width: 100px;
}

QTabBar::tab:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1e293b, stop:1 #0f172a);
    color: #818cf8;
    border-bottom: 3px solid #818cf8;
}

QTabBar::tab:hover:!selected {
    background: rgba(30, 41, 59, 0.5);
    color: #94a3b8;
}

/* --- PREMIUM TABLES --- */
QTableWidget {
    background: transparent;
    border: 1px solid #1e293b;
    border-radius: 16px;
    gridline-color: #1e293b;
    alternate-background-color: rgba(30, 41, 59, 0.3);
}

QTableWidget::item {
    padding: 14px 16px;
    border-bottom: 1px solid #1e293b;
}

QTableWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(99, 102, 241, 0.3), stop:1 rgba(139, 92, 246, 0.2));
}

QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1e293b, stop:1 #0f172a);
    color: #94a3b8;
    padding: 16px;
    border: none;
    border-bottom: 2px solid #334155;
    font-weight: 700;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* --- SLEEK SCROLLBARS --- */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #475569, stop:1 #64748b);
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background: #818cf8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px 4px;
}

QScrollBar::handle:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #475569, stop:1 #64748b);
    border-radius: 4px;
    min-width: 40px;
}

/* --- PROGRESS BARS --- */
QProgressBar {
    background: rgba(30, 41, 59, 0.5);
    border: none;
    border-radius: 8px;
    height: 10px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a855f7);
    border-radius: 8px;
}

/* --- DIALOGS --- */
QDialog {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #1e293b, stop:1 #0f172a);
    border-radius: 20px;
}

QMessageBox {
    background: #111827;
}

QMessageBox QLabel {
    color: #f1f5f9;
    font-size: 14px;
}

/* --- SPLITTERS --- */
QSplitter::handle {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent, stop:0.5 #334155, stop:1 transparent);
}

QSplitter::handle:horizontal {
    width: 3px;
}

QSplitter::handle:vertical {
    height: 3px;
}

QSplitter::handle:hover {
    background: #818cf8;
}

/* --- SCROLL AREAS --- */
QScrollArea {
    border: none;
    background: transparent;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* --- TOOLTIPS --- */
QToolTip {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #334155, stop:1 #1e293b);
    color: #f1f5f9;
    border: 1px solid #475569;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
}

/* --- LISTS --- */
QListWidget {
    background: transparent;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 8px;
    outline: none;
}

QListWidget::item {
    padding: 12px 16px;
    border-radius: 8px;
    margin: 2px 0;
}

QListWidget::item:hover {
    background: rgba(99, 102, 241, 0.1);
}

QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(99, 102, 241, 0.3), stop:1 rgba(139, 92, 246, 0.2));
    color: #c7d2fe;
}

/* --- MENU BAR --- */
QMenuBar {
    background: #0a0e17;
    color: #94a3b8;
    padding: 4px;
}

QMenuBar::item:selected {
    background: #1e293b;
    color: #818cf8;
    border-radius: 6px;
}

QMenu {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 8px;
}

QMenu::item {
    padding: 10px 24px;
    border-radius: 6px;
}

QMenu::item:selected {
    background: #4f46e5;
}

/* --- STATUS BAR --- */
QStatusBar {
    background: #0a0e17;
    border-top: 1px solid #1e293b;
    color: #64748b;
    font-size: 12px;
}
"""

# Accent color variants for specific components
ACCENT_COLORS = {
    "primary": "#818cf8",
    "secondary": "#c084fc",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "info": "#38bdf8",
}
