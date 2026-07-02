import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useVideoDetail } from "../hooks/useVideos";
import ConfidenceTimeline from "./ConfidenceTimeline";
import MetadataPanel from "./MetadataPanel";
import { formatTime } from "../utils/format";

export default function VideoPlayerPane({ shotId, spans, seekToken }) {
  const { video, loading, error } = useVideoDetail(shotId);
  const [playUrl, setPlayUrl] = useState(null);
  const [playUrlError, setPlayUrlError] = useState(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [mediaDuration, setMediaDuration] = useState(null);
  const [aspectRatio, setAspectRatio] = useState(16 / 9);
  const videoRef = useRef(null);

  useEffect(() => {
    setMediaDuration(null);
    setAspectRatio(16 / 9);
  }, [shotId]);

  useEffect(() => {
    if (!shotId) return;
    setPlayUrl(null);
    setPlayUrlError(null);
    api
      .getPlayUrl(shotId)
      .then((res) => setPlayUrl(res.url))
      .catch((err) => setPlayUrlError(err));
  }, [shotId]);

  useEffect(() => {
    if (!videoRef.current || !spans || spans.length === 0) return;
    const target = spans[0].start_s;
    videoRef.current.currentTime = target;
    videoRef.current.play?.().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seekToken]);

  if (!shotId) {
    return (
      <div className="player-pane player-pane--empty">
        <p>Select a video to preview it here.</p>
      </div>
    );
  }

  // Only overlay confidence segments when there's an active search match for
  // this video -- showing every raw event by default makes busy conversational
  // videos unreadable and isn't what the confidence bar is meant to convey.
  const timelineSegments = spans?.length ? spans.map((s) => ({ ...s, highlighted: true })) : [];

  return (
    <div className="player-pane">
      <div className="player-pane__video-wrap" style={{ aspectRatio }}>
        {playUrlError ? (
          <div className="player-pane__error">
            Playback unavailable ({playUrlError.message || "no S3 access"}).
          </div>
        ) : playUrl ? (
          <video
            ref={videoRef}
            src={playUrl}
            controls
            className="player-pane__video"
            onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)}
            onLoadedMetadata={(e) => {
              setMediaDuration(e.target.duration);
              if (e.target.videoWidth && e.target.videoHeight) {
                setAspectRatio(e.target.videoWidth / e.target.videoHeight);
              }
              if (spans?.length) e.target.currentTime = spans[0].start_s;
            }}
          />
        ) : (
          <div className="player-pane__loading">
            <span className="spinner" /> Fetching playback URL&hellip;
          </div>
        )}
      </div>

      {(video?.duration_sec ?? mediaDuration) != null && (
        <ConfidenceTimeline
          duration={video.duration_sec ?? mediaDuration}
          segments={timelineSegments}
          currentTime={currentTime}
          onSeek={(t) => {
            if (videoRef.current) videoRef.current.currentTime = t;
          }}
        />
      )}

      {spans?.length > 0 && (
        <div className="match-summary">
          {spans.length} matching moment{spans.length > 1 ? "s" : ""} found ·{" "}
          {formatTime(spans[0].start_s)}–{formatTime(spans[0].end_s)} ·{" "}
          {Math.round(spans[0].confidence * 100)}% confidence
        </div>
      )}

      {loading && <div className="player-pane__loading">Loading details&hellip;</div>}
      {error && <div className="player-pane__error">{error.message}</div>}
      {video && <MetadataPanel video={video} />}
    </div>
  );
}
