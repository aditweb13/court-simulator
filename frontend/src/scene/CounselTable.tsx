/**
 * Counsel Tables for Prosecution (left) and Defense (right).
 * Adheres to Design.md tokens:
 * - Prosecution accent: #6A2B2B
 * - Defense accent: #2B4A6A
 */

interface CounselTableProps {
  side: "prosecution" | "defense";
  position: [number, number, number];
}

const WOOD_TABLE = "#4A2E18";
const WOOD_TOP = "#5C3A1E";
const CHAIR_LEATHER = "#28231D";

function SingleTable({ side, position }: CounselTableProps) {
  const isProsecution = side === "prosecution";
  const folderColor = isProsecution ? "#6A2B2B" : "#2B4A6A";
  const tableLabel = isProsecution ? "ProsecutionTable" : "DefenseTable";

  return (
    <group name={tableLabel} position={position}>
      {/* 1. Main Table Top */}
      <mesh position={[0, 0.98, 0]} castShadow receiveShadow>
        <boxGeometry args={[3.2, 0.08, 1.4]} />
        <meshStandardMaterial color={WOOD_TOP} roughness={0.4} />
      </mesh>

      {/* 2. Modesty Panel (Front facing gallery/judge) */}
      <mesh position={[0, 0.52, -0.62]} castShadow receiveShadow>
        <boxGeometry args={[3.1, 0.88, 0.05]} />
        <meshStandardMaterial color={WOOD_TABLE} roughness={0.6} />
      </mesh>

      {/* Side Panels / Legs */}
      <mesh position={[-1.52, 0.48, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.08, 0.96, 1.3]} />
        <meshStandardMaterial color={WOOD_TABLE} roughness={0.6} />
      </mesh>
      <mesh position={[1.52, 0.48, 0]} castShadow receiveShadow>
        <boxGeometry args={[0.08, 0.96, 1.3]} />
        <meshStandardMaterial color={WOOD_TABLE} roughness={0.6} />
      </mesh>

      {/* 3. Chairs (2 per counsel table: Counsel + Assistant/Defendant) */}
      {[-0.8, 0.8].map((xOffset, idx) => (
        <group key={idx} position={[xOffset, 0, 0.85]}>
          {/* Seat cushion */}
          <mesh position={[0, 0.48, 0]} castShadow>
            <boxGeometry args={[0.62, 0.08, 0.6]} />
            <meshStandardMaterial color={CHAIR_LEATHER} roughness={0.7} />
          </mesh>
          {/* Backrest */}
          <mesh position={[0, 0.92, 0.26]} castShadow>
            <boxGeometry args={[0.6, 0.82, 0.08]} />
            <meshStandardMaterial color={CHAIR_LEATHER} roughness={0.7} />
          </mesh>
          {/* Legs */}
          <mesh position={[-0.26, 0.24, -0.25]} castShadow>
            <cylinderGeometry args={[0.025, 0.025, 0.48, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0.26, 0.24, -0.25]} castShadow>
            <cylinderGeometry args={[0.025, 0.025, 0.48, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[-0.26, 0.24, 0.25]} castShadow>
            <cylinderGeometry args={[0.025, 0.025, 0.48, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.6} roughness={0.4} />
          </mesh>
          <mesh position={[0.26, 0.24, 0.25]} castShadow>
            <cylinderGeometry args={[0.025, 0.025, 0.48, 8]} />
            <meshStandardMaterial color="#1E1E1E" metalness={0.6} roughness={0.4} />
          </mesh>
        </group>
      ))}

      {/* 4. Desktop Props: Case folders, water carafe, notepad */}
      {/* Primary case file folder */}
      <mesh position={[-0.7, 1.04, -0.1]} rotation={[0, 0.06, 0]} castShadow>
        <boxGeometry args={[0.42, 0.04, 0.32]} />
        <meshStandardMaterial color={folderColor} roughness={0.6} />
      </mesh>
      {/* Secondary file bundle */}
      <mesh position={[-0.68, 1.08, -0.1]} rotation={[0, 0.12, 0]} castShadow>
        <boxGeometry args={[0.4, 0.03, 0.3]} />
        <meshStandardMaterial color="#F4ECE1" roughness={0.8} />
      </mesh>
      {/* Legal writing notepad */}
      <mesh position={[0.7, 1.03, -0.05]} rotation={[0, -0.04, 0]} castShadow>
        <boxGeometry args={[0.34, 0.02, 0.46]} />
        <meshStandardMaterial color="#FFF8DC" roughness={0.9} />
      </mesh>
      {/* Water carafe and glass */}
      <group position={[0.05, 1.02, -0.2]}>
        <mesh position={[0, 0.12, 0]} castShadow>
          <cylinderGeometry args={[0.07, 0.08, 0.24, 16]} />
          <meshStandardMaterial color="#B0C8D8" transparent opacity={0.5} roughness={0.2} />
        </mesh>
      </group>
    </group>
  );
}

export function CounselTables() {
  return (
    <group name="CounselTables">
      {/* Prosecution Table on Courtroom Left (facing judge) */}
      <SingleTable side="prosecution" position={[-2.7, 0, -0.6]} />

      {/* Defense Table on Courtroom Right (facing judge) */}
      <SingleTable side="defense" position={[2.7, 0, -0.6]} />
    </group>
  );
}

