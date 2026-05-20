# optional/BROWSER.md — Browser Rendering & 3D Reconstruction

Read when: PyVista can't run offscreen in the sandbox, user wants WebGPU quality,
or the task involves AI 3D reconstruction (Hunyuan3D, TRELLIS, Wonder3D).

---

## When to use browser assist

- User explicitly asked for browser/GPU rendering
- PyVista/ModernGL fail without EGL/OSMesa/Xvfb
- Asset is large or user has better GPU hardware
- Interactive inspection required
- Final render needs custom WebGL/WebGPU materials

---

## Output packet

Generate and present:

```
browser/<basename>_render.html   ← self-contained Three.js / WebGPU viewer
browser/RETURN_FILES.md          ← instructions for user to capture + upload
outputs/geometry/<basename>.stl  ← embedded or linked mesh
```

---

## Three.js render kit (no-install, browser-native)

```html
<!-- Minimal Three.js orbital viewer -->
<script type="module">
import * as THREE from 'https://esm.sh/three';
import { OrbitControls } from 'https://esm.sh/three/addons/controls/OrbitControls.js';
import { STLLoader } from 'https://esm.sh/three/addons/loaders/STLLoader.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x101217);
const camera = new THREE.PerspectiveCamera(45, innerWidth/innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);

new STLLoader().load('geometry/part.stl', geo => {
  const mat  = new THREE.MeshPhongMaterial({ color: 0x4a9eff, shininess: 60 });
  const mesh = new THREE.Mesh(geo, mat);
  geo.computeBoundingBox();
  const center = new THREE.Vector3();
  geo.boundingBox.getCenter(center);
  mesh.position.sub(center);
  scene.add(mesh);
});

scene.add(new THREE.AmbientLight(0xffffff, 0.4));
const dir = new THREE.DirectionalLight(0xffffff, 0.8);
dir.position.set(5, 10, 5);
scene.add(dir);

camera.position.set(0, 0, 200);
const ctrl = new OrbitControls(camera, renderer.domElement);
const animate = () => { requestAnimationFrame(animate); ctrl.update(); renderer.render(scene, camera); };
animate();
</script>
```

---

## Hunyuan3D (low-VRAM, user's GPU)

### Decision gate

Use Hunyuan3D when:
- Object is organic, decorative, or concept-level
- User supplies a reference image
- Tolerances and manufacturability are not required

Do NOT use when:
- Part must fit, mate, seal, or manufacture accurately
- Parametric editability is needed
- → Use `build123d` instead (see `optional/CAD.md`)

### 12 GB VRAM and under

```bash
# Hunyuan3D-2.0 lightweight config
python infer.py \
  --image_path input.png \
  --output_dir output_mesh/ \
  --steps 50 \
  --guidance_scale 6.0 \
  --num_views 6          # reduce from default 8 to save VRAM
```

Memory optimization:
- `--num_views 4` → ~8 GB VRAM (quality drops slightly)
- Enable `xformers` if installed
- `torch.cuda.empty_cache()` between stages if running OOM

### Handoff format (sandbox → user → back)

```
recon_job/
├── RUN.md          ← step-by-step instructions for the user's GPU machine
├── manifest.json   ← model settings, input paths, output contract
└── inputs/
    └── reference.png
```

User uploads resulting `.glb` or `.obj` back into chat. Sandbox loads with trimesh and continues the pipeline.

---

## GlowScript / VPython (browser-native physics viz)

For simple physics animations that need browser-native primitives:

```python
# Generate a GlowScript URL or embedded iframe
# Useful for: pendulums, orbits, wave demos, particle systems
# No install. Runs in any browser.
```

Not suitable for: engineering visualization, precise geometry, CAD-derived meshes.
