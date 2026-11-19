import { cn } from "../lib/utils";
import { CAMERA_SHOTS, ShotName } from "../camera/shots";
import { useTrialStore } from "../store/trialStore";

interface CameraControlsProps {
  className?: string;
}

export function CameraControls({ className }: CameraControlsProps) {
  const currentCameraShot = useTrialStore((state) => state.currentCameraShot);
  const setCameraShot = useTrialStore((state) => state.setCameraShot);

  const shots: { id: ShotName; label: string }[] = [
    { id: "wide", label: "Wide" },
    { id: "judge", label: "Judge" },
    { id: "clerk", label: "Clerk" },
    { id: "prosecution", label: "Prosecutor" },
    { id: "defense", label: "Defense" },
    { id: "witness", label: "Witness" },
    { id: "jury", label: "Jury" },
  ];

  return (
    <div
      className={cn(
        "flex items-center gap-1.5 p-1 bg-black/60 backdrop-blur-md rounded-[var(--radius-md)] border border-neutral-700/60 shadow-lg",
        className,
      )}
      role="toolbar"
      aria-label="Camera Shot Presets"
    >
      <span className="text-[11px] font-medium text-neutral-400 px-2 uppercase tracking-wider">
        Camera:
      </span>
      {shots.map((shot) => {
        const isActive = currentCameraShot === shot.id;
        return (
          <button
            key={shot.id}
            onClick={() => setCameraShot(shot.id)}
            className={cn(
              "px-2.5 py-1 text-xs font-medium rounded transition-all cursor-pointer",
              isActive
                ? "bg-[var(--primary)] text-white shadow-sm font-semibold"
                : "text-neutral-300 hover:text-white hover:bg-white/10",
            )}
            title={CAMERA_SHOTS[shot.id].description}
            aria-pressed={isActive}
          >
            {shot.label}
          </button>
        );
      })}
    </div>
  );
}
