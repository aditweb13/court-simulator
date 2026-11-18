import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Floor } from "./Floor";

interface CourtroomCanvasProps {
  className?: string;
}

export function CourtroomCanvas({ className = "w-full h-full min-h-[450px]" }: CourtroomCanvasProps) {
  return (
    <div
      className={className}
      role="region"
      aria-label="3D Courtroom Scene Viewport"
    >
      <Canvas
        shadows
        camera={{ position: [0, 6, 14], fov: 45 }}
        gl={{ antialias: true }}
      >
        {/* Courtroom Lighting */}
        <ambientLight intensity={0.6} color="#FFE8D6" />
        <directionalLight
          position={[5, 12, 8]}
          intensity={1.2}
          color="#FFF2E0"
          castShadow
          shadow-mapSize-width={1024}
          shadow-mapSize-height={1024}
        />
        <pointLight position={[0, 8, 0]} intensity={0.4} color="#FFD1A4" />

        {/* Scene Objects */}
        <Floor />

        {/* Camera interaction */}
        <OrbitControls
          makeDefault
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={4}
          maxDistance={25}
        />
      </Canvas>
    </div>
  );
}
