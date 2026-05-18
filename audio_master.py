"""
Assembly schema validator and component builder.

Reads an assembly.json (see references/ASSEMBLY_SCHEMA.md), validates it,
builds each component from its source (build123d, mesh, step, recon), and
exports STL + STEP + a combined GLB.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path


REQUIRED_TOP = {"name", "components"}
SCHEMA_VERSION = "cad-studio/assembly/v1"


def validate_schema(schema: dict) -> list:
    """Return a list of validation error strings (empty if OK)."""
    errors = []
    missing = REQUIRED_TOP - set(schema.keys())
    if missing:
        errors.append(f"missing top-level keys: {missing}")
    seen = set()
    for c in schema.get("components", []):
        cid = c.get("id")
        if not cid:
            errors.append(f"component missing 'id': {c}")
            continue
        if cid in seen:
            errors.append(f"duplicate component id: {cid}")
        seen.add(cid)
        src = c.get("source", {})
        if "kind" not in src:
            errors.append(f"component {cid}: source.kind missing")
        if src.get("kind") in ("build123d", "step", "mesh", "recon", "openscad"):
            if "path" not in src:
                errors.append(f"component {cid}: source.path missing")
        else:
            errors.append(f"component {cid}: unknown source.kind={src.get('kind')!r}")
        # pose
        pose = c.get("pose", {})
        if "xyz" in pose and len(pose["xyz"]) != 3:
            errors.append(f"component {cid}: pose.xyz must be length 3")
        if "rpy" in pose and len(pose["rpy"]) != 3:
            errors.append(f"component {cid}: pose.rpy must be length 3")
        # explode
        e = c.get("explode")
        if e:
            if "axis" not in e or len(e["axis"]) != 3:
                errors.append(f"component {cid}: explode.axis must be length 3")
            if "distance_at_full" not in e:
                errors.append(f"component {cid}: explode.distance_at_full missing")
    return errors


def build_assembly_from_schema(schema: dict, base_dir: str) -> dict:
    """Build every component from the schema.

    For each component, exports STL (always) and STEP (when source is build123d/step).
    Returns dict id → {"mesh_path", "step_path" or None, "schema"}.
    """
    errors = validate_schema(schema)
    if errors:
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        raise ValueError(f"assembly schema invalid: {len(errors)} errors")

    out = {}
    tmp = Path("/tmp/cad-studio-build")
    tmp.mkdir(parents=True, exist_ok=True)

    for c in schema["components"]:
        cid = c["id"]
        src = c["source"]
        kind = src["kind"]
        stl_path = str(tmp / f"{cid}.stl")
        step_path = None

        if kind == "build123d":
            from build123d import export_stl, export_step
            fn = _import_callable(os.path.join(base_dir, src["path"]), src["fn"])
            part = fn(**src.get("params", {}))
            export_stl(part, stl_path)
            step_path = str(tmp / f"{cid}.step")
            export_step(part, step_path)
        elif kind == "step":
            from build123d import import_step, export_stl, export_step
            part = import_step(os.path.join(base_dir, src["path"]))
            export_stl(part, stl_path)
            step_path = str(tmp / f"{cid}.step")
            export_step(part, step_path)
        elif kind in ("mesh", "recon"):
            import trimesh
            mesh = trimesh.load(os.path.join(base_dir, src["path"]))
            if hasattr(mesh, "geometry"):
                mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
            mesh.export(stl_path)
        elif kind == "openscad":
            scad_path = os.path.join(base_dir, src["path"])
            # Try the openscad binary if present
            import shutil as _sh, subprocess
            scad_bin = _sh.which("openscad")
            if scad_bin is None:
                raise RuntimeError(
                    f"openscad binary not in PATH; cannot render {scad_path}. "
                    f"Either install openscad or pre-render this part to STL and "
                    f"reference it with kind='mesh'."
                )
            subprocess.run([scad_bin, "-o", stl_path, scad_path], check=True)

        out[cid] = {"mesh_path": stl_path, "step_path": step_path, "schema": c}

    return out


def export_assembly_glb(schema: dict, components: dict, out_path: str):
    """Combine all built components into a single GLB with materials and hierarchy."""
    import trimesh
    import numpy as np

    scene = trimesh.Scene()
    for cid, info in components.items():
        m = trimesh.load(info["mesh_path"])
        if hasattr(m, "geometry"):
            m = trimesh.util.concatenate(list(m.geometry.values()))
        c = info["schema"]
        # Apply pose
        pose = c.get("pose", {})
        T = np.eye(4)
        if "xyz" in pose:
            T[:3, 3] = pose["xyz"]
        if "rpy" in pose:
            r, p, y = pose["rpy"]
            T[:3, :3] = _rpy_to_R(r, p, y)
        m.apply_transform(T)
        # Apply material color
        mat = c.get("material", {})
        if "color" in mat:
            color255 = tuple(int(v * 255) for v in mat["color"]) + (255,)
            m.visual.face_colors = color255
        scene.add_geometry(m, geom_name=cid, node_name=cid)
    scene.export(out_path)
    return out_path


def _rpy_to_R(r, p, y):
    import numpy as np
    cr, sr = np.cos(r), np.sin(r)
    cp, sp = np.cos(p), np.sin(p)
    cy, sy = np.cos(y), np.sin(y)
    Rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _import_callable(path: str, fn: str):
    spec = importlib.util.spec_from_file_location(f"_part_mod_{Path(path).stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, fn)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("schema")
    ap.add_argument("--validate", action="store_true", help="validate only, don't build")
    ap.add_argument("--export-glb", default=None, help="path for combined GLB output")
    args = ap.parse_args()

    schema = json.loads(Path(args.schema).read_text())
    errors = validate_schema(schema)
    if errors:
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print(f"[assembly] schema OK: {len(schema.get('components', []))} components")
    if args.validate:
        sys.exit(0)

    base = str(Path(args.schema).parent)
    comps = build_assembly_from_schema(schema, base)
    print(f"[assembly] built {len(comps)} components")
    for cid, info in comps.items():
        sz = os.path.getsize(info["mesh_path"])
        step = "+step" if info["step_path"] else ""
        print(f"  {cid}: {sz:,} B STL {step}")

    if args.export_glb:
        export_assembly_glb(schema, comps, args.export_glb)
        print(f"[assembly] GLB → {args.export_glb} "
              f"({os.path.getsize(args.export_glb):,} B)")
