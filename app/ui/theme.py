from PySide6.QtGui import QColor, QPalette


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