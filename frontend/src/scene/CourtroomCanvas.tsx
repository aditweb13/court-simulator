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
import { CourtroomCharacters } from "../characters/CourtroomCharacters";
import { CameraDirector } from "../camera/CameraDirector";
import { useTrialStore } from "../store/trialStore";
import { Captions } from "../ui/Captions";
import { CameraControls } from "../ui/CameraControls";
import { cn } from "../lib/utils";

interface CourtroomCanvasProps {
  className?: string;
}

export function CourtroomCanvas({
  className = "w-full h-full min-h-[450px]",
}: CourtroomCanvasProps) {
  const activeSpeaker = useTrialStore((state) => state.activeSpeaker);
  const activeAction = useTrialStore((state) => state.activeAction);
  const currentCameraShot = useTrialStore((state) => state.currentCameraShot);

  return (
    <div
      className={cn("relative overflow-hidden", className)}
      role="region"
      aria-label="3D Courtroom Scene Viewport"
    >
      <Canvas
        shadows
        camera={{ position: [0, 6.5, 11], fov: 48 }}
        gl={{ antialias: true }}
      >
        {/* Dynamic Director Camera */}
        <CameraDirector shot={currentCameraShot} />

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

        {/* Living Courtroom Actors (Judge, Clerk, Lawyers, Witness, Jurors) */}
        <CourtroomCharacters
          activeSpeaker={activeSpeaker}
          activeAction={activeAction}
        />

        {/* Orbit controls for free look when needed */}
        <OrbitControls
          makeDefault
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={3}
          maxDistance={24}
          target={[0, 1.8, -1.5]}
        />
      </Canvas>

      {/* Floating Camera Angle Selector (top right) */}
      <div className="absolute top-4 right-4 z-10 pointer-events-auto">
        <CameraControls />
      </div>

      {/* Dynamic Subtitle Captions Overlay (bottom) */}
      <Captions />
    </div>
  );
}
