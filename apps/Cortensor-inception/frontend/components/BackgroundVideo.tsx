import React from 'react';

type Props = {
  onLoaded?: () => void;
  onError?: (e?: any) => void;
  onEnded?: () => void;
  loop?: boolean;
  src?: string;
  startMuted?: boolean;
  allowAudioUnlock?: boolean;
  className?: string;
  debug?: boolean;
};

export default function BackgroundVideo({
  onLoaded,
  onError,
  onEnded,
  loop = false,
  src = '/Top_Spinning_Video_Generated.mp4',
  startMuted = true,
  allowAudioUnlock = true,
  debug = false,
  className,
}: Props) {
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const unlockedRef = React.useRef(false);
  React.useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const log = (...args: any[]) => console.log('[BackgroundVideo]', ...args);
    log('mount', { src, startMuted, allowAudioUnlock });

    // Ensure muted state for autoplay
    video.muted = startMuted;

    // Attempt to play, retry a few times if the browser blocks autoplay briefly
    let attempts = 0;
    const maxAttempts = 5;
    let timeoutId: number | undefined;
    const tryPlay = async () => {
      log('tryPlay', { attempt: attempts + 1, readyState: video.readyState, muted: video.muted });
      try {
        await video.play();
        log('play succeeded', { readyState: video.readyState, muted: video.muted });
      } catch (err) {
        log('play failed', err, { readyState: video.readyState, muted: video.muted });
        attempts += 1;
        if (attempts <= maxAttempts) {
          timeoutId = window.setTimeout(tryPlay, 200) as unknown as number;
        }
      }
    };

    tryPlay();

    const unlockAudio = async () => {
      if (unlockedRef.current) return;
      unlockedRef.current = true;
      log('unlockAudio called');
      try {
        video.muted = false;
        await video.play();
        log('unlockAudio play succeeded', { readyState: video.readyState, muted: video.muted });
      } catch (err) {
        // Safari fallback
        video.muted = true;
        log('unlockAudio play failed', err, { readyState: video.readyState, muted: video.muted });
      }
      document.removeEventListener('click', unlockAudio);
      document.removeEventListener('touchstart', unlockAudio);
      document.removeEventListener('keydown', unlockAudio);
    };

    const handleEvent = (ev: Event) => {
      log('video event', ev.type, { readyState: video.readyState, muted: video.muted, width: video.videoWidth, height: video.videoHeight, time: video.currentTime });
      if (ev.type === 'canplay' || ev.type === 'loadeddata' || ev.type === 'playing') {
        onLoaded?.();
      }
    };

    const handleError = (ev: Event | any) => {
      log('video error event', ev);
      onError?.(ev);
    };

    // Only add interaction listeners if unlocking audio is allowed
    if (allowAudioUnlock) {
      // First interaction anywhere
      document.addEventListener('click', unlockAudio, { once: true });
      document.addEventListener('touchstart', unlockAudio, { once: true });
      document.addEventListener('keydown', unlockAudio, { once: true });
    }

    // Diagnostic video events
    video.addEventListener('loadstart', handleEvent);
    video.addEventListener('loadeddata', handleEvent);
    video.addEventListener('canplay', handleEvent);
    video.addEventListener('play', handleEvent);
    video.addEventListener('playing', handleEvent);
    video.addEventListener('waiting', handleEvent);
    video.addEventListener('stalled', handleEvent);
    video.addEventListener('error', handleError as EventListener);

    return () => {
      if (timeoutId) window.clearTimeout(timeoutId);
      if (allowAudioUnlock) {
        document.removeEventListener('click', unlockAudio);
        document.removeEventListener('touchstart', unlockAudio);
        document.removeEventListener('keydown', unlockAudio);
      }
      video.removeEventListener('loadstart', handleEvent);
      video.removeEventListener('loadeddata', handleEvent);
      video.removeEventListener('canplay', handleEvent);
      video.removeEventListener('play', handleEvent);
      video.removeEventListener('playing', handleEvent);
      video.removeEventListener('waiting', handleEvent);
      video.removeEventListener('stalled', handleEvent);
      video.removeEventListener('error', handleError as EventListener);
    };
  }, [startMuted, allowAudioUnlock, src, onError, onLoaded]);

  return (
    <video
      ref={videoRef}
      autoPlay
      muted={startMuted}
      loop={loop}
      playsInline
      preload="auto"
      onLoadedData={onLoaded}
      onCanPlay={onLoaded}
      onError={(e) => onError?.(e)}
      onEnded={onEnded}
      className={className ?? 'fixed inset-0 w-full h-full object-cover z-0'}
      // Promote to compositor layer to minimize micro-stutters when the main thread is busy
      style={{ ...(debug ? { outline: '3px solid lime' } : {}), willChange: 'transform' }}
    >
      <source src={src} type="video/mp4" />
    </video>
  );
}
