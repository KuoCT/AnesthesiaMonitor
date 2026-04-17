from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


# 顏色 helper：用 HEX code 設定 Qt 顏色
def hex_color(value: str) -> QColor:
    return QColor(value)


# 參數控制區
APP_TITLE = "Anesthesia Monitor"
APP_BG_HEX = "#18191A" # App 主背景
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
TRACKING_LINE_WIDTH = 2 # 中心位移線粗細
WAVE_THRESHOLD_LINE_WIDTH = 1 # 示波器 threshold 線粗細
RPM_TEXT = "RPM" # 呼吸速率顯示標籤
RESPIRATION_TEXT = "Respiration" # 呼吸速率卡片標籤
THRESHOLD_TEXT = "Thresh." # threshold 顯示標籤
RPM_VALUE_FONT_SIZE = 60 # 呼吸速率數值字體大小
RPM_UNIT_FONT_SIZE = 10 # RPM 單位字體大小
RESPIRATION_FONT_SIZE = 16 # Respiration 標籤字體大小
RESPIRATION_PANEL_MIN_HEIGHT = 34 # 預設狀態避免 Respiration 被 RPM 擠到消失
WAVE_Y_AXIS_LABEL_WIDTH = 34 # 示波器 Y 軸 label 預留寬度
WAVE_Y_AXIS_LABEL_FONT_SIZE = 10 # 示波器 Y 軸 label 字體大小
PANEL_PADDING_Y = 10 # 板塊 3 上下留白
DEFAULT_APP_SIZE = (860, 780) # 啟動時 app 寬高
DEFAULT_VERTICAL_SPLIT_RATIO = 0.22 # 上方板塊高度占比：1|2 / 3|4
DEFAULT_TOP_HORIZONTAL_SPLIT_RATIO = 0.82 # 上方 1|2 左側示波器占比
DEFAULT_BOTTOM_HORIZONTAL_SPLIT_RATIO = 0.90 # 下方 3|4 左側影像區占比
APP_STYLE_TEMPLATE = """
QMainWindow, QWidget {{
    background-color: {app_bg};
    color: {text};
}}
#waveformPanel, #videoPanel, #controlPanel, #rpmPanel, #rpmValuePanel, #respirationPanel, #thresholdPanel {{
    background-color: {panel_bg};
}}
QLabel {{
    color: {text};
}}
QPushButton, QComboBox {{
    background-color: {control_bg};
    color: {bright_text};
    border: 1px solid {control_border};
    border-radius: 4px;
    padding: 4px 8px;
}}
QPushButton:hover, QComboBox:hover {{
    background-color: {control_hover};
}}
QPushButton:pressed {{
    background-color: {control_pressed};
}}
QScrollArea {{
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
QSlider::handle:vertical {{
    background-color: {bright_text};
    border: 1px solid {control_border};
    width: {slider_handle_width}px;
    height: {slider_handle_height}px;
    margin: 0 -{slider_handle_margin}px;
    border-radius: {slider_border_radius}px;
}}
#rpmValuePanel, #respirationPanel, #thresholdPanel {{
    background-color: {panel_bg};
    border: 1px solid {card_border};
    border-radius: 8px;
}}
#rpmPanel QLabel, #rpmValuePanel QLabel, #respirationPanel QLabel, #controlPanel QLabel, #thresholdPanel QLabel {{
    background-color: {panel_bg};
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
ROI_PAUSED_COLOR = hex_color(ROI_PAUSED_HEX) # 暫停編輯時的 ROI 顏色
ROI_PLAYING_COLOR = hex_color(ROI_PLAYING_HEX) # 播放追蹤時的 ROI 顏色
ROI_PREVIEW_COLOR = hex_color(ROI_PREVIEW_HEX) # 新增 ROI 時的預覽顏色
TRACKING_LINE_COLOR = hex_color(TRACKING_LINE_HEX) # 中心位移線顏色


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
        self.source_label = "No source"
        self.motion_value = 0.0

    # 更新目前顯示的影像
    def set_frame(self, image: QImage, frame_size: tuple[int, int]) -> None:
        self.image = image
        self.frame_size = frame_size
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

    # 更新 ROI 顯示
    def set_roi(self, roi: tuple[int, int, int, int] | None) -> None:
        self.roi = roi
        self.update()

    # 更新參考中心和目前追蹤中心
    def set_tracking_centers(self, reference_center: tuple[float, float] | None, current_center: tuple[float, float] | None) -> None:
        self.reference_center = reference_center
        self.current_center = current_center
        self.update()

    # 更新狀態文字
    def set_status(self, source_label: str, motion_value: float) -> None:
        self.source_label = source_label
        self.motion_value = motion_value
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
        painter.drawText(16, 28, f"{self.source_label} | motion {self.motion_value:.2f}")

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
            self.zoom_scale = min(self.zoom_scale * 1.1, 8.0)
        else:
            self.zoom_scale = max(self.zoom_scale / 1.1, 0.25)

        if self.zoom_scale == old_scale:
            return

        cursor_x = event.position().x()
        cursor_y = event.position().y()
        self._anchor_zoom_to_point(anchor, cursor_x, cursor_y)
        self.update()

    # 調整 pan，讓縮放後滑鼠下的影像點維持不動
    def _anchor_zoom_to_point(self, frame_point: tuple[int, int], cursor_x: float, cursor_y: float) -> None:
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
        self.pan_x = cursor_x - base_left - frame_point[0] * draw_width / frame_width
        self.pan_y = cursor_y - base_top - frame_point[1] * draw_height / frame_height

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
    def _points_to_roi(self, start: tuple[int, int], end: tuple[int, int] | None) -> tuple[int, int, int, int] | None:
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
        if current is None or self.original_roi is None or self.drag_start is None or self.drag_handle is None:
            return self.roi

        x, y, width, height = self.original_roi
        left = x
        top = y
        right = x + width
        bottom = y + height

        if self.drag_handle == "move":
            delta_x = current[0] - self.drag_start[0]
            delta_y = current[1] - self.drag_start[1]
            return self._clamp_roi(left + delta_x, top + delta_y, right + delta_x, bottom + delta_y)

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
    def _clamp_roi(self, left: int, top: int, right: int, bottom: int) -> tuple[int, int, int, int] | None:
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
    def _draw_roi(self, painter: QPainter, roi: tuple[int, int, int, int], color: QColor) -> None:
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
    def _roi_to_canvas_box(self, roi: tuple[int, int, int, int]) -> tuple[float, float, float, float] | None:
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
        self.setMinimumHeight(80)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.values: list[float | None] = []
        self.cursor_index = 0
        self.threshold_percent = 50

    # 更新波型資料
    def set_values(self, values: list[float | None], cursor_index: int = 0) -> None:
        self.values = values
        self.cursor_index = cursor_index
        self.update()

    # 更新 threshold 顯示線
    def set_threshold_percent(self, threshold_percent: int) -> None:
        self.threshold_percent = max(0, min(threshold_percent, 100))
        self.update()

    # 繪製波型
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), PANEL_BG)
        painter.setPen(QPen(QColor("white"), 2))
        painter.drawText(16, 28, "ROI motion waveform")

        graph_left = 16
        graph_right_padding = 16 + WAVE_Y_AXIS_LABEL_WIDTH
        graph = QRect(graph_left, 45, max(1, self.width() - graph_left - graph_right_padding), max(1, self.height() - 63))
        self._draw_y_axis_labels(painter, graph)
        painter.setPen(QPen(WAVE_GRID_COLOR, 1))
        painter.drawRect(graph)

        valid_values = [value for value in self.values if value is not None]
        if len(valid_values) < 2:
            middle = graph.top() + graph.height() // 2
            painter.drawLine(graph.left(), middle, graph.right(), middle)
            self._draw_threshold(painter, graph)
            self._draw_cursor(painter, graph)
            return

        minimum = min(valid_values)
        maximum = max(valid_values)
        span = maximum - minimum if maximum > minimum else 1.0
        self._draw_threshold(painter, graph)

        painter.setPen(QPen(WAVE_LINE_COLOR, 2))
        previous = None
        for index, value in enumerate(self.values):
            if value is None:
                previous = None
                continue

            x_ratio = index / max(1, len(self.values) - 1)
            y_ratio = (value - minimum) / span
            x = graph.left() + x_ratio * graph.width()
            y = graph.bottom() - y_ratio * graph.height()
            current = (int(x), int(y))
            if previous is not None and index != self.cursor_index:
                painter.drawLine(previous[0], previous[1], current[0], current[1])
            previous = current

        self._draw_cursor(painter, graph)

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
        labels = [
            ("100", graph.top() + 4),
            ("50", graph.center().y() + 4),
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


# 主視窗 layout
class MonitorWindow(QMainWindow):
    def __init__(self, camera_indexes: tuple[int, ...]) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setStyleSheet(APP_STYLE)
        self.resize(*DEFAULT_APP_SIZE)
        self._build_layout(camera_indexes)

    # 建立 GUI 版面
    def _build_layout(self, camera_indexes: tuple[int, ...]) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar_widget = QWidget()
        toolbar_widget.setMinimumWidth(0)
        toolbar_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(0, 0, 0, 0)
        self.load_mode_menu = QComboBox()
        self.load_mode_menu.addItems(["Camera", "Video"])
        self.open_video_button = QPushButton("Open Video")
        self.camera_label = QLabel("Camera")
        self.camera_menu = QComboBox()
        self.camera_menu.addItems([str(index) for index in camera_indexes])
        self.scan_camera_button = QPushButton("Scan Cameras")
        self.play_button = QPushButton("Play")
        self.clear_roi_button = QPushButton("Clear ROI")
        self.reset_layout_button = QPushButton("Reset Layout")
        self.status_label = QLabel("Open a video or camera to begin.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setMinimumWidth(0)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

        toolbar.addWidget(QLabel("Load Mode"))
        toolbar.addWidget(self.load_mode_menu)
        toolbar.addWidget(self.open_video_button)
        toolbar.addWidget(self.camera_label)
        toolbar.addWidget(self.camera_menu)
        toolbar.addWidget(self.scan_camera_button)
        toolbar.addWidget(self.play_button)
        toolbar.addWidget(self.clear_roi_button)
        toolbar.addWidget(self.reset_layout_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.status_label, 1)

        self.toolbar_scroll = QScrollArea()
        self.toolbar_scroll.setWidget(toolbar_widget)
        self.toolbar_scroll.setWidgetResizable(True)
        self.toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.toolbar_scroll.setMinimumWidth(0)
        self.toolbar_scroll.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        self.waveform = WaveformWidget()
        self.waveform.setObjectName("waveformPanel")
        self.rpm_panel = QWidget()
        self.rpm_panel.setObjectName("rpmPanel")
        self.rpm_panel.setMinimumWidth(0)
        self.rpm_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rpm_layout = QVBoxLayout(self.rpm_panel)
        rpm_layout.setContentsMargins(10, 10, 10, 10)
        rpm_layout.setSpacing(8)
        self.rpm_value_panel = QFrame()
        self.rpm_value_panel.setObjectName("rpmValuePanel")
        self.rpm_value_panel.setMinimumWidth(0)
        self.rpm_value_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        rpm_value_layout = QVBoxLayout(self.rpm_value_panel)
        rpm_value_layout.setContentsMargins(8, 8, 8, 8)
        self.rpm_value_label = QLabel("--")
        self.rpm_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rpm_value_label.setTextFormat(Qt.TextFormat.RichText)
        self.rpm_value_label.setMinimumWidth(0)
        self.rpm_value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        rpm_value_layout.addWidget(self.rpm_value_label)
        self.respiration_panel = QFrame()
        self.respiration_panel.setObjectName("respirationPanel")
        self.respiration_panel.setMinimumHeight(RESPIRATION_PANEL_MIN_HEIGHT)
        self.respiration_panel.setMinimumWidth(0)
        self.respiration_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        respiration_layout = QVBoxLayout(self.respiration_panel)
        respiration_layout.setContentsMargins(8, 4, 8, 4)
        self.respiration_label = QLabel(RESPIRATION_TEXT)
        self.respiration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.respiration_label.setStyleSheet(f"font-size: {RESPIRATION_FONT_SIZE}px;")
        self.respiration_label.setMinimumWidth(0)
        self.respiration_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        respiration_layout.addWidget(self.respiration_label)
        rpm_layout.addWidget(self.rpm_value_panel, 3)
        rpm_layout.addWidget(self.respiration_panel, 1)

        self.control_panel = QWidget()
        self.control_panel.setObjectName("controlPanel")
        self.control_panel.setMinimumWidth(0)
        self.control_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        control_layout = QVBoxLayout(self.control_panel)
        control_layout.setContentsMargins(8, PANEL_PADDING_Y, 8, PANEL_PADDING_Y)
        control_layout.setSpacing(8)
        self.threshold_panel = QFrame()
        self.threshold_panel.setObjectName("thresholdPanel")
        self.threshold_panel.setMinimumWidth(0)
        self.threshold_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        threshold_layout = QVBoxLayout(self.threshold_panel)
        threshold_layout.setContentsMargins(10, 10, 10, 10)
        threshold_layout.setSpacing(8)
        self.threshold_title_label = QLabel(THRESHOLD_TEXT)
        self.threshold_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.threshold_title_label.setMinimumWidth(0)
        self.threshold_title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.threshold_slider = QSlider(Qt.Orientation.Vertical)
        self.threshold_slider.setObjectName("thresholdSlider")
        self.threshold_slider.setInvertedAppearance(False)
        self.threshold_slider.setMinimumWidth(0)
        self.threshold_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        threshold_layout.addWidget(self.threshold_title_label)
        threshold_layout.addWidget(self.threshold_slider, 1)
        control_layout.addWidget(self.threshold_panel, 1)

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
        self.set_load_mode("Camera")
        self.set_rpm(None)

    # 更新 camera 下拉選單
    def set_camera_indexes(self, indexes: list[str]) -> None:
        self.camera_menu.clear()
        self.camera_menu.addItems(indexes)

    # 切換載入模式顯示的控制項
    def set_load_mode(self, mode: str) -> None:
        is_camera_mode = mode == "Camera"
        self.open_video_button.setVisible(not is_camera_mode)
        self.camera_label.setVisible(is_camera_mode)
        self.camera_menu.setVisible(is_camera_mode)
        self.scan_camera_button.setVisible(is_camera_mode)

    # 更新播放按鈕文字
    def set_playing(self, playing: bool) -> None:
        self.play_button.setText("Pause" if playing else "Play")
        self.video.set_roi_editing(not playing)

    # 更新狀態列
    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    # 更新 RPM 顯示
    def set_rpm(self, rpm: float | None) -> None:
        value = "--" if rpm is None else f"{rpm:.0f}"
        self.rpm_value_label.setText(
            f"<span style='font-size:{RPM_VALUE_FONT_SIZE}px; font-weight:700;'>{value}</span>"
            f"<span style='font-size:{RPM_UNIT_FONT_SIZE}px;'> {RPM_TEXT}</span>"
        )

    # 設定 threshold 拉桿範圍
    def set_threshold_range(self, minimum: int, maximum: int, value: int) -> None:
        self.threshold_slider.setRange(minimum, maximum)
        self.threshold_slider.setValue(value)
        self.waveform.set_threshold_percent(value)

    # 更新 threshold 顯示
    def set_threshold(self, value: int) -> None:
        self.waveform.set_threshold_percent(value)

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
