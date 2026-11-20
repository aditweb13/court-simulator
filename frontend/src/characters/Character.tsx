import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { usePrefersReducedMotion } from "../lib/useReducedMotion";

export type CharacterPose = "sit" | "stand" | "talk" | "point" | "react" | "gavel";

export interface CharacterProps {
  name: string;
  role: string;
  position: [number, number, number];
  rotation?: [number, number, number];
  state?: CharacterPose;
  robe?: boolean;
  skinTone?: string;
  hairColor?: string;
  jacketColor?: string;
  shirtColor?: string;
  scale?: number;
}

export function Character({
  name,
  role,
  position,
  rotation = [0, 0, 0],
  state = "sit",
  robe = false,
  skinTone = "#D2A679",
  hairColor = "#2C221E",
  jacketColor = "#2C2C2C",
  shirtColor = "#EDEAE5",
  scale = 1.0,
}: CharacterProps) {
  const reducedMotion = usePrefersReducedMotion();
  const headRef = useRef<THREE.Group>(null);
  const jawRef = useRef<THREE.Group>(null);
  const rightArmRef = useRef<THREE.Group>(null);
  const leftArmRef = useRef<THREE.Group>(null);
  const bodyRef = useRef<THREE.Group>(null);

  const isSeated = state === "sit" || (state === "react" && role === "juror");
  const isTalking = state === "talk";
  const isPointing = state === "point";
  const isGavel = state === "gavel";
  const isReacting = state === "react";

  // Animation frame for talking, lip sync, and reaction states
  useFrame(({ clock }) => {
    if (reducedMotion) return;
    const t = clock.getElapsedTime();

    if (isTalking) {
      if (headRef.current) {
        headRef.current.rotation.x = Math.sin(t * 7) * 0.06;
        headRef.current.rotation.y = Math.cos(t * 3.5) * 0.08;
      }
      // Lip sync modulation driven by speech audio cadence
      if (jawRef.current) {
        const speechOpen = Math.abs(Math.sin(t * 13)) * 0.02;
        jawRef.current.position.y = 0.14 - speechOpen;
      }
      if (rightArmRef.current && !isPointing && !isGavel) {
        rightArmRef.current.rotation.x = -0.4 + Math.sin(t * 4) * 0.16;
        rightArmRef.current.rotation.z = Math.cos(t * 3) * 0.08;
      }
      if (bodyRef.current) {
        bodyRef.current.position.y = (isSeated ? 0 : 0.02) + Math.sin(t * 4) * 0.015;
        bodyRef.current.rotation.x = 0;
      }
    } else if (isGavel) {
      // Judicial gavel strike motion
      if (headRef.current) {
        headRef.current.rotation.x = 0.1;
      }
      if (jawRef.current) {
        jawRef.current.position.y = 0.14;
      }
      if (rightArmRef.current) {
        rightArmRef.current.rotation.x = -1.1 + Math.abs(Math.sin(t * 8)) * 0.8;
      }
    } else if (isReacting) {
      // Reaction: leaning forward attentively, slight head tilt
      if (headRef.current) {
        headRef.current.rotation.x = 0.12 + Math.sin(t * 2) * 0.02;
        headRef.current.rotation.y = -0.12 + Math.cos(t * 1.5) * 0.03;
      }
      if (jawRef.current) {
        jawRef.current.position.y = 0.14;
      }
      if (bodyRef.current) {
        bodyRef.current.position.y = (isSeated ? 0 : 0.02) + 0.01;
        bodyRef.current.rotation.x = 0.08;
      }
    } else {
      // Idle breathing
      if (headRef.current) {
        headRef.current.rotation.x = Math.sin(t * 1.5) * 0.015;
        headRef.current.rotation.y = 0;
      }
      if (jawRef.current) {
        jawRef.current.position.y = 0.14;
      }
      if (bodyRef.current) {
        bodyRef.current.position.y = Math.sin(t * 1.5) * 0.005;
        bodyRef.current.rotation.x = 0;
      }
    }
  });

  // Material colors
  const skinMaterial = <meshStandardMaterial color={skinTone} roughness={0.7} />;
  const hairMaterial = <meshStandardMaterial color={hairColor} roughness={0.9} />;
  const jacketMat = (
    <meshStandardMaterial
      color={robe ? "#121212" : jacketColor}
      roughness={0.8}
    />
  );
  const shirtMat = <meshStandardMaterial color={shirtColor} roughness={0.6} />;
  const pantsMat = <meshStandardMaterial color="#1E1E1E" roughness={0.85} />;

  // Seated vs Standing adjustments
  const torsoBaseY = isSeated ? 0.55 : 0.85;

  return (
    <group
      position={position}
      rotation={rotation}
      scale={scale}
      name={`character-${role}-${name}`}
    >
      <group ref={bodyRef}>
        {/* === LEGS === */}
        {isSeated ? (
          // Seated legs: thighs forward, shins down
          <group position={[0, 0, 0]}>
            {/* Left Leg */}
            <group position={[-0.14, 0.5, 0]}>
              <mesh position={[0, 0, 0.22]} rotation={[Math.PI / 2, 0, 0]} castShadow>
                <cylinderGeometry args={[0.07, 0.07, 0.44, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.25, 0.44]} castShadow>
                <cylinderGeometry args={[0.065, 0.06, 0.5, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.48, 0.48]} castShadow>
                <boxGeometry args={[0.11, 0.08, 0.2]} />
                <meshStandardMaterial color="#111111" roughness={0.5} />
              </mesh>
            </group>

            {/* Right Leg */}
            <group position={[0.14, 0.5, 0]}>
              <mesh position={[0, 0, 0.22]} rotation={[Math.PI / 2, 0, 0]} castShadow>
                <cylinderGeometry args={[0.07, 0.07, 0.44, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.25, 0.44]} castShadow>
                <cylinderGeometry args={[0.065, 0.06, 0.5, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.48, 0.48]} castShadow>
                <boxGeometry args={[0.11, 0.08, 0.2]} />
                <meshStandardMaterial color="#111111" roughness={0.5} />
              </mesh>
            </group>
          </group>
        ) : (
          // Standing legs: vertical
          <group position={[0, 0, 0]}>
            {/* Left Leg */}
            <group position={[-0.14, 0.42, 0]}>
              <mesh castShadow>
                <cylinderGeometry args={[0.075, 0.065, 0.85, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.42, 0.06]} castShadow>
                <boxGeometry args={[0.11, 0.08, 0.22]} />
                <meshStandardMaterial color="#111111" roughness={0.5} />
              </mesh>
            </group>
            {/* Right Leg */}
            <group position={[0.14, 0.42, 0]}>
              <mesh castShadow>
                <cylinderGeometry args={[0.075, 0.065, 0.85, 8]} />
                {pantsMat}
              </mesh>
              <mesh position={[0, -0.42, 0.06]} castShadow>
                <boxGeometry args={[0.11, 0.08, 0.22]} />
                <meshStandardMaterial color="#111111" roughness={0.5} />
              </mesh>
            </group>
          </group>
        )}

        {/* === TORSO === */}
        <group position={[0, torsoBaseY, 0]}>
          <mesh position={[0, 0.3, 0]} castShadow receiveShadow>
            <boxGeometry args={[0.42, 0.6, 0.24]} />
            {jacketMat}
          </mesh>

          {/* Shirt / Neckband */}
          <mesh position={[0, 0.42, 0.125]}>
            <boxGeometry args={[0.14, 0.3, 0.01]} />
            {shirtMat}
          </mesh>

          {/* Legal Collar Bands */}
          {(robe || role === "prosecutor" || role === "defense") && (
            <group position={[0, 0.52, 0.135]}>
              <mesh position={[-0.03, -0.06, 0]} rotation={[0, 0, -0.1]}>
                <boxGeometry args={[0.035, 0.12, 0.005]} />
                <meshStandardMaterial color="#FFFFFF" roughness={0.3} />
              </mesh>
              <mesh position={[0.03, -0.06, 0]} rotation={[0, 0, 0.1]}>
                <boxGeometry args={[0.035, 0.12, 0.005]} />
                <meshStandardMaterial color="#FFFFFF" roughness={0.3} />
              </mesh>
            </group>
          )}

          {/* Judicial / Advocate Robe Overlap */}
          {robe && (
            <group>
              <mesh position={[0, 0.2, -0.13]} castShadow>
                <boxGeometry args={[0.46, 0.75, 0.04]} />
                {jacketMat}
              </mesh>
              <mesh position={[-0.23, 0.35, 0]} castShadow>
                <boxGeometry args={[0.08, 0.45, 0.26]} />
                {jacketMat}
              </mesh>
              <mesh position={[0.23, 0.35, 0]} castShadow>
                <boxGeometry args={[0.08, 0.45, 0.26]} />
                {jacketMat}
              </mesh>
            </group>
          )}

          {/* === HEAD & NECK === */}
          <group ref={headRef} position={[0, 0.62, 0]}>
            {/* Neck */}
            <mesh position={[0, 0.06, 0]} castShadow>
              <cylinderGeometry args={[0.06, 0.07, 0.12, 8]} />
              {skinMaterial}
            </mesh>

            {/* Head */}
            <mesh position={[0, 0.22, 0]} castShadow>
              <sphereGeometry args={[0.13, 16, 16]} />
              {skinMaterial}
            </mesh>

            {/* Hair */}
            <mesh position={[0, 0.26, -0.02]} castShadow>
              <sphereGeometry args={[0.135, 12, 12, 0, Math.PI * 2, 0, Math.PI * 0.6]} />
              {hairMaterial}
            </mesh>

            {/* Nose */}
            <mesh position={[0, 0.21, 0.13]}>
              <boxGeometry args={[0.025, 0.04, 0.03]} />
              {skinMaterial}
            </mesh>

            {/* Articulated Jaw & Lips for Speech Lip Sync */}
            <group ref={jawRef} position={[0, 0.14, 0.11]}>
              {/* Lower lip / chin */}
              <mesh position={[0, -0.01, 0.01]}>
                <boxGeometry args={[0.045, 0.02, 0.015]} />
                {skinMaterial}
              </mesh>
              {/* Mouth aperture */}
              <mesh position={[0, 0.005, 0.01]}>
                <boxGeometry args={[0.035, 0.008, 0.005]} />
                <meshStandardMaterial color="#5C2525" roughness={0.6} />
              </mesh>
            </group>
          </group>

          {/* === ARMS === */}
          {/* Left Arm */}
          <group
            ref={leftArmRef}
            position={[-0.24, 0.5, 0]}
            rotation={isSeated ? [0.4, 0, 0.1] : [0.1, 0, 0.05]}
          >
            <mesh position={[0, -0.18, 0]} castShadow>
              <cylinderGeometry args={[0.06, 0.055, 0.36, 8]} />
              {jacketMat}
            </mesh>
            <mesh position={[0, -0.42, 0.08]} rotation={[-0.3, 0, 0]} castShadow>
              <cylinderGeometry args={[0.05, 0.045, 0.34, 8]} />
              {jacketMat}
            </mesh>
            <mesh position={[0, -0.6, 0.16]} castShadow>
              <boxGeometry args={[0.07, 0.09, 0.04]} />
              {skinMaterial}
            </mesh>
          </group>

          {/* Right Arm */}
          <group
            ref={rightArmRef}
            position={[0.24, 0.5, 0]}
            rotation={
              isPointing
                ? [-1.3, 0, -0.2]
                : isGavel
                  ? [-0.9, 0, 0.1]
                  : isSeated
                    ? [0.4, 0, -0.1]
                    : [0.1, 0, -0.05]
            }
          >
            <mesh position={[0, -0.18, 0]} castShadow>
              <cylinderGeometry args={[0.06, 0.055, 0.36, 8]} />
              {jacketMat}
            </mesh>
            <mesh
              position={[0, -0.42, isPointing ? 0.02 : 0.08]}
              rotation={isPointing ? [-0.1, 0, 0] : [-0.3, 0, 0]}
              castShadow
            >
              <cylinderGeometry args={[0.05, 0.045, 0.34, 8]} />
              {jacketMat}
            </mesh>
            <mesh
              position={[0, -0.6, isPointing ? 0.04 : 0.16]}
              castShadow
            >
              <boxGeometry args={[0.07, 0.09, 0.04]} />
              {skinMaterial}
            </mesh>
          </group>
        </group>
      </group>
    </group>
  );
}
