import { describe, it, expect } from "vitest";
import { Character } from "./Character";
import { CourtroomCharacters } from "./CourtroomCharacters";

describe("Courtroom Characters", () => {
  it("exports Character and CourtroomCharacters components", () => {
    expect(Character).toBeDefined();
    expect(CourtroomCharacters).toBeDefined();
  });
});
