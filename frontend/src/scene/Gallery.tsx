/**
 * Courtroom Bar (railing) and Spectator Gallery with wooden benches/pews.
 * Separates the formal court well from public seating.
 */

const WOOD_RAIL = "#4A2E18";
const WOOD_BENCH = "#5A381E";

function WoodenPew({ position, width = 4.2 }: { position: [number, number, number]; width?: number }) {
  return (
    <group position={position}>
      {/* Bench seat */}
      <mesh position={[0, 0.45, 0]} castShadow receiveShadow>
        <boxGeometry args={[width, 0.08, 0.55]} />
        <meshStandardMaterial color={WOOD_BENCH} roughness={0.5} />
      </mesh>
      {/* Backrest */}
      <mesh position={[0, 0.88, 0.24]} castShadow receiveShadow>
        <boxGeometry args={[width, 0.78, 0.08]} />
        <meshStandardMaterial color={WOOD_BENCH} roughness={0.5} />
      </mesh>
      {/* Left side arm/support */}
      <mesh position={[-width / 2 + 0.04, 0.52, 0.08]} castShadow receiveShadow>
        <boxGeometry args={[0.08, 1.04, 0.65]} />
        <meshStandardMaterial color={WOOD_RAIL} roughness={0.5} />
      </mesh>
      {/* Right side arm/support */}
      <mesh position={[width / 2 - 0.04, 0.52, 0.08]} castShadow receiveShadow>
        <boxGeometry args={[0.08, 1.04, 0.65]} />
        <meshStandardMaterial color={WOOD_RAIL} roughness={0.5} />
      </mesh>
      {/* Center support leg */}
      <mesh position={[0, 0.22, 0]} castShadow>
        <boxGeometry args={[0.08, 0.44, 0.45]} />
        <meshStandardMaterial color={WOOD_RAIL} roughness={0.5} />
      </mesh>
    </group>
  );
}

export function Gallery() {
  return (
    <group name="CourtroomGallery">
      {/* 1. The Bar (Wood divider railing with center walkway gate) */}
      <group position={[0, 0, 2.2]}>
        {/* Left railing */}
        <mesh position={[-3.6, 0.45, 0]} castShadow receiveShadow>
          <boxGeometry args={[4.4, 0.9, 0.1]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.5} />
        </mesh>
        <mesh position={[-3.6, 0.92, 0]} castShadow>
          <boxGeometry args={[4.5, 0.08, 0.18]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.4} />
        </mesh>

        {/* Right railing */}
        <mesh position={[3.6, 0.45, 0]} castShadow receiveShadow>
          <boxGeometry args={[4.4, 0.9, 0.1]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.5} />
        </mesh>
        <mesh position={[3.6, 0.92, 0]} castShadow>
          <boxGeometry args={[4.5, 0.08, 0.18]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.4} />
        </mesh>

        {/* Center swinging gate posts */}
        <mesh position={[-1.35, 0.5, 0]} castShadow>
          <cylinderGeometry args={[0.08, 0.08, 1.05, 16]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.4} />
        </mesh>
        <mesh position={[1.35, 0.5, 0]} castShadow>
          <cylinderGeometry args={[0.08, 0.08, 1.05, 16]} />
          <meshStandardMaterial color={WOOD_RAIL} roughness={0.4} />
        </mesh>

        {/* Low center brass swing gate flaps */}
        <mesh position={[-0.6, 0.4, 0]} castShadow>
          <boxGeometry args={[1.2, 0.5, 0.04]} />
          <meshStandardMaterial color="#B88A3B" metalness={0.7} roughness={0.4} />
        </mesh>
        <mesh position={[0.6, 0.4, 0]} castShadow>
          <boxGeometry args={[1.2, 0.5, 0.04]} />
          <meshStandardMaterial color="#B88A3B" metalness={0.7} roughness={0.4} />
        </mesh>
      </group>

      {/* 2. Gallery Spectator Pews (Left & Right of center aisle) */}
      {/* Row 1 */}
      <WoodenPew position={[-3.4, 0, 3.8]} width={4.2} />
      <WoodenPew position={[3.4, 0, 3.8]} width={4.2} />

      {/* Row 2 */}
      <WoodenPew position={[-3.4, 0, 5.4]} width={4.2} />
      <WoodenPew position={[3.4, 0, 5.4]} width={4.2} />
    </group>
  );
}

