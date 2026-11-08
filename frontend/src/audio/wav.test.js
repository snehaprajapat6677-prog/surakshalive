import { test } from "node:test";
import assert from "node:assert/strict";
import { downmixToMono, encodeWav } from "./wav.js";

function readText(buffer, offset, length) {
  return String.fromCharCode(...new Uint8Array(buffer, offset, length));
}

test("encodeWav writes a 16-bit mono PCM header at the requested rate", () => {
  const buffer = encodeWav(new Float32Array([0, 0.5, -0.5, 1, -1]), 16000);
  const view = new DataView(buffer);
  assert.equal(readText(buffer, 0, 4), "RIFF");
  assert.equal(readText(buffer, 8, 4), "WAVE");
  assert.equal(readText(buffer, 12, 4), "fmt ");
  assert.equal(view.getUint32(16, true), 16);
  assert.equal(view.getUint16(20, true), 1, "PCM");
  assert.equal(view.getUint16(22, true), 1, "mono");
  assert.equal(view.getUint32(24, true), 16000, "sample rate");
  assert.equal(view.getUint32(28, true), 32000, "byte rate");
  assert.equal(view.getUint16(34, true), 16, "bits per sample");
  assert.equal(readText(buffer, 36, 4), "data");
  assert.equal(view.getUint32(40, true), 10, "data bytes");
  assert.equal(buffer.byteLength, 54);
});

test("encodeWav scales and clamps samples to the 16-bit range", () => {
  const view = new DataView(encodeWav(new Float32Array([0.5, 1, -1, 2, -2, 0]), 16000));
  assert.ok(Math.abs(view.getInt16(44, true) - 16383) <= 1);
  assert.equal(view.getInt16(46, true), 32767);
  assert.equal(view.getInt16(48, true), -32768);
  assert.equal(view.getInt16(50, true), 32767, "values above 1 clamp");
  assert.equal(view.getInt16(52, true), -32768, "values below -1 clamp");
  assert.equal(view.getInt16(54, true), 0, "last sample is zero");
});

test("encodeWav output records the sample count", () => {
  const samples = new Float32Array(16000);
  const buffer = encodeWav(samples, 16000);
  assert.equal(new DataView(buffer).getUint32(40, true), samples.length * 2);
});

test("downmixToMono averages channels and passes mono through", () => {
  const stereo = downmixToMono([Float32Array.from([1, 0, -1]), Float32Array.from([0, 0, 1])]);
  assert.deepEqual(Array.from(stereo), [0.5, 0, 0]);
  assert.deepEqual(Array.from(downmixToMono([Float32Array.from([0.25, -0.25])])), [0.25, -0.25]);
  assert.equal(downmixToMono([]).length, 0);
});
