import { Mic, Square, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { importVoice } from "../api";
import type { VoiceProfile } from "../types";

const minRecordedSeconds = 5;
const maxRecordedSeconds = 30;

type Props = {
  onImported?: (profile: VoiceProfile) => void;
};

type RecordingSession = {
  stream: MediaStream;
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  chunks: Float32Array[];
  sampleRate: number;
};

export function ImportVoice({ onImported }: Props) {
  const [displayName, setDisplayName] = useState("Alice");
  const [confirmedBy, setConfirmedBy] = useState("local_user");
  const [notes, setNotes] = useState("Confirmed self or written permission for private synthetic voice use.");
  const [referenceText, setReferenceText] = useState("");
  const [consentConfirmed, setConsentConfirmed] = useState(false);
  const [recordedFile, setRecordedFile] = useState<File | null>(null);
  const [recordedSeconds, setRecordedSeconds] = useState<number | null>(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recordingSession = useRef<RecordingSession | null>(null);
  const canImport = consentConfirmed && confirmedBy.trim().length > 0 && referenceText.trim().length > 0;

  useEffect(() => {
    return () => {
      void stopActiveRecording(false);
    };
  }, []);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    if (!canImport) {
      setError("Confirm consent before importing a voice sample.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const profile = await importVoice(file, displayName, {
        confirmed_by: confirmedBy,
        notes,
        reference_text: referenceText,
      });
      onImported?.(profile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice import failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleStartRecording() {
    if (!canImport) {
      setError("Confirm consent before recording a voice sample.");
      return;
    }
    const AudioContextConstructor = getAudioContextConstructor();
    if (!navigator.mediaDevices?.getUserMedia || !AudioContextConstructor) {
      setError("Microphone recording is not available in this browser.");
      return;
    }

    setError(null);
    setRecordedFile(null);
    setRecordedSeconds(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const context = new AudioContextConstructor();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);
      const chunks: Float32Array[] = [];
      processor.onaudioprocess = (event) => {
        chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
      };
      source.connect(processor);
      processor.connect(context.destination);
      recordingSession.current = {
        stream,
        context,
        source,
        processor,
        chunks,
        sampleRate: context.sampleRate,
      };
      setRecording(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone recording failed");
    }
  }

  async function handleStopRecording() {
    await stopActiveRecording(true);
  }

  async function stopActiveRecording(saveFile: boolean) {
    const session = recordingSession.current;
    if (!session) return;
    recordingSession.current = null;
    session.processor.onaudioprocess = null;
    session.source.disconnect();
    session.processor.disconnect();
    session.stream.getTracks().forEach((track) => track.stop());
    await session.context.close();
    setRecording(false);

    if (!saveFile) return;
    if (session.chunks.length === 0) {
      setError("No microphone audio was captured.");
      return;
    }
    const wavBlob = encodeMonoWav(session.chunks, session.sampleRate);
    const durationSeconds = sampleCount(session.chunks) / session.sampleRate;
    setRecordedFile(new File([wavBlob], `${displayName}-recording.wav`, { type: "audio/wav" }));
    setRecordedSeconds(durationSeconds);
  }

  const recordedDurationError = recordedSeconds === null ? null : recordedDurationErrorText(recordedSeconds);

  return (
    <section className="panel">
      <h2>Import Voice</h2>
      <label>
        Speaker name
        <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
      </label>
      <label>
        Confirmed by
        <input value={confirmedBy} onChange={(event) => setConfirmedBy(event.target.value)} />
      </label>
      <label>
        Consent notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>
      <label>
        Reference transcript
        <textarea value={referenceText} onChange={(event) => setReferenceText(event.target.value)} />
      </label>
      <label className="checkbox-row">
        <input
          aria-label="Confirm voice consent"
          type="checkbox"
          checked={consentConfirmed}
          onChange={(event) => setConsentConfirmed(event.target.checked)}
        />
        <span>I confirm this speaker is me or gave written permission for private synthetic voice use.</span>
      </label>
      <label className="file-button">
        <Upload size={18} />
        <span>{busy ? "Importing" : "Import consented sample"}</span>
        <input
          aria-label="Import consented voice sample"
          type="file"
          accept="audio/*"
          disabled={busy || !canImport}
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />
      </label>
      <div className="recorder-controls" aria-label="Microphone recorder">
        <button
          type="button"
          disabled={busy || !canImport || recording}
          onClick={() => void handleStartRecording()}
        >
          <Mic size={18} />
          Start microphone recording
        </button>
        <button type="button" disabled={!recording} onClick={() => void handleStopRecording()}>
          <Square size={18} />
          Stop microphone recording
        </button>
      </div>
      {recordedFile ? (
        <div className="recorded-sample">
          <div>
            <span>{recordedFile.name}</span>
            {recordedSeconds !== null ? <small>{recordedSeconds.toFixed(1)}s recorded</small> : null}
            {recordedDurationError ? <small className="duration-warning">{recordedDurationError}</small> : null}
          </div>
          <button
            type="button"
            disabled={busy || !canImport || recordedDurationError !== null}
            onClick={() => void handleFile(recordedFile)}
          >
            Import recorded sample
          </button>
        </div>
      ) : null}
      {error ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : null}
      <p>Import a 5-30 second WAV sample and transcript with self or written permission before blending.</p>
    </section>
  );
}

function getAudioContextConstructor(): typeof AudioContext | undefined {
  const browserWindow = window as Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext };
  return browserWindow.AudioContext ?? browserWindow.webkitAudioContext;
}

function encodeMonoWav(chunks: Float32Array[], sampleRate: number): Blob {
  const samples = sampleCount(chunks);
  const buffer = new ArrayBuffer(44 + samples * 2);
  const view = new DataView(buffer);
  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + samples * 2, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, samples * 2, true);

  let offset = 44;
  chunks.forEach((chunk) => {
    chunk.forEach((sample) => {
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(offset, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
      offset += 2;
    });
  });

  return new Blob([view], { type: "audio/wav" });
}

function sampleCount(chunks: Float32Array[]): number {
  return chunks.reduce((count, chunk) => count + chunk.length, 0);
}

function recordedDurationErrorText(durationSeconds: number): string | null {
  if (durationSeconds < minRecordedSeconds) {
    return `Record at least ${minRecordedSeconds} seconds before importing.`;
  }
  if (durationSeconds > maxRecordedSeconds) {
    return `Record ${maxRecordedSeconds} seconds or less before importing.`;
  }
  return null;
}

function writeAscii(view: DataView, offset: number, text: string) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}
