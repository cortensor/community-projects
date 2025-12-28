"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import BackgroundVideo from "@/components/BackgroundVideo";
import { useSession } from "next-auth/react";

export default function Intro() {
  const router = useRouter();
  const { data: session, status } = useSession();

  useEffect(() => {
    if (status === 'authenticated') {
      // If the user is already signed in, send them to /home immediately
      router.replace('/home');
    }
  }, [status, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-black text-white">
      <BackgroundVideo
        src="/landing.mp4"
        loop={false}
        startMuted
        allowAudioUnlock={true}
        onEnded={() => router.push('/login')}
        className="w-full h-full object-cover fixed inset-0 z-0"
      />

      
    </div>
  );
}
