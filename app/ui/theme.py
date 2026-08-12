"""Colour palette and application-wide stylesheet for the dark-glass UI."""
from __future__ import annotations

DARK = "#06182a"
# Glass panels are approximately 20% transparent (80% opaque), with a deep blue tone.
PANEL = "rgba(7, 31, 55, 205)"
PANEL_2 = "rgba(10, 42, 71, 216)"
PANEL_3 = "rgba(14, 54, 89, 222)"
BORDER = "#397db2"
ACCENT = "#2f91ee"
ACCENT_HOVER = "#5eb3ff"
TEXT = "#f4f8fd"
MUTED = "#b8cee3"
SUCCESS = "#41d187"
WARNING = "#f0b458"


def build_stylesheet() -> str:
    return f"""
        * {{ font-family: 'Segoe UI'; font-size: 12px; color: {TEXT}; }}
        QMainWindow, QWidget {{ background: transparent; }}
        #titleBar {{ background-color: rgba(4, 18, 34, 220); border-bottom: 1px solid rgba(69, 132, 181, 180); }}
        #windowTitle {{ font-size: 13px; font-weight: 500; }}
        #windowControl {{ background: transparent; border: none; font-size: 19px; padding: 0; }}
        #windowControl:hover {{ background: rgba(37, 87, 129, 210); }}
        #brandHeader {{ background: rgba(4, 20, 38, 76); border-bottom: 1px solid rgba(67, 128, 177, 130); }}
        #brandLogo {{ background: transparent; }}
        #creditLabel {{ font-size: 13px; color: white; background: transparent; }}
        #glassPanel {{ background-color: {PANEL}; border: 1px solid {BORDER}; border-radius: 13px; }}
        #statusCard, #fileCard, #previewHeader {{ background-color: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 10px; }}
        #sectionTitle {{ font-size: 20px; font-weight: 700; }}
        #navButton, #navActive {{ text-align: left; padding: 0 14px; border-radius: 9px; border: 1px solid {BORDER}; background: rgba(10, 42, 71, 207); }}
        #navButton:hover {{ background: rgba(23, 74, 113, 226); border: 1px solid #64a8dc; }}
        #navActive {{ background: rgba(32, 116, 199, 230); border: 1px solid #6ebaff; font-weight: 700; }}
        #readyLabel, #footerReady {{ color: {SUCCESS}; font-weight: 600; }}
        #mutedLabel, #fieldLabel, #groupJobs {{ color: {MUTED}; }}
        #dropZone {{ border: 1px dashed #70a9d3; border-radius: 10px; background: rgba(9, 42, 72, 199); }}
        #dropZone:hover {{ border: 1px dashed {ACCENT}; background: rgba(17, 62, 99, 216); }}
        #dropTitle, #fileName, #groupTitle {{ font-size: 13px; font-weight: 700; }}
        #pdfBadge {{ background: #fff2f2; color: #ed3131; border-radius: 6px; font-size: 11px; font-weight: 800; }}
        #wordBadge {{ background: #2479dc; color: white; border-radius: 5px; font-size: 13px; font-weight: 800; }}
        #previewFile {{ color: {ACCENT}; }}
        #previewImage {{ background: rgba(245, 247, 250, 244); border-radius: 7px; border: 1px solid #456f94; padding: 8px; }}
        QLineEdit, QDateEdit, QComboBox, QSpinBox, QTextEdit {{ background: rgba(8, 38, 65, 224); border: 1px solid #4f88b6; border-radius: 6px; padding: 7px 9px; selection-background-color: {ACCENT}; }}
        QLineEdit:focus, QDateEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
        QComboBox QAbstractItemView {{ background: #123e64; selection-background-color: #267fc8; }}
        #secondaryButton, #largeSecondary, #largePrimary {{ border-radius: 7px; padding: 9px 14px; min-height: 20px; font-weight: 700; }}
        #secondaryButton, #largeSecondary {{ background: rgba(12, 49, 81, 229); border: 1px solid #5798c9; }}
        #secondaryButton:hover, #largeSecondary:hover {{ background: rgba(26, 84, 127, 235); }}
        #largePrimary {{ background: rgba(33, 119, 213, 238); border: 1px solid #74bbf7; }}
        #largePrimary:hover {{ background: {ACCENT_HOVER}; }}
        #workTree {{ background: rgba(5, 28, 50, 216); border: 1px solid #4c83ad; border-radius: 8px; outline: 0; alternate-background-color: rgba(17, 57, 91, 220); }}
        #workTree::item {{ min-height: 24px; border-bottom: 1px solid rgba(73, 126, 166, 105); }}
        #workTree::item:selected {{ background: rgba(36, 117, 188, 226); }}
        QHeaderView::section {{ background: rgba(13, 54, 88, 235); color: white; border: none; border-right: 1px solid #558db7; border-bottom: 1px solid #558db7; padding: 7px; font-weight: 700; }}
        #groupScroll {{ background: transparent; border: none; }}
        #groupCard, #groupCardSelected {{ background: rgba(9, 40, 68, 220); border: 1px solid #4f87b3; border-radius: 9px; }}
        #groupCard:hover {{ background: rgba(23, 76, 117, 232); border: 1px solid #73b4e5; }}
        #groupCardSelected {{ background: rgba(26, 91, 145, 232); border: 1px solid {ACCENT}; }}
        #countBadge {{ background: #2f78b2; border-radius: 13px; font-weight: 700; }}
        #chevron {{ font-size: 25px; color: #d9e9fb; }}
        #footer {{ background: rgba(4, 22, 40, 218); border-top: 1px solid rgba(69, 132, 181, 180); }}
        #reportCount {{ color: {ACCENT}; font-weight: 700; }}
        QScrollBar:vertical {{ background: rgba(9, 39, 65, 220); width: 10px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: #4e86af; min-height: 28px; border-radius: 5px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QMenu {{ background: #123e64; border: 1px solid #5792bd; padding: 5px; }}
        QMenu::item {{ padding: 7px 22px; border-radius: 4px; }}
        QMenu::item:selected {{ background: #267fc8; }}
        QMessageBox, QDialog {{ background: #103a5d; }}
    """
