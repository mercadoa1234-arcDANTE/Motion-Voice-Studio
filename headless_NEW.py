"""
Headless display setup for any X-dependent renderer (pyvista, VTK, vpython server-side).

Usage:
    from headless import headless_display
    with headless_display():
        import pyvista as pv
        ...
"""
import os
import subprocess
import time
import contextlib
import atexit


_XVFB_PROC = None


def _start_xvfb(display: str = ":99", width: int = 1920, height: int = 1080,
                depth: int = 24) -> subprocess.Popen:
    """Start an Xvfb server on the given display. Returns the Popen handle.

    Idempotent: if an Xvfb is already running on this display, returns its handle
    (or None, since we don't track external ones — the env var setup is enough).
    """
    global _XVFB_PROC
    if _XVFB_PROC is not None and _XVFB_PROC.poll() is None:
        os.environ["DISPLAY"] = display
        return _XVFB_PROC

    proc = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", f"{width}x{height}x{depth}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Give Xvfb a moment to come up
    time.sleep(0.6)
    if proc.poll() is not None:
        raise RuntimeError(f"Xvfb failed to start on {display}; rc={proc.returncode}")
    os.environ["DISPLAY"] = display
    _XVFB_PROC = proc
    atexit.register(_cleanup)
    return proc


def _cleanup():
    global _XVFB_PROC
    if _XVFB_PROC is not None and _XVFB_PROC.poll() is None:
        _XVFB_PROC.terminate()
        try:
            _XVFB_PROC.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _XVFB_PROC.kill()
        _XVFB_PROC = None


@contextlib.contextmanager
def headless_display(display: str = ":99", width: int = 1920, height: int = 1080):
    """Context manager that ensures an Xvfb display is running with DISPLAY set."""
    _start_xvfb(display, width, height)
    try:
        yield display
    finally:
        # Leave Xvfb running for the rest of the process — cheaper than restarting
        # for each render call. atexit will clean up.
        pass


if __name__ == "__main__":
    # Self-test: start xvfb, import pyvista, render a sphere
    with headless_display():
        import pyvista as pv
        m = pv.Sphere(radius=1.0, theta_resolution=64, phi_resolution=64)
        p = pv.Plotter(off_screen=True, window_size=(400, 300))
        p.add_mesh(m, color="lightcoral", smooth_shading=True)
        p.screenshot("/tmp/headless_selftest.png")
        print("Self-test render written to /tmp/headless_selftest.png")
