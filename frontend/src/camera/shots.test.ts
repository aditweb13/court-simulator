import { describe, it, expect } from "vitest";
import { CAMERA_SHOTS, getShotForSpeaker } from "./shots";

describe("Camera Shots Director Presets", () => {
  it("defines standard camera shots for all courtroom participants", () => {
    expect(CAMERA_SHOTS.wide).toBeDefined();
    expect(CAMERA_SHOTS.judge).toBeDefined();
    expect(CAMERA_SHOTS.witness).toBeDefined();
    expect(CAMERA_SHOTS.prosecution).toBeDefined();
    expect(CAMERA_SHOTS.defense).toBeDefined();
    expect(CAMERA_SHOTS.jury).toBeDefined();
    expect(CAMERA_SHOTS.clerk).toBeDefined();

    expect(CAMERA_SHOTS.wide.fov).toBeGreaterThan(0);
    expect(CAMERA_SHOTS.judge.position).toHaveLength(3);
    expect(CAMERA_SHOTS.judge.target).toHaveLength(3);
  });

  it("maps speakers correctly to camera angles", () => {
    expect(getShotForSpeaker("judge").name).toBe("judge");
    expect(getShotForSpeaker("prosecutor").name).toBe("prosecution");
    expect(getShotForSpeaker("defense").name).toBe("defense");
    expect(getShotForSpeaker("witness").name).toBe("witness");
    expect(getShotForSpeaker("clerk").name).toBe("clerk");
    expect(getShotForSpeaker("juror").name).toBe("jury");
    expect(getShotForSpeaker("unknown_role").name).toBe("wide");
    expect(getShotForSpeaker(null).name).toBe("wide");
  });

  it("recognizes direct shot names", () => {
    expect(getShotForSpeaker("jury").name).toBe("jury");
    expect(getShotForSpeaker("wide").name).toBe("wide");
  });
});
