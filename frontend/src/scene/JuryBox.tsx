/**
 * Tiered Jury Box enclosure on the courtroom side wall.
 * Features 2 tiered rows of juror chairs, wooden railings, and privacy paneling.
 */

const WOOD_BOX = "#4A2E18";
const WOOD_RAILING = "#5C3A1E";
const CHAIR_CUSHION = "#2D2620";

export function JuryBox() {
  return (
    <group name="JuryBox" position={[-5.8, 0, -2.4]} rotation={[0, Math.PI / 2, 0]}>
      {/* 1. Tiered Platforms */}
      {/* Front row platform */}
      <mesh position={[0, 0.15, 0.9]} castShadow receiveShadow>
        <boxGeometry args={[4.4, 0.3, 1.4]} />
        <meshStandardMaterial color={WOOD_BOX} roughness={0.6} />
      </mesh>
      {/* Back row raised platform */}
      <mesh position={[0, 0.45, -0.5]} castShadow receiveShadow>
        <boxGeometry args={[4.4, 0.9, 1.4]} />
        <meshStandardMaterial color={WOOD_BOX} roughness={0.6} />
      </mesh>

      {/* 2. Front Enclosing Wall / Railing */}
      <mesh position={[0, 0.85, 1.65]} castShadow receiveShadow>
        <boxGeometry args={[4.4, 1.1, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>
      <mesh position={[0, 1.42, 1.65]} castShadow>
        <boxGeometry args={[4.5, 0.08, 0.2]} />
        <meshStandardMaterial color={WOOD_BOX} roughness={0.4} />
      </mesh>

      {/* Side Return Walls */}
      <mesh position={[-2.2, 0.85, 0.6]} rotation={[0, Math.PI / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[2.2, 1.1, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>
      <mesh position={[2.2, 0.85, 0.6]} rotation={[0, Math.PI / 2, 0]} castShadow receiveShadow>
        <boxGeometry args={[2.2, 1.1, 0.1]} />
        <meshStandardMaterial color={WOOD_RAILING} roughness={0.5} />
      </mesh>

      {/* 3. Front Row Chairs (3 seats) */}
      {[-1.3, 0, 1.3].map((xOffset, idx) => (
        <group key={`front-juror-${idx}`} position={[xOffset, 0.3, 0.8]}>
          <mesh position={[0, 0.4, 0]} castShadow>
            <boxGeometry args={[0.55, 0.08, 0.52]} />
            <meshStandardMaterial color={CHAIR_CUSHION} roughness={0.7} />
          </mesh>
          <mesh position={[0, 0.8, -0.22]} castShadow>
            <boxGeometry args={[0.55, 0.72, 0.08]} />
            <meshStandardMaterial color={CHAIR_CUSHION} roughness={0.7} />
          </mesh>
          {/* Leg column */}
          <mesh position={[0, 0.2, 0]} castShadow>
            <cylinderGeometry args={[0.035, 0.035, 0.4, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.5} roughness={0.5} />
          </mesh>
        </group>
      ))}

      {/* 4. Back Row Chairs (4 seats) */}
      {[-1.5, -0.5, 0.5, 1.5].map((xOffset, idx) => (
        <group key={`back-juror-${idx}`} position={[xOffset, 0.9, -0.5]}>
          <mesh position={[0, 0.4, 0]} castShadow>
            <boxGeometry args={[0.55, 0.08, 0.52]} />
            <meshStandardMaterial color={CHAIR_CUSHION} roughness={0.7} />
          </mesh>
          <mesh position={[0, 0.8, -0.22]} castShadow>
            <boxGeometry args={[0.55, 0.72, 0.08]} />
            <meshStandardMaterial color={CHAIR_CUSHION} roughness={0.7} />
          </mesh>
          {/* Leg column */}
          <mesh position={[0, 0.2, 0]} castShadow>
            <cylinderGeometry args={[0.035, 0.035, 0.4, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.5} roughness={0.5} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

