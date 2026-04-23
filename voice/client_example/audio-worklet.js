// AudioWorklet that converts the mic input (AudioContext sample rate, typ.
// 44.1/48 kHz Float32) down to 16 kHz 16-bit little-endian PCM and posts
// each chunk back to the main thread as a transferable ArrayBuffer.

class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const processorOpts = options?.processorOptions ?? {};
    this.targetRate = processorOpts.targetRate ?? 16000;
    this.sourceRate = sampleRate;
    this.ratio = this.sourceRate / this.targetRate;
    // Emit ~50ms at 16kHz (800 samples, 1600 bytes) per message.
    this.chunkSamples = Math.round(this.targetRate * 0.05);
    this.outBuffer = new Int16Array(this.chunkSamples);
    this.outIdx = 0;
    this.srcPhase = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const channel = input[0]; // mono — first channel only
    if (!channel) return true;

    // Linear interpolation downsample from source rate to target rate.
    let phase = this.srcPhase;
    while (phase < channel.length) {
      const i = Math.floor(phase);
      const frac = phase - i;
      const a = channel[i] || 0;
      const b = channel[i + 1] ?? a;
      const sample = a + (b - a) * frac;
      // Clamp and convert float [-1, 1] to int16.
      const clipped = Math.max(-1, Math.min(1, sample));
      this.outBuffer[this.outIdx++] =
        clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
      if (this.outIdx === this.chunkSamples) {
        const copy = this.outBuffer.slice().buffer;
        this.port.postMessage(copy, [copy]);
        this.outIdx = 0;
      }
      phase += this.ratio;
    }
    this.srcPhase = phase - channel.length;
    return true;
  }
}

registerProcessor("pcm-capture", PcmCaptureProcessor);
