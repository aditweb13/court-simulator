import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserTTS, ROLE_VOICE_CONFIGS } from "./tts";

describe("BrowserTTS Service", () => {
  let mockSynth: {
    speak: ReturnType<typeof vi.fn>;
    cancel: ReturnType<typeof vi.fn>;
    pause: ReturnType<typeof vi.fn>;
    resume: ReturnType<typeof vi.fn>;
    getVoices: ReturnType<typeof vi.fn>;
    speaking: boolean;
    paused: boolean;
    onvoiceschanged: (() => void) | null;
  };

  beforeEach(() => {
    mockSynth = {
      speak: vi.fn(),
      cancel: vi.fn(),
      pause: vi.fn(),
      resume: vi.fn(),
      getVoices: vi.fn().mockReturnValue([
        { name: "Veena", lang: "en-IN", default: true },
        { name: "Alex", lang: "en-US", default: false },
      ]),
      speaking: false,
      paused: false,
      onvoiceschanged: null,
    };

    // Mock window.speechSynthesis
    Object.defineProperty(window, "speechSynthesis", {
      value: mockSynth,
      writable: true,
      configurable: true,
    });

    // Mock SpeechSynthesisUtterance
    class MockUtterance {
      text: string;
      pitch: number = 1.0;
      rate: number = 1.0;
      voice: unknown = null;
      constructor(text: string) {
        this.text = text;
      }
    }
    Object.defineProperty(window, "SpeechSynthesisUtterance", {
      value: MockUtterance,
      writable: true,
      configurable: true,
    });
  });

  it("checks voice configurations for all courtroom roles", () => {
    expect(ROLE_VOICE_CONFIGS.judge.pitch).toBeLessThan(1.0);
    expect(ROLE_VOICE_CONFIGS.witness.pitch).toBeGreaterThan(1.0);
    expect(ROLE_VOICE_CONFIGS.clerk.rate).toBeGreaterThan(1.0);
    expect(ROLE_VOICE_CONFIGS.prosecutor.rate).toBeGreaterThan(1.0);
  });

  it("does not speak if enabled is false", () => {
    const tts = new BrowserTTS();
    tts.setEnabled(false);
    tts.speak("judge", "Order in the court!");
    expect(mockSynth.speak).not.toHaveBeenCalled();
  });

  it("speaks dialogue with role configuration when enabled", () => {
    const tts = new BrowserTTS();
    tts.setEnabled(true);
    tts.speak("judge", "The court will now hear opening statements.");
    expect(mockSynth.cancel).toHaveBeenCalled();
    expect(mockSynth.speak).toHaveBeenCalled();
  });

  it("pauses and resumes speech correctly", () => {
    const tts = new BrowserTTS();
    mockSynth.speaking = true;
    tts.pause();
    expect(mockSynth.pause).toHaveBeenCalled();

    mockSynth.paused = true;
    tts.resume();
    expect(mockSynth.resume).toHaveBeenCalled();
  });

  it("cancels speech when disabled", () => {
    const tts = new BrowserTTS();
    tts.setEnabled(true);
    tts.setEnabled(false);
    expect(mockSynth.cancel).toHaveBeenCalled();
  });
});

