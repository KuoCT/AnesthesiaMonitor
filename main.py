from __future__ import annotations

import sys
from collections import deque
from dataclasses import dataclass
from math import hypot
from pathlib import Path
from time import perf_counter

import cv2
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog

from GUI import MonitorWindow


# 參數控制區
DEFAULT_CAMERA_INDEXES = tuple(range(6)) # 第一版先列出常見 camera index
DEFAULT_FPS = 30.0 # 攝影機或影片讀不到 FPS 時使用
SIGNAL_WINDOW_SECONDS = 10.0 # 波型顯示最近幾秒
MIN_ROI_SIZE = 8 # ROI 太小通常是誤畫
TRACK_SEARCH_MARGIN = 80 # ROI 追蹤時在上一個位置周圍搜尋的像素範圍
DETECTION_RATE_HZ = 60 # 每秒執行幾次 ROI 追蹤與呼吸偵測
RPM_AVERAGE_BREATH_COUNT = 2 # 使用最近幾次呼吸間隔計算平均 RPM
THRESHOLD_MIN = 0 # threshold 拉桿最小百分比
THRESHOLD_MAX = 100 # threshold 拉桿最大百分比
THRESHOLD_DEFAULT = 50 # threshold 拉桿預設百分比


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
        self.template = None

    # 依 FPS 重設波型長度
    def configure(self, fps: float) -> None:
        max_samples = max(2, int(fps * SIGNAL_WINDOW_SECONDS))
        self.values = [None] * max_samples
        self.cursor_index = 0
        self.reference_roi = None
        self.current_roi = None
        self.reference_center = None
        self.template = None

    # ROI 改變時清掉上一段訊號
    def reset(self) -> None:
        self.values = [None] * len(self.values)
        self.cursor_index = 0
        self.reference_roi = None
        self.current_roi = None
        self.reference_center = None
        self.template = None

    # 用目前畫面建立追蹤模板
    def set_reference(self, frame, roi: Roi) -> None:
        frame_height, frame_width = frame.shape[:2]
        roi = roi.clamp(frame_width, frame_height)
        roi_frame = frame[roi.y : roi.y + roi.height, roi.x : roi.x + roi.width]
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        self.reference_roi = roi
        self.current_roi = roi
        self.reference_center = roi.center()
        self.template = gray
        self.values = [None] * len(self.values)
        self.cursor_index = 0

    # 更新單幀 ROI 位置與位移訊號
    def update(self, frame) -> tuple[Roi | None, float]:
        if self.template is None or self.current_roi is None or self.reference_center is None:
            return None, 0.0

        frame_height, frame_width = frame.shape[:2]
        search_left = max(0, self.current_roi.x - TRACK_SEARCH_MARGIN)
        search_top = max(0, self.current_roi.y - TRACK_SEARCH_MARGIN)
        search_right = min(frame_width, self.current_roi.x + self.current_roi.width + TRACK_SEARCH_MARGIN)
        search_bottom = min(frame_height, self.current_roi.y + self.current_roi.height + TRACK_SEARCH_MARGIN)
        search_frame = frame[search_top:search_bottom, search_left:search_right]

        if search_frame.shape[0] < self.template.shape[0] or search_frame.shape[1] < self.template.shape[1]:
            return self.current_roi, self._append_displacement(self.current_roi)

        search_gray = cv2.cvtColor(search_frame, cv2.COLOR_BGR2GRAY)
        search_gray = cv2.GaussianBlur(search_gray, (5, 5), 0)
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

    # 將目前中心到初始中心的線長加入波型
    def _append_displacement(self, roi: Roi) -> float:
        if self.reference_center is None:
            return 0.0

        center_x, center_y = roi.center()
        reference_x, reference_y = self.reference_center
        displacement = hypot(center_x - reference_x, center_y - reference_y)
        self.values[self.cursor_index] = displacement
        self.cursor_index = (self.cursor_index + 1) % len(self.values)
        return displacement

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
    def __init__(self, threshold_percent: int, average_count: int) -> None:
        self.threshold_percent = threshold_percent
        self.intervals: deque[float] = deque(maxlen=average_count)
        self.was_above_threshold = False
        self.last_breath_time: float | None = None

    # 修改 threshold 時重置狀態，避免舊 crossing 污染
    def set_threshold_percent(self, threshold_percent: int) -> None:
        self.threshold_percent = threshold_percent
        self.reset()

    # 清除目前呼吸計數狀態
    def reset(self) -> None:
        self.intervals.clear()
        self.was_above_threshold = False
        self.last_breath_time = None

    # 更新位移值，突破後回到 threshold 下方算一次呼吸
    def update(self, value: float, values: list[float | None], timestamp: float) -> float | None:
        threshold = self._threshold_value(values)
        if threshold is None:
            return None

        if value > threshold:
            self.was_above_threshold = True
            return self.rpm()

        if self.was_above_threshold and value < threshold:
            if self.last_breath_time is not None:
                interval = timestamp - self.last_breath_time
                if interval > 0:
                    self.intervals.append(interval)
            self.last_breath_time = timestamp
            self.was_above_threshold = False

        return self.rpm()

    # 將百分比 threshold 轉成目前波型範圍內的實際位移值
    def _threshold_value(self, values: list[float | None]) -> float | None:
        valid_values = [value for value in values if value is not None]
        if len(valid_values) < 2:
            return None

        minimum = min(valid_values)
        maximum = max(valid_values)
        if maximum <= minimum:
            return None

        return minimum + (maximum - minimum) * (self.threshold_percent / 100)

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
    height, width = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    bytes_per_line = 3 * width
    image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return image.copy()


# 主程式控制器
class MonitorController:
    def __init__(self) -> None:
        self.app = QApplication(sys.argv)
        self.window = MonitorWindow(DEFAULT_CAMERA_INDEXES)
        self.window.set_threshold_range(THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_DEFAULT)
        self.source = CaptureSource()
        self.tracker = RoiTracker()
        self.breath_detector = BreathRateDetector(THRESHOLD_DEFAULT, RPM_AVERAGE_BREATH_COUNT)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.playing = False
        self.roi: Roi | None = None
        self.last_frame = None
        self.current_motion = 0.0
        self.next_detection_time = 0.0
        self.selected_video_path: Path | None = None
        self._connect_events()

    # 綁定 GUI 事件
    def _connect_events(self) -> None:
        self.window.load_mode_menu.currentTextChanged.connect(self.change_load_mode)
        self.window.open_video_button.clicked.connect(self.open_video)
        self.window.scan_camera_button.clicked.connect(self.scan_cameras)
        self.window.play_button.clicked.connect(self.toggle_play)
        self.window.clear_roi_button.clicked.connect(self.clear_roi)
        self.window.reset_layout_button.clicked.connect(self.reset_layout)
        self.window.threshold_slider.valueChanged.connect(self.change_threshold)
        self.window.video.roi_selected.connect(self.set_roi)
        self.window.video.edit_rejected.connect(self.window.set_status)
        self.app.aboutToQuit.connect(self.close)

    # 切換載入模式
    def change_load_mode(self, mode: str) -> None:
        self._stop_current_source()
        self.window.set_load_mode(mode)
        if mode == "Camera":
            self.window.set_status("Camera mode selected. Press Play to open the selected camera.")
        else:
            if self.selected_video_path is None:
                self.window.set_status("Video mode selected. Open a video file to begin.")
            else:
                self.window.set_status(f"Video mode selected: {self.selected_video_path.name}. Press Play to start.")

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
        self.window.set_status(f"Video loaded: {self.source.label}. Press Play to start.")

    # 開啟目前選到的攝影機
    def open_camera(self) -> bool:
        index = int(self.window.camera_menu.currentText())
        if not self.source.open_camera(index):
            self.window.set_status(f"Unable to open Camera {index}.")
            return False

        self._reset_for_loaded_source(playing=True)
        self.window.set_status(f"Camera opened: Camera {index}")
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

    # 還原 layout 比例並讓影像符合視窗
    def reset_layout(self) -> None:
        self.window.apply_default_splitter_sizes()
        self.window.video.fit_to_window()
        self.window.set_status("Layout reset. Video fit to window.")

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
            self.window.set_status("Playing. The waveform updates after an ROI is set.")
            self._start_timer()
        else:
            self.timer.stop()
            self.window.set_status("Paused. Drag on the video to draw an ROI.")

    # 判斷是否需要開啟或切換相機
    def _should_open_selected_camera(self) -> bool:
        index = self.window.camera_menu.currentText()
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
        self.window.set_status("Playing. The waveform updates after an ROI is set.")
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
        self.window.set_status("ROI set. Press Play to start updating the waveform.")

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
        self.window.video.set_status(self.source.label, self.current_motion)
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
        self.window.video.set_status("No source", self.current_motion)
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
            detection_interval = 1 / max(1, DETECTION_RATE_HZ)
            self.next_detection_time = now + detection_interval
            tracked_roi, displacement = self.tracker.update(frame)
            if tracked_roi is not None:
                self.roi = tracked_roi
                self.current_motion = displacement
                rpm = self.breath_detector.update(displacement, self.tracker.series(), now)
                self.window.waveform.set_values(self.tracker.series(), self.tracker.cursor())
                self.window.set_rpm(rpm)

        self._display_frame(frame)

    # 將目前影格送到 GUI
    def _display_frame(self, frame) -> None:
        image = frame_to_qimage(frame)
        frame_size = (frame.shape[1], frame.shape[0])
        self.window.video.set_frame(image, frame_size)
        self.window.video.set_roi(self.roi.as_tuple() if self.roi is not None else None)
        self.window.video.set_tracking_centers(self.tracker.reference_center, self.tracker.current_center())
        self.window.video.set_status(self.source.label, self.current_motion)

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
