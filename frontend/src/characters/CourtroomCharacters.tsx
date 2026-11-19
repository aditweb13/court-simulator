import { Character, CharacterPose } from "./Character";

export interface CourtroomCharactersProps {
  activeSpeaker?: string | null;
  activeAction?: string | null;
}

export function CourtroomCharacters({
  activeSpeaker = null,
  activeAction = null,
}: CourtroomCharactersProps) {
  const getPose = (role: string, defaultPose: CharacterPose = "sit"): CharacterPose => {
    if (activeSpeaker?.toLowerCase() === role.toLowerCase()) {
      if (activeAction === "point") return "point";
      return "talk";
    }
    return defaultPose;
  };

  const isStandingSpeaker = (role: string): boolean => {
    return (
      activeSpeaker?.toLowerCase() === role.toLowerCase() &&
      (role === "prosecutor" || role === "defense" || role === "prosecution")
    );
  };

  return (
    <group name="courtroom-characters">
      {/* 1. Judge Rao — Elevated Bench Dais */}
      <Character
        name="Hon. Judge Rao"
        role="judge"
        position={[0, 0.8, -6.7]}
        rotation={[0, 0, 0]}
        state={getPose("judge", "sit")}
        robe={true}
        hairColor="#E0DDD7"
        skinTone="#C69567"
      />

      {/* 2. Court Clerk — Clerk's Desk Beside Dais */}
      <Character
        name="Court Clerk"
        role="clerk"
        position={[3.2, 0, -5.2]}
        rotation={[0, -0.2, 0]}
        state={getPose("clerk", "sit")}
        jacketColor="#22262B"
        shirtColor="#FFFFFF"
        skinTone="#B38054"
      />

      {/* 3. Special Prosecutor — Counsel Table (Left) */}
      <Character
        name="Public Prosecutor"
        role="prosecutor"
        position={[-4.2, 0, isStandingSpeaker("prosecutor") ? 1.5 : 1.8]}
        rotation={[0, Math.PI, 0]}
        state={
          isStandingSpeaker("prosecutor")
            ? activeAction === "point"
              ? "point"
              : "talk"
            : getPose("prosecution", "sit")
        }
        jacketColor="#1C1B1A"
        shirtColor="#F7F5F2"
        skinTone="#C08D5E"
      />

      {/* 4. Defense Counsel — Counsel Table (Right) */}
      <Character
        name="Defense Advocate"
        role="defense"
        position={[3.6, 0, isStandingSpeaker("defense") ? 1.5 : 1.8]}
        rotation={[0, Math.PI, 0]}
        state={
          isStandingSpeaker("defense")
            ? activeAction === "point"
              ? "point"
              : "talk"
            : getPose("defense", "sit")
        }
        jacketColor="#202228"
        shirtColor="#FFFFFF"
        skinTone="#CF9E70"
      />

      {/* 5. Accused / Defendant — Seated with Defense */}
      <Character
        name="The Accused"
        role="defendant"
        position={[4.8, 0, 1.8]}
        rotation={[0, Math.PI, 0]}
        state={getPose("defendant", "sit")}
        jacketColor="#4A453E"
        shirtColor="#C5BFB6"
        skinTone="#C89768"
      />

      {/* 6. Witness — Elevated Witness Stand */}
      <Character
        name="Witness"
        role="witness"
        position={[-6.0, 0.5, -4.0]}
        rotation={[0, Math.PI * 0.25, 0]}
        state={getPose("witness", "sit")}
        jacketColor="#35424A"
        shirtColor="#EDEAE5"
        skinTone="#B88656"
      />

      {/* 7. Juror Panel (7 Jurors) — Tiered Jury Box */}
      {/* Front Row (3 Jurors) */}
      <Character
        name="Juror 1"
        role="juror"
        position={[6.4, 0.2, -2.5]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#3B342C"
        skinTone="#C89768"
      />
      <Character
        name="Juror 2"
        role="juror"
        position={[7.2, 0.2, -2.5]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#273238"
        skinTone="#D4A373"
      />
      <Character
        name="Juror 3"
        role="juror"
        position={[8.0, 0.2, -2.5]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#4B3F38"
        skinTone="#B07D4F"
      />

      {/* Back Row (4 Jurors) */}
      <Character
        name="Juror 4"
        role="juror"
        position={[6.2, 0.5, -4.0]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#2B363B"
        skinTone="#BE8B5C"
      />
      <Character
        name="Juror 5"
        role="juror"
        position={[7.0, 0.5, -4.0]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#443B33"
        skinTone="#D9AC7E"
      />
      <Character
        name="Juror 6"
        role="juror"
        position={[7.8, 0.5, -4.0]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#2F3B3F"
        skinTone="#AE7B4E"
      />
      <Character
        name="Juror 7"
        role="juror"
        position={[8.6, 0.5, -4.0]}
        rotation={[0, -Math.PI / 2, 0]}
        state="sit"
        jacketColor="#3E3832"
        skinTone="#C59466"
      />
    </group>
  );
}
