"""
Render an orbital-camera animation as a PNG sequence.

The output frames can then be muxed by ffmpeg into MP4/WebM. Designed to stay
within the 4 GB / 1 CPU budget: holds one plotter, mutates the camera each frame,
writes PNG, never opens a movie codec.

Usage:
    python render_orbit.py <input> <out_dir> [--duration 4 --fps 24 --width 1280 --height 720]
"""
import argparse
import math
import os
import time
from pathlib import Path


def render_orbit(
    input_path: str,
    out_dir: str,
    duration: float = 4.0,
    fps: int = 24,
    resolution=(1280, 720),
    elevation_deg: float = 25.0,
    azimuth_from_deg: float = 0.0,
    azimuth_to_deg: float = 360.0,
    color: str = "#7aa9d6",
    bg: str = "#f5f7fa",
    metallic: bool = False,
    on_progress=None,
):
    """Render an orbital camera move.

    Frames are written as frame_0000.png, frame_0001.png, ... in out_dir.
    Returns: dict {n_frames, duration, fps, size_bytes_total}.
    """
    from headless import headless_display

    os.makedirs(out_dir, exist_ok=True)
    n_frames = max(1, int(round(duration * fps)))

    with headless_display():
        import pyvista as pv

        ext = Path(input_path).suffix.lower()
        if ext in (".step", ".stp"):
            from build123d import import_step, export_stl
            part = import_step(input_path)
            tmp_stl = "/tmp/_render_orbit_in.stl"
            export_stl(part, tmp_stl)
            mesh = pv.read(tmp_stl)
        else:
            mesh = pv.read(input_path)

        b = mesh.bounds
        cx = (b[0] + b[1]) / 2
        cy = (b[2] + b[3]) / 2
        cz = (b[4] + b[5]) / 2
        radius = max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) * 1.7
        elev_rad = math.radians(elevation_deg)

        plotter = pv.Plotter(off_screen=True, window_size=resolution)
        plotter.set_background(bg)
        plotter.add_mesh(
            mesh,
            color=color,
            smooth_shading=True,
            ambient=0.20,
            diffuse=0.85,
            specular=0.85 if metallic else 0.45,
            specular_power=60 if metallic else 20,
        )
        plotter.add_axes()

        t0 = time.time()
        total_bytes = 0
        for i in range(n_frames):
            t = i / max(1, n_frames - 1)
            az_deg = azimuth_from_deg + t * (azimuth_to_deg - azimuth_from_deg)
            az_rad = math.radians(az_deg)
            cam = (
                cx + radius * math.cos(az_rad) * math.cos(elev_rad),
                cy + radius * math.sin(az_rad) * math.cos(elev_rad),
                cz + radius * math.sin(elev_rad),
            )
            plotter.camera_position = [cam, (cx, cy, cz), (0, 0, 1)]
            fname = os.path.join(out_dir, f"frame_{i:04d}.png")
            plotter.render()
            plotter.screenshot(fname)
            total_bytes += os.path.getsize(fname)
            if on_progress and (i % 10 == 0 or i == n_frames - 1):
                on_progress(i + 1, n_frames, time.time() - t0)

        plotter.close()

    return {
        "n_frames": n_frames,
        "duration": duration,
        "fps": fps,
        "size_bytes_total": total_bytes,
        "out_dir": out_dir,
        "wall_seconds": time.time() - t0,
    }


def _default_progress(i, n, elapsed):
    eta = (elapsed / i) * (n - i) if i > 0 else 0
    print(f"  [{i}/{n}] {elapsed:.1f}s elapsed, ETA {eta:.1f}s", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("out_dir")
    ap.add_argument("--duration", type=float, default=4.0)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--elevation", type=float, default=25.0)
    ap.add_argument("--from-azim", type=float, default=0.0)
    ap.add_argument("--to-azim", type=float, default=360.0)
    ap.add_argument("--color", default="#7aa9d6")
    ap.add_argument("--metallic", action="store_true")
    args = ap.parse_args()

    info = render_orbit(
        args.input, args.out_dir,
        duration=args.duration, fps=args.fps,
        resolution=(args.width, args.height),
        elevation_deg=args.elevation,
        azimuth_from_deg=args.from_azim,
        azimuth_to_deg=args.to_azim,
        color=args.color, metallic=args.metallic,
        on_progress=_default_progress,
    )
    print(f"[render_orbit] {info['n_frames']} frames, "
          f"{info['size_bytes_total']:,} B total, "
          f"wall={info['wall_seconds']:.1f}s")
    print(f"Next: ffmpeg -framerate {info['fps']} -i {info['out_dir']}/frame_%04d.png "
          f"-c:v libx264 -pix_fmt yuv420p orbit.mp4")
