import { useEffect, useRef, useState } from "react";
import { convertBlobToWav } from "../audio/wav.js";

// Gnani's REST endpoint accepts clips up to 30 seconds.
export const MAX_SECONDS = 30;

function pickMimeType() {
  const options = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
  return options.find((type) => window.MediaRecorder?.isTypeSupported?.(type)) ?? "";
}

function permissionMessage(err) {
  switch (err?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Microphone permission was denied. Allow microphone access in your browser settings and try again.";
    case "NotFoundError":
      return "No microphone was found on this device.";
    case "NotReadableError":
      return "The microphone is in use by another app.";
    default:
      return "Could not start the microphone.";
  }
}

export default function Recorder({ onAudio, disabled }) {
  const [recording, setRecording] = useState(false);
  const [converting, setConverting] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [notice, setNotice] = useState("");
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const onAudioRef = useRef(onAudio);

  useEffect(() => {
    onAudioRef.current = onAudio;
  }, [onAudio]);

  useEffect(() => {
    return () => {
      const recorder = recorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.onstop = null;
        recorder.stop();
      }
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  useEffect(() => {
    if (!recording) return undefined;
    const id = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [recording]);

  async function start() {
    setNotice("");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setNotice("This browser cannot record audio. Upload a WAV, MP3 or OGG file instead.");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      setNotice(permissionMessage(err));
      return;
    }
    const mimeType = pickMimeType();
    const recorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);
    chunksRef.current = [];
    streamRef.current = stream;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      const type = recorder.mimeType || mimeType || "audio/webm";
      const blob = new Blob(chunksRef.current, { type });
      if (blob.size === 0) {
        setNotice("No audio was captured. Check your microphone and try again.");
        return;
      }
      // Gnani does not accept WebM, so the recording is converted to WAV before upload.
      setConverting(true);
      convertBlobToWav(blob)
        .then((wav) => onAudioRef.current(wav, "call.wav"))
        .catch(() =>
          setNotice("Could not convert this recording to WAV in this browser. Upload a WAV, MP3 or OGG file instead.")
        )
        .finally(() => setConverting(false));
    };
    recorderRef.current = recorder;
    recorder.start();
    setSeconds(0);
    setRecording(true);
  }

  function stop() {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") recorder.stop();
    setRecording(false);
  }

  useEffect(() => {
    if (recording && seconds >= MAX_SECONDS) stop();
  }, [recording, seconds]);

  function handleFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) onAudioRef.current(file, file.name);
  }

  return (
    <section className="card">
      <h2>Call capture</h2>
      <p className="muted">
        Batch mode: the recording is converted to WAV and sent to Gnani after you stop. The limit is {MAX_SECONDS}{" "}
        seconds. Use synthetic or consented audio only.
      </p>
      <div className="controls">
        {recording ? (
          <button className="btn danger" onClick={stop}>
            Stop recording ({MAX_SECONDS - seconds}s left)
          </button>
        ) : (
          <button className="btn primary" onClick={start} disabled={disabled || converting}>
            Start recording
          </button>
        )}
        <label className={`btn ghost ${disabled || recording || converting ? "is-disabled" : ""}`}>
          Upload audio file
          <input
            type="file"
            accept=".wav,.mp3,.ogg,.flac,.aac,.m4a"
            onChange={handleFile}
            disabled={disabled || recording || converting}
            hidden
          />
        </label>
      </div>
      {recording && (
        <p className="rec-indicator">
          <span className="dot" /> Recording {seconds}s
        </p>
      )}
      {converting && <p className="muted">Converting to WAV…</p>}
      {notice && <p className="notice">{notice}</p>}
    </section>
  );
}
