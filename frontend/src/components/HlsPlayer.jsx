import { useEffect, useRef } from 'react';
import Hls from 'hls.js';

/**
 * HLS.js video player with native Safari fallback and graceful MP4 passthrough.
 * Plays any URL. If the URL ends with .m3u8, uses hls.js on Chrome/FF or native on Safari.
 */
export const HlsPlayer = ({ src, className = '', poster = null, autoPlay = true, testid = 'hls-player' }) => {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return undefined;

    const isHls = src.toLowerCase().includes('.m3u8');

    if (!isHls) {
      // Non-HLS source — let <video> play it directly (MP4/mock)
      video.src = src;
      if (autoPlay) video.play().catch(() => {});
      return undefined;
    }

    if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS (Safari, iOS)
      video.src = src;
      if (autoPlay) video.play().catch(() => {});
      return undefined;
    }

    if (Hls.isSupported()) {
      const hls = new Hls({ lowLatencyMode: true, enableWorker: true });
      hlsRef.current = hls;
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        if (autoPlay) video.play().catch(() => {});
      });
      hls.on(Hls.Events.ERROR, (_evt, data) => {
        if (data.fatal) {
          // eslint-disable-next-line no-console
          console.warn('HLS fatal error:', data.type, data.details);
        }
      });
      return () => {
        hls.destroy();
        hlsRef.current = null;
      };
    }

    // Last-resort fallback
    video.src = src;
    return undefined;
  }, [src, autoPlay]);

  return (
    <video
      ref={videoRef}
      data-testid={testid}
      controls
      playsInline
      poster={poster}
      className={className || 'w-full h-full'}
    >
      Your browser does not support the video tag.
    </video>
  );
};

export default HlsPlayer;
