// 搏闻首页 3D 物件：一个画布，按每个格子的位置分区绘制（scissor），每个物件有自己的悬停动作。
// 失败时什么也不做，页面保留图片版。
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";

const KEYS = ["world", "econ", "ai", "side", "deep", "tear", "inbox"];
const FILE = { world: "globe", econ: "coin", ai: "chip", side: "bulb", deep: "lens", tear: "stack", inbox: "plane" };
const calm = () => document.documentElement.classList.contains("calm");
const lerp = (a, b, t) => a + (b - a) * t;

let renderer;
try {
  const canvas = document.createElement("canvas");
  canvas.id = "stage3d";
  canvas.setAttribute("aria-hidden", "true");
  document.body.appendChild(canvas);
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: "high-performance" });
} catch (e) { renderer = null; }

if (renderer) start();

function start() {
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setClearColor(0x000000, 0);
  renderer.setScissorTest(true);
  renderer.autoClear = false;

  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;

  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const objs = {};

  KEYS.forEach((k) => {
    loader.load(`assets/models/${FILE[k]}.glb`, (g) => {
      const scene = new THREE.Scene();
      scene.environment = env;
      const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(2.5, 3.5, 4); scene.add(key);
      const rim = new THREE.DirectionalLight(0xbfd4ff, 0.8); rim.position.set(-3, 1, -2); scene.add(rim);
      const model = g.scene;
      // 居中并缩放到半径 1
      model.updateMatrixWorld(true);
      const box = new THREE.Box3().setFromObject(model, true);
      const c = box.getCenter(new THREE.Vector3());
      const sph = box.getBoundingSphere(new THREE.Sphere());
      model.position.sub(c);
      const holder = new THREE.Group(); holder.add(model); holder.scale.setScalar(1 / sph.radius);
      const pivot = new THREE.Group(); pivot.add(holder); scene.add(pivot);
      const cam = new THREE.PerspectiveCamera(28, 1, 0.1, 50); cam.position.set(0, 0, 4.1);
      const o = { k, scene, cam, pivot, holder, model, mats: {}, layers: [], hover: 0, px: 0, py: 0, t0: Math.random() * 10, fly: 0 };
      model.traverse((n) => {
        if (n.isMesh) {
          const m = n.material;
          m.envMapIntensity = 1.0;
          // 透明玻璃：用半透明代替折射，多视口绘制更稳
          if (m.transmission > 0) {
            m.transmission = 0; m.transparent = true; m.opacity = 0.22; m.roughness = 0.03; m.metalness = 0;
            m.depthWrite = false; m.envMapIntensity = 2.2; m.side = THREE.DoubleSide;
            if ("clearcoat" in m) { m.clearcoat = 1; m.clearcoatRoughness = 0.02; }
          }
          o.mats[m.name] = m;
        }
        if (/^layer\d/.test(n.name)) o.layers.push(n);
      });
      o.layers.sort((a, b) => a.name.localeCompare(b.name));
      o.layers.forEach((l) => { l.userData.z0 = l.position.clone(); });
      if (k === "side") {
        o.glow = new THREE.PointLight(0xffb35c, 0, 6); o.glow.position.set(0, 0.25, 0.6); scene.add(o.glow);
        const f = o.mats.filament; if (f) { o.fil0 = f.emissiveIntensity; }
      }
      if (k === "ai") { const d = o.mats.die; if (d) o.die0 = d.emissiveIntensity; }
      objs[k] = o;
    }, undefined, () => {});
  });

  // 指针：记录在哪个格子上
  let pointer = { x: -1, y: -1 };
  window.addEventListener("pointermove", (e) => { pointer.x = e.clientX; pointer.y = e.clientY; }, { passive: true });
  window.addEventListener("pointerleave", () => { pointer.x = pointer.y = -1; });
  document.addEventListener("pointerdown", (e) => { pointer.x = e.clientX; pointer.y = e.clientY; }, { passive: true });

  const clock = new THREE.Clock();
  function frame() {
    requestAnimationFrame(frame);
    const tiles = document.querySelectorAll(".tile[data-go]");
    const canvas = renderer.domElement;
    if (!tiles.length || document.hidden) { if (canvas.style.display !== "none") canvas.style.display = "none"; return; }
    canvas.style.display = "";
    const W = window.innerWidth, H = window.innerHeight;
    const size = renderer.getSize(new THREE.Vector2());
    if (size.x !== W || size.y !== H) renderer.setSize(W, H, false);
    const dt = Math.min(clock.getDelta(), 0.05), t = clock.elapsedTime;
    const still = calm();
    renderer.setScissor(0, 0, W, H); renderer.setViewport(0, 0, W, H); renderer.clear();

    tiles.forEach((tile) => {
      const k = tile.getAttribute("data-go"), o = objs[k];
      if (!o) return;
      const wrap = tile.querySelector(".obj-wrap"); if (!wrap) return;
      const r = wrap.getBoundingClientRect(), tr = tile.getBoundingClientRect();
      if (r.bottom < 0 || r.top > H || r.width < 4) return;
      if (!tile.classList.contains("live")) tile.classList.add("live");

      const inside = pointer.x >= tr.left && pointer.x <= tr.right && pointer.y >= tr.top && pointer.y <= tr.bottom;
      const tx = inside ? (pointer.x - (r.left + r.width / 2)) / tr.width : 0;
      const ty = inside ? (pointer.y - (r.top + r.height / 2)) / tr.height : 0;
      const ease = 1 - Math.pow(0.0015, dt);
      o.hover = lerp(o.hover, inside && !still ? 1 : 0, ease);
      o.px = lerp(o.px, still ? 0 : tx, ease); o.py = lerp(o.py, still ? 0 : ty, ease);
      if (inside) { tile.style.setProperty("--mx", ((pointer.x - tr.left) / tr.width * 100).toFixed(1) + "%"); tile.style.setProperty("--my", ((pointer.y - tr.top) / tr.height * 100).toFixed(1) + "%"); }
      animate(o, still ? 0 : t + o.t0, dt, still, tile);

      // 视口：取 obj-wrap 区域的最大正方形
      // 视口：底边贴着物件区底部，可以往上越过物件区，但不超出格子
      const s = Math.min(r.width * 0.95, r.height * 1.25, r.bottom - tr.top - 4);
      const vx = r.left + (r.width - s) / 2, vtop = r.bottom - s;
      const vy = H - r.bottom;
      const sx = Math.max(vx, tr.left), sTop = Math.max(vtop, tr.top), sr = Math.min(vx + s, tr.right), sb = Math.min(r.bottom, tr.bottom);
      if (sr <= sx || sb <= sTop) return;
      o.cam.aspect = 1; o.cam.updateProjectionMatrix();
      renderer.setViewport(vx, vy, s, s);
      renderer.setScissor(sx, H - sb, sr - sx, sb - sTop);
      renderer.render(o.scene, o.cam);
    });
  }
  requestAnimationFrame(frame);

  function animate(o, t, dt, still, tile) {
    const h = o.hover, p = o.pivot, bob = still ? 0 : Math.sin(t * 1.1) * 0.05;
    p.position.set(0, bob, 0);
    switch (o.k) {
      case "world": { // 地球：慢慢自转；悬停时随鼠标拨动
        o.spin = (o.spin || 0) + dt * (still ? 0 : 0.18 + h * 0.2) ;
        o.model.rotation.y = o.spin + o.px * 2.2 * h;
        p.rotation.set(o.py * 0.5 * h, 0, 0);
        break;
      }
      case "econ": { // 硬币：鼠标在哪就转向哪
        const idle = still ? 0 : Math.sin(t * 0.7) * 0.35 * (1 - h);
        p.rotation.set(o.py * 0.9 * h, idle + o.px * 3.0 * h, 0);
        break;
      }
      case "ai": { // 芯片：悬停时亮起、朝鼠标倾斜
        p.rotation.set(o.py * 0.6 * h, o.px * 0.8 * h, 0);
        const d = o.mats.die; if (d && o.die0 != null) d.emissiveIntensity = o.die0 * (1 + h * (1.6 + Math.sin(t * 6) * 0.4));
        break;
      }
      case "side": { // 灯泡：悬停点亮
        p.rotation.set(0, o.px * 0.6 * h, Math.sin(t * 0.9) * 0.05 * (1 - h) - o.px * 0.15 * h);
        const f = o.mats.filament; if (f) { f.emissive.setRGB(1, 0.55, 0.18); f.emissiveIntensity = 0.6 + h * 9; }
        const g = o.mats.glass; if (g) { g.emissive.setRGB(1, 0.45, 0.08); g.emissiveIntensity = h * 0.55; g.opacity = 0.22 + h * 0.3; }
        if (o.glow) o.glow.intensity = h * 14;
        tile.style.setProperty("--glow", h.toFixed(3));
        break;
      }
      case "deep": { // 放大镜：跟着鼠标移动
        p.position.set(o.px * 0.9 * h, -o.py * 0.7 * h + bob, 0);
        p.rotation.set(o.py * 0.4 * h, o.px * 0.5 * h, -o.px * 0.3 * h);
        break;
      }
      case "tear": { // 拆解叠层：悬停时层层拉开
        p.rotation.set(o.py * 0.4 * h, o.px * 0.6 * h, 0);
        o.layers.forEach((l, i) => { const z0 = l.userData.z0; const n = o.layers.length; const off = (i - (n - 1) / 2) * 0.35 * h; l.position.set(z0.x, z0.y - off, z0.z); });
        break;
      }
      case "inbox": { // 纸飞机：轻轻飘，悬停时机头对着鼠标；点击飞走
        const fly = tile.classList.contains("flyout");
        o.fly = fly ? Math.min(1, o.fly + dt * 2.2) : 0;
        p.rotation.set(-o.py * 0.6 * h + Math.sin(t * 1.3) * 0.06, o.px * 0.9 * h, Math.sin(t * 0.8) * 0.08 + o.px * 0.25 * h);
        p.position.x += o.px * 0.3 * h + o.fly * 3.5; p.position.y += -o.py * 0.2 * h + o.fly * 2.2;
        p.scale.setScalar(1 - o.fly * 0.5);
        break;
      }
    }
  }
}
