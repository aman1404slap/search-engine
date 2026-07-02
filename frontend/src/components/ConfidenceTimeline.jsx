import { useRef } from "react";
import { formatTime } from "../utils/format";

export default function ConfidenceTimeline({ duration, segments = [], currentTime = 0, onSeek }) {
  const trackRef = useRef(null);

  if (!duration) return null;

  function handleClick(e) {
    const rect = trackRef.current.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    onSeek(ratio * duration);
  }

  const playheadPct = Math.min(100, (currentTime / duration) * 100);

  return (
    <div className="timeline">
      <div className="timeline__track" ref={trackRef} onClick={handleClick}>
        {segments.map((seg, i) => {
          const left = (seg.start_s / duration) * 100;
          const width = Math.max(0.6, ((seg.end_s - seg.start_s) / duration) * 100);
          const opacity = seg.confidence != null ? 0.35 + seg.confidence * 0.65 : 0.5;
          return (
            <div
              key={i}
              className={`timeline__segment ${seg.highlighted ? "timeline__segment--highlighted" : ""}`}
              style={{ left: `${left}%`, width: `${width}%`, opacity }}
              title={
                seg.confidence != null
                  ? `${formatTime(seg.start_s)}–${formatTime(seg.end_s)} · ${Math.round(seg.confidence * 100)}% match`
                  : `${formatTime(seg.start_s)}–${formatTime(seg.end_s)}`
              }
            />
          );
        })}
        <div className="timeline__playhead" style={{ left: `${playheadPct}%` }} />
      </div>
      <div className="timeline__labels">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
}
