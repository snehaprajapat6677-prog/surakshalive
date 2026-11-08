// Converts a recorded blob to 16 kHz mono 16-bit PCM WAV, a format Gnani's REST endpoint accepts.
// Gnani accepts WAV, MP3, OGG, FLAC, AAC and M4A, but not WebM, which MediaRecorder produces in Chrome and Edge.
export const TARGET_SAMPLE_RATE = 16000;

export function downmixToMono(channels) {
  if (channels.length === 0) return new Float32Array(0);
  if (channels.length === 1) return Float32Array.from(channels[0]);
  const length = channels[0].length;
  const out = new Float32Array(length);
  for (let i = 0; i < length; i++) {
    let sum = 0;
    for (const channel of channels) sum += channel[i] ?? 0;
    out[i] = sum / channels.length;
  }
  return out;
}

function writeText(view, offset, text) {
  for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
}

export function encodeWav(samples, sampleRate) {
  const dataSize = samples.length * 2;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);
  writeText(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeText(view, 8, "WAVE");
  writeText(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // byte rate
  view.setUint16(32, 2, true); // block align
  view.setUint16(34, 16, true); // bits per sample
  writeText(view, 36, "data");
  view.setUint32(40, dataSize, true);
  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return buffer;
}

export async function convertBlobToWav(blob, sampleRate = TARGET_SAMPLE_RATE) {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx || typeof OfflineAudioContext === "undefined") {
    throw new Error("This browser cannot convert audio to WAV.");
  }
  const decodeContext = new AudioCtx();
  let decoded;
  try {
    decoded = await decodeContext.decodeAudioData(await blob.arrayBuffer());
  } finally {
    decodeContext.close?.();
  }
  const frames = Math.max(1, Math.ceil(decoded.duration * sampleRate));
  const offline = new OfflineAudioContext(decoded.numberOfChannels, frames, sampleRate);
  const source = offline.createBufferSource();
  source.buffer = decoded;
  source.connect(offline.destination);
  source.start(0);
  const rendered = await offline.startRendering();
  const channels = [];
  for (let i = 0; i < rendered.numberOfChannels; i++) channels.push(rendered.getChannelData(i));
  return new Blob([encodeWav(downmixToMono(channels), sampleRate)], { type: "audio/wav" });
}
