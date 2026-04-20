from __future__ import annotations

import sys
import winsound
from collections import deque
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Lock, Thread
from time import perf_counter

import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog

from GUI import MonitorWindow


# 參數控制區
APP_NAME = "Anesthesia Monitor" # App 顯示名稱
APP_VERSION = "1.2.1" # App 版本號
APP_TITLE = f"{APP_NAME} {APP_VERSION}" # 視窗標題統一由 main 注入
DEFAULT_CAMERA_INDEXES = tuple(range(6)) # 第一版先列出常見 camera index
CAMERA_AUTO_EXPOSURE_VALUE: float | None = 0.25 # 手動快門時送給 DSHOW 的自動曝光關閉值
CAMERA_AUTO_EXPOSURE_AUTO_VALUE: float | None = 0.75 # 持續 auto 時送給 DSHOW 的自動曝光值
CAMERA_EXPOSURE_PROPERTY = cv2.CAP_PROP_GAIN # 曝光列對應 OpenCV gain
CAMERA_SHUTTER_PROPERTY = cv2.CAP_PROP_EXPOSURE # 快門列對應 OpenCV exposure
CAMERA_MANUAL_EXPOSURE_DEFAULT = 192.0 # 軟體手動控制預設 gain
CAMERA_MANUAL_SHUTTER_DEFAULT = -6.0 # 軟體手動控制預設快門/曝光時間
SOFTWARE_CAMERA_CONTROL_DEFAULT = False # 啟動時是否讓 CV2 介入 camera 控制
CAMERA_AUTO_DEFAULT = False # 軟體控制啟用時是否使用持續 auto
DEFAULT_FPS = 30.0 # 攝影機或影片讀不到 FPS 時使用
SIGNAL_WINDOW_SECONDS = 5.0 # 波型顯示最近幾秒
MIN_ROI_SIZE = 8 # ROI 太小通常是誤畫
TRACK_SEARCH_MARGIN = 10 # ROI 追蹤時在上一個位置周圍搜尋的預設像素範圍
DETECTION_RATE_DEFAULT_HZ = 30 # 預設每秒執行幾次 ROI 追蹤與呼吸偵測
RPM_AVERAGE_BREATH_COUNT = 5 # 使用最近幾次呼吸間隔計算平均 RPM
BREATH_MIN_TRIGGER_INTERVAL_MS = 500 # 忽略太短時間內重複觸發的呼吸訊號
BREATH_PEAK_LIFETIME_SECONDS = 15.0 # peak 超過這段時間就不再參與 RPM
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
DETECTION_RANGE_MIN = 1 # 偵測範圍拉桿最小像素
DETECTION_RANGE_MAX = 100 # 偵測範圍拉桿最大像素
DETECTION_RANGE_DEFAULT = TRACK_SEARCH_MARGIN # 偵測範圍拉桿預設像素
BEEP_FREQUENCY_HZ = 479 # 呼吸 peak 提示音頻率
BEEP_DURATION_MS = 100 # 呼吸 peak 提示音長度
VIEW_NAV_HINT = "Wheel to zoom, middle-drag to pan." # 影像操作提示
ROI_DELETE_HINT = "Press Del to clear ROI while paused." # 暫停時可刪除 ROI 的提示


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

    # 即時套用目前相機設定
    def set_camera_property(self, property_id: int, value: float) -> bool:
        if self.capture is None or self.mode != "Camera":
            return False
        return bool(self.capture.set(property_id, value))

    # 讀取目前相機設定值
    def get_camera_property(self, property_id: int) -> float | None:
        if self.capture is None or self.mode != "Camera":
            return None
        value = float(self.capture.get(property_id))
        return value if value != -1 else None

    # 解除手動曝光，交回 camera driver 自動控制
    def restore_camera_auto_exposure(self) -> bool:
        if CAMERA_AUTO_EXPOSURE_AUTO_VALUE is None:
            return False
        return self.set_camera_property(cv2.CAP_PROP_AUTO_EXPOSURE, CAMERA_AUTO_EXPOSURE_AUTO_VALUE)

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


# 背景 camera 讀取器，避免 OpenCV read 卡住 UI thread
class CameraWorker:
    def __init__(self) -> None:
        self.thread: Thread | None = None
        self.stop_event = Event()
        self.command_queue: Queue[tuple] = Queue()
        self.lock = Lock()
        self.capture: cv2.VideoCapture | None = None
        self.label = "No source"
        self.fps = DEFAULT_FPS
        self.mode: str | None = None
        self.identifier: str | None = None
        self.latest_frame = None
        self.frame_sequence = 0
        self.opening = False
        self.open_failed = False
        self.software_control_enabled = SOFTWARE_CAMERA_CONTROL_DEFAULT
        self.auto_enabled = CAMERA_AUTO_DEFAULT
        self.manual_exposure = CAMERA_MANUAL_EXPOSURE_DEFAULT
        self.manual_shutter = CAMERA_MANUAL_SHUTTER_DEFAULT

    # 開始在背景開啟 camera
    def open_camera(
        self,
        index: int,
        software_control_enabled: bool,
        auto_enabled: bool,
        manual_exposure: float,
        manual_shutter: float,
    ) -> None:
        self.release()
        self.stop_event.clear()
        self.open_failed = False
        self.opening = True
        self.label = f"Camera {index}"
        self.fps = DEFAULT_FPS
        self.mode = "Camera"
        self.identifier = str(index)
        self.latest_frame = None
        self.frame_sequence = 0
        self.software_control_enabled = software_control_enabled
        self.auto_enabled = auto_enabled
        self.manual_exposure = manual_exposure
        self.manual_shutter = manual_shutter
        self.thread = Thread(target=self._run, args=(index,), daemon=True)
        self.thread.start()

    # 背景 thread 主迴圈
    def _run(self, index: int) -> None:
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not capture.isOpened():
            capture.release()
            self.open_failed = True
            self.opening = False
            return

        fps = float(capture.get(cv2.CAP_PROP_FPS))
        with self.lock:
            self.capture = capture
            self.fps = fps if fps > 0 else DEFAULT_FPS
            self.opening = False
        self._apply_camera_mode(capture)

        while not self.stop_event.is_set():
            self._process_commands(capture)
            ok, frame = capture.read()
            if not ok or frame is None:
                self.open_failed = True
                break
            with self.lock:
                self.latest_frame = frame
                self.frame_sequence += 1

        capture.release()
        with self.lock:
            if self.capture is capture:
                self.capture = None

    # 處理 UI thread 送來的 camera 設定命令
    def _process_commands(self, capture: cv2.VideoCapture) -> None:
        while True:
            try:
                command = self.command_queue.get_nowait()
            except Empty:
                return

            name = command[0]
            if name == "software":
                self.software_control_enabled = command[1]
                self._apply_camera_mode(capture)
            elif name == "auto":
                self.auto_enabled = command[1]
                self._apply_camera_mode(capture)
            elif name == "manual":
                _, property_id, value = command
                if property_id == CAMERA_EXPOSURE_PROPERTY:
                    self.manual_exposure = value
                elif property_id == CAMERA_SHUTTER_PROPERTY:
                    self.manual_shutter = value
                self.auto_enabled = False
                self._apply_manual_control(capture)
            elif name == "restore_auto":
                self.software_control_enabled = False
                self.auto_enabled = True
                self._apply_driver_auto(capture)

    # 依目前模式套用 camera 控制
    def _apply_camera_mode(self, capture: cv2.VideoCapture) -> None:
        if not self.software_control_enabled:
            self._apply_driver_auto(capture)
            return
        if self.auto_enabled:
            self._apply_driver_auto(capture)
            return
        self._apply_manual_control(capture)

    # 交回 driver 持續 auto
    def _apply_driver_auto(self, capture: cv2.VideoCapture) -> None:
        if CAMERA_AUTO_EXPOSURE_AUTO_VALUE is not None:
            capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, CAMERA_AUTO_EXPOSURE_AUTO_VALUE)

    # 套用軟體手動 gain / shutter
    def _apply_manual_control(self, capture: cv2.VideoCapture) -> None:
        if CAMERA_AUTO_EXPOSURE_VALUE is not None:
            capture.set(cv2.CAP_PROP_AUTO_EXPOSURE, CAMERA_AUTO_EXPOSURE_VALUE)
        capture.set(CAMERA_EXPOSURE_PROPERTY, self.manual_exposure)
        capture.set(CAMERA_SHUTTER_PROPERTY, self.manual_shutter)

    # 送出 software control 切換命令
    def set_software_control(self, enabled: bool) -> None:
        self.command_queue.put(("software", enabled))

    # 送出持續 auto 切換命令
    def set_auto_control(self, enabled: bool) -> None:
        self.command_queue.put(("auto", enabled))

    # 送出手動數值命令
    def set_manual_property(self, property_id: int, value: float) -> None:
        self.command_queue.put(("manual", property_id, value))

    # 解除軟體控制並交回 driver auto
    def restore_camera_auto_exposure(self) -> None:
        self.command_queue.put(("restore_auto",))

    # 取出最新一幀
    def read_latest(self) -> tuple[bool, object | None, int]:
        with self.lock:
            return self.latest_frame is not None, self.latest_frame, self.frame_sequence

    # 判斷 camera 是否正在背景開啟
    def is_opening(self) -> bool:
        return self.opening

    # 判斷 camera 是否可讀
    def is_opened(self) -> bool:
        return self.capture is not None

    # 停止背景讀取並釋放 camera
    def release(self) -> None:
        self.stop_event.set()
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=1.5)
        self.thread = None
        self.stop_event.clear()
        self.capture = None
        self.latest_frame = None
        self.frame_sequence = 0
        self.opening = False
        self.open_failed = False
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
        self.motion_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.match_mode = MATCH_MODE_NONE
        self.template = None

    # 更新 match 使用的影像增強模式
    def set_match_mode(self, mode: str) -> None:
        if self.match_mode == mode:
            return
        self.match_mode = mode

    # 更新 ROI 追蹤搜尋範圍
    def set_search_margin(self, search_margin: int) -> None:
        search_margin = max(1, search_margin)
        if self.search_margin == search_margin:
            return
        self.search_margin = search_margin

    # 更新位移訊號平滑強度
    def set_smooth_strength(self, smooth_strength: float) -> None:
        smooth_strength = max(0.0, min(smooth_strength, 1.0))
        if self.smooth_strength == smooth_strength:
            return
        self.smooth_strength = smooth_strength
        self.smoothed_displacement = None

    # 依 FPS 重設波型長度
    def configure(self, fps: float) -> None:
        max_samples = max(2, int(fps * SIGNAL_WINDOW_SECONDS))
        self.values = [None] * max_samples
        self._clear_values()
        self._clear_tracking_state()

    # ROI 改變時清掉上一段訊號
    def reset(self) -> None:
        self._clear_values()
        self._clear_tracking_state()

    # 清空波型資料
    def _clear_values(self) -> None:
        self.values = [None] * len(self.values)
        self.cursor_index = 0

    # 清空 ROI 追蹤狀態
    def _clear_tracking_state(self) -> None:
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
        self._clear_values()
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
        return cv2.morphologyEx(blurred, cv2.MORPH_GRADIENT, self.motion_kernel)

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
        return self.values

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
        peak_lifetime_seconds: float,
    ) -> None:
        self.threshold_percent = threshold_percent
        self.max_value = max(MOTION_MAX_EFFECTIVE_MIN, max_value)
        self.average_count = max(1, average_count)
        self.min_trigger_interval = max(0.0, min_trigger_interval_ms / 1000)
        self.peak_lifetime = max(self.min_trigger_interval, peak_lifetime_seconds)
        self.peak_times: deque[float] = deque(maxlen=self.average_count + 1)
        self.was_above_threshold = False

    # 修改 threshold 時保留已經累積的 peak
    def set_threshold_percent(self, threshold_percent: int) -> None:
        self.threshold_percent = threshold_percent
        self.was_above_threshold = False

    # 修改 Max 時保留已經累積的 peak
    def set_max_value(self, max_value: float) -> None:
        self.max_value = max(MOTION_MAX_EFFECTIVE_MIN, max_value)
        self.was_above_threshold = False

    # 修改最短觸發間隔
    def set_min_trigger_interval_ms(self, interval_ms: int) -> None:
        self.min_trigger_interval = max(0.0, interval_ms / 1000)
        self.peak_lifetime = max(self.min_trigger_interval, self.peak_lifetime)
        self.reset()

    # 清除目前呼吸計數狀態
    def reset(self) -> None:
        self.peak_times.clear()
        self.was_above_threshold = False

    # 更新位移值，突破後回到 threshold 下方算一次呼吸
    def update(self, value: float, timestamp: float) -> tuple[float | None, bool]:
        self._drop_expired_peaks(timestamp)
        threshold = self._threshold_value()
        breath_detected = False
        if value > threshold:
            self.was_above_threshold = True
            return self.rpm(timestamp), breath_detected

        if self.was_above_threshold and value < threshold:
            if self.peak_times and timestamp - self.peak_times[-1] < self.min_trigger_interval:
                self.was_above_threshold = False
                return self.rpm(timestamp), breath_detected
            self.peak_times.append(timestamp)
            self.was_above_threshold = False
            breath_detected = True

        return self.rpm(timestamp), breath_detected

    # 將百分比 threshold 轉成 0 到 Max 之間的實際位移值
    def _threshold_value(self) -> float:
        return self.max_value * (self.threshold_percent / 100)

    # 清掉已經不可靠的舊 peak
    def _drop_expired_peaks(self, timestamp: float) -> None:
        oldest_alive = timestamp - self.peak_lifetime
        while self.peak_times and self.peak_times[0] < oldest_alive:
            self.peak_times.popleft()

    # 以仍存活的相鄰 peak 間隔計算 RPM
    def rpm(self, timestamp: float | None = None) -> float | None:
        if timestamp is not None:
            self._drop_expired_peaks(timestamp)
        if len(self.peak_times) < 2:
            return None

        intervals = [
            current - previous
            for previous, current in zip(self.peak_times, list(self.peak_times)[1:])
        ]
        if not intervals:
            return None

        average_interval = sum(intervals) / len(intervals)
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
    bytes_per_line = 3 * width
    image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
    return image.copy()


# 主程式控制器
class MonitorController:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.window = MonitorWindow(DEFAULT_CAMERA_INDEXES, APP_TITLE)
        self.motion_max_limit = MOTION_MAX_MAX
        self.window.set_threshold_range(THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_DEFAULT)
        self.window.set_gain_range(
            self.motion_max_to_slider_value(self.motion_max_limit),
            self.motion_max_to_slider_value(MOTION_MAX_MIN),
            self.motion_max_to_slider_value(MOTION_MAX_DEFAULT),
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
        self.source = CaptureSource()
        self.camera_worker = CameraWorker()
        self.tracker = RoiTracker()
        self.tracker.set_search_margin(DETECTION_RANGE_DEFAULT)
        self.tracker.set_smooth_strength(SMOOTH_DEFAULT)
        self.breath_detector = BreathRateDetector(
            THRESHOLD_DEFAULT,
            MOTION_MAX_DEFAULT,
            RPM_AVERAGE_BREATH_COUNT,
            BREATH_MIN_TRIGGER_INTERVAL_MS,
            BREATH_PEAK_LIFETIME_SECONDS,
        )
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.use_software_camera_control = SOFTWARE_CAMERA_CONTROL_DEFAULT
        self.camera_auto_enabled = CAMERA_AUTO_DEFAULT
        self.manual_exposure_value = CAMERA_MANUAL_EXPOSURE_DEFAULT
        self.manual_shutter_value = CAMERA_MANUAL_SHUTTER_DEFAULT
        self.last_camera_frame_sequence = 0
        self.playing = False
        self.roi: Roi | None = None
        self.last_frame = None
        self.current_motion = 0.0
        self.next_detection_time = 0.0
        self.selected_video_path: Path | None = None
        self.muted = False
        self.beep_frequency_hz = BEEP_FREQUENCY_HZ
        self.detection_rate_hz = DETECTION_RATE_DEFAULT_HZ
        self.camera_settings_connected = False
        self.delete_roi_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.window)
        self.delete_roi_shortcut.activated.connect(self.clear_roi_when_paused)
        self.apply_topmost()
        self._connect_events()

    # 綁定 GUI 事件
    def _connect_events(self) -> None:
        self.window.load_mode_menu.currentTextChanged.connect(self.change_load_mode)
        self.window.open_video_button.clicked.connect(self.open_video)
        self.window.scan_camera_button.clicked.connect(self.scan_cameras)
        self.window.play_button.clicked.connect(self.toggle_play)
        self.window.fit_button.clicked.connect(self.fit_video_to_window)
        self.window.camera_settings_button.clicked.connect(self.show_camera_settings)
        self.window.mute_button.clicked.connect(self.toggle_mute)
        self.window.topmost_check.clicked.connect(self.toggle_topmost)
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

    # 將 Max 小數值轉成目前 Gain factor 下的反向拉桿刻度
    def motion_max_to_slider_value(self, value: float) -> int:
        max_value = max(MOTION_MAX_MIN, min(value, self.motion_max_limit))
        gain_value = self.motion_max_limit - max_value + MOTION_MAX_MIN
        return round(gain_value * MOTION_MAX_SCALE)

    # 將 Gain 反向拉桿刻度轉回目前 Gain factor 下的 Max 小數值
    def slider_value_to_motion_max(self, value: int) -> float:
        gain_value = value / MOTION_MAX_SCALE
        return max(MOTION_MAX_EFFECTIVE_MIN, self.motion_max_limit - gain_value + MOTION_MAX_MIN)

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
        self.source.release()
        self.camera_worker.open_camera(
            index,
            self.use_software_camera_control,
            self.camera_auto_enabled,
            self.manual_exposure_value,
            self.manual_shutter_value,
        )
        self._reset_for_camera_source(index, playing=True)
        self.window.set_status(with_view_hint(f"Opening Camera {index} in background..."))
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
        self.window.set_status(f"Threshold set to {value}%.", pulse=True)

    # 更新示波器 Gain
    def change_gain(self, value: int) -> None:
        max_value = self.slider_value_to_motion_max(value)
        self.window.set_gain(max_value)
        self.breath_detector.set_max_value(max_value)
        self.window.set_status(f"Waveform max set to {max_value:.2f}.", pulse=True)

    # 更新位移訊號平滑強度
    def change_smooth(self, value: int) -> None:
        smooth_strength = slider_value_to_smooth(value)
        self.window.set_smooth(smooth_strength)
        self.tracker.set_smooth_strength(smooth_strength)
        self.window.set_status(f"Smooth set to {smooth_strength:.2f}.", pulse=True)

    # 更新 Sens 搜尋範圍
    def change_sens(self, value: int) -> None:
        self.window.set_sens(value)
        self.tracker.set_search_margin(value)
        self.window.set_status(f"Range set to {value} px.", pulse=True)

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

    # 只讓影像符合目前視窗
    def fit_video_to_window(self) -> None:
        self.window.video.fit_to_window()
        self.window.set_status(with_view_hint("Video fit to window."))

    # 顯示 setting 小視窗
    def show_camera_settings(self) -> None:
        dialog = self.window.show_camera_settings()
        if not self.camera_settings_connected:
            dialog.exposure_changed.connect(self.change_camera_exposure)
            dialog.shutter_changed.connect(self.change_camera_shutter)
            dialog.detect_rate_changed.connect(self.change_detection_rate)
            dialog.beep_frequency_changed.connect(self.change_beep_frequency)
            dialog.gain_factor_changed.connect(self.change_gain_factor)
            dialog.camera_auto_changed.connect(self.change_camera_auto_control)
            dialog.camera_reset_requested.connect(self.reset_camera_firmware_control)
            dialog.software_control_changed.connect(self.change_software_camera_control)
            dialog.roi_reset_requested.connect(self.clear_roi)
            dialog.panel_reset_requested.connect(self.reset_layout)
            dialog.adjustment_reset_requested.connect(self.reset_settings)
            self.camera_settings_connected = True
        dialog.set_software_control_enabled(self.use_software_camera_control)
        dialog.set_camera_auto_enabled(self.camera_auto_enabled)
        dialog.set_exposure_value(self.manual_exposure_value)
        dialog.set_shutter_value(self.manual_shutter_value)
        dialog.reset_adjustments(self.detection_rate_hz, self.beep_frequency_hz, self.motion_max_limit)

    # 切換是否允許 CV2 介入 camera 設定
    def change_software_camera_control(self, enabled: bool) -> None:
        self.use_software_camera_control = enabled
        if enabled:
            self.camera_auto_enabled = False
            self.manual_exposure_value = CAMERA_MANUAL_EXPOSURE_DEFAULT
            self.manual_shutter_value = CAMERA_MANUAL_SHUTTER_DEFAULT
            dialog = self.window.camera_settings_dialog
            if dialog is not None:
                dialog.set_camera_auto_enabled(False)
                dialog.set_exposure_value(self.manual_exposure_value)
                dialog.set_shutter_value(self.manual_shutter_value)
            self.camera_worker.set_software_control(True)
            self.camera_worker.set_manual_property(CAMERA_EXPOSURE_PROPERTY, self.manual_exposure_value)
            self.camera_worker.set_manual_property(CAMERA_SHUTTER_PROPERTY, self.manual_shutter_value)
            self.window.set_status(
                f"Software camera control enabled: Exposure {self.manual_exposure_value:.2f}, "
                f"Shutter {self.manual_shutter_value:.2f}."
            )
            return

        self.camera_auto_enabled = False
        dialog = self.window.camera_settings_dialog
        if dialog is not None:
            dialog.set_camera_auto_enabled(False)
        self.camera_worker.restore_camera_auto_exposure()
        if self.source.mode == "Camera":
            self.source.restore_camera_auto_exposure()
        self.window.set_status("Software camera control disabled. Camera auto restored.")

    # 即時更新相機曝光增益
    def change_camera_exposure(self, value: float) -> None:
        self.change_camera_property(CAMERA_EXPOSURE_PROPERTY, value, "Exposure")

    # 即時更新相機快門/曝光時間
    def change_camera_shutter(self, value: float) -> None:
        self.change_camera_property(CAMERA_SHUTTER_PROPERTY, value, "Shutter")

    # 套用 Setting 小視窗的相機控制值
    def change_camera_property(self, property_id: int, value: float, label: str) -> None:
        if not self.use_software_camera_control:
            self.window.set_status("Enable software camera control before changing camera settings.")
            return
        self.camera_auto_enabled = False
        if property_id == CAMERA_EXPOSURE_PROPERTY:
            self.manual_exposure_value = value
        elif property_id == CAMERA_SHUTTER_PROPERTY:
            self.manual_shutter_value = value
        dialog = self.window.camera_settings_dialog
        if dialog is not None:
            dialog.set_camera_auto_enabled(False)
        if self.camera_worker.mode == "Camera":
            self.camera_worker.set_manual_property(property_id, value)
            self.window.set_status(f"{label} set to {value:.2f}.")
        elif self.source.set_camera_property(property_id, value):
            self.window.set_status(f"{label} set to {value:.2f}.")
        else:
            self.window.set_status(f"{label} setting is not available for the current camera.")

    # 切換持續 auto 控制
    def change_camera_auto_control(self, enabled: bool) -> None:
        if not self.use_software_camera_control:
            self.window.set_status("Enable software camera control before using camera auto.")
            return
        self.camera_auto_enabled = enabled
        if self.camera_worker.mode == "Camera":
            self.camera_worker.set_auto_control(enabled)
            if not enabled:
                self.camera_worker.set_manual_property(CAMERA_EXPOSURE_PROPERTY, self.manual_exposure_value)
                self.camera_worker.set_manual_property(CAMERA_SHUTTER_PROPERTY, self.manual_shutter_value)
            self.window.set_status("Camera continuous auto enabled." if enabled else "Camera manual control enabled.")
            return
        if self.source.mode == "Camera":
            value = CAMERA_AUTO_EXPOSURE_AUTO_VALUE if enabled else CAMERA_AUTO_EXPOSURE_VALUE
            if value is not None:
                self.source.set_camera_property(cv2.CAP_PROP_AUTO_EXPOSURE, value)
        self.window.set_status("Camera continuous auto enabled." if enabled else "Camera manual control enabled.")

    # 重開 camera，讓韌體回到未被 CV2 設定介入的狀態
    def reset_camera_firmware_control(self) -> None:
        self.manual_exposure_value = CAMERA_MANUAL_EXPOSURE_DEFAULT
        self.manual_shutter_value = CAMERA_MANUAL_SHUTTER_DEFAULT
        dialog = self.window.camera_settings_dialog
        if dialog is not None:
            dialog.set_software_control_enabled(self.use_software_camera_control)
            dialog.set_camera_auto_enabled(self.camera_auto_enabled)
            dialog.set_exposure_value(CAMERA_MANUAL_EXPOSURE_DEFAULT)
            dialog.set_shutter_value(CAMERA_MANUAL_SHUTTER_DEFAULT)
        self.camera_worker.restore_camera_auto_exposure()
        if self.camera_worker.mode != "Camera" and self.source.mode != "Camera":
            self.window.set_status("Camera reset is available only in Camera mode.")
            return

        was_playing = self.playing
        identifier = self.camera_worker.identifier or self.source.identifier or self.window.camera_menu.currentData() or 0
        index = int(identifier)
        self.timer.stop()
        self.camera_worker.restore_camera_auto_exposure()
        self.camera_worker.open_camera(
            index,
            self.use_software_camera_control,
            self.camera_auto_enabled,
            self.manual_exposure_value,
            self.manual_shutter_value,
        )
        self.playing = was_playing
        self.current_motion = 0.0
        self.next_detection_time = 0.0
        self.last_camera_frame_sequence = 0
        self.breath_detector.reset()
        self.window.set_playing(was_playing)
        if self.roi is not None:
            self.tracker.reset()
        self.window.video.fit_to_window()
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(None)
        if was_playing:
            self._start_timer()
        self.window.set_status("Camera reset in background.")

    # 還原偵測相關設定
    def reset_settings(self) -> None:
        threshold_value = THRESHOLD_DEFAULT
        self.motion_max_limit = MOTION_MAX_MAX
        gain_value = self.motion_max_to_slider_value(MOTION_MAX_DEFAULT)
        smooth_value = smooth_to_slider_value(SMOOTH_DEFAULT)
        sens_value = DETECTION_RANGE_DEFAULT

        dialog = self.window.camera_settings_dialog
        if dialog is not None:
            dialog.reset_adjustments(DETECTION_RATE_DEFAULT_HZ, BEEP_FREQUENCY_HZ, self.motion_max_limit)
        self.window.threshold_slider.setValue(threshold_value)
        self.window.set_gain_range(
            self.motion_max_to_slider_value(self.motion_max_limit),
            self.motion_max_to_slider_value(MOTION_MAX_MIN),
            gain_value,
            MOTION_MAX_DEFAULT,
        )
        self.window.gain_slider.setValue(gain_value)
        self.window.smooth_slider.setValue(smooth_value)
        self.window.sens_slider.setValue(sens_value)
        self.change_detection_rate(DETECTION_RATE_DEFAULT_HZ)
        self.change_beep_frequency(BEEP_FREQUENCY_HZ)
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

    # 更新 Gain factor 並重建右側 Gain slider 範圍
    def change_gain_factor(self, value: float) -> None:
        self.motion_max_limit = max(MOTION_MAX_EFFECTIVE_MIN, value)
        current_max = max(MOTION_MAX_EFFECTIVE_MIN, min(self.breath_detector.max_value, self.motion_max_limit))
        self.window.gain_slider.blockSignals(True)
        self.window.set_gain_range(
            self.motion_max_to_slider_value(self.motion_max_limit),
            self.motion_max_to_slider_value(MOTION_MAX_MIN),
            self.motion_max_to_slider_value(current_max),
            current_max,
        )
        self.window.gain_slider.blockSignals(False)
        self.breath_detector.set_max_value(current_max)
        self.window.set_status(f"Gain factor set to {self.motion_max_limit:.2f}.")

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
            self.breath_detector.reset()
            self.window.set_rpm(None)
            self.window.set_status(with_view_hint("Playing. The waveform updates after an ROI is set."))
            self._start_timer()
        else:
            self.timer.stop()
            self.breath_detector.reset()
            self.window.set_status(with_view_hint(f"Paused. Drag on the video to draw an ROI. {ROI_DELETE_HINT}"))

    # 判斷是否需要開啟或切換相機
    def _should_open_selected_camera(self) -> bool:
        index = str(self.window.camera_menu.currentData() or 0)
        return self.camera_worker.mode != "Camera" or self.camera_worker.identifier != index

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

    # 暫停時用 Del 清除目前 ROI
    def clear_roi_when_paused(self) -> None:
        if self.playing:
            return
        if self.roi is None:
            self.window.set_status("No ROI to clear.")
            return
        self.clear_roi()

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

    # camera 背景來源啟動時重置狀態
    def _reset_for_camera_source(self, index: int, playing: bool) -> None:
        self.playing = playing
        self.roi = None
        self.last_frame = None
        self.current_motion = 0.0
        self.tracker.configure(DEFAULT_FPS)
        self.breath_detector.reset()
        self.next_detection_time = 0.0
        self.last_camera_frame_sequence = 0
        self.window.set_playing(playing)
        self.window.video.set_roi(None)
        self.window.video.set_tracking_centers(None, None)
        self.window.video.set_status(f"Camera {index}|Enhance: None|FPS: {format_fps(DEFAULT_FPS)}|Motion: 0.00")
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
        self.camera_worker.release()
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
        fps = self.camera_worker.fps if self.camera_worker.mode == "Camera" else self.source.fps
        interval = max(10, int(1000 / fps))
        self.timer.start(interval)

    # 更新影像與波型
    def update_frame(self) -> None:
        if not self.playing:
            return

        if self.camera_worker.mode == "Camera":
            self.update_camera_frame()
            return

        if self.source.capture is None:
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

    # 從背景 camera worker 取最新影格
    def update_camera_frame(self) -> None:
        if self.camera_worker.open_failed:
            self.timer.stop()
            self.playing = False
            self.window.set_playing(False)
            self.camera_worker.release()
            self.window.set_status("Camera source was disconnected or failed to open.")
            return

        ok, frame, sequence = self.camera_worker.read_latest()
        if not ok or frame is None or sequence == self.last_camera_frame_sequence:
            return

        self.last_camera_frame_sequence = sequence
        if self.camera_worker.fps != self.source.fps:
            self.source.fps = self.camera_worker.fps
            if self.timer.isActive():
                self._start_timer()
        self.source.label = self.camera_worker.label
        self.source.mode = self.camera_worker.mode
        self.source.identifier = self.camera_worker.identifier
        self.last_frame = frame
        self.process_frame_analysis(frame)
        self._display_frame(frame)

    # 依目前 ROI 更新追蹤與呼吸訊號
    def process_frame_analysis(self, frame) -> None:
        now = perf_counter()
        if self.roi is None or now < self.next_detection_time:
            return

        detection_interval = 1 / max(1, self.detection_rate_hz)
        self.next_detection_time = now + detection_interval
        tracked_roi, displacement = self.tracker.update(frame)
        if tracked_roi is None:
            return

        self.roi = tracked_roi
        self.current_motion = displacement
        rpm, breath_detected = self.breath_detector.update(displacement, now)
        if breath_detected:
            self._play_peak_beep()
        self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
        self.window.set_rpm(rpm)

    # 將目前影格送到 GUI
    def _display_frame(self, frame) -> None:
        display_frame = (
            frame if self.window.show_raw_check.isChecked()
            else self._enhance_display_frame(frame)
        )
        image = frame_to_qimage(display_frame)
        frame_size = (frame.shape[1], frame.shape[0])
        self.window.video.set_frame_state(
            image,
            frame_size,
            self.roi.as_tuple() if self.roi is not None else None,
            self.tracker.reference_center,
            self.tracker.current_center(),
            self._video_status_text(),
        )

    # 組合影片區左上角狀態標題
    def _video_status_text(self) -> str:
        enhance_mode = self.window.enhancement_menu.currentData() or self.window.enhancement_menu.currentText()
        enhance_text = f"Enhance: {enhance_mode}"
        label = self.camera_worker.label if self.camera_worker.mode == "Camera" else self.source.label
        fps = self.camera_worker.fps if self.camera_worker.mode == "Camera" else self.source.fps
        fps_text = format_fps(fps)
        return (
            f"{label}|{enhance_text}|"
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
        self.camera_worker.release()
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
