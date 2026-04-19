from __future__ import annotations

import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)


# 資源路徑
ASSET_DIR = Path(__file__).resolve().parent / "asset" # SVG 圖示資料夾


# 顏色 helper：用 HEX code 設定 Qt 顏色
def hex_color(value: str) -> QColor:
    return QColor(value)


# 將 HEX 轉成 Windows DWM 使用的 COLORREF
def hex_to_colorref(value: str) -> int:
    color = QColor(value)
    return color.red() | (color.green() << 8) | (color.blue() << 16)


# 設定 Windows 原生標題列深色
def set_windows_title_bar_color(window: QWidget) -> None:
    if sys.platform != "win32":
        return

    try:
        hwnd = int(window.winId())
        dwmapi = ctypes.windll.dwmapi
        true_value = ctypes.c_int(1)
        caption_color = ctypes.c_int(hex_to_colorref(TITLE_BAR_HEX))
        text_color = ctypes.c_int(hex_to_colorref(TITLE_TEXT_HEX))

        # Windows 10/11 的深色標題列屬性版本可能不同，兩個都嘗試
        for attribute in (20, 19):
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(true_value),
                ctypes.sizeof(true_value),
            )

        # Windows 11 支援直接指定標題列與文字顏色
        for attribute, value in ((35, caption_color), (36, text_color)):
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
    except Exception:
        return


# 參數控制區
DEFAULT_APP_SIZE = (1080, 780) # 啟動時 app 寬高
TOOLBAR_GROUP_WIDTH = 1020 # toolbar 透明群組固定寬度
APP_BG_HEX = "#18191A" # App 主背景
TITLE_BAR_HEX = "#18191A" # Windows 原生標題列顏色
TITLE_TEXT_HEX = "#e8e8e8" # Windows 原生標題列文字顏色
CONTROL_BG_HEX = "#383B3F" # 按鈕和下拉選單背景
CONTROL_HOVER_HEX = "#141414" # 按鈕和下拉選單 hover 背景
CONTROL_PRESSED_HEX = "#2F3031" # 按鈕按下時背景
PANEL_BG_HEX = "#101011" # 影像區與示波器區背景
CONTROL_BORDER_HEX = "#555555" # 控制項邊框
SPLITTER_HANDLE_HEX = "#525252" # 示波器與影像區中間隔線顏色
TEXT_HEX = "#e8e8e8" # 一般文字
BRIGHT_TEXT_HEX = "#f0f0f0" # 控制項文字
WAVE_GRID_HEX = "#8F8F92" # 示波器格線顏色
WAVE_LINE_HEX = "#43a1df" # 示波器波型顏色
WAVE_CURSOR_HEX = "#ffc14d" # 示波器掃描游標顏色
WAVE_THRESHOLD_HEX = "#e73e3e" # 示波器 threshold 線顏色
RPM_VALUE_HEX = WAVE_LINE_HEX # RPM 數值顏色
CARD_BORDER_HEX = "#555555" # 右側資訊卡外框顏色
ROI_PAUSED_HEX = "#35d46a" # 暫停編輯時的 ROI 顏色
ROI_PLAYING_HEX = "#e73e3e" # 播放追蹤時的 ROI 顏色
ROI_PREVIEW_HEX = "#ffc14d" # 新增 ROI 時的預覽顏色
TRACKING_LINE_HEX = "#43a1df" # 中心位移線顏色
SPLITTER_HANDLE_WIDTH = 1 # 示波器與影像區中間隔線粗細
SLIDER_GROOVE_WIDTH = 10 # threshold 拉桿滑軌寬度
SLIDER_HANDLE_WIDTH = 25 # threshold 拉桿按鈕寬度
SLIDER_HANDLE_HEIGHT = 32 # threshold 拉桿按鈕高度
SLIDER_BORDER_RADIUS = 4 # threshold 拉桿圓角
ROI_LINE_WIDTH = 1 # ROI 框線粗細
ROI_CENTER_SIZE = 6 # ROI 中心控制點大小
ROI_HANDLE_SIZE = 6 # ROI 邊角調整點大小
ROI_HANDLE_LINE_WIDTH = 1 # ROI 調整點外框粗細
TRACKING_LINE_WIDTH = 4 # 中心位移線粗細
WAVE_THRESHOLD_LINE_WIDTH = 1 # 示波器 threshold 線粗細
RESPIRATION_TEXT = "Respiration (RPM)" # 呼吸速率標題
SMOOTH_TEXT = "Smooth" # 訊號平滑顯示標籤
THRESHOLD_TEXT = "Thresh." # threshold 顯示標籤
GAIN_TEXT = "Gain" # 示波器增益顯示標籤
SENS_TEXT = "Range" # 偵測靈敏度顯示標籤
WAVE_GRAPH_MARGIN_X = 16 # 示波器圖形左右留白
WAVE_GRAPH_MARGIN_TOP = 8 # 示波器圖形上方留白
WAVE_GRAPH_MARGIN_BOTTOM = 6 # 示波器標題下方留白
WAVE_TITLE_HEIGHT = 20 # 示波器標題預留高度
RESPIRATION_TITLE_HEIGHT = 20 # Respiration 與示波器標題共用高度
WAVE_TITLE_MIN_VISIBLE_HEIGHT = 70 # 高度不足時優先隱藏示波器標題
PANEL_TITLE_FONT_SIZE = 10 # 波型與 RPM 區標題字體大小
RPM_VALUE_FONT_SIZE = 48 # 呼吸速率數值字體大小
RESPIRATION_FONT_SIZE = 10 # Respiration 標題字體大小
THRESHOLD_LABEL_MIN_HEIGHT = 22 # 拉桿標籤最小高度
THRESHOLD_PANEL_MARGIN_X = 8 # Threshold 外框左右留白
THRESHOLD_PANEL_MARGIN_Y = 6 # Threshold 外框上下留白
WAVE_Y_AXIS_LABEL_WIDTH = 34 # 示波器 Y 軸 label 預留寬度
WAVE_Y_AXIS_LABEL_FONT_SIZE = 10 # 示波器 Y 軸 label 字體大小
PANEL_PADDING_Y = 10 # 板塊 3 上下留白
APP_CONTENT_MARGIN_X = 6 # app 內容左右留白
APP_CONTENT_MARGIN_Y = 4 # app 內容上下留白
APP_CONTENT_SPACING = 0 # toolbar 與主板塊間距
TOOLBAR_ITEM_SPACING = 5 # toolbar 元件與群組固定間距
TOOLBAR_GROUP_SPACING = 0 # toolbar 群組內 label 與輸入框間距
TOOLBAR_GROUP_BORDER_HEX = CONTROL_BORDER_HEX # toolbar 數值群組外框顏色
TOOLBAR_GROUP_BORDER_RADIUS = 4 # toolbar 數值群組外框圓角
TOOLBAR_GROUP_PADDING_X = 5 # toolbar 數值群組左右內距
TOOLBAR_GROUP_PADDING_Y = 3 # toolbar 數值群組上下內距
TOOLBAR_GROUP_SPIN_HEIGHT = 24 # toolbar 數值群組內 QSpinBox 高度
TOOLBAR_SPIN_MARGIN_RIGHT = 2 # toolbar QSpinBox 右側外距
TOOLBAR_SPIN_VALUE_PADDING_X = 2 # toolbar QSpinBox 數值和箭頭保留距離
TOOLBAR_MENU_STRETCH = 1 # toolbar 一般選單 expand 比例
TOOLBAR_ENHANCE_STRETCH = 5 # toolbar Enhance 選單 expand 比例
TOOLBAR_SPIN_GROUP_STRETCH = 1 # toolbar 數值群組 expand 比例
CONTROL_PADDING_X = 6 # 控制元件左右 padding
CONTROL_PADDING_Y = 6 # 控制元件上下 padding
CHECKBOX_BORDER_HEX = CONTROL_BORDER_HEX # checkbox 外框顏色
TOOLBAR_SCROLL_BG_HEX = APP_BG_HEX # toolbar scroll 背景色
TOOLBAR_SCROLL_HANDLE_HEX = "#90929C" # toolbar scroll handle 顏色
TOOLBAR_SCROLL_HANDLE_HOVER_HEX = "#71737A" # toolbar scroll hover 顏色
TOOLBAR_SCROLLBAR_HEIGHT = 4 # toolbar 水平 scroll 高度
TOOLBAR_SCROLL_BOTTOM_RESERVED_HEIGHT = 4 # toolbar 內容下方預留給水平 scroll 的空白
CAMERA_SETTING_DIALOG_WIDTH = 420 # Setting 小視窗寬度
CAMERA_SETTING_LABEL_WIDTH = 64 # Setting 相機設定名稱寬度
CAMERA_SETTING_AUTO_WIDTH = 54 # Setting auto checkbox 寬度
CAMERA_SETTING_VALUE_WIDTH = 90 # Setting 數值輸入寬度
CAMERA_SETTING_SLIDER_SCALE = 100 # 小數設定轉成水平 slider 整數刻度
CAMERA_EXPOSURE_MIN = 0.0 # 曝光控制最小值，實際支援依相機 driver
CAMERA_EXPOSURE_MAX = 255.0 # 曝光控制最大值，實際支援依相機 driver
CAMERA_EXPOSURE_DEFAULT = 0.0 # 曝光手動控制預設值
CAMERA_SHUTTER_MIN = -13.0 # 快門控制最小值，常見 UVC 使用負數
CAMERA_SHUTTER_MAX = 0.0 # 快門控制最大值，常見 UVC 使用負數
CAMERA_SHUTTER_DEFAULT = -6.0 # 快門手動控制預設值
SETTING_RESET_BUTTON_STRETCH = 1 # Setting reset 按鈕 expand 比例
SETTING_RESET_SPACER_STRETCH = 50 # Setting reset 右側透明拉伸比例
SETTING_RESET_LABEL_WIDTH = CAMERA_SETTING_LABEL_WIDTH # Setting reset 標籤寬度
CONTROL_WIDGET_HEIGHT = 32 # 按鈕和下拉選單統一高度
LOAD_MODE_MENU_WIDTH = 82 # toolbar Load Mode menu 寬度
CAMERA_MENU_WIDTH = 72 # toolbar Camera menu 寬度
ENHANCEMENT_MENU_WIDTH = 126 # toolbar Enhancement menu 寬度
SHOW_RAW_CHECK_WIDTH = 85 # toolbar Show RAW checkbox 寬度
DETECT_RATE_GROUP_WIDTH = 120 # toolbar Detect rate 群組寬度
DETECT_RATE_LABEL_WIDTH = 64 # toolbar Detect rate label 寬度
DETECT_RATE_SPIN_WIDTH = 46 # toolbar Detect rate 寬度
SOUND_FREQ_GROUP_WIDTH = 125 # toolbar Sound freq. 群組寬度
BEEP_LABEL_WIDTH = 70 # toolbar Sound freq. label 寬度
BEEP_FREQ_SPIN_WIDTH = 45 # toolbar Beep Hz 寬度，最多顯示 4 位數
MUTE_BUTTON_WIDTH = 58 # toolbar Mute 寬度
TOPMOST_CHECK_WIDTH = 78 # toolbar Topmost checkbox 寬度
STATUS_BAR_MAX_HEIGHT = 20 # 狀態列最大高度
DEFAULT_MAX_ZOOM_SCALE = 16.0 # 影片滾輪縮放最大倍率
DEFAULT_VERTICAL_SPLIT_RATIO = 0.22 # 上方板塊高度占比：1|2 / 3|4
DEFAULT_TOP_HORIZONTAL_SPLIT_RATIO = 0.83 # 上方 1|2 左側示波器占比
DEFAULT_BOTTOM_HORIZONTAL_SPLIT_RATIO = 0.83 # 下方 3|4 左側影像區占比
APP_STYLE_TEMPLATE = """
QMainWindow, QWidget {{
    background-color: {app_bg};
    color: {text};
}}
#waveformPanel, #videoPanel, #controlPanel, #rpmPanel,
#smoothPanel, #thresholdPanel, #gainPanel, #sensPanel {{
    background-color: {panel_bg};
}}
QLabel {{
    color: {text};
}}
QPushButton, QComboBox, QSpinBox {{
    background-color: {control_bg};
    color: {bright_text};
    border: 1px solid {control_border};
    border-radius: 4px;
    padding: {control_padding_y}px {control_padding_x}px;
}}
QPushButton:hover, QComboBox:hover, QSpinBox:hover {{
    background-color: {control_hover};
}}
QPushButton:pressed {{
    background-color: {control_pressed};
}}
QScrollArea {{
    background-color: {app_bg};
    border: none;
    margin: 0;
    padding: 0;
}}
QScrollBar:horizontal {{
    background-color: {toolbar_scroll_bg};
    border: none;
    height: {toolbar_scrollbar_height}px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {toolbar_scroll_handle};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {toolbar_scroll_handle_hover};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    background: none;
    border: none;
    width: 0;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background-color: {toolbar_scroll_bg};
}}
#toolbarContent {{
    background-color: transparent;
    border: none;
}}
QSplitter::handle {{
    background-color: {splitter_handle};
    height: {splitter_handle_width}px;
}}
QSlider::groove:vertical {{
    background-color: {control_bg};
    width: {slider_groove_width}px;
    border-radius: {slider_border_radius}px;
}}
QSlider {{
    background-color: {panel_bg};
}}
QSlider#cameraSettingSlider {{
    background-color: {app_bg};
}}
QSlider::handle:vertical {{
    background-color: {bright_text};
    border: 1px solid {control_border};
    width: {slider_handle_width}px;
    height: {slider_handle_height}px;
    margin: 0 -{slider_handle_margin}px;
    border-radius: {slider_border_radius}px;
}}
#smoothPanel, #thresholdPanel, #gainPanel, #sensPanel {{
    background-color: {panel_bg};
    border: 1px solid {card_border};
    border-radius: 8px;
}}
#controlPanel QLabel, #smoothPanel QLabel, #thresholdPanel QLabel,
#gainPanel QLabel, #sensPanel QLabel {{
    background-color: {panel_bg};
}}
QStatusBar {{
    background-color: {app_bg};
    color: {text};
    border-top: 1px solid {control_border};
}}
QStatusBar::item {{
    border: none;
}}
QStatusBar QLabel {{
    background-color: {app_bg};
    color: {text};
}}
QCheckBox {{
    background-color: transparent;
    color: {bright_text};
    spacing: 5px;
}}
#toolbarSpinGroup {{
    background-color: {control_bg};
    border: 1px solid {toolbar_group_border};
    border-radius: {toolbar_group_radius}px;
}}
#toolbarSpinGroup QLabel {{
    background-color: transparent;
}}
QSpinBox#toolbarInlineSpin {{
    background-color: {control_bg};
    color: {bright_text};
    border: none;
    margin-right: {toolbar_spin_margin_right}px;
    padding: 2px {toolbar_spin_value_padding_x}px;
}}
"""
APP_STYLE = APP_STYLE_TEMPLATE.format(
    app_bg=APP_BG_HEX,
    text=TEXT_HEX,
    control_bg=CONTROL_BG_HEX,
    bright_text=BRIGHT_TEXT_HEX,
    control_border=CONTROL_BORDER_HEX,
    control_hover=CONTROL_HOVER_HEX,
    control_pressed=CONTROL_PRESSED_HEX,
    control_padding_x=CONTROL_PADDING_X,
    control_padding_y=CONTROL_PADDING_Y,
    toolbar_group_border=TOOLBAR_GROUP_BORDER_HEX,
    toolbar_group_radius=TOOLBAR_GROUP_BORDER_RADIUS,
    toolbar_spin_margin_right=TOOLBAR_SPIN_MARGIN_RIGHT,
    toolbar_spin_value_padding_x=TOOLBAR_SPIN_VALUE_PADDING_X,
    toolbar_scroll_bg=TOOLBAR_SCROLL_BG_HEX,
    toolbar_scroll_handle=TOOLBAR_SCROLL_HANDLE_HEX,
    toolbar_scroll_handle_hover=TOOLBAR_SCROLL_HANDLE_HOVER_HEX,
    toolbar_scrollbar_height=TOOLBAR_SCROLLBAR_HEIGHT,
    splitter_handle=SPLITTER_HANDLE_HEX,
    splitter_handle_width=SPLITTER_HANDLE_WIDTH,
    slider_groove_width=SLIDER_GROOVE_WIDTH,
    slider_handle_width=SLIDER_HANDLE_WIDTH,
    slider_handle_height=SLIDER_HANDLE_HEIGHT,
    slider_handle_margin=max(0, (SLIDER_HANDLE_WIDTH - SLIDER_GROOVE_WIDTH) // 2),
    slider_border_radius=SLIDER_BORDER_RADIUS,
    panel_bg=PANEL_BG_HEX,
    card_border=CARD_BORDER_HEX,
)
PANEL_BG = hex_color(PANEL_BG_HEX)
WAVE_GRID_COLOR = hex_color(WAVE_GRID_HEX) # 示波器格線顏色
WAVE_LINE_COLOR = hex_color(WAVE_LINE_HEX) # 示波器波型顏色
WAVE_CURSOR_COLOR = hex_color(WAVE_CURSOR_HEX) # 示波器掃描游標顏色
WAVE_THRESHOLD_COLOR = hex_color(WAVE_THRESHOLD_HEX) # 示波器 threshold 線顏色
RPM_VALUE_COLOR = hex_color(RPM_VALUE_HEX) # RPM 數值顏色
ROI_PAUSED_COLOR = hex_color(ROI_PAUSED_HEX) # 暫停編輯時的 ROI 顏色
ROI_PLAYING_COLOR = hex_color(ROI_PLAYING_HEX) # 播放追蹤時的 ROI 顏色
ROI_PREVIEW_COLOR = hex_color(ROI_PREVIEW_HEX) # 新增 ROI 時的預覽顏色
TRACKING_LINE_COLOR = hex_color(TRACKING_LINE_HEX) # 中心位移線顏色
ICON_BUTTON_SIZE = 32 # 純圖示按鈕固定大小
BUTTON_ICON_SIZE = 20 # 按鈕內圖示大小


# 保留原生勾勾，只補強 checkbox 外框
class BorderCheckBox(QCheckBox):
    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        option = QStyleOptionButton()
        self.initStyleOption(option)
        indicator = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator,
            option,
            self,
        )
        painter = QPainter(self)
        painter.setPen(QPen(hex_color(CHECKBOX_BORDER_HEX), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(indicator.adjusted(0, 0, -1, -1))


# Setting 小視窗
class CameraSettingsDialog(QDialog):
    exposure_changed = Signal(float)
    shutter_changed = Signal(float)
    camera_auto_changed = Signal(bool)
    camera_reset_requested = Signal()
    software_control_changed = Signal(bool)
    roi_reset_requested = Signal()
    panel_reset_requested = Signal()
    adjustment_reset_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Setting")
        self.setMinimumWidth(CAMERA_SETTING_DIALOG_WIDTH)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self._build_layout()

    # 建立相機設定與 reset 控制列
    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.software_control_check = BorderCheckBox("Use Software Camera Control")
        self.software_control_check.setChecked(True)
        self.software_control_check.stateChanged.connect(self.change_software_control)
        layout.addWidget(self.software_control_check)

        camera_grid = QGridLayout()
        camera_grid.setContentsMargins(0, 0, 0, 0)
        camera_grid.setSpacing(8)
        self.camera_auto_check = BorderCheckBox("Auto")
        self.camera_auto_check.setChecked(False)
        self.camera_auto_check.setFixedWidth(CAMERA_SETTING_AUTO_WIDTH)
        self.camera_auto_check.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.camera_auto_check.stateChanged.connect(self.change_camera_auto)
        camera_grid.addWidget(self.camera_auto_check, 0, 1, 2, 1)

        self.exposure_value, self.exposure_slider = self._add_camera_row(
            camera_grid,
            0,
            "Exposure",
            CAMERA_EXPOSURE_MIN,
            CAMERA_EXPOSURE_MAX,
            CAMERA_EXPOSURE_DEFAULT,
            self.exposure_changed,
        )
        self.shutter_value, self.shutter_slider = self._add_camera_row(
            camera_grid,
            1,
            "Shutter",
            CAMERA_SHUTTER_MIN,
            CAMERA_SHUTTER_MAX,
            CAMERA_SHUTTER_DEFAULT,
            self.shutter_changed,
        )
        camera_grid.setColumnStretch(3, 1)
        layout.addLayout(camera_grid)
        self._add_reset_row(layout)
        self.set_camera_controls_enabled(True)

    # 切換是否允許 CV2 寫入 camera 設定
    def change_software_control(self, state: int) -> None:
        enabled = state == Qt.CheckState.Checked.value
        self.set_camera_controls_enabled(enabled)
        self.software_control_changed.emit(enabled)

    # 同步 controller 目前的軟體控制狀態
    def set_software_control_enabled(self, enabled: bool) -> None:
        self.software_control_check.blockSignals(True)
        self.software_control_check.setChecked(enabled)
        self.software_control_check.blockSignals(False)
        self.set_camera_controls_enabled(enabled)

    # 啟用或停用會寫入 camera 的控制項
    def set_camera_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.camera_auto_check,
            self.exposure_value,
            self.exposure_slider,
            self.shutter_value,
            self.shutter_slider,
        ):
            widget.setEnabled(enabled)

    # 同步持續 auto 狀態
    def set_camera_auto_enabled(self, enabled: bool) -> None:
        self.camera_auto_check.blockSignals(True)
        self.camera_auto_check.setChecked(enabled)
        self.camera_auto_check.blockSignals(False)

    # 切換持續 auto
    def change_camera_auto(self, state: int) -> None:
        self.camera_auto_changed.emit(state == Qt.CheckState.Checked.value)

    # 建立 reset 功能列
    def _add_reset_row(self, layout: QVBoxLayout) -> None:
        reset_label = QLabel("Reset")
        reset_label.setFixedWidth(SETTING_RESET_LABEL_WIDTH)
        roi_button = QPushButton("ROI")
        panel_button = QPushButton("Panel layout")
        adjustment_button = QPushButton("Adjustment")
        camera_button = QPushButton("Camera")
        reset_spacer = QWidget()
        roi_button.clicked.connect(self.roi_reset_requested.emit)
        panel_button.clicked.connect(self.panel_reset_requested.emit)
        adjustment_button.clicked.connect(self.adjustment_reset_requested.emit)
        camera_button.clicked.connect(self.reset_camera_controls)

        for button in (roi_button, panel_button, adjustment_button, camera_button):
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        reset_layout = QHBoxLayout()
        reset_layout.setContentsMargins(0, 0, 0, 0)
        reset_layout.setSpacing(8)
        reset_layout.addWidget(reset_label)
        reset_layout.addWidget(roi_button, SETTING_RESET_BUTTON_STRETCH)
        reset_layout.addWidget(panel_button, SETTING_RESET_BUTTON_STRETCH)
        reset_layout.addWidget(adjustment_button, SETTING_RESET_BUTTON_STRETCH)
        reset_layout.addWidget(camera_button, SETTING_RESET_BUTTON_STRETCH)
        reset_layout.addWidget(reset_spacer, SETTING_RESET_SPACER_STRETCH)
        layout.addLayout(reset_layout)

    # 將相機控制列重置回預設值，不主動寫入 camera
    def reset_camera_controls(self) -> None:
        self.set_software_control_enabled(False)
        self.set_camera_auto_enabled(False)
        self._reset_camera_row(
            self.exposure_value,
            self.exposure_slider,
            CAMERA_EXPOSURE_DEFAULT,
        )
        self._reset_camera_row(
            self.shutter_value,
            self.shutter_slider,
            CAMERA_SHUTTER_DEFAULT,
        )
        self.camera_reset_requested.emit()

    # 還原單列相機控制的數值與 slider
    def _reset_camera_row(
        self,
        value_spin: QDoubleSpinBox,
        slider: QSlider,
        value: float,
    ) -> None:
        value_spin.blockSignals(True)
        slider.blockSignals(True)
        value_spin.setValue(value)
        slider.setValue(round(value * CAMERA_SETTING_SLIDER_SCALE))
        value_spin.blockSignals(False)
        slider.blockSignals(False)

    # 從 camera 讀回數值後同步到控制列
    def set_exposure_value(self, value: float) -> None:
        self._set_camera_row_value(self.exposure_value, self.exposure_slider, value)

    # 從 camera 讀回數值後同步到控制列
    def set_shutter_value(self, value: float) -> None:
        self._set_camera_row_value(self.shutter_value, self.shutter_slider, value)

    # 更新控制列但不要再送出 camera 寫入
    def _set_camera_row_value(
        self,
        value_spin: QDoubleSpinBox,
        slider: QSlider,
        value: float,
    ) -> None:
        value = max(value_spin.minimum(), min(value, value_spin.maximum()))
        self._reset_camera_row(value_spin, slider, value)

    # 建立單列數值框和水平滑桿
    def _add_camera_row(
        self,
        layout: QGridLayout,
        row: int,
        label_text: str,
        minimum: float,
        maximum: float,
        value: float,
        changed_signal: Signal,
    ) -> tuple[QDoubleSpinBox, QSlider]:
        label = QLabel(label_text)
        label.setFixedWidth(CAMERA_SETTING_LABEL_WIDTH)

        value_spin = QDoubleSpinBox()
        value_spin.setRange(minimum, maximum)
        value_spin.setDecimals(2)
        value_spin.setSingleStep(1.0)
        value_spin.setValue(value)
        value_spin.setFixedWidth(CAMERA_SETTING_VALUE_WIDTH)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("cameraSettingSlider")
        slider.setRange(
            round(minimum * CAMERA_SETTING_SLIDER_SCALE),
            round(maximum * CAMERA_SETTING_SLIDER_SCALE),
        )
        slider.setValue(round(value * CAMERA_SETTING_SLIDER_SCALE))
        slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        def emit_value() -> None:
            changed_signal.emit(value_spin.value())

        def update_spin(slider_value: int) -> None:
            value_spin.blockSignals(True)
            value_spin.setValue(slider_value / CAMERA_SETTING_SLIDER_SCALE)
            value_spin.blockSignals(False)
            emit_value()

        def update_slider(spin_value: float) -> None:
            slider.blockSignals(True)
            slider.setValue(round(spin_value * CAMERA_SETTING_SLIDER_SCALE))
            slider.blockSignals(False)
            emit_value()

        slider.valueChanged.connect(update_spin)
        value_spin.valueChanged.connect(update_slider)

        layout.addWidget(label, row, 0)
        layout.addWidget(value_spin, row, 2)
        layout.addWidget(slider, row, 3)
        return value_spin, slider


# 影片顯示與 ROI 編輯區
class VideoWidget(QWidget):
    roi_selected = Signal(int, int, int, int)
    edit_rejected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image: QImage | None = None
        self.frame_size: tuple[int, int] | None = None
        self.image_rect = QRect()
        self.roi: tuple[int, int, int, int] | None = None
        self.reference_center: tuple[float, float] | None = None
        self.current_center: tuple[float, float] | None = None
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.middle_drag_start: tuple[float, float] | None = None
        self.middle_drag_pan: tuple[float, float] | None = None
        self.editing_enabled = False
        self.drag_start: tuple[int, int] | None = None
        self.drag_current: tuple[int, int] | None = None
        self.drag_action: str | None = None
        self.drag_handle: str | None = None
        self.original_roi: tuple[int, int, int, int] | None = None
        self.status_text = "No source|Enhance: None|FPS: 0|Motion: 0.00"
        self.max_zoom_scale = DEFAULT_MAX_ZOOM_SCALE

    # 更新目前顯示的影像
    def set_frame(self, image: QImage, frame_size: tuple[int, int]) -> None:
        self.image = image
        self.frame_size = frame_size
        self.update()

    # 一次更新影像與 overlay，避免同一幀觸發多次重畫
    def set_frame_state(
        self,
        image: QImage,
        frame_size: tuple[int, int],
        roi: tuple[int, int, int, int] | None,
        reference_center: tuple[float, float] | None,
        current_center: tuple[float, float] | None,
        status_text: str,
    ) -> None:
        self.image = image
        self.frame_size = frame_size
        self.roi = roi
        self.reference_center = reference_center
        self.current_center = current_center
        self.status_text = status_text
        self.update()

    # 清除目前顯示的影像
    def clear_frame(self) -> None:
        self.image = None
        self.frame_size = None
        self.image_rect = QRect()
        self.fit_to_window()

    # 將影像縮放和平移還原成符合視窗
    def fit_to_window(self) -> None:
        self.zoom_scale = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

    # 更新滾輪縮放最大倍率
    def set_max_zoom_scale(self, value: float) -> None:
        self.max_zoom_scale = max(1.0, value)
        self.zoom_scale = max(1 / self.max_zoom_scale, min(self.zoom_scale, self.max_zoom_scale))
        self.update()

    # 更新 ROI 顯示
    def set_roi(self, roi: tuple[int, int, int, int] | None) -> None:
        if self.roi == roi:
            return
        self.roi = roi
        self.update()

    # 更新參考中心和目前追蹤中心
    def set_tracking_centers(
        self,
        reference_center: tuple[float, float] | None,
        current_center: tuple[float, float] | None,
    ) -> None:
        if self.reference_center == reference_center and self.current_center == current_center:
            return
        self.reference_center = reference_center
        self.current_center = current_center
        self.update()

    # 更新狀態文字
    def set_status(self, text: str) -> None:
        if self.status_text == text:
            return
        self.status_text = text
        self.update()

    # 啟用或停用 ROI 編輯
    def set_roi_editing(self, enabled: bool) -> None:
        self.editing_enabled = enabled
        if not enabled:
            self.drag_start = None
            self.drag_current = None
        self.update()

    # 繪製影片和 ROI
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL_BG)

        if self.image is None or self.frame_size is None:
            return

        self.image_rect = self._fit_rect(self.image.width(), self.image.height())
        painter.drawImage(self.image_rect, self.image)

        painter.setPen(QPen(QColor("white"), 2))
        painter.drawText(16, 28, self.status_text)

        if self.roi is not None:
            roi_color = ROI_PAUSED_COLOR if self.editing_enabled else ROI_PLAYING_COLOR
            self._draw_roi(painter, self.roi, roi_color)
            if self.editing_enabled:
                self._draw_roi_handles(painter, self.roi)

        if self.drag_start is not None and self.drag_current is not None:
            preview_roi = self._points_to_roi(self.drag_start, self.drag_current)
            if preview_roi is not None:
                self._draw_roi(painter, preview_roi, ROI_PREVIEW_COLOR)

        self._draw_tracking_line(painter)

    # 滑鼠按下開始畫 ROI
    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            if event.button() == Qt.MouseButton.MiddleButton:
                self.middle_drag_start = (event.position().x(), event.position().y())
                self.middle_drag_pan = (self.pan_x, self.pan_y)
                return
            return
        if not self.editing_enabled:
            self.edit_rejected.emit("Pause the video before drawing an ROI.")
            return

        point = self._widget_to_frame(event.position().x(), event.position().y())
        if point is None:
            return

        if self.roi is not None:
            handle = self._hit_handle(event.position().x(), event.position().y())
            if handle is None:
                return
            self.drag_action = "transform"
            self.drag_handle = handle
            self.drag_start = point
            self.original_roi = self.roi
            self.update()
            return

        self.drag_action = "draw"
        self.drag_start = point
        self.drag_current = point
        self.update()

    # 拖曳 ROI 過程
    def mouseMoveEvent(self, event) -> None:
        if self.drag_start is None:
            if self.middle_drag_start is not None and self.middle_drag_pan is not None:
                delta_x = event.position().x() - self.middle_drag_start[0]
                delta_y = event.position().y() - self.middle_drag_start[1]
                self.pan_x = self.middle_drag_pan[0] + delta_x
                self.pan_y = self.middle_drag_pan[1] + delta_y
                self.update()
            return
        point = self._widget_to_frame(event.position().x(), event.position().y())
        if point is None:
            return
        if self.drag_action == "transform":
            self.roi = self._transform_roi(point)
        else:
            self.drag_current = point
        self.update()

    # 滑鼠放開完成 ROI
    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self.drag_start is None:
            if event.button() == Qt.MouseButton.MiddleButton:
                self.middle_drag_start = None
                self.middle_drag_pan = None
                return
            return

        point = self._widget_to_frame(event.position().x(), event.position().y())
        if self.drag_action == "transform":
            roi = self._transform_roi(point) if point is not None else self.roi
        else:
            roi = self._points_to_roi(self.drag_start, point) if point is not None else None

        self.drag_start = None
        self.drag_current = None
        self.drag_action = None
        self.drag_handle = None
        self.original_roi = None

        if roi is None:
            self.edit_rejected.emit("ROI is too small. Pause and drag a larger area.")
            self.update()
            return

        self.roi_selected.emit(*roi)
        self.update()

    # 滾輪縮放影像顯示
    def wheelEvent(self, event) -> None:
        if self.image is None:
            return

        anchor = self._widget_to_frame(event.position().x(), event.position().y())
        if anchor is None:
            return

        old_scale = self.zoom_scale
        if event.angleDelta().y() > 0:
            self.zoom_scale = min(self.zoom_scale * 1.1, self.max_zoom_scale)
        else:
            self.zoom_scale = max(self.zoom_scale / 1.1, 1 / self.max_zoom_scale)

        if self.zoom_scale == old_scale:
            return

        cursor_x = event.position().x()
        cursor_y = event.position().y()
        self._anchor_zoom_to_point(anchor, cursor_x, cursor_y)
        self.update()

    # 調整 pan，讓縮放後滑鼠下的影像點維持不動
    def _anchor_zoom_to_point(
        self,
        frame_point: tuple[int, int],
        cursor_x: float,
        cursor_y: float,
    ) -> None:
        if self.frame_size is None:
            return

        frame_width, frame_height = self.frame_size
        widget_width = max(1, self.width())
        widget_height = max(1, self.height())
        base_scale = min(widget_width / frame_width, widget_height / frame_height)
        draw_width = max(1, int(frame_width * base_scale * self.zoom_scale))
        draw_height = max(1, int(frame_height * base_scale * self.zoom_scale))
        base_left = (widget_width - draw_width) // 2
        base_top = (widget_height - draw_height) // 2
        self.pan_x = (
            cursor_x
            - base_left
            - frame_point[0] * draw_width / frame_width
        )
        self.pan_y = (
            cursor_y
            - base_top
            - frame_point[1] * draw_height / frame_height
        )

    # 讓影像依視窗大小等比例縮放
    def _fit_rect(self, image_width: int, image_height: int) -> QRect:
        widget_width = max(1, self.width())
        widget_height = max(1, self.height())
        scale = min(widget_width / image_width, widget_height / image_height)
        draw_width = max(1, int(image_width * scale * self.zoom_scale))
        draw_height = max(1, int(image_height * scale * self.zoom_scale))
        base_left = (widget_width - draw_width) // 2
        base_top = (widget_height - draw_height) // 2
        left = int(base_left + self.pan_x)
        top = int(base_top + self.pan_y)
        return QRect(left, top, draw_width, draw_height)

    # 將 widget 座標轉成原始影像座標
    def _widget_to_frame(self, x: float, y: float) -> tuple[int, int] | None:
        if self.frame_size is None or self.image_rect.isNull():
            return None
        if not self.image_rect.contains(int(x), int(y)):
            return None

        frame_width, frame_height = self.frame_size
        frame_x = int((x - self.image_rect.left()) * frame_width / self.image_rect.width())
        frame_y = int((y - self.image_rect.top()) * frame_height / self.image_rect.height())
        frame_x = max(0, min(frame_x, frame_width - 1))
        frame_y = max(0, min(frame_y, frame_height - 1))
        return frame_x, frame_y

    # 將兩點轉成 ROI tuple
    def _points_to_roi(
        self,
        start: tuple[int, int],
        end: tuple[int, int] | None,
    ) -> tuple[int, int, int, int] | None:
        if end is None:
            return None

        x1, y1 = start
        x2, y2 = end
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        return left, top, right - left, bottom - top

    # 依照拖曳中的 handle 移動或縮放 ROI
    def _transform_roi(self, current: tuple[int, int] | None) -> tuple[int, int, int, int] | None:
        if (
            current is None
            or self.original_roi is None
            or self.drag_start is None
            or self.drag_handle is None
        ):
            return self.roi

        x, y, width, height = self.original_roi
        left = x
        top = y
        right = x + width
        bottom = y + height

        if self.drag_handle == "move":
            delta_x = current[0] - self.drag_start[0]
            delta_y = current[1] - self.drag_start[1]
            return self._clamp_roi(
                left + delta_x,
                top + delta_y,
                right + delta_x,
                bottom + delta_y,
            )

        if "w" in self.drag_handle:
            left = current[0]
        if "e" in self.drag_handle:
            right = current[0]
        if "n" in self.drag_handle:
            top = current[1]
        if "s" in self.drag_handle:
            bottom = current[1]

        return self._clamp_roi(left, top, right, bottom)

    # 將 ROI 限制在影像範圍內
    def _clamp_roi(
        self,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> tuple[int, int, int, int] | None:
        if self.frame_size is None:
            return None

        frame_width, frame_height = self.frame_size
        left, right = sorted((left, right))
        top, bottom = sorted((top, bottom))
        left = max(0, min(left, frame_width - 1))
        right = max(0, min(right, frame_width))
        top = max(0, min(top, frame_height - 1))
        bottom = max(0, min(bottom, frame_height))
        return left, top, right - left, bottom - top

    # 在影片上畫 ROI
    def _draw_roi(
        self,
        painter: QPainter,
        roi: tuple[int, int, int, int],
        color: QColor,
    ) -> None:
        if self.frame_size is None:
            return

        frame_width, frame_height = self.frame_size
        x, y, width, height = roi
        x_scale = self.image_rect.width() / frame_width
        y_scale = self.image_rect.height() / frame_height
        left = int(self.image_rect.left() + x * x_scale)
        top = int(self.image_rect.top() + y * y_scale)
        draw_width = int(width * x_scale)
        draw_height = int(height * y_scale)

        painter.setPen(QPen(color, ROI_LINE_WIDTH))
        painter.drawRect(left, top, draw_width, draw_height)

    # 畫出 ROI 的 9 點調整點
    def _draw_roi_handles(self, painter: QPainter, roi: tuple[int, int, int, int]) -> None:
        for name, (x, y) in self._handle_positions(roi).items():
            size = ROI_CENTER_SIZE if name == "move" else ROI_HANDLE_SIZE
            half = size / 2
            fill = ROI_PAUSED_COLOR if name == "move" else QColor("white")
            painter.setPen(QPen(QColor("black"), ROI_HANDLE_LINE_WIDTH))
            painter.setBrush(fill)
            painter.drawRect(int(x - half), int(y - half), size, size)

    # 取得 ROI 調整點的畫面座標
    def _handle_positions(self, roi: tuple[int, int, int, int]) -> dict[str, tuple[float, float]]:
        canvas_box = self._roi_to_canvas_box(roi)
        if canvas_box is None:
            return {}

        left, top, right, bottom = canvas_box
        center_x = (left + right) / 2
        center_y = (top + bottom) / 2
        return {
            "nw": (left, top),
            "n": (center_x, top),
            "ne": (right, top),
            "e": (right, center_y),
            "se": (right, bottom),
            "s": (center_x, bottom),
            "sw": (left, bottom),
            "w": (left, center_y),
            "move": (center_x, center_y),
        }

    # 判斷滑鼠是否壓在 ROI 調整點上
    def _hit_handle(self, x: float, y: float) -> str | None:
        if self.roi is None:
            return None

        for name, (handle_x, handle_y) in self._handle_positions(self.roi).items():
            hit_size = ROI_CENTER_SIZE if name == "move" else ROI_HANDLE_SIZE
            if abs(x - handle_x) <= hit_size and abs(y - handle_y) <= hit_size:
                return name
        return None

    # 取得 ROI 的畫面座標
    def _roi_to_canvas_box(
        self,
        roi: tuple[int, int, int, int],
    ) -> tuple[float, float, float, float] | None:
        if self.frame_size is None:
            return None

        frame_width, frame_height = self.frame_size
        x, y, width, height = roi
        x_scale = self.image_rect.width() / frame_width
        y_scale = self.image_rect.height() / frame_height
        left = self.image_rect.left() + x * x_scale
        top = self.image_rect.top() + y * y_scale
        right = self.image_rect.left() + (x + width) * x_scale
        bottom = self.image_rect.top() + (y + height) * y_scale
        return left, top, right, bottom

    # 畫出初始中心到目前中心的位移線
    def _draw_tracking_line(self, painter: QPainter) -> None:
        if self.editing_enabled or self.reference_center is None or self.current_center is None:
            return

        start = self._frame_point_to_canvas(self.reference_center)
        end = self._frame_point_to_canvas(self.current_center)
        if start is None or end is None:
            return

        pen = QPen(TRACKING_LINE_COLOR, TRACKING_LINE_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(int(start[0]), int(start[1]), int(end[0]), int(end[1]))

    # 將影像座標點轉成畫面座標
    def _frame_point_to_canvas(self, point: tuple[float, float]) -> tuple[float, float] | None:
        if self.frame_size is None:
            return None

        frame_width, frame_height = self.frame_size
        x_scale = self.image_rect.width() / frame_width
        y_scale = self.image_rect.height() / frame_height
        return (
            self.image_rect.left() + point[0] * x_scale,
            self.image_rect.top() + point[1] * y_scale,
        )


# 波型顯示區
class WaveformWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.values: list[float | None] = []
        self.cursor_index = 0
        self.threshold_percent = 50
        self.max_value = 100.0

    # 更新波型資料
    def set_values(self, values: list[float | None], cursor_index: int = 0) -> None:
        self.values = values
        self.cursor_index = cursor_index
        self.update()

    # 更新 threshold 顯示線
    def set_threshold_percent(self, threshold_percent: int) -> None:
        threshold_percent = max(0, min(threshold_percent, 100))
        if self.threshold_percent == threshold_percent:
            return
        self.threshold_percent = threshold_percent
        self.update()

    # 更新示波器最大位移值
    def set_max_value(self, max_value: float) -> None:
        max_value = max(0.0, max_value)
        if self.max_value == max_value:
            return
        self.max_value = max_value
        self.update()

    # 繪製波型
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL_BG)

        title_visible = self.height() >= WAVE_TITLE_MIN_VISIBLE_HEIGHT
        graph_left = WAVE_GRAPH_MARGIN_X
        graph_right_padding = WAVE_GRAPH_MARGIN_X + WAVE_Y_AXIS_LABEL_WIDTH
        graph_bottom_padding = (
            WAVE_GRAPH_MARGIN_BOTTOM
            + (WAVE_TITLE_HEIGHT if title_visible else 0)
        )
        graph = QRect(
            graph_left,
            WAVE_GRAPH_MARGIN_TOP,
            max(1, self.width() - graph_left - graph_right_padding),
            max(1, self.height() - WAVE_GRAPH_MARGIN_TOP - graph_bottom_padding),
        )
        self._draw_y_axis_labels(painter, graph)
        painter.setPen(QPen(WAVE_GRID_COLOR, 1))
        painter.drawRect(graph)

        valid_count = 0
        for value in self.values:
            if value is not None:
                valid_count += 1
                if valid_count >= 2:
                    break
        if valid_count < 2:
            painter.drawLine(graph.left(), graph.bottom(), graph.right(), graph.bottom())
            self._draw_threshold(painter, graph)
            self._draw_cursor(painter, graph)
            self._draw_title(painter, title_visible)
            return

        span = max(0.01, self.max_value)
        self._draw_threshold(painter, graph)

        painter.setPen(QPen(WAVE_LINE_COLOR, 2))
        previous = None
        for index, value in enumerate(self.values):
            if value is None:
                previous = None
                continue

            x_ratio = index / max(1, len(self.values) - 1)
            y_ratio = max(0.0, min(value / span, 1.0))
            x = graph.left() + x_ratio * graph.width()
            y = graph.bottom() - y_ratio * graph.height()
            current = (int(x), int(y))
            if previous is not None and index != self.cursor_index:
                painter.drawLine(previous[0], previous[1], current[0], current[1])
            previous = current

        self._draw_cursor(painter, graph)
        self._draw_title(painter, title_visible)

    # 標題放在下方，高度不足時先犧牲
    def _draw_title(self, painter: QPainter, visible: bool) -> None:
        if not visible:
            return

        font = painter.font()
        font.setPointSize(PANEL_TITLE_FONT_SIZE)
        painter.setFont(font)
        painter.setPen(QPen(QColor("white"), 2))
        title_y = max(WAVE_GRAPH_MARGIN_TOP, self.height() - WAVE_GRAPH_MARGIN_BOTTOM)
        painter.drawText(WAVE_GRAPH_MARGIN_X, title_y, "ROI motion waveform")

    # 畫出 threshold 水平線
    def _draw_threshold(self, painter: QPainter, graph: QRect) -> None:
        y_ratio = self.threshold_percent / 100
        y = int(graph.bottom() - y_ratio * graph.height())
        y = max(graph.top(), min(y, graph.bottom()))
        painter.setPen(QPen(WAVE_THRESHOLD_COLOR, WAVE_THRESHOLD_LINE_WIDTH))
        painter.drawLine(graph.left(), y, graph.right(), y)

    # 畫出示波器 Y 軸裝飾 label
    def _draw_y_axis_labels(self, painter: QPainter, graph: QRect) -> None:
        painter.setPen(QPen(WAVE_GRID_COLOR, 1))
        font = painter.font()
        font.setPointSize(WAVE_Y_AXIS_LABEL_FONT_SIZE)
        painter.setFont(font)
        half_value = self.max_value / 2
        labels = [
            (f"{self.max_value:.2f}", graph.top() + 4),
            (f"{half_value:.2f}", graph.center().y() + 4),
            ("0", graph.bottom()),
        ]
        label_x = graph.right() + 4
        for text, y in labels:
            painter.drawText(label_x, int(y), text)

    # 畫出 ECG sweep 游標
    def _draw_cursor(self, painter: QPainter, graph: QRect) -> None:
        if not self.values:
            return

        cursor = max(0, min(self.cursor_index, len(self.values) - 1))
        x_ratio = cursor / max(1, len(self.values) - 1)
        x = int(graph.left() + x_ratio * graph.width())
        painter.setPen(QPen(WAVE_CURSOR_COLOR, 2))
        painter.drawLine(x, graph.top(), x, graph.bottom())


# RPM 顯示區
class RpmWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(0)
        self.setMinimumWidth(0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self.rpm: float | None = None

    # 更新 RPM 顯示
    def set_rpm(self, rpm: float | None) -> None:
        if self.rpm == rpm:
            return
        self.rpm = rpm
        self.update()

    # 繪製 RPM 卡片與標題
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL_BG)

        title_visible = self.height() >= WAVE_TITLE_MIN_VISIBLE_HEIGHT
        content_rect = QRect(
            WAVE_GRAPH_MARGIN_X,
            WAVE_GRAPH_MARGIN_TOP,
            max(1, self.width() - (2 * WAVE_GRAPH_MARGIN_X)),
            max(
                1,
                self.height()
                - WAVE_GRAPH_MARGIN_TOP
                - WAVE_GRAPH_MARGIN_BOTTOM
                - (WAVE_TITLE_HEIGHT if title_visible else 0),
            ),
        )

        painter.setPen(QPen(QColor(CARD_BORDER_HEX), 1))
        painter.drawRoundedRect(content_rect, 8, 8)

        value = "--" if self.rpm is None else f"{self.rpm:.0f}"

        value_font = painter.font()
        value_font.setPointSize(RPM_VALUE_FONT_SIZE)
        value_font.setBold(True)
        painter.setFont(value_font)
        painter.setPen(QPen(RPM_VALUE_COLOR, 1))
        painter.drawText(content_rect, Qt.AlignmentFlag.AlignCenter, value)

        self._draw_title(painter, title_visible)

    # 標題放在下方，高度不足時先犧牲
    def _draw_title(self, painter: QPainter, visible: bool) -> None:
        if not visible:
            return

        font = painter.font()
        font.setPointSize(RESPIRATION_FONT_SIZE)
        painter.setFont(font)
        painter.setPen(QPen(QColor("white"), 2))
        title_y = max(WAVE_GRAPH_MARGIN_TOP, self.height() - WAVE_GRAPH_MARGIN_BOTTOM)
        painter.drawText(WAVE_GRAPH_MARGIN_X, title_y, RESPIRATION_TEXT)


# 主視窗 layout
class MonitorWindow(QMainWindow):
    def __init__(self, camera_indexes: tuple[int, ...], app_title: str) -> None:
        super().__init__()
        self.setWindowTitle(app_title)
        self.setWindowIcon(QIcon(str(ASSET_DIR / "logo.svg")))
        self.setStyleSheet(APP_STYLE)
        self.resize(*DEFAULT_APP_SIZE)
        self.camera_settings_dialog: CameraSettingsDialog | None = None
        set_windows_title_bar_color(self)
        self._build_layout(camera_indexes)

    # 建立 GUI 版面
    def _build_layout(self, camera_indexes: tuple[int, ...]) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(
            APP_CONTENT_MARGIN_X,
            APP_CONTENT_MARGIN_Y,
            APP_CONTENT_MARGIN_X,
            APP_CONTENT_MARGIN_Y,
        )
        layout.setSpacing(APP_CONTENT_SPACING)

        self.toolbar_content = QFrame()
        self.toolbar_content.setObjectName("toolbarContent")
        self.toolbar_content.setFrameShape(QFrame.Shape.NoFrame)
        self.toolbar_content.setLineWidth(0)
        self.toolbar_content.setMidLineWidth(0)
        self.toolbar_content.setContentsMargins(0, 0, 0, 0)
        self.toolbar_content.setFixedWidth(TOOLBAR_GROUP_WIDTH)
        self.toolbar_content.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        toolbar = QHBoxLayout(self.toolbar_content)
        toolbar.setContentsMargins(0, 0, 0, TOOLBAR_SCROLL_BOTTOM_RESERVED_HEIGHT)
        toolbar.setSpacing(TOOLBAR_ITEM_SPACING)
        self.load_mode_menu = QComboBox()
        self.load_mode_menu.addItems(["Camera", "Video"])
        self.open_video_button = QPushButton("Open Video")
        self.open_video_button.setIcon(QIcon(str(ASSET_DIR / "file.svg")))
        self.open_video_button.setIconSize(QSize(BUTTON_ICON_SIZE, BUTTON_ICON_SIZE))
        self.open_video_button.setText("")
        self.open_video_button.setToolTip("Open Video")
        self.camera_menu = QComboBox()
        for index in camera_indexes:
            self.camera_menu.addItem(f"Cam {index}", str(index))
        self.scan_camera_button = QPushButton("Scan Cameras")
        self.scan_camera_button.setIcon(QIcon(str(ASSET_DIR / "scancam.svg")))
        self.scan_camera_button.setIconSize(QSize(BUTTON_ICON_SIZE, BUTTON_ICON_SIZE))
        self.scan_camera_button.setText("")
        self.scan_camera_button.setToolTip("Scan Cameras")
        self.enhancement_menu = QComboBox()
        self.enhancement_menu.addItem("Enhance: None", "None")
        for mode in [
            "Gray Blur",
            "CLAHE Gray",
            "Sobel Edge",
            "Laplacian Edge",
            "Motion Edge",
        ]:
            self.enhancement_menu.addItem(mode, mode)
        self.show_raw_check = BorderCheckBox("Show RAW")
        self.show_raw_check.setChecked(False)
        self.play_button = QPushButton("Play")
        self.play_icon = QIcon(str(ASSET_DIR / "play.svg"))
        self.pause_icon = QIcon(str(ASSET_DIR / "pause.svg"))
        self.play_button.setIcon(self.play_icon)
        self.play_button.setIconSize(QSize(BUTTON_ICON_SIZE, BUTTON_ICON_SIZE))
        self.play_button.setText("")
        self.play_button.setToolTip("Play")
        self.camera_settings_button = QPushButton("Setting")
        self.camera_settings_button.setIcon(QIcon(str(ASSET_DIR / "setting.svg")))
        self.camera_settings_button.setIconSize(QSize(BUTTON_ICON_SIZE, BUTTON_ICON_SIZE))
        self.camera_settings_button.setText("")
        self.camera_settings_button.setToolTip("Setting")
        self.detect_rate_label = QLabel("Detect rate")
        self.detect_rate_spin = QSpinBox()
        self.detect_rate_spin.setRange(1, 999)
        self.detect_rate_spin.setSingleStep(1)
        self.detect_rate_spin.setValue(60)
        self.detect_rate_spin.setObjectName("toolbarInlineSpin")
        self.detect_rate_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.detect_rate_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.beep_label = QLabel("Sound freq.")
        self.beep_frequency_spin = QSpinBox()
        self.beep_frequency_spin.setRange(100, 4000)
        self.beep_frequency_spin.setSingleStep(1)
        self.beep_frequency_spin.setValue(479)
        self.beep_frequency_spin.setObjectName("toolbarInlineSpin")
        self.beep_frequency_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beep_frequency_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.mute_button = BorderCheckBox("Mute")
        self.mute_button.setChecked(False)
        self.topmost_check = BorderCheckBox("Topmost")
        self.topmost_check.setChecked(True)

        self.load_mode_menu.setMinimumWidth(LOAD_MODE_MENU_WIDTH)
        self.load_mode_menu.setFixedHeight(CONTROL_WIDGET_HEIGHT)
        self.load_mode_menu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.open_video_button.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.camera_menu.setMinimumWidth(CAMERA_MENU_WIDTH)
        self.camera_menu.setFixedHeight(CONTROL_WIDGET_HEIGHT)
        self.camera_menu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.scan_camera_button.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.enhancement_menu.setMinimumWidth(ENHANCEMENT_MENU_WIDTH)
        self.enhancement_menu.setFixedHeight(CONTROL_WIDGET_HEIGHT)
        self.enhancement_menu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.show_raw_check.setMinimumWidth(SHOW_RAW_CHECK_WIDTH)
        self.show_raw_check.setFixedHeight(CONTROL_WIDGET_HEIGHT)
        self.play_button.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.camera_settings_button.setFixedSize(ICON_BUTTON_SIZE, ICON_BUTTON_SIZE)
        self.detect_rate_label.setFixedWidth(DETECT_RATE_LABEL_WIDTH)
        self.detect_rate_label.setFixedHeight(TOOLBAR_GROUP_SPIN_HEIGHT)
        self.detect_rate_spin.setMinimumWidth(DETECT_RATE_SPIN_WIDTH)
        self.detect_rate_spin.setFixedHeight(TOOLBAR_GROUP_SPIN_HEIGHT)
        self.detect_rate_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.beep_label.setFixedWidth(BEEP_LABEL_WIDTH)
        self.beep_label.setFixedHeight(TOOLBAR_GROUP_SPIN_HEIGHT)
        self.beep_frequency_spin.setMinimumWidth(BEEP_FREQ_SPIN_WIDTH)
        self.beep_frequency_spin.setFixedHeight(TOOLBAR_GROUP_SPIN_HEIGHT)
        self.beep_frequency_spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.mute_button.setMinimumWidth(MUTE_BUTTON_WIDTH)
        self.mute_button.setFixedHeight(CONTROL_WIDGET_HEIGHT)
        self.topmost_check.setMinimumWidth(TOPMOST_CHECK_WIDTH)
        self.topmost_check.setFixedHeight(CONTROL_WIDGET_HEIGHT)

        # toolbar 小群組：群組內零間距，群組之間使用 toolbar 固定間距
        def make_toolbar_pair(label: QLabel, widget: QWidget, width: int) -> QFrame:
            pair = QFrame()
            pair.setObjectName("toolbarSpinGroup")
            pair.setFrameShape(QFrame.Shape.NoFrame)
            pair.setContentsMargins(0, 0, 0, 0)
            pair.setFixedHeight(CONTROL_WIDGET_HEIGHT)
            pair.setMinimumWidth(width)
            pair.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            pair_layout = QHBoxLayout(pair)
            pair_layout.setContentsMargins(
                TOOLBAR_GROUP_PADDING_X,
                TOOLBAR_GROUP_PADDING_Y,
                TOOLBAR_GROUP_PADDING_X,
                TOOLBAR_GROUP_PADDING_Y,
            )
            pair_layout.setSpacing(TOOLBAR_GROUP_SPACING)
            pair_layout.addWidget(label)
            pair_layout.addWidget(widget, 1)
            return pair

        self.detect_rate_group = make_toolbar_pair(
            self.detect_rate_label,
            self.detect_rate_spin,
            DETECT_RATE_GROUP_WIDTH,
        )
        self.beep_group = make_toolbar_pair(
            self.beep_label,
            self.beep_frequency_spin,
            SOUND_FREQ_GROUP_WIDTH,
        )

        toolbar.addWidget(self.load_mode_menu, TOOLBAR_MENU_STRETCH)
        toolbar.addWidget(self.camera_menu, TOOLBAR_MENU_STRETCH)
        toolbar.addWidget(self.open_video_button)
        toolbar.addWidget(self.scan_camera_button)
        toolbar.addWidget(self.play_button)
        toolbar.addWidget(self.camera_settings_button)
        toolbar.addWidget(self.enhancement_menu, TOOLBAR_ENHANCE_STRETCH)
        toolbar.addWidget(self.show_raw_check)
        toolbar.addWidget(self.detect_rate_group, TOOLBAR_SPIN_GROUP_STRETCH)
        toolbar.addWidget(self.beep_group, TOOLBAR_SPIN_GROUP_STRETCH)
        toolbar.addWidget(self.mute_button)
        toolbar.addWidget(self.topmost_check)

        self.toolbar_content.adjustSize()
        self.toolbar_content.setFixedHeight(self.toolbar_content.sizeHint().height())

        self.toolbar_scroll = QScrollArea()
        self.toolbar_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.toolbar_scroll.setLineWidth(0)
        self.toolbar_scroll.setMidLineWidth(0)
        self.toolbar_scroll.setContentsMargins(0, 0, 0, 0)
        self.toolbar_scroll.setViewportMargins(0, 0, 0, 0)
        self.toolbar_scroll.setWidget(self.toolbar_content)
        self.toolbar_scroll.setWidgetResizable(False)
        self.toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.toolbar_scroll.setMinimumWidth(0)
        self.toolbar_scroll.setFixedHeight(self.toolbar_content.height() + TOOLBAR_SCROLLBAR_HEIGHT)
        self.toolbar_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.waveform = WaveformWidget()
        self.waveform.setObjectName("waveformPanel")
        self.rpm_panel = RpmWidget()
        self.rpm_panel.setObjectName("rpmPanel")

        self.control_panel = QWidget()
        self.control_panel.setObjectName("controlPanel")
        self.control_panel.setMinimumWidth(0)
        self.control_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        control_layout = QGridLayout(self.control_panel)
        control_layout.setContentsMargins(8, PANEL_PADDING_Y, 8, PANEL_PADDING_Y)
        control_layout.setSpacing(8)
        self.smooth_panel = QFrame()
        self.smooth_panel.setObjectName("smoothPanel")
        self.smooth_panel.setMinimumWidth(0)
        self.smooth_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        smooth_layout = QVBoxLayout(self.smooth_panel)
        smooth_layout.setContentsMargins(
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
        )
        smooth_layout.setSpacing(8)
        self.smooth_title_label = QLabel(SMOOTH_TEXT)
        self.smooth_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.smooth_title_label.setMinimumHeight(THRESHOLD_LABEL_MIN_HEIGHT)
        self.smooth_title_label.setMinimumWidth(0)
        self.smooth_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.smooth_slider = QSlider(Qt.Orientation.Vertical)
        self.smooth_slider.setObjectName("smoothSlider")
        self.smooth_slider.setInvertedAppearance(False)
        self.smooth_slider.setMinimumWidth(0)
        self.smooth_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        smooth_layout.addWidget(self.smooth_title_label)
        smooth_layout.addWidget(self.smooth_slider, 1)
        control_layout.addWidget(self.smooth_panel, 1, 0)
        self.threshold_panel = QFrame()
        self.threshold_panel.setObjectName("thresholdPanel")
        self.threshold_panel.setMinimumWidth(0)
        self.threshold_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        threshold_layout = QVBoxLayout(self.threshold_panel)
        threshold_layout.setContentsMargins(
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
        )
        threshold_layout.setSpacing(8)
        self.threshold_title_label = QLabel(THRESHOLD_TEXT)
        self.threshold_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_title_label.setMinimumHeight(THRESHOLD_LABEL_MIN_HEIGHT)
        self.threshold_title_label.setMinimumWidth(0)
        self.threshold_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.threshold_slider = QSlider(Qt.Orientation.Vertical)
        self.threshold_slider.setObjectName("thresholdSlider")
        self.threshold_slider.setInvertedAppearance(False)
        self.threshold_slider.setMinimumWidth(0)
        self.threshold_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        threshold_layout.addWidget(self.threshold_title_label)
        threshold_layout.addWidget(self.threshold_slider, 1)
        control_layout.addWidget(self.threshold_panel, 0, 1)
        self.gain_panel = QFrame()
        self.gain_panel.setObjectName("gainPanel")
        self.gain_panel.setMinimumWidth(0)
        self.gain_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        gain_layout = QVBoxLayout(self.gain_panel)
        gain_layout.setContentsMargins(
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
        )
        gain_layout.setSpacing(8)
        self.gain_title_label = QLabel(GAIN_TEXT)
        self.gain_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.gain_title_label.setMinimumHeight(THRESHOLD_LABEL_MIN_HEIGHT)
        self.gain_title_label.setMinimumWidth(0)
        self.gain_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.gain_slider = QSlider(Qt.Orientation.Vertical)
        self.gain_slider.setObjectName("gainSlider")
        self.gain_slider.setInvertedAppearance(False)
        self.gain_slider.setMinimumWidth(0)
        self.gain_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        gain_layout.addWidget(self.gain_title_label)
        gain_layout.addWidget(self.gain_slider, 1)
        control_layout.addWidget(self.gain_panel, 0, 0)
        self.sens_panel = QFrame()
        self.sens_panel.setObjectName("sensPanel")
        self.sens_panel.setMinimumWidth(0)
        self.sens_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sens_layout = QVBoxLayout(self.sens_panel)
        sens_layout.setContentsMargins(
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
            THRESHOLD_PANEL_MARGIN_X,
            THRESHOLD_PANEL_MARGIN_Y,
        )
        sens_layout.setSpacing(8)
        self.sens_title_label = QLabel(SENS_TEXT)
        self.sens_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sens_title_label.setMinimumHeight(THRESHOLD_LABEL_MIN_HEIGHT)
        self.sens_title_label.setMinimumWidth(0)
        self.sens_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.sens_slider = QSlider(Qt.Orientation.Vertical)
        self.sens_slider.setObjectName("sensSlider")
        self.sens_slider.setInvertedAppearance(False)
        self.sens_slider.setMinimumWidth(0)
        self.sens_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sens_layout.addWidget(self.sens_title_label)
        sens_layout.addWidget(self.sens_slider, 1)
        control_layout.addWidget(self.sens_panel, 1, 1)
        control_layout.setRowStretch(0, 1)
        control_layout.setRowStretch(1, 1)
        control_layout.setColumnStretch(0, 1)
        control_layout.setColumnStretch(1, 1)

        self.video = VideoWidget()
        self.video.setObjectName("videoPanel")
        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.addWidget(self.waveform)
        self.top_splitter.addWidget(self.rpm_panel)
        self.top_splitter.setStretchFactor(0, 5)
        self.top_splitter.setStretchFactor(1, 1)

        self.bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.bottom_splitter.addWidget(self.video)
        self.bottom_splitter.addWidget(self.control_panel)
        self.bottom_splitter.setStretchFactor(0, 5)
        self.bottom_splitter.setStretchFactor(1, 1)

        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.addWidget(self.top_splitter)
        self.content_splitter.addWidget(self.bottom_splitter)
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 4)

        layout.addWidget(self.toolbar_scroll)
        layout.addWidget(self.content_splitter, 1)
        self.setCentralWidget(root)

        self.status_label = QLabel("Open a video or camera to begin. Wheel to zoom, middle-drag to pan.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setMinimumWidth(0)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.status_bar.setContentsMargins(0, 0, 0, 0)
        self.status_bar.setMinimumHeight(0)
        self.status_bar.setMaximumHeight(STATUS_BAR_MAX_HEIGHT)
        self.status_bar.addWidget(self.status_label, 1)
        self.setStatusBar(self.status_bar)

        self.set_load_mode("Camera")
        self.set_rpm(None)

    # 顯示 setting 小視窗
    def show_camera_settings(self) -> CameraSettingsDialog:
        if self.camera_settings_dialog is None:
            self.camera_settings_dialog = CameraSettingsDialog(self)
        self.camera_settings_dialog.show()
        set_windows_title_bar_color(self.camera_settings_dialog)
        self.camera_settings_dialog.raise_()
        self.camera_settings_dialog.activateWindow()
        return self.camera_settings_dialog

    # 更新 camera 下拉選單
    def set_camera_indexes(self, indexes: list[str]) -> None:
        self.camera_menu.clear()
        for index in indexes:
            self.camera_menu.addItem(f"Cam {index}", index)

    # 切換載入模式顯示的控制項
    def set_load_mode(self, mode: str) -> None:
        is_camera_mode = mode == "Camera"
        self.open_video_button.setVisible(not is_camera_mode)
        self.camera_menu.setVisible(is_camera_mode)
        self.scan_camera_button.setVisible(is_camera_mode)

    # 更新播放按鈕圖示
    def set_playing(self, playing: bool) -> None:
        self.play_button.setIcon(self.pause_icon if playing else self.play_icon)
        self.play_button.setToolTip("Pause" if playing else "Play")
        self.video.set_roi_editing(not playing)

    # 更新狀態列
    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # 更新靜音按鈕狀態
    def set_muted(self, muted: bool) -> None:
        self.mute_button.setChecked(muted)

    # 更新 RPM 顯示
    def set_rpm(self, rpm: float | None) -> None:
        self.rpm_panel.set_rpm(rpm)

    # 設定 threshold 拉桿範圍
    def set_threshold_range(self, minimum: int, maximum: int, value: int) -> None:
        self.threshold_slider.setRange(minimum, maximum)
        self.threshold_slider.setValue(value)
        self.set_threshold(value)

    # 更新 threshold 顯示
    def set_threshold(self, value: int) -> None:
        self.waveform.set_threshold_percent(value)

    # 設定 Gain 拉桿範圍
    def set_gain_range(self, minimum: int, maximum: int, value: int, max_value: float) -> None:
        self.gain_slider.setRange(minimum, maximum)
        self.gain_slider.setValue(value)
        self.set_gain(max_value)

    # 更新示波器 Gain
    def set_gain(self, value: float) -> None:
        self.waveform.set_max_value(value)

    # 設定 Smooth 拉桿範圍
    def set_smooth_range(self, minimum: int, maximum: int, value: int) -> None:
        self.smooth_slider.setRange(minimum, maximum)
        self.smooth_slider.setValue(value)

    # 更新 Smooth 顯示
    def set_smooth(self, value: float) -> None:
        pass

    # 設定 Sens 拉桿範圍
    def set_sens_range(self, minimum: int, maximum: int, value: int) -> None:
        self.sens_slider.setRange(minimum, maximum)
        self.sens_slider.setValue(value)

    # 更新 Sens 顯示
    def set_sens(self, value: int) -> None:
        pass

    # 套用啟動時的 waveform / video 比例
    def apply_default_splitter_sizes(self) -> None:
        width, height = DEFAULT_APP_SIZE
        top_height = int(height * DEFAULT_VERTICAL_SPLIT_RATIO)
        bottom_height = max(1, height - top_height)
        top_left_width = int(width * DEFAULT_TOP_HORIZONTAL_SPLIT_RATIO)
        top_right_width = max(1, width - top_left_width)
        bottom_left_width = int(width * DEFAULT_BOTTOM_HORIZONTAL_SPLIT_RATIO)
        bottom_right_width = max(1, width - bottom_left_width)
        self.content_splitter.setSizes([top_height, bottom_height])
        self.top_splitter.setSizes([top_left_width, top_right_width])
        self.bottom_splitter.setSizes([bottom_left_width, bottom_right_width])
