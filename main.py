from __future__ import annotations

import sys
import winsound
from collections import deque
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from threading import Thread
from time import perf_counter

import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from GUI import MonitorWindow


# 參數控制區
APP_NAME = "Anesthesia Monitor" # App 顯示名稱
APP_VERSION = "1.0.1" # App 版本號
APP_TITLE = f"{APP_NAME} v{APP_VERSION}" # 視窗標題統一由 main 注入
DEFAULT_CAMERA_INDEXES = tuple(range(6)) # 第一版先列出常見 camera index
DEFAULT_FPS = 30.0 # 攝影機或影片讀不到 FPS 時使用
SIGNAL_WINDOW_SECONDS = 5.0 # 波型顯示最近幾秒
MIN_ROI_SIZE = 8 # ROI 太小通常是誤畫
TRACK_SEARCH_MARGIN = 80 # ROI 追蹤時在上一個位置周圍搜尋的預設像素範圍
DETECTION_RATE_DEFAULT_HZ = 30 # 預設每秒執行幾次 ROI 追蹤與呼吸偵測
RPM_AVERAGE_BREATH_COUNT = 5 # 使用最近幾次呼吸間隔計算平均 RPM
BREATH_MIN_TRIGGER_INTERVAL_MS = 500 # 忽略太短時間內重複觸發的呼吸訊號
MATCH_CLAHE_CLIP_LIMIT = 2.0 # CLAHE 對比增強強度
MATCH_CLAHE_TILE_GRID_SIZE = (8, 8) # CLAHE 區塊大小
MATCH_BLUR_KERNEL_SIZE = (5, 5) # match 前的平滑 kernel
MATCH_MODE_GRAY_BLUR = "Gray Blur" # 原始 gray + blur match
MATCH_MODE_CLAHE_GRAY = "CLAHE Gray" # CLAHE gray + blur match
MATCH_MODE_NONE = "None" # 不額外增強影像，直接用原始 frame match
MATCH_MODE_SOBEL_EDGE = "Sobel Edge" # Sobel 邊緣強度 match
MATCH_MODE_LAPLACIAN_EDGE = "Laplacian Edge" # Laplacian 邊緣強度 match
MATCH_MODE_MOTION_EDGE = "Motion Edge" # 形態學邊緣強化 match
THRESHOLD_MIN = 0 # threshold 拉桿最小百分比
THRESHOLD_MAX = 100 # threshold 拉桿最大百分比
THRESHOLD_DEFAULT = 50 # threshold 拉桿預設百分比
MOTION_MAX_SCALE = 100 # Gain 拉桿整數刻度轉換成 Max 小數後 2 位
MOTION_MAX_MIN = 0.00 # 示波器 Max 最小位移值
MOTION_MAX_MAX = 20.00 # 示波器 Max 最大位移值
MOTION_MAX_DEFAULT = 10.00 # 示波器 Max 預設位移值
MOTION_MAX_EFFECTIVE_MIN = 0.01 # 避免 Gain 最高時 threshold 卡在 0
SMOOTH_SCALE = 100 # Smooth 拉桿整數刻度轉換成平滑強度小數後 2 位
SMOOTH_MIN = 0.00 # 最低訊號平滑強度
SMOOTH_MAX = 1.00 # 最高訊號平滑強度
SMOOTH_DEFAULT = 0.20 # 預設訊號平滑強度
DETECTION_RANGE_MIN = 10 # 偵測範圍拉桿最小像素
DETECTION_RANGE_MAX = 250 # 偵測範圍拉桿最大像素
DETECTION_RANGE_DEFAULT = TRACK_SEARCH_MARGIN # 偵測範圍拉桿預設像素
BEEP_FREQUENCY_HZ = 479 # 呼吸 peak 提示音頻率
BEEP_DURATION_MS = 100 # 呼吸 peak 提示音長度
VIEW_NAV_HINT = "Wheel to zoom, middle-drag to pan." # 影像操作提示


# 將 FPS 顯示成精簡文字
def format_fps(fps: float) -> str:
    return f"{fps:.0f}" if fps.is_integer() else f"{fps:.1f}"


# 狀態列補上影像操作提示
def with_view_hint(text: str) -> str:
    return f"{text} {VIEW_NAV_HINT}"


@dataclass
class Roi:
    x: int
    y: int
    width: int
    height: int

    # 確認 ROI 是否足夠用來分析呼吸訊號
    def is_valid(self) -> bool:
        return self.width >= MIN_ROI_SIZE and self.height >= MIN_ROI_SIZE

    # 將 ROI 限制在影像邊界內
    def clamp(self, frame_width: int, frame_height: int) -> "Roi":
        x = max(0, min(self.x, frame_width - 1))
        y = max(0, min(self.y, frame_height - 1))
        width = max(0, min(self.width, frame_width - x))
        height = max(0, min(self.height, frame_height - y))
        return Roi(x, y, width, height)

    # 轉成 GUI 可以直接顯示的 tuple
    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.width, self.height

    # 取得 ROI 中心點
    def center(self) -> tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2


# 將 Max 小數值轉成 Gain 反向拉桿刻度
def motion_max_to_slider_value(value: float) -> int:
    max_value = max(MOTION_MAX_MIN, min(value, MOTION_MAX_MAX))
    gain_value = MOTION_MAX_MAX - max_value + MOTION_MAX_MIN
    return round(gain_value * MOTION_MAX_SCALE)


# 將 Gain 反向拉桿刻度轉回 Max 小數值
def slider_value_to_motion_max(value: int) -> float:
    gain_value = value / MOTION_MAX_SCALE
    return max(MOTION_MAX_EFFECTIVE_MIN, MOTION_MAX_MAX - gain_value + MOTION_MAX_MIN)


# 將 Smooth 強度轉成 QSlider 可以使用的整數刻度
def smooth_to_slider_value(value: float) -> int:
    return round(value * SMOOTH_SCALE)


# 將 QSlider 整數刻度轉回 Smooth 強度
def slider_value_to_smooth(value: int) -> float:
    return value / SMOOTH_SCALE


# 影像來源封裝
class CaptureSource:
    def __init__(self) -> None:
        self.capture: cv2.VideoCapture | None = None
        self.label = "No source"
        self.fps = DEFAULT_FPS
        self.mode: str | None = None
        self.identifier: str | None = None

    # 開啟影片檔
    def open_video(self, path: Path) -> bool:
        return self._open(cv2.VideoCapture(str(path)), path.name, "Video", str(path))

    # 開啟指定攝影機
    def open_camera(self, index: int) -> bool:
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        return self._open(capture, f"Camera {index}", "Camera", str(index))

    # 套用新的 OpenCV capture
    def _open(self, capture: cv2.VideoCapture, label: str, mode: str, identifier: str) -> bool:
        self.release()
        if not capture.isOpened():
            capture.release()
            return False

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        self.capture = capture
        self.label = label
        self.fps = fps if fps > 0 else DEFAULT_FPS
        self.mode = mode
        self.identifier = identifier
        return True

    # 讀取下一張影格
    def read(self):
        if self.capture is None:
            return False, None
        return self.capture.read()

    # 釋放目前來源
    def release(self) -> None:
        if self.capture is not None:
            self.capture.release()
        self.capture = None
        self.label = "No source"
        self.fps = DEFAULT_FPS
        self.mode = None
        self.identifier = None


# 從 ROI 位移產生呼吸相關的運動訊號
class RoiTracker:
    def __init__(self) -> None:
        self.values: list[float | None] = [None] * int(DEFAULT_FPS * SIGNAL_WINDOW_SECONDS)
        self.cursor_index = 0
        self.reference_roi: Roi | None = None
        self.current_roi: Roi | None = None
        self.reference_center: tuple[float, float] | None = None
        self.search_margin = TRACK_SEARCH_MARGIN
        self.smooth_strength = SMOOTH_DEFAULT
        self.smoothed_displacement: float | None = None
        self.clahe = cv2.createCLAHE(
            clipLimit=MATCH_CLAHE_CLIP_LIMIT,
            tileGridSize=MATCH_CLAHE_TILE_GRID_SIZE,
        )
        self.match_mode = MATCH_MODE_NONE
        self.template = None

    # 更新 match 使用的影像增強模式
    def set_match_mode(self, mode: str) -> None:
        self.match_mode = mode

    # 更新 ROI 追蹤搜尋範圍
    def set_search_margin(self, search_margin: int) -> None:
        self.search_margin = max(1, search_margin)

    # 更新位移訊號平滑強度
    def set_smooth_strength(self, smooth_strength: float) -> None:
        self.smooth_strength = max(0.0, min(smooth_strength, 1.0))
        self.smoothed_displacement = None

    # 依 FPS 重設波型長度
    def configure(self, fps: float) -> None:
        max_samples = max(2, int(fps * SIGNAL_WINDOW_SECONDS))
        self.values = [None] * max_samples
        self.cursor_index = 0
        self.reference_roi = None
        self.current_roi = None
        self.reference_center = None
        self.smoothed_displacement = None
        self.template = None

    # ROI 改變時清掉上一段訊號
    def reset(self) -> None:
        self.values = [None] * len(self.values)
        self.cursor_index = 0
        self.reference_roi = None
        self.current_roi = None
        self.reference_center = None
        self.smoothed_displacement = None
        self.template = None

    # 用目前畫面建立追蹤模板
    def set_reference(self, frame, roi: Roi) -> None:
        frame_height, frame_width = frame.shape[:2]
        roi = roi.clamp(frame_width, frame_height)
        roi_frame = frame[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
        gray = self._prepare_match_frame(roi_frame)
        self.reference_roi = roi
        self.current_roi = roi
        self.reference_center = roi.center()
        self.template = gray
        self.values = [None] * len(self.values)
        self.cursor_index = 0
        self.smoothed_displacement = None

    # 更新單幀 ROI 位置與位移訊號
    def update(self, frame) -> tuple[Roi | None, float]:
        if self.template is None or self.current_roi is None or self.reference_center is None:
            return None, 0.0

        frame_height, frame_width = frame.shape[:2]
        search_left = max(0, self.current_roi.x - self.search_margin)
        search_top = max(0, self.current_roi.y - self.search_margin)
        search_right = min(frame_width, self.current_roi.x + self.current_roi.width + self.search_margin)
        search_bottom = min(frame_height, self.current_roi.y + self.current_roi.height + self.search_margin)
        search_frame = frame[search_top:search_bottom, search_left:search_right]

        if search_frame.shape[0] < self.template.shape[0] or search_frame.shape[1] < self.template.shape[1]:
            return self.current_roi, self._append_displacement(self.current_roi)

        search_gray = self._prepare_match_frame(search_frame)
        match = cv2.matchTemplate(search_gray, self.template, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_location = cv2.minMaxLoc(match)

        new_roi = Roi(
            x=search_left + max_location[0],
            y=search_top + max_location[1],
            width=self.current_roi.width,
            height=self.current_roi.height,
        ).clamp(frame_width, frame_height)

        self.current_roi = new_roi
        displacement = self._append_displacement(new_roi)
        return new_roi, displacement

    # 將影像轉成目前選擇的 match 格式
    def _prepare_match_frame(self, frame):
        if self.match_mode == MATCH_MODE_NONE:
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.match_mode == MATCH_MODE_CLAHE_GRAY:
            gray = self.clahe.apply(gray)
            return cv2.GaussianBlur(gray, MATCH_BLUR_KERNEL_SIZE, 0)
        if self.match_mode == MATCH_MODE_SOBEL_EDGE:
            return self._sobel_edges(gray)
        if self.match_mode == MATCH_MODE_LAPLACIAN_EDGE:
            return self._laplacian_edges(gray)
        if self.match_mode == MATCH_MODE_MOTION_EDGE:
            return self._motion_edges(gray)
        return cv2.GaussianBlur(gray, MATCH_BLUR_KERNEL_SIZE, 0)

    # 取出 Sobel 邊緣強度
    def _sobel_edges(self, gray):
        blurred = cv2.GaussianBlur(gray, MATCH_BLUR_KERNEL_SIZE, 0)
        grad_x = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = cv2.magnitude(grad_x, grad_y)
        return cv2.normalize(magnitude, None, 0, 255, cv2.NORM_MINMAX).astype("uint8")

    # 取出 Laplacian 邊緣強度
    def _laplacian_edges(self, gray):
        blurred = cv2.GaussianBlur(gray, MATCH_BLUR_KERNEL_SIZE, 0)
        edge = cv2.Laplacian(blurred, cv2.CV_32F, ksize=3)
        edge = cv2.convertScaleAbs(edge)
        return edge

    # 用形態學梯度凸顯局部位移邊界
    def _motion_edges(self, gray):
        blurred = cv2.GaussianBlur(gray, MATCH_BLUR_KERNEL_SIZE, 0)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        return cv2.morphologyEx(blurred, cv2.MORPH_GRADIENT, kernel)

    # 將目前中心到初始中心的線長加入波型
    def _append_displacement(self, roi: Roi) -> float:
        if self.reference_center is None:
            return 0.0

        center_x, center_y = roi.center()
        reference_x, reference_y = self.reference_center
        displacement = hypot(center_x - reference_x, center_y - reference_y)
        displacement = self._smooth_displacement(displacement)
        self.values[self.cursor_index] = displacement
        self.cursor_index = (self.cursor_index + 1) % len(self.values)
        return displacement

    # 平滑極短時間內的上下跳動
    def _smooth_displacement(self, displacement: float) -> float:
        if self.smoothed_displacement is None:
            self.smoothed_displacement = displacement
            return displacement

        alpha = max(0.02, 1.0 - self.smooth_strength)
        self.smoothed_displacement += alpha * (displacement - self.smoothed_displacement)
        return self.smoothed_displacement

    # 取得目前追蹤中心
    def current_center(self) -> tuple[float, float] | None:
        if self.current_roi is None:
            return None
        return self.current_roi.center()

    # 取出目前波型資料
    def series(self) -> list[float | None]:
        return list(self.values)

    # 取得下一筆資料會寫入的位置
    def cursor(self) -> int:
        return self.cursor_index


# 從 threshold crossing 計算呼吸速率
class BreathRateDetector:
    def __init__(
        self,
        threshold_percent: int,
        max_value: float,
        average_count: int,
        min_trigger_interval_ms: int,
    ) -> None:
        self.threshold_percent = threshold_percent
        self.max_value = max(MOTION_MAX_EFFECTIVE_MIN, max_value)
        self.min_trigger_interval = max(0.0, min_trigger_interval_ms / 1000)
        self.intervals: deque[float] = deque(maxlen=average_count)
        self.was_above_threshold = False
        self.last_breath_time: float | None = None

    # 修改 threshold 時重置狀態，避免舊 crossing 污染
    def set_threshold_percent(self, threshold_percent: int) -> None:
        self.threshold_percent = threshold_percent
        self.reset()

    # 修改 Max 時重置狀態，避免舊 crossing 污染
    def set_max_value(self, max_value: float) -> None:
        self.max_value = max(MOTION_MAX_EFFECTIVE_MIN, max_value)
        self.reset()

    # 修改最短觸發間隔
    def set_min_trigger_interval_ms(self, interval_ms: int) -> None:
        self.min_trigger_interval = max(0.0, interval_ms / 1000)
        self.reset()

    # 清除目前呼吸計數狀態
    def reset(self) -> None:
        self.intervals.clear()
        self.was_above_threshold = False
        self.last_breath_time = None

    # 更新位移值，突破後回到 threshold 下方算一次呼吸
    def update(self, value: float, timestamp: float) -> tuple[float | None, bool]:
        threshold = self._threshold_value()
        breath_detected = False
        if value > threshold:
            self.was_above_threshold = True
            return self.rpm(), breath_detected

        if self.was_above_threshold and value < threshold:
            if self.last_breath_time is not None:
                interval = timestamp - self.last_breath_time
                if interval < self.min_trigger_interval:
                    self.was_above_threshold = False
                    return self.rpm(), breath_detected
                self.intervals.append(interval)
            self.last_breath_time = timestamp
            self.was_above_threshold = False
            breath_detected = True

        return self.rpm(), breath_detected

    # 將百分比 threshold 轉成 0 到 Max 之間的實際位移值
    def _threshold_value(self) -> float:
        return self.max_value * (self.threshold_percent / 100)

    # 以最近幾次呼吸間隔計算 RPM
    def rpm(self) -> float | None:
        if not self.intervals:
            return None

        average_interval = sum(self.intervals) / len(self.intervals)
        if average_interval <= 0:
            return None
        return 60 / average_interval


# 將 BGR frame 轉成 Qt image
def frame_to_qimage(frame) -> QImage:
    if len(frame.shape) == 2:
        height, width = frame.shape
        image = QImage(frame.data, width, height, width, QImage.Format.Format_Grayscale8)
        return image.copy()

    height, width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    bytes_per_line = 3 * width
    image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return image.copy()


# 主程式控制器
class MonitorController:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.window = MonitorWindow(DEFAULT_CAMERA_INDEXES, APP_TITLE)
        self.window.set_threshold_range(THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_DEFAULT)
        self.window.set_gain_range(
            motion_max_to_slider_value(MOTION_MAX_MAX),
            motion_max_to_slider_value(MOTION_MAX_MIN),
            motion_max_to_slider_value(MOTION_MAX_DEFAULT),
            MOTION_MAX_DEFAULT,
        )
        self.window.set_smooth_range(
            smooth_to_slider_value(SMOOTH_MIN),
            smooth_to_slider_value(SMOOTH_MAX),
            smooth_to_slider_value(SMOOTH_DEFAULT),
        )
        self.window.set_sens_range(
            DETECTION_RANGE_MIN,
            DETECTION_RANGE_MAX,
            DETECTION_RANGE_DEFAULT,
        )
        self.window.detect_rate_spin.setValue(DETECTION_RATE_DEFAULT_HZ)
        self.source = CaptureSource()
        self.tracker = RoiTracker()
        self.tracker.set_search_margin(DETECTION_RANGE_DEFAULT)
        self.tracker.set_smooth_strength(SMOOTH_DEFAULT)
        self.breath_detector = BreathRateDetector(
            THRESHOLD_DEFAULT,
            MOTION_MAX_DEFAULT,
            RPM_AVERAGE_BREATH_COUNT,
            BREATH_MIN_TRIGGER_INTERVAL_MS,
        )
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.playing = False
        self.roi: Roi | None = None
        self.last_frame = None
        self.current_motion = 0.0
        self.next_detection_time = 0.0
        self.selected_video_path: Path | None = None
        self.muted = False
        self.beep_frequency_hz = BEEP_FREQUENCY_HZ
        self.detection_rate_hz = DETECTION_RATE_DEFAULT_HZ
        self.apply_topmost()
        self._connect_events()

    # 綁定 GUI 事件
    def _connect_events(self) -> None:
        self.window.load_mode_menu.currentTextChanged.connect(self.change_load_mode)
        self.window.open_video_button.clicked.connect(self.open_video)
        self.window.scan_camera_button.clicked.connect(self.scan_cameras)
        self.window.play_button.clicked.connect(self.toggle_play)
        self.window.clear_roi_button.clicked.connect(self.clear_roi)
        self.window.reset_button.clicked.connect(self.choose_reset)
        self.window.mute_button.clicked.connect(self.toggle_mute)
        self.window.topmost_check.clicked.connect(self.toggle_topmost)
        self.window.detect_rate_spin.valueChanged.connect(self.change_detection_rate)
        self.window.beep_frequency_spin.valueChanged.connect(self.change_beep_frequency)
        self.window.enhancement_menu.currentTextChanged.connect(self.change_enhancement_mode)
        self.window.show_raw_check.stateChanged.connect(self.change_show_raw)
        self.window.threshold_slider.valueChanged.connect(self.change_threshold)
        self.window.gain_slider.valueChanged.connect(self.change_gain)
        self.window.smooth_slider.valueChanged.connect(self.change_smooth)
        self.window.sens_slider.valueChanged.connect(self.change_sens)
        self.window.video.roi_selected.connect(self.set_roi)
        self.window.video.edit_rejected.connect(self.window.set_status)
        self.app.aboutToQuit.connect(self.close)

    # 切換載入模式
    def change_load_mode(self, mode: str) -> None:
        self._stop_current_source()
        self.window.set_load_mode(mode)
        if mode == "Camera":
            self.window.set_status(with_view_hint("Camera mode selected. Press Play to open the selected camera."))
        else:
            if self.selected_video_path is None:
                self.window.set_status(with_view_hint("Video mode selected. Open a video file to begin."))
            else:
                self.window.set_status(with_view_hint(f"Video mode selected: {self.selected_video_path.name}. Press Play to start."))

    # 開啟影片檔
    def open_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "Select Video File",
            "",
            "Video files (*.mp4 *.avi *.mov *.mkv);;All files (*.*)",
        )
        if not path:
            return

        self.selected_video_path = Path(path)
        if not self.source.open_video(self.selected_video_path):
            self.window.set_status("Unable to open the selected video.")
            return

        self._reset_for_loaded_source(playing=False)
        ok, frame = self.source.read()
        if ok and frame is not None:
            self.last_frame = frame
            self._display_frame(frame)
        self.window.set_status(with_view_hint(f"Video loaded: {self.source.label}. Press Play to start."))

    # 開啟目前選到的攝影機
    def open_camera(self) -> bool:
        index = int(self.window.camera_menu.currentData() or 0)
        if not self.source.open_camera(index):
            self.window.set_status(f"Unable to open Camera {index}.")
            return False

        self._reset_for_loaded_source(playing=True)
        self.window.set_status(with_view_hint(f"Camera opened: Camera {index}"))
        self._start_timer()
        return True

    # 掃描可開啟的 camera index
    def scan_cameras(self) -> None:
        available = []
        for index in DEFAULT_CAMERA_INDEXES:
            capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if capture.isOpened():
                available.append(str(index))
            capture.release()

        if not available:
            available = [str(index) for index in DEFAULT_CAMERA_INDEXES]
            self.window.set_status("No cameras detected. Keeping the default index list.")
        else:
            self.window.set_status(f"Available cameras: {', '.join(available)}")

        self.window.set_camera_indexes(available)

    # 更新呼吸偵測 threshold
    def change_threshold(self, value: int) -> None:
        self.window.set_threshold(value)
        self.breath_detector.set_threshold_percent(value)
        self.window.set_rpm(None)

    # 更新示波器 Gain
    def change_gain(self, value: int) -> None:
        max_value = slider_value_to_motion_max(value)
        self.window.set_gain(max_value)
        self.breath_detector.set_max_value(max_value)
        self.window.set_rpm(None)

    # 更新位移訊號平滑強度
    def change_smooth(self, value: int) -> None:
        smooth_strength = slider_value_to_smooth(value)
        self.window.set_smooth(smooth_strength)
        self.tracker.set_smooth_strength(smooth_strength)
        self.breath_detector.reset()
        self.window.set_rpm(None)

    # 更新 Sens 搜尋範圍
    def change_sens(self, value: int) -> None:
        self.window.set_sens(value)
        self.tracker.set_search_margin(value)

    # 切換影像增強與 match 模式
    def change_enhancement_mode(self, mode: str) -> None:
        mode = self.window.enhancement_menu.currentData() or mode
        self.tracker.set_match_mode(mode)
        self.tracker.reset()
        self.breath_detector.reset()
        self.current_motion = 0.0
        if self.roi is not None and self.last_frame is not None:
            self.tracker.set_reference(self.last_frame, self.roi)
            self.window.video.set_tracking_centers(self.roi.center(), self.roi.center())
        else:
            self.window.video.set_tracking_centers(None, None)

        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)
        if self.last_frame is not None:
            self._display_frame(self.last_frame)
        self.window.set_status(f"Enhancement mode: {mode}")

    # 切換影像區是否顯示原始畫面
    def change_show_raw(self, _state: int | None = None) -> None:
        if self.last_frame is not None:
            self._display_frame(self.last_frame)
        self.window.set_status(
            "Showing raw video preview." if self.window.show_raw_check.isChecked()
            else "Showing enhanced video preview."
        )

    # 還原 layout 比例並讓影像符合視窗
    def reset_layout(self) -> None:
        self.window.apply_default_splitter_sizes()
        self.window.video.fit_to_window()
        self.window.set_status(with_view_hint("Layout reset. Video fit to window."))

    # 選擇要重置的項目
    def choose_reset(self) -> None:
        dialog = QMessageBox(self.window)
        dialog.setWindowTitle("Reset")
        dialog.setText("Select what you want to reset.")
        layout_button = dialog.addButton("Layout", QMessageBox.ButtonRole.AcceptRole)
        settings_button = dialog.addButton("Settings", QMessageBox.ButtonRole.AcceptRole)
        both_button = dialog.addButton("Both", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton(QMessageBox.StandardButton.Cancel)
        dialog.exec()

        clicked_button = dialog.clickedButton()
        if clicked_button == layout_button:
            self.reset_layout()
        elif clicked_button == settings_button:
            self.reset_settings()
        elif clicked_button == both_button:
            self.reset_layout()
            self.reset_settings()
            self.window.set_status("Layout and settings reset.")

    # 還原偵測相關設定
    def reset_settings(self) -> None:
        threshold_value = THRESHOLD_DEFAULT
        gain_value = motion_max_to_slider_value(MOTION_MAX_DEFAULT)
        smooth_value = smooth_to_slider_value(SMOOTH_DEFAULT)
        sens_value = DETECTION_RANGE_DEFAULT

        self.window.detect_rate_spin.setValue(DETECTION_RATE_DEFAULT_HZ)
        self.window.threshold_slider.setValue(threshold_value)
        self.window.gain_slider.setValue(gain_value)
        self.window.smooth_slider.setValue(smooth_value)
        self.window.sens_slider.setValue(sens_value)
        self.change_detection_rate(DETECTION_RATE_DEFAULT_HZ)
        self.change_threshold(threshold_value)
        self.change_gain(gain_value)
        self.change_smooth(smooth_value)
        self.change_sens(sens_value)
        self.window.set_status("Settings reset to defaults.")

    # 更新呼吸提示音頻率
    def change_beep_frequency(self, value: int) -> None:
        self.beep_frequency_hz = value
        self.window.set_status(f"Peak beep frequency set to {value} Hz.")

    # 更新 ROI 偵測頻率
    def change_detection_rate(self, value: int) -> None:
        self.detection_rate_hz = max(1, value)
        self.window.set_status(f"Detection rate set to {self.detection_rate_hz} Hz.")

    # 切換呼吸提示音
    def toggle_mute(self, _checked: bool | None = None) -> None:
        self.muted = self.window.mute_button.isChecked()
        self.window.set_muted(self.muted)
        self.window.set_status("Muted peak beep." if self.muted else "Peak beep enabled.")

    # 套用目前的置頂設定
    def apply_topmost(self) -> None:
        self.window.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint,
            self.window.topmost_check.isChecked(),
        )

    # 切換視窗置頂
    def toggle_topmost(self, _checked: bool | None = None) -> None:
        self.apply_topmost()
        self.window.show()
        topmost = self.window.topmost_check.isChecked()
        self.window.set_status("Window topmost enabled." if topmost else "Window topmost disabled.")

    # 切換播放與暫停
    def toggle_play(self) -> None:
        mode = self.window.load_mode_menu.currentText()
        if mode == "Camera" and self._should_open_selected_camera():
            self.open_camera()
            return

        if mode == "Video":
            if self.selected_video_path is None:
                self.window.set_status("Open a video file before pressing Play.")
                return
            if self._should_open_selected_video():
                self.open_selected_video_for_playback()
                return

        self.playing = not self.playing
        self.window.set_playing(self.playing)

        if self.playing:
            self.window.set_status(with_view_hint("Playing. The waveform updates after an ROI is set."))
            self._start_timer()
        else:
            self.timer.stop()
            self.window.set_status(with_view_hint("Paused. Drag on the video to draw an ROI."))

    # 判斷是否需要開啟或切換相機
    def _should_open_selected_camera(self) -> bool:
        index = str(self.window.camera_menu.currentData() or 0)
        return self.source.capture is None or self.source.mode != "Camera" or self.source.identifier != index

    # 判斷是否需要開啟影片
    def _should_open_selected_video(self) -> bool:
        return self.source.capture is None or self.source.mode != "Video"

    # 開啟已選取的影片並開始播放
    def open_selected_video_for_playback(self) -> bool:
        if self.selected_video_path is None:
            self.window.set_status("Open a video file before pressing Play.")
            return False

        if not self.source.open_video(self.selected_video_path):
            self.window.set_status("Unable to open the selected video.")
            return False

        self._reset_for_loaded_source(playing=True)
        self.window.set_status(with_view_hint("Playing. The waveform updates after an ROI is set."))
        self._start_timer()
        return True

    # 清除目前 ROI 和波型
    def clear_roi(self) -> None:
        self.roi = None
        self.tracker.reset()
        self.breath_detector.reset()
        self.current_motion = 0.0
        self.window.video.set_roi(None)
        self.window.video.set_tracking_centers(None, None)
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)
        self.window.set_status("ROI cleared.")

    # 套用新 ROI
    def set_roi(self, x: int, y: int, width: int, height: int) -> None:
        roi = Roi(x, y, width, height)
        if self.last_frame is not None:
            frame_height, frame_width = self.last_frame.shape[:2]
            roi = roi.clamp(frame_width, frame_height)

        if not roi.is_valid():
            self.window.set_status("ROI is too small. Pause and drag a larger area.")
            return

        self.roi = roi
        self.tracker.reset()
        self.breath_detector.reset()
        if self.last_frame is not None:
            self.tracker.set_reference(self.last_frame, roi)
        self.current_motion = 0.0
        self.next_detection_time = 0.0
        self.window.video.set_roi(roi.as_tuple())
        self.window.video.set_tracking_centers(roi.center(), roi.center())
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)
        self.window.set_status(with_view_hint("ROI set. Press Play to start updating the waveform."))

    # 新來源啟動時重置狀態
    def _reset_for_loaded_source(self, playing: bool) -> None:
        self.playing = playing
        self.roi = None
        self.last_frame = None
        self.current_motion = 0.0
        self.tracker.configure(self.source.fps)
        self.breath_detector.reset()
        self.next_detection_time = 0.0
        self.window.set_playing(playing)
        self.window.video.set_roi(None)
        self.window.video.set_tracking_centers(None, None)
        self.window.video.set_status(self._video_status_text())
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)

    # 停止並釋放目前來源
    def _stop_current_source(self) -> None:
        self.timer.stop()
        self.playing = False
        self.roi = None
        self.last_frame = None
        self.current_motion = 0.0
        self.tracker.reset()
        self.breath_detector.reset()
        self.next_detection_time = 0.0
        self.source.release()
        self.window.set_playing(False)
        self.window.video.set_roi(None)
        self.window.video.set_tracking_centers(None, None)
        self.window.video.clear_frame()
        self.window.video.set_status("No source|Enhance: None|FPS: 0|Motion: 0.00")
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)

    # 啟動播放 timer
    def _start_timer(self) -> None:
        interval = max(10, int(1000 / self.source.fps))
        self.timer.start(interval)

    # 更新影像與波型
    def update_frame(self) -> None:
        if not self.playing or self.source.capture is None:
            return

        ok, frame = self.source.read()
        if not ok or frame is None:
            self.timer.stop()
            self.playing = False
            self.window.set_playing(False)
            self.source.release()
            self.window.set_status("Playback ended or the source was disconnected.")
            return

        self.last_frame = frame
        now = perf_counter()
        if self.roi is not None and now >= self.next_detection_time:
            detection_interval = 1 / max(1, self.detection_rate_hz)
            self.next_detection_time = now + detection_interval
            tracked_roi, displacement = self.tracker.update(frame)
            if tracked_roi is not None:
                self.roi = tracked_roi
                self.current_motion = displacement
                rpm, breath_detected = self.breath_detector.update(displacement, now)
                if breath_detected:
                    self._play_peak_beep()
                self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
                self.window.set_rpm(rpm)

        self._display_frame(frame)

    # 將目前影格送到 GUI
    def _display_frame(self, frame) -> None:
        display_frame = (
            frame if self.window.show_raw_check.isChecked()
            else self._enhance_display_frame(frame)
        )
        image = frame_to_qimage(display_frame)
        frame_size = (frame.shape[1], frame.shape[0])
        self.window.video.set_frame(image, frame_size)
        self.window.video.set_roi(self.roi.as_tuple() if self.roi is not None else None)
        self.window.video.set_tracking_centers(self.tracker.reference_center, self.tracker.current_center())
        self.window.video.set_status(self._video_status_text())

    # 組合影片區左上角狀態標題
    def _video_status_text(self) -> str:
        enhance_mode = self.window.enhancement_menu.currentData() or self.window.enhancement_menu.currentText()
        enhance_text = f"Enhance: {enhance_mode}"
        fps_text = format_fps(self.source.fps)
        return (
            f"{self.source.label}|{enhance_text}|"
            f"FPS: {fps_text}|Motion: {self.current_motion:.2f}"
        )

    # 依下拉選單產生影像區預覽畫面
    def _enhance_display_frame(self, frame):
        mode = self.window.enhancement_menu.currentData()
        if mode == MATCH_MODE_NONE:
            return frame

        return self.tracker._prepare_match_frame(frame)

    # 用短促 beep 標記呼吸 peak
    def _play_peak_beep(self) -> None:
        if self.muted:
            return

        Thread(
            target=winsound.Beep,
            args=(self.beep_frequency_hz, BEEP_DURATION_MS),
            daemon=True,
        ).start()

    # 釋放攝影機與 timer
    def close(self) -> None:
        self.timer.stop()
        self.source.release()

    # 啟動 app
    def run(self) -> int:
        self.window.show()
        self.window.apply_default_splitter_sizes()
        return self.app.exec()


# 程式進入點
def main() -> None:
    controller = MonitorController()
    raise SystemExit(controller.run())


if __name__ == "__main__":
    main()
