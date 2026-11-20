import { describe, it, expect, vi, beforeEach } from "vitest";
import { CourtroomSFX, courtroomSFX } from "./sfx";

interface MockAudioParam {
  setValueAtTime: ReturnType<typeof vi.fn>;
  exponentialRampToValueAtTime?: ReturnType<typeof vi.fn>;
}

interface MockOscillatorNode {
  type: string;
  frequency: MockAudioParam;
  connect: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
}

interface MockGainNode {
  gain: MockAudioParam;
  connect: ReturnType<typeof vi.fn>;
}

interface MockAudioBuffer {
  getChannelData: ReturnType<typeof vi.fn>;
}

interface MockAudioBufferSourceNode {
  buffer: unknown;
  loop: boolean;
  connect: ReturnType<typeof vi.fn>;
  start: ReturnType<typeof vi.fn>;
  stop: ReturnType<typeof vi.fn>;
}

interface MockBiquadFilterNode {
  type: string;
  frequency: MockAudioParam;
  Q: MockAudioParam;
  connect: ReturnType<typeof vi.fn>;
}

interface MockAudioContextType {
  state: string;
  currentTime: number;
  sampleRate: number;
  destination: Record<string, unknown>;
  createOscillator: ReturnType<typeof vi.fn>;
  createGain: ReturnType<typeof vi.fn>;
  createBuffer: ReturnType<typeof vi.fn>;
  createBufferSource: ReturnType<typeof vi.fn>;
  createBiquadFilter: ReturnType<typeof vi.fn>;
  resume: ReturnType<typeof vi.fn>;
}

describe("CourtroomSFX Web Audio Engine", () => {
  let mockAudioContext: MockAudioContextType;
  let mockOscillator: MockOscillatorNode;
  let mockGain: MockGainNode;
  let mockBuffer: MockAudioBuffer;
  let mockBufferSource: MockAudioBufferSourceNode;
  let mockFilter: MockBiquadFilterNode;

  beforeEach(() => {
    mockOscillator = {
      type: "sine",
      frequency: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };

    mockGain = {
      gain: {
        setValueAtTime: vi.fn(),
        exponentialRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };

    mockBuffer = {
      getChannelData: vi.fn().mockReturnValue(new Float32Array(100)),
    };

    mockBufferSource = {
      buffer: null,
      loop: false,
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    };

    mockFilter = {
      type: "bandpass",
      frequency: {
        setValueAtTime: vi.fn(),
      },
      Q: {
        setValueAtTime: vi.fn(),
      },
      connect: vi.fn(),
    };

    mockAudioContext = {
      state: "running",
      currentTime: 10,
      sampleRate: 44100,
      destination: {},
      createOscillator: vi.fn().mockReturnValue(mockOscillator),
      createGain: vi.fn().mockReturnValue(mockGain),
      createBuffer: vi.fn().mockReturnValue(mockBuffer),
      createBufferSource: vi.fn().mockReturnValue(mockBufferSource),
      createBiquadFilter: vi.fn().mockReturnValue(mockFilter),
      resume: vi.fn().mockResolvedValue(undefined),
    };

    class MockAudioContextClass {
      constructor() {
        return mockAudioContext;
      }
    }

    vi.stubGlobal("AudioContext", MockAudioContextClass);
  });

  it("initializes with SFX enabled by default", () => {
    const sfx = new CourtroomSFX();
    expect(sfx.isEnabled).toBe(true);
  });

  it("can toggle SFX state on and off", () => {
    const sfx = new CourtroomSFX();
    sfx.setEnabled(false);
    expect(sfx.isEnabled).toBe(false);

    sfx.setEnabled(true);
    expect(sfx.isEnabled).toBe(true);
  });

  it("synthesizes a gavel strike with audio nodes", () => {
    const sfx = new CourtroomSFX();
    sfx.playGavel();

    expect(mockAudioContext.createOscillator).toHaveBeenCalled();
    expect(mockAudioContext.createGain).toHaveBeenCalled();
    expect(mockOscillator.start).toHaveBeenCalled();
    expect(mockOscillator.stop).toHaveBeenCalled();
  });

  it("does not play sounds when disabled", () => {
    const sfx = new CourtroomSFX();
    sfx.setEnabled(false);
    sfx.playGavel();
    sfx.playFootstep();

    expect(mockAudioContext.createOscillator).not.toHaveBeenCalled();
  });

  it("synthesizes footstep audio", () => {
    const sfx = new CourtroomSFX();
    sfx.playFootstep();

    expect(mockAudioContext.createOscillator).toHaveBeenCalled();
    expect(mockGain.connect).toHaveBeenCalledWith(mockAudioContext.destination);
  });

  it("starts and stops gallery murmur loop", () => {
    const sfx = new CourtroomSFX();
    sfx.startMurmur();

    expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
    expect(mockBufferSource.start).toHaveBeenCalled();

    sfx.stopMurmur();
    expect(mockBufferSource.stop).toHaveBeenCalled();
  });

  it("singleton instance is exported", () => {
    expect(courtroomSFX).toBeInstanceOf(CourtroomSFX);
  });
});
