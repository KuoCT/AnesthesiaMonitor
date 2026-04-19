# Anesthesia Monitor

Anesthesia Monitor is a desktop app for monitoring the respiration rate of anesthetized mice inside a dark chamber. It reads video from an infrared camera or a video file, lets the user select an ROI on the animal, and estimates respiration rate in RPM by tracking small motion in that region.

The UI is built with PySide6, and video capture and image processing are handled with OpenCV.

## Requirements

- Windows
- Python 3.14
- uv
- An infrared camera, or a video file for testing

## Installation

Run this command from the project directory:

```powershell
uv sync
```

`uv sync` creates the `.venv` environment from `pyproject.toml` and `uv.lock`, then installs the required dependencies such as PySide6 and OpenCV.

## Launching

For development or testing, run:

```powershell
uv run python main.py
```

On Windows, you can also double-click:

```text
AnesthesiaMonitor.bat
```

The batch file launches the app with `.venv\Scripts\pythonw.exe`, so it does not open an extra command prompt window.

To create a desktop shortcut, run:

```text
CreateDesktopLink.bat
```

## Basic Usage

1. Point the infrared camera at the mouse inside the dark chamber. The best target area is usually the chest, abdomen, or another region that moves regularly with breathing.
2. Start the app. It opens in `Camera` mode by default.
3. Choose a camera index from the camera menu, or click the scan camera button to detect available cameras.
4. Click the play button to open the selected camera and start reading frames.
5. Pause playback, then drag on the video to draw an ROI. Choose an area with clear breathing motion and minimal background noise.
6. Click play again. The app tracks ROI motion, updates the waveform, and displays the estimated respiration rate in RPM.
7. Use `Thresh.`, `Gain`, `Smooth`, and `Range` to tune detection sensitivity and waveform display.
8. A short beep plays when a breathing peak is detected. Enable `Mute` to turn off the sound.

## Video Mode

To test with a recorded video:

1. Change the mode in the top-left menu to `Video`.
2. Click the open video button and select a video file.
3. Click play.
4. Pause the video, draw an ROI, then play again to start analysis.

## Controls

- Use the mouse wheel to zoom the video.
- Middle-drag to pan the video.
- Pause playback before drawing or adjusting the ROI.
- Press `Del` while paused to clear the current ROI.
- Enable `Show RAW` to display the original frame.
- Use `Enhance` to choose an image enhancement mode for viewing and ROI tracking.
- Open `Setting` to adjust camera exposure, shutter, detection rate, beep frequency, and gain factor.

## Notes

- Camera control support depends on the infrared camera and its driver. If exposure or shutter controls do not respond, the camera driver may not support the corresponding OpenCV property.
- If the ROI is too small or the image is noisy, the RPM estimate may become unstable. Adjust the camera, lighting, ROI position, threshold, and gain as needed.
- This tool is intended as an experimental monitoring aid. Anesthesia depth and animal status should still be assessed by trained personnel according to the relevant experimental protocol.
