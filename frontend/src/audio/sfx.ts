/**
 * Procedural Web Audio API sound effects for the courtroom simulator.
 * Generates gavel strikes, footsteps, and gallery murmurs without external audio files.
 */

export class CourtroomSFX {
  private ctx: AudioContext | null = null;
  private enabled: boolean = true;
  private murmurNode: AudioNode | null = null;

  constructor() {
    // AudioContext will be initialized on first user gesture or sound playback
  }

  private getAudioContext(): AudioContext | null {
    if (typeof window === "undefined") return null;

    if (!this.ctx) {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    }

    if (this.ctx && this.ctx.state === "suspended") {
      this.ctx.resume().catch(() => {});
    }

    return this.ctx;
  }

  public get isEnabled(): boolean {
    return this.enabled;
  }

  public setEnabled(val: boolean): void {
    this.enabled = val;
    if (!val) {
      this.stopMurmur();
    }
  }

  /**
   * Synthesize a crisp, resonant wooden gavel strike on soundboard.
   */
  public playGavel(): void {
    if (!this.enabled) return;
    const ctx = this.getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    // 1. Initial sharp impact strike (transient high snap)
    const snapOsc = ctx.createOscillator();
    const snapGain = ctx.createGain();
    snapOsc.type = "triangle";
    snapOsc.frequency.setValueAtTime(480, now);
    snapOsc.frequency.exponentialRampToValueAtTime(140, now + 0.04);

    snapGain.gain.setValueAtTime(0.8, now);
    snapGain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

    snapOsc.connect(snapGain);
    snapGain.connect(ctx.destination);

    snapOsc.start(now);
    snapOsc.stop(now + 0.05);

    // 2. Deep wooden body cavity resonance (teak soundboard)
    const woodOsc = ctx.createOscillator();
    const woodGain = ctx.createGain();
    woodOsc.type = "sine";
    woodOsc.frequency.setValueAtTime(125, now);
    woodOsc.frequency.exponentialRampToValueAtTime(80, now + 0.25);

    woodGain.gain.setValueAtTime(0.9, now);
    woodGain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    woodOsc.connect(woodGain);
    woodGain.connect(ctx.destination);

    woodOsc.start(now);
    woodOsc.stop(now + 0.35);

    // 3. Noise burst for wooden surface texture
    try {
      const bufferSize = ctx.sampleRate * 0.05;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const output = buffer.getChannelData(0);
      for (let i = 0; i < bufferSize; i++) {
        output[i] = Math.random() * 2 - 1;
      }
      const noise = ctx.createBufferSource();
      noise.buffer = buffer;

      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(1200, now);
      filter.Q.setValueAtTime(1.5, now);

      const noiseGain = ctx.createGain();
      noiseGain.gain.setValueAtTime(0.4, now);
      noiseGain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);

      noise.connect(filter);
      filter.connect(noiseGain);
      noiseGain.connect(ctx.destination);

      noise.start(now);
      noise.stop(now + 0.05);
    } catch {
      // Ignore noise buffer fallback in mocked environments
    }
  }

  /**
   * Synthesize a soft leather shoe footstep on courtroom hardwood floor.
   */
  public playFootstep(): void {
    if (!this.enabled) return;
    const ctx = this.getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(160, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.08);

    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.1);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.1);
  }

  /**
   * Start a low ambient murmur (crowd whisper) in gallery/deliberation.
   */
  public startMurmur(): void {
    if (!this.enabled || this.murmurNode) return;
    const ctx = this.getAudioContext();
    if (!ctx) return;

    try {
      const bufferSize = ctx.sampleRate * 2;
      const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
      const data = buffer.getChannelData(0);
      let b0 = 0,
        b1 = 0,
        b2 = 0;
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1;
        b0 = 0.99886 * b0 + white * 0.0555179;
        b1 = 0.99332 * b1 + white * 0.0750759;
        b2 = 0.969 * b2 + white * 0.153852;
        data[i] = (b0 + b1 + b2) * 0.1;
      }

      const noise = ctx.createBufferSource();
      noise.buffer = buffer;
      noise.loop = true;

      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.setValueAtTime(550, ctx.currentTime);
      filter.Q.setValueAtTime(2.0, ctx.currentTime);

      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.08, ctx.currentTime);

      noise.connect(filter);
      filter.connect(gain);
      gain.connect(ctx.destination);

      noise.start();
      this.murmurNode = noise;
    } catch {
      // Mocked or unsupported environments
    }
  }

  /**
   * Stop the gallery murmur.
   */
  public stopMurmur(): void {
    if (this.murmurNode) {
      try {
        (this.murmurNode as AudioScheduledSourceNode).stop();
      } catch {
        // Already stopped
      }
      this.murmurNode = null;
    }
  }
}

export const courtroomSFX = new CourtroomSFX();
