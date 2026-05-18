# Troubleshooting

## Geometry

| Symptom | Likely cause | Fix |
|---|---|---|
| Part is tiny or huge | Unit mismatch | Confirm `units`; rescale mesh; regenerate report. |
| STL has no volume | Open surface or non-watertight mesh | Repair only if needed; prefer fixing CAD source. |
| Holes disappear | Mesh decimation or bad boolean | Render from higher-resolution mesh; inspect CAD source. |
| STEP export missing | Source is mesh/SCAD only or build123d export failed | Return source plus STL; state STEP limitation. |
| Exploded view moves wrong part | Components not named | Split assembly into named exports or map mesh groups. |

## Audio

| Symptom | Likely cause | Fix |
|---|---|---|
| No narration audio | TTS unavailable | Use `espeak-ng`, external command, browser speech, or silent timing. |
| Audio duration wrong | Cached old WAV or browser capture drift | Delete affected scene audio and regenerate; check with ffprobe. |
| Clipping | TTS output too loud or mux gain | Normalize in `generate_audio.py` or lower gain in `mux.py`. |
| Robotic voice | OS fallback TTS | Use supplied neural TTS assets or user-provided narration. |

## Rendering

| Symptom | Likely cause | Fix |
|---|---|---|
| PyVista fails headless | Missing EGL/OSMesa/display | Use software fallback or browser-assist. |
| ModernGL cannot create context | No OpenGL context | Use browser WebGL/WebGPU or PyVista/software path. |
| Browser record is black | Browser blocked WebGL/canvas capture or shader failed | Try another browser, disable hardware acceleration toggle, or return screenshots/logs. |
| Browser audio missing | Audio capture requires user click or unsupported `captureStream` | Mux sandbox WAV onto returned silent WebM/MP4. |
| Video duration drifts | MediaRecorder real-time timing variability | Convert with ffmpeg; for strict timing use frame sequence capture. |

## Hunyuan3D / AI mesh

| Symptom | Likely cause | Fix |
|---|---|---|
| VRAM OOM during texture | Texture pipeline exceeds GPU | Shape-only local, texture remote/cloud, lower resolution. |
| Mesh is not dimensionally useful | Generative mesh is not CAD | Rebuild engineered geometry in build123d. |
| Organic mesh too heavy | High polygon output | Decimate, bake normals, or use it only in close-up. |

## Final video

| Symptom | Likely cause | Fix |
|---|---|---|
| Final MP4 has no audio | Mux used silent input or wrong stream map | Re-run `mux.py` with explicit audio path. |
| Final MP4 will not play | Codec/container issue | Re-encode H.264/AAC with ffmpeg. |
| Labels unreadable | Camera/resolution/material contrast | Increase label size, simplify camera, or use cutaway/callout focus. |
