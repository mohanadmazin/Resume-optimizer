from PySide6.QtGui import QColor, QFont, QPalette


# ── Rezi-style color palette ──────────────────────────────────────────────

REZI_COLORS = {
    "window_bg": "#0d1729",
    "sidebar_bg": "#101c31",
    "card_bg": "#1d293d",
    "input_bg": "#1d293d",
    "border": "#34425b",
    "input_border": "#4a5a73",
    "input_border_focus": "#8493ff",
    "primary": "#8190f7",
    "primary_hover": "#929fff",
    "primary_pressed": "#6e7ee5",
    "primary_dark": "#7d8cf8",
    "purple": "#7a22ad",
    "purple_check": "#8997ff",
    "text_primary": "#ffffff",
    "text_secondary": "#9aa7bd",
    "text_muted": "#66738b",
    "dark_text": "#08101e",
    "icon_inactive": "#d9e2f0",
    "hover_bg": "rgba(123, 139, 255, 0.12)",
    "menu_bg": "#1d293d",
    "menu_border": "#33425d",
    "toggle_track_on": "#8191ff",
    "toggle_thumb_on": "#d8ddff",
    "toggle_track_off": "#344258",
    "toggle_thumb_off": "#172337",
}

REZI_FONT_FAMILY = "Inter, Arial, Segoe UI, sans-serif"


def rezi_font(size: int = 14, weight: int = 400) -> QFont:
    """Create a QFont with the Rezi font stack."""
    font = QFont("Inter", size)
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    if weight >= 700:
        font.setBold(True)
    return font


DARK_STYLESHEET = """

/* Main window */
QMainWindow {
    background-color: #0F172A;
}


/* Global widgets */
QWidget {
    background-color: #0F172A;
    color: #E2E8F0;
    font-family: "Segoe UI";
   
}


/* Sidebar */
QListWidget {
    background-color: #111827;
    border: none;
    padding: 10px;
    outline: none;
}


QListWidget::item {
    color: #CBD5E1;
    padding: 14px;
    margin: 4px 0;
    border-radius: 8px;
}


QListWidget::item:hover {
    background-color: #1E293B;
    color: white;
}


QListWidget::item:selected {
    background-color: #2563EB;
    color: white;
}


/* Stack pages */
QStackedWidget {
    background-color: #0F172A;
}


/* Labels */
QLabel {
    color: #E2E8F0;
}


/* Buttons */
QPushButton {
    background-color: #2563EB;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
}


QPushButton:hover {
    background-color: #1D4ED8;
}


QPushButton:pressed {
    background-color: #1E40AF;
}


/* Inputs */
QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox {

    background-color: #1E293B;
    color: #F8FAFC;

    border: 1px solid #334155;
    border-radius: 8px;

    padding: 8px;
}


QLineEdit:focus,
QTextEdit:focus,
QPlainTextEdit:focus,
QComboBox:focus {

    border: 1px solid #3B82F6;
}


/* Combo box */
QComboBox QAbstractItemView {

    background-color: #1E293B;
    color: white;
    selection-background-color: #2563EB;
}


/* Group boxes */
QGroupBox {

    border: 1px solid #334155;
    border-radius: 12px;

    margin-top: 15px;
    padding: 15px;

    color: #93C5FD;
    font-weight: bold;
}


/* Scroll bars */
QScrollBar:vertical {

    background-color: #111827;
    width: 10px;
}


QScrollBar::handle:vertical {

    background-color: #475569;
    border-radius: 5px;
}


QScrollBar::handle:vertical:hover {

    background-color: #64748B;
}


/* Status bar */
QStatusBar {

    background-color: #111827;
    color: #94A3B8;
}

/* Loading overlay */
LoadingOverlay {
    background-color: rgba(0, 0, 0, 150);
}

LoadingOverlay QLabel {
    color: white;
    background: transparent;
}

/* Pipeline button */
#pipelineBtn {
    background-color: #2563EB;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
}

#pipelineBtn:hover {
    background-color: #1D4ED8;
}

#pipelineBtn:disabled {
    background-color: #334155;
    color: #94A3B8;
}

#cancelBtn {
    background-color: #EF4444;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: bold;
}

#cancelBtn:hover {
    background-color: #DC2626;
}

#pipelineDesc {
    color: #94A3B8;
    font-size: 13px;
}

#stepLabel {
    color: #94A3B8;
    font-size: 13px;
}

/* Fact guard review panel */
#reviewPanel {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px;
}

#reviewHeader {
    color: #F59E0B;
    font-weight: bold;
    font-size: 14px;
    padding: 4px 0;
}

#changeCard {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px;
}

#factBanner {
    border-radius: 6px;
}

"""
LIGHT_STYLESHEET = """

QMainWindow {
    background-color: #F8FAFC;
}


QWidget {
    background-color: #F8FAFC;
    color: #0F172A;
    font-family: "Segoe UI";
    
}
QStackedWidget {
    background-color: #F8FAFC;
}
QLabel {
    color: #0F172A;
}

QListWidget {

    background-color: #FFFFFF;
    border-right: 1px solid #E2E8F0;
    padding: 10px;
}


QListWidget::item {

    color: #334155;
    padding: 14px;
    border-radius: 8px;
}


QListWidget::item:hover {

    background-color: #E2E8F0;
}


QListWidget::item:selected {

    background-color: #2563EB;
    color: white;
}


QLineEdit,
QTextEdit,
QPlainTextEdit,
QComboBox {

    background-color: white;
    color: #0F172A;

    border: 1px solid #CBD5E1;
    border-radius: 8px;

    padding: 8px;
}


QPushButton {

    background-color: #2563EB;
    color: white;

    border-radius: 8px;
    padding: 10px 18px;

    font-weight: bold;
}


QPushButton:hover {

    background-color: #1D4ED8;
}


QStatusBar {

    background-color: #FFFFFF;
    color: #64748B;
}

/* Loading overlay */
LoadingOverlay {
    background-color: rgba(0, 0, 0, 100);
}

LoadingOverlay QLabel {
    color: white;
    background: transparent;
}

/* Pipeline button */
#pipelineBtn {
    background-color: #2563EB;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 15px;
    font-weight: bold;
}

#pipelineBtn:hover {
    background-color: #1D4ED8;
}

#pipelineBtn:disabled {
    background-color: #CBD5E1;
    color: #94A3B8;
}

#cancelBtn {
    background-color: #EF4444;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: bold;
}

#cancelBtn:hover {
    background-color: #DC2626;
}

#pipelineDesc {
    color: #64748B;
    font-size: 13px;
}

#stepLabel {
    color: #64748B;
    font-size: 13px;
}

/* Fact guard review panel */
#reviewPanel {
    background-color: #F1F5F9;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px;
}

#reviewHeader {
    color: #D97706;
    font-weight: bold;
    font-size: 14px;
    padding: 4px 0;
}

#changeCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 4px;
}

#factBanner {
    border-radius: 6px;
}

"""

def create_dark_theme():

    return {

        QPalette.Window:
            QColor("#0F172A"),

        QPalette.WindowText:
            QColor("#E2E8F0"),

        QPalette.Base:
            QColor("#111827"),

        QPalette.AlternateBase:
            QColor("#1E293B"),

        QPalette.Text:
            QColor("#E2E8F0"),

        QPalette.Button:
            QColor("#2563EB"),

        QPalette.ButtonText:
            QColor("#FFFFFF"),

        QPalette.Highlight:
            QColor("#2563EB"),

        QPalette.HighlightedText:
            QColor("#FFFFFF"),

    }



def create_light_theme():

    return {

        QPalette.Window:
            QColor("#F8FAFC"),

        QPalette.WindowText:
            QColor("#0F172A"),

        QPalette.Base:
            QColor("#FFFFFF"),

        QPalette.AlternateBase:
            QColor("#F1F5F9"),

        QPalette.Text:
            QColor("#0F172A"),

        QPalette.Button:
            QColor("#2563EB"),

        QPalette.ButtonText:
            QColor("#FFFFFF"),

        QPalette.Highlight:
            QColor("#2563EB"),

        QPalette.HighlightedText:
            QColor("#FFFFFF"),

    }