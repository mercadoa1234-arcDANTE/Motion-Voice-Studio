# Browser-assisted rendering

Browser assist is a first-class path, not an afterthought. Use it whenever the sandbox is too constrained for the requested visual quality.

## When to use browser assist

- The user asked for browser/GPU rendering.
- PyVista/ModernGL cannot run in the sandbox.
- The asset is large or the user has better GPU hardware.
- The user wants to inspect the animation interactively.
- Final render needs WebGL/WebGPU materials or custom browser capture.

## Output packet

Generate:

```txt
browser/<basename>_render.html
browser/RETURN_FILES.md
outputs/geometry/<basename>.stl or embedded mesh data
outputs/audio/full_mix.wav or embedded base64 audio
outputs/reports/mesh_report.json
```

The HTML should include:

- Canvas preview.
- Play/pause controls.
- Record button.
- Download `.webm` button.
- Render settings: resolution scale, FPS, quality.
- Camera path and scene names.
- Return-file checklist.

## User instructions template

```md
Open `<basename>_render.html` in a desktop browser.
Click **Play** to preview.
Click **Record** and let the full animation finish.
Save the downloaded `.webm`.
Upload the `.webm` back here. Also upload screenshots if something looks wrong.
```

## Return files

Ask for only what is needed:

| Situation | Return |
|---|---|
| Browser record includes video + audio | `.webm` |
| Browser record is silent | `.webm` plus generated audio remains in sandbox |
| Browser cannot record | Frame sequence zip or screenshots |
| User reports issue | Screenshot plus browser name/version and GPU if available |

## Browser render caveats

- MediaRecorder often outputs WebM/VP8/VP9/Opus. Convert to MP4 in the sandbox with ffmpeg.
- Some browsers do not allow autoplay with audio. Include a manual click start.
- Audio capture from an `<audio>` element may require user interaction.
- Canvas capture FPS can vary under load. Check duration after return.
- If final timing is critical, prefer frame-sequence capture over real-time MediaRecorder.

## Quality controls for low VRAM/integrated GPUs

Expose:

- Resolution scale: 0.5, 0.75, 1.0.
- MSAA/FXAA toggle.
- Shadow toggle.
- Material complexity: flat, shaded, PBR-like.
- Frame capture mode: realtime recording vs deterministic frame step.

## GlowScript/VPython pattern

Use Web VPython/GlowScript for simple mechanism/physics animations. Keep imported CAD out of this path unless the CAD can be approximated with primitives.

Good examples:

- Gear ratio demo.
- Force arrows on a bracket.
- Piston/linkage motion.
- Assembly order with boxes/cylinders.

Poor examples:

- Exact complex STEP import.
- Photorealistic product render.
- Material-accurate metal/plastic visualization.
