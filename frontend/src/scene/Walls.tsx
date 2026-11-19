/**
 * Courtroom Architectural Enclosure: Back wall, side walls with arched windows,
 * wood wainscoting, and the Judicial Scales / State Emblem insignia.
 */

const WALL_UPPER = "#EFE8DC";
const WAINSCOT_WOOD = "#4A2E18";
const WINDOW_FRAME = "#362012";
const WINDOW_GLASS = "#D0E4F2";
const BRASS_EMBLEM = "#C89D4B";

export function Walls() {
  return (
    <group name="CourtroomArchitecture">
      {/* 1. Back Wall Behind the Judge's Bench (z = -8.5) */}
      <group position={[0, 5, -8.5]}>
        {/* Upper Plaster Wall */}
        <mesh position={[0, 2.5, 0]} receiveShadow>
          <boxGeometry args={[18, 5, 0.4]} />
          <meshStandardMaterial color={WALL_UPPER} roughness={0.9} />
        </mesh>
        {/* Lower Wood Wainscoting */}
        <mesh position={[0, -2.5, 0.05]} receiveShadow>
          <boxGeometry args={[18, 5, 0.45]} />
          <meshStandardMaterial color={WAINSCOT_WOOD} roughness={0.6} />
        </mesh>
        {/* Wainscot top chair rail molding */}
        <mesh position={[0, 0.05, 0.3]}>
          <boxGeometry args={[18.1, 0.12, 0.2]} />
          <meshStandardMaterial color="#341E0F" roughness={0.5} />
        </mesh>

        {/* Judicial Emblem (Scales of Justice / State Motif) */}
        <group position={[0, 2.8, 0.25]}>
          {/* Emblem circular backing */}
          <mesh castShadow receiveShadow>
            <cylinderGeometry args={[0.9, 0.9, 0.08, 32]} />
            <meshStandardMaterial color={BRASS_EMBLEM} metalness={0.8} roughness={0.3} />
          </mesh>
          {/* Outer concentric decorative rim */}
          <mesh position={[0, 0.02, 0]}>
            <cylinderGeometry args={[1.02, 1.02, 0.04, 32]} />
            <meshStandardMaterial color="#8C6627" metalness={0.7} roughness={0.4} />
          </mesh>
          {/* Balance Scales representation */}
          {/* Center pillar */}
          <mesh position={[0, 0.06, 0]} rotation={[0, 0, 0]}>
            <cylinderGeometry args={[0.03, 0.03, 0.9, 12]} />
            <meshStandardMaterial color="#2B2117" roughness={0.5} />
          </mesh>
          {/* Crossbeam */}
          <mesh position={[0, 0.4, 0.06]} rotation={[0, 0, Math.PI / 2]}>
            <cylinderGeometry args={[0.02, 0.02, 0.8, 12]} />
            <meshStandardMaterial color="#2B2117" roughness={0.5} />
          </mesh>
          {/* Left scale pan */}
          <mesh position={[-0.35, 0.15, 0.06]}>
            <cylinderGeometry args={[0.12, 0.02, 0.05, 16]} />
            <meshStandardMaterial color="#2B2117" roughness={0.5} />
          </mesh>
          {/* Right scale pan */}
          <mesh position={[0.35, 0.15, 0.06]}>
            <cylinderGeometry args={[0.12, 0.02, 0.05, 16]} />
            <meshStandardMaterial color="#2B2117" roughness={0.5} />
          </mesh>
        </group>
      </group>

      {/* 2. Left Wall (x = -8.5) with High Windows */}
      <group position={[-8.5, 5, 0]} rotation={[0, Math.PI / 2, 0]}>
        <mesh position={[0, 2.5, 0]} receiveShadow>
          <boxGeometry args={[20, 5, 0.4]} />
          <meshStandardMaterial color={WALL_UPPER} roughness={0.9} />
        </mesh>
        <mesh position={[0, -2.5, 0.05]} receiveShadow>
          <boxGeometry args={[20, 5, 0.45]} />
          <meshStandardMaterial color={WAINSCOT_WOOD} roughness={0.6} />
        </mesh>

        {/* Windows on left wall */}
        {[-4.5, 0, 4.5].map((zPos, idx) => (
          <group key={`win-left-${idx}`} position={[zPos, 2.8, 0.22]}>
            {/* Window frame */}
            <mesh>
              <boxGeometry args={[1.8, 2.6, 0.1]} />
              <meshStandardMaterial color={WINDOW_FRAME} roughness={0.6} />
            </mesh>
            {/* Glass pane emitting subtle daylight */}
            <mesh position={[0, 0, 0.02]}>
              <boxGeometry args={[1.5, 2.3, 0.04]} />
              <meshStandardMaterial
                color={WINDOW_GLASS}
                emissive="#FFF5E0"
                emissiveIntensity={0.25}
                transparent
                opacity={0.8}
                roughness={0.1}
              />
            </mesh>
          </group>
        ))}
      </group>

      {/* 3. Right Wall (x = 8.5) */}
      <group position={[8.5, 5, 0]} rotation={[0, -Math.PI / 2, 0]}>
        <mesh position={[0, 2.5, 0]} receiveShadow>
          <boxGeometry args={[20, 5, 0.4]} />
          <meshStandardMaterial color={WALL_UPPER} roughness={0.9} />
        </mesh>
        <mesh position={[0, -2.5, 0.05]} receiveShadow>
          <boxGeometry args={[20, 5, 0.45]} />
          <meshStandardMaterial color={WAINSCOT_WOOD} roughness={0.6} />
        </mesh>

        {/* Windows on right wall */}
        {[-4.5, 0, 4.5].map((zPos, idx) => (
          <group key={`win-right-${idx}`} position={[zPos, 2.8, 0.22]}>
            <mesh>
              <boxGeometry args={[1.8, 2.6, 0.1]} />
              <meshStandardMaterial color={WINDOW_FRAME} roughness={0.6} />
            </mesh>
            <mesh position={[0, 0, 0.02]}>
              <boxGeometry args={[1.5, 2.3, 0.04]} />
              <meshStandardMaterial
                color={WINDOW_GLASS}
                emissive="#FFF5E0"
                emissiveIntensity={0.2}
                transparent
                opacity={0.8}
                roughness={0.1}
              />
            </mesh>
          </group>
        ))}
      </group>
    </group>
  );
}

