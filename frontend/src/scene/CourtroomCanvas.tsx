import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { Lighting } from "./Lighting";
import { Walls } from "./Walls";
import { Floor } from "./Floor";
import { Bench } from "./Bench";
import { WitnessStand } from "./WitnessStand";
import { CounselTables } from "./CounselTable";
import { JuryBox } from "./JuryBox";
import { Gallery } from "./Gallery";

interface CourtroomCanvasProps {
  className?: string;
}

export function CourtroomCanvas({
  className = "w-full h-full min-h-[450px]",
}: CourtroomCanvasProps) {
  return (
    <div
      className={className}
      role="region"
      aria-label="3D Courtroom Scene Viewport"
    >
      <Canvas
        shadows
        camera={{ position: [0, 5.5, 9.5], fov: 46 }}
        gl={{ antialias: true }}
      >
        {/* Courtroom Lighting System */}
        <Lighting />

        {/* Architectural Room Shell */}
        <Walls />
        <Floor />

        {/* Courtroom Furniture */}
        <Bench />
        <WitnessStand />
        <CounselTables />
        <JuryBox />
        <Gallery />

        {/* Camera interaction */}
        <OrbitControls
          makeDefault
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={3}
          maxDistance={22}
          target={[0, 1.5, -2]}
        />
      </Canvas>
    </div>
  );
}
