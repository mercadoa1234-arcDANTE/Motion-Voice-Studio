"""
Exploded-view math and rendering.

Two modes:

1. Schema-driven: load an assembly.json (see references/ASSEMBLY_SCHEMA.md),
   build each component, then animate `t` from 0 (assembled) to 1 (exploded).

2. Auto-mode for a flat mesh / Scene: compute explode directions from each
   component's centroid relative to the scene centroid (radial explode).

Both modes share the rendering core.
"""
import argparse
import importlib.util
import json
import math
import os
import time
from pathlib import Path
import numpy as np


# ---------- easing ----------

def ease(name: str, t: float) -> float:
    t = max(0.0, min(1.0, t))
    if name == "linear":
        return t
    if name == "ease_in":
        return t * t
    if name == "ease_out":
        return 1 - (1 - t) ** 2
    if name == "ease_in_out":
        return 0.5 * (1 - math.cos(math.pi * t))
    raise ValueError(f"unknown easing: {name}")


# ---------- schema loader ----------

def _import_callable(path: str, fn: str):
    """Import path/fn lazily so this script doesn't require build123d to import."""
    spec = importlib.util.spec_from_file_location("_part_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn)


def build_components(schema: dict, base_dir: str):
    """Build each component, return a dict id → {part, mesh_path, schema}.

    `mesh_path` is a freshly-exported STL on disk (in /tmp/cad-studio/<id>.stl).
    """
    from build123d import export_stl, import_step
    import trimesh

    out = {}
    tmp = Path("/tmp/cad-studio-build")
    tmp.mkdir(parents=True, exist_ok=True)

    for c in schema["components"]:
        cid = c["id"]
        src = c["source"]
        kind = src["kind"]
        stl_path = str(tmp / f"{cid}.stl")

        if kind == "build123d":
            fn = _import_callable(os.path.join(base_dir, src["path"]), src["fn"])
            part = fn(**src.get("params", {}))
            export_stl(part, stl_path)
        elif kind == "step":
            part = import_step(os.path.join(base_dir, src["path"]))
            export_stl(part, stl_path)
        elif kind in ("mesh", "recon"):
            # Already a mesh file. Convert through trimesh to ensure STL.
            mesh = trimesh.load(os.path.join(base_dir, src["path"]))
            if hasattr(mesh, "geometry"):  # Scene
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            mesh.export(stl_path)
        elif kind == "openscad":
            raise NotImplementedError(
                "OpenSCAD components require the openscad binary; either install it "
                "or pre-render to STL and reference as kind='mesh'."
            )
        else:
            raise ValueError(f"unknown source kind: {kind}")

        out[cid] = {"mesh_path": stl_path, "schema": c}
    return out


# ---------- explode math ----------

def explode_offset(component: dict, t: float):
    """Return (dx, dy, dz) offset to add to the component's pose at explode t∈[0,1]."""
    e = component.get("explode")
    if not e:
        return (0.0, 0.0, 0.0)
    axis = np.array(e.get("axis", [0, 0, 1]), dtype=float)
    n = np.linalg.norm(axis)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    axis = axis / n
    distance = e.get("distance_at_full", 30.0)
    eased = ease(e.get("easing", "ease_in_out"), t)
    v = axis * (distance * eased)
    return (float(v[0]), float(v[1]), float(v[2]))


def auto_explode_radial(scene_or_meshes, distance: float = 30.0):
    """Compute axes for each part by radial direction from scene centroid.

    Returns dict id → {"axis": [...], "distance_at_full": ...}.
    """
    import trimesh
    if isinstance(scene_or_meshes, trimesh.Scene):
        items = list(scene_or_meshes.geometry.items())
    elif isinstance(scene_or_meshes, dict):
        items = list(scene_or_meshes.items())
    else:
        raise TypeError("expected trimesh.Scene or dict")

    all_centroids = np.array([m.centroid for _, m in items])
    scene_centroid = all_centroids.mean(axis=0)

    result = {}
    for (cid, mesh), c in zip(items, all_centroids):
        direction = c - scene_centroid
        n = np.linalg.norm(direction)
        if n < 1e-6:
            axis = [0.0, 0.0, 1.0]
        else:
            axis = (direction / n).tolist()
        result[cid] = {"axis": axis, "distance_at_full": distance}
    return result


# ---------- rendering ----------

def render_explode_frames(
    schema: dict,
    components: dict,
    out_dir: str,
    duration: float = 4.0,
    fps: int = 24,
    resolution=(1280, 720),
    camera: str = "orbit",
    elevation_deg: float = 25.0,
    azim_from: float = 30.0,
    azim_to: float = 60.0,
    bg: str = "#f5f7fa",
    t_from: float = 0.0,
    t_to: float = 1.0,
    on_progress=None,
):
    """Render the explode animation."""
    from headless import headless_display
    import pyvista as pv

    os.makedirs(out_dir, exist_ok=True)
    n_frames = max(1, int(round(duration * fps)))

    # Pre-load all meshes once
    meshes = {}
    for cid, info in components.items():
        meshes[cid] = pv.read(info["mesh_path"])

    # Compute scene bounds AT EXPLODED (t=1) to keep camera framing stable
    bounds = None
    for cid, m in meshes.items():
        c = components[cid]["schema"]
        pose = c.get("pose", {}).get("xyz", [0, 0, 0])
        off = explode_offset(c, 1.0)
        b = np.array(m.bounds).reshape(3, 2)
        b[:, 0] += pose[0] + off[0]; b[:, 1] += pose[0] + off[0]  # x
        # Actually simpler — just compute scene bounding box from translated meshes
        bounds = (m.copy().translate([pose[0] + off[0], pose[1] + off[1], pose[2] + off[2]]).bounds if bounds is None
                  else _union_bounds(bounds, m.copy().translate([pose[0] + off[0], pose[1] + off[1], pose[2] + off[2]]).bounds))
    cx = (bounds[0] + bounds[1]) / 2
    cy = (bounds[2] + bounds[3]) / 2
    cz = (bounds[4] + bounds[5]) / 2
    radius = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]) * 1.6

    with headless_display():
        plotter = pv.Plotter(off_screen=True, window_size=resolution)
        plotter.set_background(bg)
        actors = {}
        for cid, m in meshes.items():
            c = components[cid]["schema"]
            mat = c.get("material", {})
            color = mat.get("color", [0.5, 0.6, 0.7])
            if isinstance(color, list):
                color = tuple(color)
            metallic = mat.get("metallic", 0.0) > 0.5
            actor = plotter.add_mesh(
                m.copy(),
                color=color,
                smooth_shading=True,
                ambient=0.2, diffuse=0.85,
                specular=0.85 if metallic else 0.45,
                specular_power=60 if metallic else 20,
                opacity=mat.get("opacity", 1.0),
            )
            actors[cid] = actor

        t0 = time.time()
        elev_rad = math.radians(elevation_deg)

        for i in range(n_frames):
            t_anim = i / max(1, n_frames - 1)
            t_explode = t_from + t_anim * (t_to - t_from)

            # Move each actor to its current explode offset
            for cid, actor in actors.items():
                c = components[cid]["schema"]
                pose = c.get("pose", {}).get("xyz", [0, 0, 0])
                off = explode_offset(c, t_explode)
                actor.SetPosition(pose[0] + off[0], pose[1] + off[1], pose[2] + off[2])

            # Camera
            if camera == "orbit":
                az_deg = azim_from + t_anim * (azim_to - azim_from)
                az_rad = math.radians(az_deg)
                cam = (
                    cx + radius * math.cos(az_rad) * math.cos(elev_rad),
                    cy + radius * math.sin(az_rad) * math.cos(elev_rad),
                    cz + radius * math.sin(elev_rad),
                )
                plotter.camera_position = [cam, (cx, cy, cz), (0, 0, 1)]
            # camera == "static" leaves whatever was set; user can set before calling

            fname = os.path.join(out_dir, f"frame_{i:04d}.png")
            plotter.render()
            plotter.screenshot(fname)

            if on_progress and (i % 10 == 0 or i == n_frames - 1):
                on_progress(i + 1, n_frames, time.time() - t0)

        plotter.close()
        return {"n_frames": n_frames, "duration": duration, "fps": fps,
                "out_dir": out_dir, "wall_seconds": time.time() - t0}


def _union_bounds(b1, b2):
    return (
        min(b1[0], b2[0]), max(b1[1], b2[1]),
        min(b1[2], b2[2]), max(b1[3], b2[3]),
        min(b1[4], b2[4]), max(b1[5], b2[5]),
    )


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("schema", help="path to assembly schema JSON")
    ap.add_argument("out_dir", help="frame output directory")
    ap.add_argument("--duration", type=float, default=4.0)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--from-t", type=float, default=0.0)
    ap.add_argument("--to-t", type=float, default=1.0)
    args = ap.parse_args()

    schema = json.loads(Path(args.schema).read_text())
    base = str(Path(args.schema).parent)
    comps = build_components(schema, base)
    info = render_explode_frames(
        schema, comps, args.out_dir,
        duration=args.duration, fps=args.fps,
        resolution=(args.width, args.height),
        t_from=args.from_t, t_to=args.to_t,
        on_progress=lambda i, n, e: print(f"  [{i}/{n}] {e:.1f}s", flush=True),
    )
    print(f"[exploded_view] {info}")


if __name__ == "__main__":
    main()
