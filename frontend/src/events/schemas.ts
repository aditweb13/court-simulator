/**
 * TypeScript event types mirroring backend/app/ws/schemas.py.
 */

export interface AuthEvent {
  type: "auth";
  token: string;
}

export interface AckEvent {
  type: "ack";
  seq: number;
}

export interface HumanActionEvent {
  type: "human_action";
  action: string;
  text?: string;
  target?: string;
}

export interface ObjectEvent {
  type: "object";
  objection_type: string;
  reason?: string;
}

export type ClientEvent = AuthEvent | AckEvent | HumanActionEvent | ObjectEvent;

export interface LineEvent {
  type: "line";
  seq: number;
  speaker: string;
  text: string;
  action?: string | null;
  emotion?: string | null;
  camera?: string | null;
  audio_url?: string | null;
}

export interface RulingEvent {
  type: "ruling";
  seq: number;
  objection_type: string;
  ruling: "sustained" | "overruled";
  struck: boolean;
  reason?: string | null;
}

export interface StateEvent {
  type: "state";
  state: string;
  previous_state?: string | null;
}

export interface PromptEvent {
  type: "prompt";
  role: string;
  options: string[];
}

export interface VerdictEvent {
  type: "verdict";
  outcome: "guilty" | "not_guilty" | "hung";
  score: number;
  threshold: number;
  disagreement: number;
  matches_truth?: boolean | null;
  reasoning?: string | null;
}

export interface ErrorEvent {
  type: "error";
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export type ServerEvent =
  | LineEvent
  | RulingEvent
  | StateEvent
  | PromptEvent
  | VerdictEvent
  | ErrorEvent;

