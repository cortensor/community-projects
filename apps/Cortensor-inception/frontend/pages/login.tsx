import { useState } from 'react'
import BackgroundVideo from '../components/BackgroundVideo'
import GoogleSignIn from '../components/GoogleSignIn'
import { ComicText } from "../components/ui/comic-text";

import dynamic from 'next/dynamic'

// TopScene uses browser-only APIs (three.js); load it client-side only

export default function Login() {
  const [videoReady, setVideoReady] = useState(false)
  const [videoError, setVideoError] = useState(false)
  return (
    <main className="min-h-screen relative overflow-hidden bg-black text-white">
      <BackgroundVideo
        src="/top.mp4"
        loop
        onLoaded={() => setVideoReady(true)}
        onError={() => { setVideoError(true); setVideoReady(true); }}
        startMuted={true}
        allowAudioUnlock={false}
        debug={false}
        className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[240px] h-[240px] object-cover z-0 rounded-lg"
      />
      {/* ensure a solid black background if video doesn't cover */}
      <div className="fixed inset-0 bg-black -z-20" />

      {/* Center column: title above video, 3D top overlay, sign-in below */}
      <div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-6 z-30">
        {/* spinner while video is loading (above the title) */}
        {!videoReady && (
          <div className="mb-2">
            <div className="animate-spin h-8 w-8 border-4 border-t-transparent border-white rounded-full" />
          </div>
        )}

        {/* Title above the video */}
        <ComicText
  fontSize={4}
  className="mb-2"
>
  Inception
</ComicText>

        {/* Video + 3D top wrapper */}
        <div className="relative w-[380px] h-[380px]">
          <BackgroundVideo
            src="/top.mp4"
            loop
            onLoaded={() => setVideoReady(true)}
            onError={() => { setVideoError(true); setVideoReady(true); }}
            startMuted={true}
            allowAudioUnlock={false}
            debug={false}
            className="absolute inset-0 w-full h-full object-cover rounded-lg z-0"
          />

          {/* 3D Top overlayed on the video */}
          
        </div>

        {/* Sign-in button below the video */}
        <div className="z-40">
          <GoogleSignIn />
        </div>
      </div>

     
    </main>
  )
}


