export type ShotName =
  | "wide"
  | "judge"
  | "witness"
  | "prosecution"
  | "defense"
  | "jury"
  | "clerk";

export interface CameraShot {
  name: ShotName;
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
  description: string;
}

export const CAMERA_SHOTS: Record<ShotName, CameraShot> = {
  wide: {
    name: "wide",
    position: [0, 6.5, 11],
    target: [0, 1.8, -1.5],
    fov: 48,
    description: "Wide courtroom establishing view showing dais, tables and jury",
  },
  judge: {
    name: "judge",
    position: [0, 3.2, -3.2],
    target: [0, 3.1, -6.7],
    fov: 36,
    description: "Close shot of Hon. Judge Rao on the elevated judicial dais",
  },
  witness: {
    name: "witness",
    position: [-3.8, 2.6, -1.8],
    target: [-6.0, 2.4, -4.0],
    fov: 36,
    description: "Close examination angle focused on the witness stand",
  },
  prosecution: {
    name: "prosecution",
    position: [-2.6, 2.2, 4.2],
    target: [-4.2, 1.6, 1.5],
    fov: 38,
    description: "Close angle on the Public Prosecutor table",
  },
  defense: {
    name: "defense",
    position: [2.6, 2.2, 4.2],
    target: [4.0, 1.6, 1.5],
    fov: 38,
    description: "Close angle on the Defense Counsel and Accused table",
  },
  jury: {
    name: "jury",
    position: [2.5, 3.0, -1.5],
    target: [7.2, 2.2, -3.2],
    fov: 42,
    description: "Medium angle capturing the 7-juror deliberation panel",
  },
  clerk: {
    name: "clerk",
    position: [1.8, 2.2, -2.5],
    target: [3.2, 1.8, -5.2],
    fov: 36,
    description: "Medium shot of the Court Clerk station",
  },
};

/**
 * Returns a camera shot for a given speaker or camera request string.
 */
export function getShotForSpeaker(
  speakerOrCamera?: string | null,
  fallback: ShotName = "wide",
): CameraShot {
  if (!speakerOrCamera) return CAMERA_SHOTS[fallback];

  const key = speakerOrCamera.toLowerCase().trim();

  if (key in CAMERA_SHOTS) {
    return CAMERA_SHOTS[key as ShotName];
  }

  // Role mappings to camera shots
  if (key.includes("judge")) return CAMERA_SHOTS.judge;
  if (key.includes("prosecut")) return CAMERA_SHOTS.prosecution;
  if (key.includes("defen")) return CAMERA_SHOTS.defense;
  if (key.includes("witn")) return CAMERA_SHOTS.witness;
  if (key.includes("clerk")) return CAMERA_SHOTS.clerk;
  if (key.includes("jur")) return CAMERA_SHOTS.jury;

  return CAMERA_SHOTS[fallback];
}

