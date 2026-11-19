/**
 * Witness Stand: An elevated wooden box with railings, microphone, and seat.
 * Positioned beside the judge's bench facing the well and jury.
 */

const WOOD_FRAME = "#4A2E18";
const WOOD_RAILING = "#6B4423";
const BRASS_ACCENT = "#C89D4B";
const METAL_MIC = "#2B2A28";

export function WitnessStand() {
  return (
    <group name="WitnessStand" position={[3.6, 0, -4.8]}>
      {/* 1. Base Platform (Elevated) */}
      <mesh position={[0, 0.25, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.8, 0.5, 1.8]} />
        <meshStandardMaterial color={WOOD_FRAME} roughness={0.6} />
      </mesh>

      {/* Entry step */}
      <mesh position={[-1.1, 0.12, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.5, 0.24, 0.9]} />
        <meshStandardMaterial color={WOOD_FRAME} roughness={0.6} />
      </mesh>

      {/* 2. Enclosing Railings (Front, Right, Back) */}
      {/* Front rail facing courtroom well */}
      <mesh position={[0, 0.95, 0.85]} castShadow receiveShadow>
        <boxGeometry args={[1.8, 0.9, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>

      {/* Front cap rail */}
      <mesh position={[0, 1.42, 0.85]} castShadow>
        <boxGeometry args={[1.9, 0.08, 0.18]} />
        <meshStandardMaterial color={WOOD_FRAME} roughness={0.4} />
      </mesh>

      {/* Outer side rail (right) */}
      <mesh position={[0.85, 0.95, 0]} rotation={[0, Math.PI / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.8, 0.9, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>
      <mesh position={[0.85, 1.42, 0]} rotation={[0, Math.PI / 2, 0]} castShadow>
        <boxGeometry args={[1.9, 0.08, 0.18]} />
        <meshStandardMaterial color={WOOD_FRAME} roughness={0.4} />
      </mesh>

      {/* Back rail */}
      <mesh position={[0, 0.95, -0.85]} castShadow receiveShadow>
        <boxGeometry args={[1.8, 0.9, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>

      {/* 3. Witness Swivel Armchair */}
      <group position={[0, 0.5, -0.1]}>
        {/* Base pedestal */}
        <mesh position={[0, 0.2, 0]} castShadow>
          <cylinderGeometry args={[0.04, 0.04, 0.4, 12]} />
          <meshStandardMaterial color="#1E1E1E" metalness={0.7} roughness={0.4} />
        </mesh>
        <mesh position={[0, 0.02, 0]} castShadow>
          <cylinderGeometry args={[0.26, 0.26, 0.04, 16]} />
          <meshStandardMaterial color="#1E1E1E" metalness={0.7} roughness={0.4} />
        </mesh>
        {/* Seat cushion */}
        <mesh position={[0, 0.44, 0]} castShadow>
          <boxGeometry args={[0.65, 0.1, 0.6]} />
          <meshStandardMaterial color="#2B2621" roughness={0.7} />
        </mesh>
        {/* Chair back */}
        <mesh position={[0, 0.85, -0.27]} castShadow>
          <boxGeometry args={[0.62, 0.75, 0.08]} />
          <meshStandardMaterial color="#2B2621" roughness={0.7} />
        </mesh>
      </group>

      {/* 4. Gooseneck Courtroom Microphone */}
      <group position={[-0.45, 1.45, 0.8]}>
        {/* Base mount */}
        <mesh position={[0, 0.02, 0]} castShadow>
          <cylinderGeometry args={[0.04, 0.05, 0.03, 16]} />
          <meshStandardMaterial color={BRASS_ACCENT} metalness={0.8} roughness={0.3} />
        </mesh>
        {/* Curved stem */}
        <mesh position={[0, 0.18, -0.06]} rotation={[0.4, 0, 0]} castShadow>
          <cylinderGeometry args={[0.009, 0.009, 0.35, 12]} />
          <meshStandardMaterial color={METAL_MIC} roughness={0.4} />
        </mesh>
        {/* Mic head */}
        <mesh position={[0, 0.32, -0.16]} rotation={[0.6, 0, 0]} castShadow>
          <cylinderGeometry args={[0.02, 0.02, 0.07, 12]} />
          <meshStandardMaterial color="#111111" roughness={0.9} />
        </mesh>
      </group>

      {/* Oath Book (Constitution / Holy book) on stand ledge */}
      <mesh position={[0.3, 1.48, 0.82]} rotation={[0.1, -0.1, 0]} castShadow>
        <boxGeometry args={[0.3, 0.04, 0.22]} />
        <meshStandardMaterial color="#8A2B2B" roughness={0.6} />
      </mesh>
    </group>
  );
}

