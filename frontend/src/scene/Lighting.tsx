/**
 * Courtroom lighting setup: warm, dignified illumination with soft shadows.
 * Adheres to Design.md aesthetic (warm ambient, directional sunlight, warm point accents).
 */

export function Lighting() {
  return (
    <group name="CourtroomLighting">
      {/* Soft warm ambient fill for consistent baseline visibility */}
      <ambientLight intensity={0.65} color="#FAF0E6" />

      {/* Main directional sunbeam through courtroom high windows */}
      <directionalLight
        position={[8, 14, 6]}
        intensity={1.3}
        color="#FFF4DE"
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
        shadow-camera-near={0.5}
        shadow-camera-far={35}
        shadow-camera-left={-12}
        shadow-camera-right={12}
        shadow-camera-top={12}
        shadow-camera-bottom={-12}
        shadow-bias={-0.0005}
      />

      {/* Soft cool fill from opposite side */}
      <directionalLight position={[-8, 10, -4]} intensity={0.35} color="#E8EEF5" />

      {/* Warm focused downlight over the Judge's Bench */}
      <pointLight position={[0, 7.5, -5.5]} intensity={0.9} distance={12} color="#FFDCA8" />

      {/* Accent lights over Witness Stand */}
      <pointLight position={[3.8, 5.5, -4.8]} intensity={0.6} distance={8} color="#FFE6C2" />

      {/* Gentle illumination over Counsel Well */}
      <pointLight position={[0, 6, 0.5]} intensity={0.5} distance={14} color="#FFF2DB" />
    </group>
  );
}

