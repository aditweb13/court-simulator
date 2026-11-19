import { useEffect, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { CAMERA_SHOTS, ShotName } from "./shots";
import { usePrefersReducedMotion } from "../lib/useReducedMotion";

export interface CameraDirectorProps {
  shot?: ShotName;
  enabled?: boolean;
}

export function CameraDirector({
  shot = "wide",
  enabled = true,
}: CameraDirectorProps) {
  const reducedMotion = usePrefersReducedMotion();

  const currentLookAtRef = useRef(new THREE.Vector3(0, 1.8, -1.5));
  const targetLookAtRef = useRef(new THREE.Vector3(0, 1.8, -1.5));
  const targetPosRef = useRef(new THREE.Vector3(0, 6.5, 11));
  const targetFovRef = useRef<number>(48);
  const needsInstantCutRef = useRef<boolean>(false);

  // Update target when shot prop changes
  useEffect(() => {
    const config = CAMERA_SHOTS[shot] || CAMERA_SHOTS.wide;
    targetPosRef.current.set(...config.position);
    targetLookAtRef.current.set(...config.target);
    targetFovRef.current = config.fov;
    if (reducedMotion) {
      needsInstantCutRef.current = true;
    }
  }, [shot, reducedMotion]);

  useFrame((state, delta) => {
    if (!enabled) return;
    const cam = state.camera;

    if (reducedMotion || needsInstantCutRef.current) {
      needsInstantCutRef.current = false;
      cam.position.copy(targetPosRef.current);
      currentLookAtRef.current.copy(targetLookAtRef.current);
      cam.lookAt(currentLookAtRef.current);
      if ("fov" in cam && typeof (cam as THREE.PerspectiveCamera).fov === "number") {
        (cam as THREE.PerspectiveCamera).fov = targetFovRef.current;
        (cam as THREE.PerspectiveCamera).updateProjectionMatrix();
      }
      return;
    }

    // Smooth lerp speed (scaled by delta)
    const lerpSpeed = Math.min(delta * 2.5, 1.0);

    // Lerp camera position
    cam.position.lerp(targetPosRef.current, lerpSpeed);

    // Lerp camera lookAt vector
    currentLookAtRef.current.lerp(targetLookAtRef.current, lerpSpeed);
    cam.lookAt(currentLookAtRef.current);

    // Lerp FOV if perspective camera
    if ("fov" in cam && typeof (cam as THREE.PerspectiveCamera).fov === "number") {
      const pCam = cam as THREE.PerspectiveCamera;
      const diff = Math.abs(pCam.fov - targetFovRef.current);
      if (diff > 0.05) {
        pCam.fov = THREE.MathUtils.lerp(pCam.fov, targetFovRef.current, lerpSpeed);
        pCam.updateProjectionMatrix();
      }
    }
  });

  return null;
}
