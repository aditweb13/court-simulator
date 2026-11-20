/**
 * Browser-native Text-to-Speech (TTS) integration using the Web Speech API.
 * Provides per-role voice parameters (pitch, rate, preferred voice) and controls.
 */

export interface RoleVoiceConfig {
  pitch: number;
  rate: number;
  genderHint?: "male" | "female";
}

export const ROLE_VOICE_CONFIGS: Record<string, RoleVoiceConfig> = {
  judge: { pitch: 0.85, rate: 0.9 }, // Authoritative, solemn, lower pitch
  clerk: { pitch: 1.0, rate: 1.05 }, // Formal, neutral, brisk
  prosecutor: { pitch: 1.05, rate: 1.05 }, // Assertive, energetic
  defense: { pitch: 0.95, rate: 0.95 }, // Composed, measured, deliberate
  witness: { pitch: 1.1, rate: 0.9 }, // Slightly higher, expressive, hesitant
  defendant: { pitch: 1.0, rate: 0.85 }, // Anxious, cautious, slow
  juror: { pitch: 1.0, rate: 1.0 }, // Grounded, conversational
};

export class BrowserTTS {
  private synth: SpeechSynthesis | null = null;
  private voices: SpeechSynthesisVoice[] = [];
  private enabled: boolean = false;

  constructor() {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      this.synth = window.speechSynthesis;
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  public get isSupported(): boolean {
    return this.synth !== null;
  }

  public get isEnabled(): boolean {
    return this.enabled;
  }

  public setEnabled(val: boolean): void {
    this.enabled = val;
    if (!val) {
      this.cancel();
    }
  }

  private loadVoices(): void {
    if (!this.synth) return;
    this.voices = this.synth.getVoices();
  }

  /**
   * Select a voice matching the language or character preferences.
   * Prefers Indian English (en-IN) then standard English.
   */
  private selectVoice(): SpeechSynthesisVoice | null {
    if (this.voices.length === 0) return null;

    // Prefer en-IN for Indian BNS courtroom simulation
    const inVoice = this.voices.find(
      (v) => v.lang === "en-IN" || v.lang.startsWith("en-IN"),
    );
    if (inVoice) return inVoice;

    // Fall back to any English voice
    const enVoice = this.voices.find((v) => v.lang.startsWith("en"));
    if (enVoice) return enVoice;

    return this.voices[0] || null;
  }

  /**
   * Speak a line of courtroom dialogue with role-specific acoustics.
   */
  public speak(speaker: string, text: string): void {
    if (!this.synth || !this.enabled || !text) return;

    this.synth.cancel(); // Cancel any lingering utterance

    const cleanText = text.replace(/[*_#`]/g, "").trim();
    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const config = ROLE_VOICE_CONFIGS[speaker.toLowerCase()] || {
      pitch: 1.0,
      rate: 1.0,
    };

    utterance.pitch = config.pitch;
    utterance.rate = config.rate;

    const voice = this.selectVoice();
    if (voice) {
      utterance.voice = voice;
    }

    this.synth.speak(utterance);
  }

  public pause(): void {
    if (this.synth && this.synth.speaking) {
      this.synth.pause();
    }
  }

  public resume(): void {
    if (this.synth && this.synth.paused) {
      this.synth.resume();
    }
  }

  public cancel(): void {
    if (this.synth) {
      this.synth.cancel();
    }
  }
}

export const browserTTS = new BrowserTTS();

