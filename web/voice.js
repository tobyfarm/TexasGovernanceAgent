// voice.js — browser-side audio plumbing for Gemini 3.1 Flash Live
// Exposes window.startVoice(runId) and window.stopVoice().
// Mic capture: 16kHz PCM mono -> WebSocket -> FastAPI /voice/{run_id} proxy -> bridge.py -> Gemini.
// Playback:    24kHz PCM mono <- WebSocket <- bridge.py <- Gemini.

(function () {
  let ws = null;
  let micStream = null;
  let audioCtx = null;
  let processor = null;
  let micSource = null;
  let playbackCtx = null;
  let playbackQueueTime = 0;

  function setStatus(text) {
    const el = document.getElementById("voice-status");
    if (el) el.textContent = text;
    console.log("[voice]", text);
  }

  function isActive() {
    return ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING);
  }

  window.startVoice = async function (runId) {
    if (isActive()) {
      console.warn("[voice] already active");
      return;
    }
    if (!runId) {
      alert("No run_id; analyze a packet first.");
      return;
    }

    setStatus("connecting...");
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/voice/${encodeURIComponent(runId)}`;
    try {
      ws = new WebSocket(url);
    } catch (e) {
      setStatus("connect failed");
      console.error(e);
      return;
    }
    ws.binaryType = "arraybuffer";

    ws.onopen = async () => {
      setStatus("requesting mic...");
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: 16000,
            channelCount: 1,
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
      } catch (e) {
        setStatus("mic denied");
        console.error(e);
        try { ws.close(); } catch {}
        return;
      }

      // Capture context — many browsers ignore the requested sampleRate, so resample if needed.
      audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
      const inputRate = audioCtx.sampleRate;
      micSource = audioCtx.createMediaStreamSource(micStream);
      processor = audioCtx.createScriptProcessor(4096, 1, 1);
      micSource.connect(processor);
      // Connect to a muted gain so the processor runs without echoing the mic to the speakers.
      const sink = audioCtx.createGain();
      sink.gain.value = 0;
      processor.connect(sink);
      sink.connect(audioCtx.destination);

      processor.onaudioprocess = (e) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        const f32 = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(maybeResample(f32, inputRate, 16000));
        ws.send(pcm16.buffer);
      };

      // Playback context fixed at 24kHz to match Gemini output.
      playbackCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      playbackQueueTime = playbackCtx.currentTime;

      setStatus("listening");
    };

    ws.onmessage = (ev) => {
      if (ev.data instanceof ArrayBuffer) {
        if (!playbackCtx) return;
        const i16 = new Int16Array(ev.data);
        if (i16.length === 0) return;
        const f32 = new Float32Array(i16.length);
        for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 0x8000;
        const buf = playbackCtx.createBuffer(1, f32.length, 24000);
        buf.copyToChannel(f32, 0);
        const node = playbackCtx.createBufferSource();
        node.buffer = buf;
        node.connect(playbackCtx.destination);
        const startAt = Math.max(playbackCtx.currentTime, playbackQueueTime);
        node.start(startAt);
        playbackQueueTime = startAt + buf.duration;
      } else {
        // Text message — likely an error JSON.
        try {
          const j = JSON.parse(ev.data);
          if (j.type === "error") setStatus(`error: ${j.message}`);
          else console.log("[voice] msg", j);
        } catch {
          console.log("[voice] text", ev.data);
        }
      }
    };

    ws.onclose = (ev) => {
      setStatus(`disconnected${ev.code ? ` (${ev.code})` : ""}`);
      cleanup();
    };
    ws.onerror = (e) => {
      setStatus("error");
      console.error("[voice] ws error", e);
    };
  };

  window.stopVoice = function () {
    setStatus("stopping...");
    if (ws) {
      try { ws.close(); } catch {}
    }
    cleanup();
    setStatus("stopped");
  };

  function cleanup() {
    try { if (processor) processor.disconnect(); } catch {}
    try { if (micSource) micSource.disconnect(); } catch {}
    try { if (audioCtx) audioCtx.close(); } catch {}
    try { if (playbackCtx) playbackCtx.close(); } catch {}
    if (micStream) {
      try { micStream.getTracks().forEach((t) => t.stop()); } catch {}
    }
    processor = null;
    micSource = null;
    audioCtx = null;
    playbackCtx = null;
    micStream = null;
    ws = null;
    playbackQueueTime = 0;
  }

  function floatTo16BitPCM(f32) {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      const s = Math.max(-1, Math.min(1, f32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  // Linear resampler — adequate for speech. No-op when rates match.
  function maybeResample(input, fromRate, toRate) {
    if (fromRate === toRate) return input;
    const ratio = fromRate / toRate;
    const outLen = Math.floor(input.length / ratio);
    const out = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const srcIdx = i * ratio;
      const i0 = Math.floor(srcIdx);
      const i1 = Math.min(i0 + 1, input.length - 1);
      const frac = srcIdx - i0;
      out[i] = input[i0] * (1 - frac) + input[i1] * frac;
    }
    return out;
  }
})();
