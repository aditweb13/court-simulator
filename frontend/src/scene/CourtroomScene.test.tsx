import { describe, it, expect } from "vitest";
import { Bench } from "./Bench";
import { WitnessStand } from "./WitnessStand";
import { CounselTables } from "./CounselTable";
import { JuryBox } from "./JuryBox";
import { Gallery } from "./Gallery";
import { Walls } from "./Walls";
import { Floor } from "./Floor";
import { Lighting } from "./Lighting";
import { CourtroomCanvas } from "./CourtroomCanvas";

describe("Courtroom 3D Scene Components", () => {
  it("exports all courtroom furniture and lighting components", () => {
    expect(Bench).toBeDefined();
    expect(WitnessStand).toBeDefined();
    expect(CounselTables).toBeDefined();
    expect(JuryBox).toBeDefined();
    expect(Gallery).toBeDefined();
    expect(Walls).toBeDefined();
    expect(Floor).toBeDefined();
    expect(Lighting).toBeDefined();
    expect(CourtroomCanvas).toBeDefined();
  });
});

