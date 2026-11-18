/**
 * Courtroom floor plane component.
 */
export function Floor() {
  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, -0.01, 0]}
      receiveShadow
    >
      <planeGeometry args={[30, 30]} />
      <meshStandardMaterial
        color="#3A281A"
        roughness={0.7}
        metalness={0.1}
      />
    </mesh>
  );
}

