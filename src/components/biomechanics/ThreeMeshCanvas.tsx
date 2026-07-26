"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OBJLoader } from "three/examples/jsm/loaders/OBJLoader.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { useBiomechanicsStore } from "@/lib/store";
import { Box, Eye, RefreshCw } from "lucide-react";

interface ThreeMeshCanvasProps {
  width?: string;
  height?: string;
  glbUrl?: string;
  defaultSource?: "obj" | "glb";
}

const objMeshCache: Record<number, THREE.Group> = {};
const materialCache: Record<string, THREE.MeshStandardMaterial> = {};

function getMeshMaterial(style: string) {
  if (materialCache[style]) return materialCache[style];

  let mat: THREE.MeshStandardMaterial;
  switch (style) {
    case "wireframe":
      mat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        wireframe: true,
        transparent: true,
        opacity: 0.75,
      });
      break;
    case "matte":
      mat = new THREE.MeshStandardMaterial({
        color: 0xe2e8f0,
        roughness: 0.35,
        metalness: 0.05,
      });
      break;
    case "glass":
      mat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        wireframe: true,
        transparent: true,
        opacity: 0.25,
      });
      break;
    case "chrome":
    default:
      mat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 0.1,
        metalness: 0.9,
        envMapIntensity: 1.5,
      });
      break;
  }
  materialCache[style] = mat;
  return mat;
}

export function ThreeMeshCanvas({
  height = "540px",
  glbUrl = "/squat_multiview_animated.glb",
  defaultSource = "glb",
}: ThreeMeshCanvasProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const { activeFrame } = useBiomechanicsStore();

  const [meshStyle, setMeshStyle] = useState<"chrome" | "matte" | "wireframe" | "glass">("wireframe");
  const [sourceType, setSourceType] = useState<"obj" | "glb">(defaultSource);
  const [isLoadingMesh, setIsLoadingMesh] = useState(false);
  // Mesh assets (.glb/.obj) are gitignored generated output and are absent from
  // a fresh clone. Without this the viewport just renders an empty grid and the
  // only clue is a console error, which reads as "the 3D viewer is broken".
  const [loadError, setLoadError] = useState<string | null>(null);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const mainGroupRef = useRef<THREE.Group | null>(null);
  const currentMeshRef = useRef<THREE.Group | null>(null);
  const loadedGlbSceneRef = useRef<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);

  // Initialize Scene, Lights, Floor Grid
  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 650;
    const h = container.clientHeight || 540;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / h, 0.1, 1000);
    camera.position.set(2.4, 1.2, 2.4);
    camera.lookAt(0, 0.5, 0);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(width, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    // Grid Helper
    const gridHelper = new THREE.GridHelper(10, 20, 0xffffff, 0x333333);
    gridHelper.position.y = 0;
    scene.add(gridHelper);

    // Floor Plane
    const floorGeo = new THREE.PlaneGeometry(10, 10);
    const floorMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 0.8, metalness: 0.2 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.005;
    scene.add(floor);

    // Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.5);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xffffff, 2.5);
    keyLight.position.set(5, 10, 7);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0xffffff, 1.8);
    rimLight.position.set(-5, 8, -5);
    scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0xaaaaaa, 0.8);
    fillLight.position.set(0, -5, 5);
    scene.add(fillLight);

    const mainGroup = new THREE.Group();
    scene.add(mainGroup);
    mainGroupRef.current = mainGroup;

    // Orbit Controls for viewport camera movement
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0.8, 0);
    controls.update();

    // Render loop
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      controls.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Effect to load GLB model when sourceType === "glb"
  useEffect(() => {
    if (sourceType !== "glb" || !mainGroupRef.current) return;
    const mainGroup = mainGroupRef.current;
    const mat = getMeshMaterial(meshStyle);

    if (loadedGlbSceneRef.current) {
      // Update materials on already loaded GLB
      loadedGlbSceneRef.current.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          (child as THREE.Mesh).material = mat;
        }
      });
      return;
    }

    setIsLoadingMesh(true);
    setLoadError(null);
    const loader = new GLTFLoader();
    loader.load(
      glbUrl,
      (gltf) => {
        const model = gltf.scene;
        model.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.geometry.computeVertexNormals();
            mesh.material = mat;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          }
        });

        if (gltf.animations && gltf.animations.length > 0) {
          const mixer = new THREE.AnimationMixer(model);
          const action = mixer.clipAction(gltf.animations[0]);
          action.play();
          mixerRef.current = mixer;
        }

        if (currentMeshRef.current) {
          mainGroup.remove(currentMeshRef.current);
        }

        loadedGlbSceneRef.current = model;
        mainGroup.add(model);
        currentMeshRef.current = model;
        setIsLoadingMesh(false);
      },
      undefined,
      (err) => {
        console.error("GLB load error:", err);
        setLoadError(glbUrl);
        setIsLoadingMesh(false);
      }
    );
  }, [sourceType, glbUrl, meshStyle]);

  // Synchronize GLB animation mixer with activeFrame
  useEffect(() => {
    if (sourceType === "glb" && mixerRef.current) {
      const targetTime = (activeFrame / 291.0) * (mixerRef.current.getRoot() ? 9.7 : 1);
      mixerRef.current.setTime(targetTime);
    }
  }, [activeFrame, sourceType]);

  // Update OBJ mesh geometry dynamically based on activeFrame when sourceType === "obj"
  useEffect(() => {
    if (sourceType !== "obj" || !mainGroupRef.current) return;
    const mainGroup = mainGroupRef.current;
    const mat = getMeshMaterial(meshStyle);

    const frameIdx = Math.min(290, Math.max(0, activeFrame));
    const frameStr = String(frameIdx).padStart(4, "0");
    const objPath = `/meshes/frame_${frameStr}.obj`;

    if (objMeshCache[frameIdx]) {
      const cachedObj = objMeshCache[frameIdx];
      cachedObj.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          (child as THREE.Mesh).material = mat;
        }
      });

      if (currentMeshRef.current && currentMeshRef.current !== cachedObj) {
        mainGroup.remove(currentMeshRef.current);
      }
      mainGroup.add(cachedObj);
      currentMeshRef.current = cachedObj;
      return;
    }

    // `cancelled` guards against out-of-order loads: scrubbing the timeline
    // fires one request per frame, and without this a slow earlier fetch can
    // resolve last and leave the viewport showing a frame the user has already
    // scrubbed past. The load also runs in an async callback rather than
    // synchronously in the effect body, so setting the spinner state cannot
    // cascade a second render before paint.
    let cancelled = false;

    (async () => {
      setIsLoadingMesh(true);
      setLoadError(null);
      try {
        const obj = await new OBJLoader().loadAsync(objPath);
        if (cancelled) return;

        obj.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.geometry.computeVertexNormals();
            mesh.material = mat;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          }
        });

        objMeshCache[frameIdx] = obj;

        if (currentMeshRef.current) {
          mainGroup.remove(currentMeshRef.current);
        }
        mainGroup.add(obj);
        currentMeshRef.current = obj;
      } catch (err) {
        if (!cancelled) {
          console.error(`OBJ load error (${objPath}):`, err);
          setLoadError(objPath);
        }
      } finally {
        if (!cancelled) setIsLoadingMesh(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeFrame, meshStyle, sourceType]);

  return (
    <div className="relative rounded-none border border-[#262626] bg-[#000000] overflow-hidden flex flex-col shadow-2xl font-mono">
      {/* 3D Control Header Overlay */}
      <div className="p-3 border-b border-[#262626] bg-[#0a0a0a] flex flex-wrap items-center justify-between gap-2 z-10">
        <div className="flex items-center gap-2 text-xs text-[#ffffff]">
          <Box className="h-4 w-4 text-[#ffffff]" />
          {/* Named the backend that produced nothing on this page. The viewport
              renders whatever asset it is handed; it is not tied to a backend. */}
          <span className="font-bold uppercase tracking-widest">SMPL 6,890-VERTEX 3D MESH VIEWPORT</span>
          {isLoadingMesh && <RefreshCw className="h-3 w-3 text-[#a3a3a3] animate-spin ml-2" />}
        </div>

        {/* Viewport Source & Material Controls */}
        <div className="flex items-center gap-2 text-[10px]">
          {/* Mesh Source Mode Switcher */}
          <div className="flex items-center gap-1 bg-[#000000] border border-[#262626] p-1">
            <button
              onClick={() => {
                if (currentMeshRef.current && mainGroupRef.current) {
                  mainGroupRef.current.remove(currentMeshRef.current);
                  currentMeshRef.current = null;
                }
                setSourceType("glb");
              }}
              className={`px-2.5 py-0.5 transition-all uppercase font-bold ${
                sourceType === "glb"
                  ? "bg-[#ffffff] text-[#000000]"
                  : "text-[#a3a3a3] hover:text-[#ffffff] hover:bg-[#171717]"
              }`}
            >
              Animated GLB (.blend)
            </button>
            <button
              onClick={() => {
                if (currentMeshRef.current && mainGroupRef.current) {
                  mainGroupRef.current.remove(currentMeshRef.current);
                  currentMeshRef.current = null;
                }
                setSourceType("obj");
              }}
              className={`px-2.5 py-0.5 transition-all uppercase font-bold ${
                sourceType === "obj"
                  ? "bg-[#ffffff] text-[#000000]"
                  : "text-[#a3a3a3] hover:text-[#ffffff] hover:bg-[#171717]"
              }`}
            >
              OBJ Sequence (291F)
            </button>
          </div>

          {/* Viewport Material Controls */}
          <div className="flex items-center gap-1 bg-[#000000] border border-[#262626] p-1">
            {([
              { id: "wireframe", label: "Wireframe" },
              { id: "chrome", label: "Chrome" },
              { id: "matte", label: "Matte" },
              { id: "glass", label: "Translucent" },
            ] as const).map((m) => (
              <button
                key={m.id}
                onClick={() => setMeshStyle(m.id)}
                className={`px-2.5 py-0.5 transition-all uppercase ${
                  meshStyle === m.id
                    ? "bg-[#ffffff] text-[#000000] font-bold"
                    : "text-[#a3a3a3] hover:text-[#ffffff] hover:bg-[#171717]"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Three.js Rendering Container */}
      <div className="relative">
        <div ref={mountRef} style={{ height }} className="w-full cursor-grab active:cursor-grabbing relative" />
        {loadError && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#000000]/85 p-6">
            <div className="max-w-md space-y-2 border border-[#262626] bg-[#0a0a0a] p-4 text-center">
              <div className="text-xs font-bold uppercase tracking-widest text-[#ffffff]">
                Mesh asset not found
              </div>
              <p className="text-[11px] leading-relaxed text-[#a3a3a3]">
                Could not load <code className="text-[#ffffff]">{loadError}</code>. Mesh
                assets are generated output and are not committed to the repository,
                so they are absent from a fresh clone.
              </p>
              <p className="text-[11px] leading-relaxed text-[#a3a3a3]">
                See <code className="text-[#ffffff]">docs/ASSETS.md</code> for how to
                obtain or regenerate them.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-2.5 border-t border-[#262626] bg-[#0a0a0a] text-[10px] text-[#a3a3a3] flex justify-between items-center px-4">
        {/*
          Shows the asset actually loaded — this previously hardcoded
          "squat_multiview_animated.glb" regardless of the glbUrl prop, so /demo
          named a file it was not rendering. The accuracy claim that followed it
          ("Sub-centimeter", ci-allow) was never measured against a reference standard.
        */}
        <span>
          {sourceType === "glb" ? glbUrl.replace(/^\//, "") : `Frame ${activeFrame + 1} / 291`}{" "}
          • SMPL surface mesh • accuracy not validated
        </span>
        <span className="flex items-center gap-1 text-[#ffffff]">
          <Eye className="h-3 w-3 text-[#ffffff]" /> Drag mouse to rotate 360°
        </span>
      </div>
    </div>
  );
}
