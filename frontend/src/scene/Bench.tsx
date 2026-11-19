/**
 * Elevated Judge's Bench and Clerk's Station.
 * Features dark polished wood, molded paneling, brass trim, gavel and sound block.
 */

const WOOD_DARK = "#422814";
const WOOD_TRIM = "#5A381E";
const WOOD_TOP = "#341E0F";
const BRASS_ACCENT = "#C89D4B";
const LEATHER_BLACK = "#1F1D1A";

export function Bench() {
  return (
    <group name="BenchAndClerk" position={[0, 0, -6]}>
      {/* 1. Elevated Judge's Platform (Dais) */}
      <mesh position={[0, 0.4, 0]} receiveShadow castShadow>
        <boxGeometry args={[7.2, 0.8, 3.6]} />
        <meshStandardMaterial color={WOOD_TRIM} roughness={0.7} />
      </mesh>

      {/* Steps up to Judge's Platform */}
      <mesh position={[-3.9, 0.2, 0]} receiveShadow castShadow>
        <boxGeometry args={[0.8, 0.4, 2.0]} />
        <meshStandardMaterial color={WOOD_TRIM} roughness={0.7} />
      </mesh>
      <mesh position={[3.9, 0.2, 0]} receiveShadow castShadow>
        <boxGeometry args={[0.8, 0.4, 2.0]} />
        <meshStandardMaterial color={WOOD_TRIM} roughness={0.7} />
      </mesh>

      {/* 2. Main Bench Front & Paneling */}
      <group position={[0, 1.45, 1.2]}>
        {/* Main front facade */}
        <mesh position={[0, 0, 0]} castShadow receiveShadow>
          <boxGeometry args={[5.2, 1.3, 0.3]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>

        {/* Decorative recessed panel left */}
        <mesh position={[-1.5, 0, 0.16]} castShadow receiveShadow>
          <boxGeometry args={[1.4, 0.9, 0.05]} />
          <meshStandardMaterial color={WOOD_TOP} roughness={0.6} />
        </mesh>
        {/* Decorative recessed panel center */}
        <mesh position={[0, 0, 0.16]} castShadow receiveShadow>
          <boxGeometry args={[1.2, 0.9, 0.05]} />
          <meshStandardMaterial color={WOOD_TOP} roughness={0.6} />
        </mesh>
        {/* Decorative recessed panel right */}
        <mesh position={[1.5, 0, 0.16]} castShadow receiveShadow>
          <boxGeometry args={[1.4, 0.9, 0.05]} />
          <meshStandardMaterial color={WOOD_TOP} roughness={0.6} />
        </mesh>

        {/* Brass Emblem / Medallion on Center Panel */}
        <mesh position={[0, 0, 0.2]} castShadow>
          <cylinderGeometry args={[0.22, 0.22, 0.04, 24]} />
          <meshStandardMaterial color={BRASS_ACCENT} metalness={0.8} roughness={0.3} />
        </mesh>

        {/* Bench Desktop with overhang */}
        <mesh position={[0, 0.7, -0.45]} castShadow receiveShadow>
          <boxGeometry args={[5.5, 0.1, 1.3]} />
          <meshStandardMaterial color={WOOD_TOP} roughness={0.4} />
        </mesh>

        {/* Side wings */}
        <mesh position={[-2.6, 0, -0.45]} rotation={[0, Math.PI / 2, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.2, 1.3, 0.3]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>
        <mesh position={[2.6, 0, -0.45]} rotation={[0, Math.PI / 2, 0]} castShadow receiveShadow>
          <boxGeometry args={[1.2, 1.3, 0.3]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>

        {/* Gavel and Sound Block on Bench Top */}
        <group position={[0.7, 0.78, -0.2]}>
          {/* Circular strike block */}
          <mesh position={[0, 0, 0]} castShadow>
            <cylinderGeometry args={[0.16, 0.18, 0.05, 16]} />
            <meshStandardMaterial color={WOOD_TOP} roughness={0.4} />
          </mesh>
          {/* Gavel head */}
          <mesh position={[0.02, 0.1, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
            <cylinderGeometry args={[0.055, 0.055, 0.22, 16]} />
            <meshStandardMaterial color={WOOD_DARK} roughness={0.4} />
          </mesh>
          {/* Gavel handle */}
          <mesh position={[0.16, 0.1, 0]} rotation={[0, 0, -Math.PI / 6]} castShadow>
            <cylinderGeometry args={[0.018, 0.022, 0.32, 12]} />
            <meshStandardMaterial color={WOOD_DARK} roughness={0.4} />
          </mesh>
        </group>

        {/* Judicial document folders & pen stand */}
        <mesh position={[-0.8, 0.76, -0.2]} rotation={[0, 0.1, 0]} castShadow>
          <boxGeometry args={[0.45, 0.04, 0.35]} />
          <meshStandardMaterial color="#E8DAC1" roughness={0.8} />
        </mesh>
      </group>

      {/* 3. High-back Judge's Chair */}
      <group position={[0, 0.8, -0.3]}>
        {/* Seat cushion */}
        <mesh position={[0, 0.55, 0]} castShadow>
          <boxGeometry args={[0.85, 0.18, 0.8]} />
          <meshStandardMaterial color={LEATHER_BLACK} roughness={0.6} />
        </mesh>
        {/* High backrest */}
        <mesh position={[0, 1.45, -0.35]} castShadow>
          <boxGeometry args={[0.85, 1.6, 0.18]} />
          <meshStandardMaterial color={LEATHER_BLACK} roughness={0.6} />
        </mesh>
        {/* Wood frame back trim */}
        <mesh position={[0, 2.3, -0.35]} castShadow>
          <boxGeometry args={[0.9, 0.15, 0.2]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>
        {/* Armrests */}
        <mesh position={[-0.45, 0.85, -0.05]} castShadow>
          <boxGeometry args={[0.1, 0.08, 0.65]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>
        <mesh position={[0.45, 0.85, -0.05]} castShadow>
          <boxGeometry args={[0.1, 0.08, 0.65]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>
      </group>

      {/* 4. Clerk's Station (Positioned just in front and lower than the bench) */}
      <group position={[-1.8, 0, 2.6]}>
        {/* Clerk Desk */}
        <mesh position={[0, 0.55, 0]} castShadow receiveShadow>
          <boxGeometry args={[2.2, 1.1, 1.0]} />
          <meshStandardMaterial color={WOOD_DARK} roughness={0.5} />
        </mesh>
        {/* Desk top */}
        <mesh position={[0, 1.12, 0]} castShadow receiveShadow>
          <boxGeometry args={[2.3, 0.06, 1.1]} />
          <meshStandardMaterial color={WOOD_TOP} roughness={0.4} />
        </mesh>
        {/* Clerk Chair */}
        <mesh position={[0, 0.5, -0.8]} castShadow>
          <boxGeometry args={[0.6, 0.1, 0.6]} />
          <meshStandardMaterial color={LEATHER_BLACK} roughness={0.7} />
        </mesh>
        <mesh position={[0, 0.95, -1.05]} castShadow>
          <boxGeometry args={[0.6, 0.8, 0.1]} />
          <meshStandardMaterial color={LEATHER_BLACK} roughness={0.7} />
        </mesh>
        {/* Court Ledger / Documents on Clerk Desk */}
        <mesh position={[0.3, 1.16, 0]} rotation={[0, -0.08, 0]} castShadow>
          <boxGeometry args={[0.5, 0.05, 0.4]} />
          <meshStandardMaterial color="#FAF0E6" roughness={0.8} />
        </mesh>
        {/* Brass Desk Reading Lamp */}
        <group position={[-0.7, 1.15, -0.2]}>
          <mesh position={[0, 0.02, 0]} castShadow>
            <cylinderGeometry args={[0.08, 0.09, 0.04, 16]} />
            <meshStandardMaterial color={BRASS_ACCENT} metalness={0.8} roughness={0.3} />
          </mesh>
          <mesh position={[0, 0.22, 0]} castShadow>
            <cylinderGeometry args={[0.015, 0.015, 0.38, 12]} />
            <meshStandardMaterial color={BRASS_ACCENT} metalness={0.8} roughness={0.3} />
          </mesh>
          <mesh position={[0, 0.42, 0]} rotation={[0, 0, Math.PI / 2]} castShadow>
            <cylinderGeometry args={[0.06, 0.06, 0.24, 16]} />
            <meshStandardMaterial color="#2E523A" roughness={0.3} />
          </mesh>
        </group>
      </group>
    </group>
  );
}

