# Tool Choice — the long decision tree

Read this when starting any non-trivial CAD or 3D job. The short table is in SKILL.md;
this is the full reasoning.

## 1. Parametric solid modeling

### Use `build123d` when
- The deliverable is a single part or multi-part assembly with mate-quality precision
- You need exact STEP export for downstream CAD interchange
- Booleans must be exact (BREP) — gears, cams, intersecting cylinders
- You'll edit dimensions later and re-build
- The user described the part in terms of "thickness", "tolerance", "fillet", "chamfer", "mate"

**Confirmed working in sandbox.** OCP wheel pulls cleanly. Cold import ~1.5s, first
build ~1s. STEP export is fast (<100 ms for typical parts).

### Use `solidpython2` → emit OpenSCAD when
- The user has existing `.scad` files
- The user has BOSL2 / NopSCADlib / MCAD libraries they want to use
- CSG-only is genuinely simpler: lattices, repeated subtraction, infill patterns
- Output is for 3D-printing community workflows where OpenSCAD is the lingua franca

Note: the openscad binary is NOT in the sandbox by default. `solidpython2` emits .scad
*text*. To render to STL in-sandbox, install openscad (~300 MB) or hand off to user.

### Use `cadquery` only when
- The user explicitly insists on it
- The user provides existing CadQuery code to extend

Otherwise, build123d is strictly better. Same OCCT kernel, more Pythonic API, active
development, better selectors. **Default refusal: "build123d is the modern equivalent
and is already installed; want me to use that?"**

### Do NOT use
- **FreeCAD scripting** — heavy, requires X, slow startup
- **PythonOCC directly** — too low-level; build123d wraps it cleanly
- **manim's 3D primitives** for CAD — they're for math animation, not engineering

## 2. Mesh layer

### `trimesh` is the default for everything mesh
- Loading STL/OBJ/GLB/PLY/3MF
- Watertight check (`mesh.is_watertight`)
- Repair: `fill_holes`, `merge_vertices`, `remove_duplicate_faces`, `fix_normals`
- Boolean fallback (when OCCT boolean fails or input is already triangle-soup)
- Mass properties (volume, center of mass, inertia)
- Exploded-view math (centroid offset along axis)
- Scene assembly with hierarchy
- **GLB export with materials** — preferred web-friendly format

### `open3d` only when
- Point-cloud algorithms (ICP, normal estimation, Poisson reconstruction)
- The user brings back a Gaussian splat from ReconViaGen and wants to mesh it

Not installed by default. ~150 MB; install if needed.

### `pymeshlab` only when
- Specific MeshLab filters are required (quadric decimation with very specific
  parameters, advanced remeshing)
- Trimesh's simplification isn't enough

Not installed by default. ~250 MB.

## 3. Rendering

### `pyvista` + Xvfb is the default
- Engineering-quality lit shading, smooth normals, edge highlighting
- Multi-light setups (use `plotter.add_light(...)` for studio lighting)
- Camera control (orbit, dolly, zoom — see `scripts/render_orbit.py`)
- Screenshot at any resolution (1080p tested, 4K should work but is slower)
- Slicing planes, vector fields, scalar bars (for scientific visualization)
- Annotations (`add_text`, `add_point_labels` — these become the CAD callouts)

**Always** wrap with `scripts/headless.py`'s `headless_display()` context manager
which starts Xvfb on :99. Don't try `pv.start_xvfb()` — it's been removed in the
installed version.

### `matplotlib` for
- 2D diagrams (block diagrams, free-body diagrams, kinematic schematics)
- BOM tables (`ax.table`)
- 3D fallback only if pyvista fails (rare). Avoid alpha < 1.0 in matplotlib 3D —
  triangles depth-sort wrong and you'll get artifacts.
- Plots that go alongside the 3D scene (torque curves, deflection curves)

### `plotly` for
- Interactive HTML output the user can rotate (orbit + zoom in a browser)
- Not for video — plotly's static export needs kaleido which is heavy

Not installed by default.

### `manim` for
- Animated equations
- Number-line / coordinate-system reveals
- Abstract math overlays that must composite over a CAD scene

Opt-in only. Install cost ~1 GB (LaTeX + cairo + pango). If a user job is
50% CAD + 50% equations, weigh the install cost against accepting "static equation
PNG overlays" rendered by matplotlib.

### `moderngl` for
- Custom GLSL shaders on the CPU via Mesa software rasterizer
- Advanced procedural materials (Perlin noise patterns, hatching, blueprint look)

Already installed. Use sparingly; pyvista's standard shaders are usually enough.

### Browser handoff (three.js / WebGPU / vpython / OpenJSCAD)
- Real-time interaction or PBR-quality render is wanted
- The user has a modern GPU and can open an HTML file
- See `references/WEBGPU_HANDOFF.md`

## 4. 2D engineering drawings

### `ezdxf` is the default
- True DXF output (AutoCAD compatible)
- Layers, dimensions, hatches, leader lines
- Read DXF input if the user supplies one

Pipeline: build123d part → take orthographic sections (XY, XZ, YZ projections) →
extract edges → write to DXF via ezdxf → render preview PNG via matplotlib for
inclusion in the deliverable.

See `scripts/drawing_2d.py` for the skeleton.

### `svgwrite` for
- Tiny pure-SVG schematics where DXF is overkill

Not installed by default.

### `reportlab` for
- Multi-page PDF assembly drawings with title block, BOM table, multiple views

Not installed by default. Install if user requests a "drawing package" deliverable.

## 5. Image-to-3D and Video-to-3D (AI reconstruction)

**All of these are user-GPU handoffs.** None run in 4 GB CPU. See
`references/AI_HANDOFF.md` for full templates.

### Single image → mesh
- **SAM 3D Objects** (Meta, 2025). 16 GB VRAM. Best for general objects. Output
  GLB with texture. Requires a mask (use SAM 3 to make one).
- **TripoSG / Hunyuan3D 2.0** if user prefers higher resolution and has 24 GB+.

### Multi-view photos (8–16) → mesh
- **ReconViaGen v0.2** (ICLR 2026). 18 GB VRAM no-refine, 24 GB with refine.
  Highest-fidelity option among the open-source set. Output: mesh + Gaussian splat.

### Video → mesh
- ffmpeg extracts 12–16 well-spread frames (in-sandbox); feed to ReconViaGen.
- Alternative: Gaussian-splat pipelines (3DGS, MipGaussian) if user has 24 GB+.

### Person → mesh
- **SAM 3D Body** (Meta, 2025). 16 GB VRAM. Output: MHR rig (convertible to
  FBX/glTF). Aligns with SAM 3D Objects when combined.

### Mask generation (single image)
- **SAM 3** (Meta, Nov 2025). 8 GB VRAM. Text or click prompts. Can run on the
  same machine as SAM 3D Objects in a single pipeline.

### Text → mesh
- Not handled by this skill directly. Refer user to TripoSG / Hunyuan3D 2.0
  documentation if needed.

## 6. Voice-over

### `gTTS` (default)
- Online, free, single API call, no install cost beyond Python lib
- Many languages and accents
- Output: MP3, resample with ffmpeg to 48 kHz / mono / 192 kbps for video

### `piper-tts` (offline option)
- Install: pip + one voice model (~60 MB per voice)
- Best for sandbox-no-network jobs or specific voice character requirements
- Output: WAV at 22050 Hz

### `espeak-ng` (fallback)
- Synthetic voice, low quality, but always available if system package is installed
- Use only when other options fail

### Captions
- Generate SRT alongside audio (one cue per narration line; durations from storyboard)
- Burn in with ffmpeg `subtitles=` filter; opt-out via `captions=False` in storyboard

## 7. Video assembly

### `ffmpeg` is the only video tool
- Frame sequence → MP4: `ffmpeg -framerate 30 -i frame_%04d.png -c:v libx264 ...`
- Mux audio + video: `-i video.mp4 -i audio.mp3 -c:v copy -c:a aac -shortest`
- Burn captions: `-vf subtitles=captions.srt`
- Overlay PNG (for callouts/lower-thirds): `-filter_complex overlay=...`

See `scripts/storyboard.py` and `scripts/voiceover.py` for canonical invocations.

## 8. Anti-patterns

- **Don't use pyvista without `headless_display()`** — you'll get
  `bad X server connection` and the script aborts.
- **Don't use matplotlib 3D with alpha < 1.0** — back-faces show through.
- **Don't render frames with `plotter.open_movie()`** — codec path is unreliable
  on software OpenGL. Render PNGs, mux with ffmpeg.
- **Don't install manim "just in case"** — only if equations are explicitly part
  of the deliverable. 1 GB install for a single rendered MP4 is a bad trade.
- **Don't try to install openscad binary unless asked** — it's 300 MB. Hand off the
  .scad text instead.
- **Don't claim a render is done without `view`-ing the PNG.**
- **Don't run more than 3 pyvista plotters concurrently** — each VTK window holds
  ~100 MB; you'll OOM on the 4 GB box.
- **Don't simplify meshes below the build123d default tolerance** without telling
  the user — 0.1 mm chord deviation is fine for render, too coarse for analysis.
