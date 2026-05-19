"""
Render a single still PNG of a mesh or build123d part.

Usage:
    python render_still.py <input.stl|.obj|.glb|.step> <output.png> [--view iso|front|top|right]

This is the canonical "show me one frame" script. Use it to pass Gate B.
"""
import sys
import argparse
import os
from pathlib import Path


def render_still(
    input_path: str,
    output_path: str,
    view: str = "iso",
    resolution=(1280, 720),
    color: str = "#7aa9d6",
    bg: str = "#f5f7fa",
    show_edges: bool = False,
    show_axes: bool = True,
    metallic: bool = False,
):
    """Render `input_path` to `output_path` as a PNG.

    Supported inputs: .stl .obj .ply .glb .vtk .step .stp
    For .step/.stp the file is imported via build123d and tessellated.

    Returns:
        dict with keys: bytes (file size), view (final view used), bounds.
    """
    from headless import headless_display

    with headless_display():
        import pyvista as pv
        ext = Path(input_path).suffix.lower()
        if ext in (".step", ".stp"):
            # Import via build123d → temp STL → load
            from build123d import import_step, export_stl
            part = import_step(input_path)
            tmp_stl = "/tmp/_render_still_in.stl"
            export_stl(part, tmp_stl)
            mesh = pv.read(tmp_stl)
        else:
            mesh = pv.read(input_path)

        plotter = pv.Plotter(off_screen=True, window_size=resolution)
        plotter.set_background(bg)
        material = dict(
            color=color,
            smooth_shading=True,
            ambient=0.20,
            diffuse=0.85,
            specular=0.45 if not metallic else 0.85,
            specular_power=20 if not metallic else 60,
            show_edges=show_edges,
            edge_color="#1c3a5f",
            line_width=0.5,
        )
        plotter.add_mesh(mesh, **material)
        if show_axes:
            plotter.add_axes()
        plotter.camera_position = _camera_for_view(view, mesh)
        plotter.screenshot(output_path)
        plotter.close()
        return {
            "bytes": os.path.getsize(output_path),
            "view": view,
            "bounds": mesh.bounds,
        }


def _camera_for_view(view: str, mesh):
    """Return a pyvista camera_position string or tuple for the named view."""
    if view == "iso":
        return "iso"
    if view == "front":
        return "xy"   # looking down −Z (front of XY plane)
    if view == "top":
        return "xz"
    if view == "right":
        return "yz"
    if view == "iso_back":
        # Manually construct: opposite of iso
        b = mesh.bounds  # xmin xmax ymin ymax zmin zmax
        cx = (b[0] + b[1]) / 2
        cy = (b[2] + b[3]) / 2
        cz = (b[4] + b[5]) / 2
        d = max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) * 1.8
        return [(cx - d, cy - d, cz + d), (cx, cy, cz), (0, 0, 1)]
    raise ValueError(f"Unknown view: {view}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--view", default="iso", choices=["iso", "front", "top", "right", "iso_back"])
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--color", default="#7aa9d6")
    ap.add_argument("--bg", default="#f5f7fa")
    ap.add_argument("--edges", action="store_true")
    ap.add_argument("--metallic", action="store_true")
    args = ap.parse_args()

    info = render_still(
        args.input,
        args.output,
        view=args.view,
        resolution=(args.width, args.height),
        color=args.color,
        bg=args.bg,
        show_edges=args.edges,
        metallic=args.metallic,
    )
    print(f"[render_still] {args.input} → {args.output}  "
          f"({info['bytes']:,} B, view={info['view']})")
    print(f"  bounds: {info['bounds']}")
