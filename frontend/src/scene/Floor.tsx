/**
 * Courtroom floor with polished hardwood parquet and central well carpet runner.
 */

export function Floor() {
  return (
    <group name="CourtroomFloor">
      {/* 1. Main Parquet Hardwood Base Floor */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, -0.01, 0]}
        receiveShadow
      >
        <planeGeometry args={[20, 22]} />
        <meshStandardMaterial
          color="#3A2514"
          roughness={0.55}
          metalness={0.1}
        />
      </mesh>

      {/* 2. Central Well Carpet Runner (Dignified warm wine/burgundy #5C2222) */}
      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0.005, 0.5]}
        receiveShadow
      >
        <planeGeometry args={[2.2, 14]} />
        <meshStandardMaterial
          color="#4E2323"
          roughness={0.9}
        />
      </mesh>
    </group>
  );
}
