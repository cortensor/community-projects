"use client";

import React from 'react';
import Link from 'next/link';
import { motion } from "motion/react";
import BackgroundVideo from "@/components/BackgroundVideo";
import { ComicText } from "@/components/ui/comic-text";
import { useSession, signOut } from "next-auth/react";
import BlendedResult from "@/components/BlendedResult";

export default function Home() {
  const { data: session } = useSession();

  return (
    <main className="min-h-screen bg-white text-black">

      {/* Side headings (click to jump) */}


      {/* Side states navigation (LOCK / VALIDATE / DECIDE) */}
     



        
      {/* Side result-states (RELEASE / REJECT / ESCALATE) */}
      
      {/* ================= HERO ================= */}
      <section id="hero" className="relative border-b-4 border-black">
        <div className="max-w-7xl mx-auto px-10 py-32 grid grid-cols-1 lg:grid-cols-12 gap-20 items-center">

          {/* LEFT — IDEA */}
          <motion.div
            className="lg:col-span-7 border-l-8 border-black pl-10"
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <ComicText fontSize={6}>Inception</ComicText>

            <p className="mt-10 text-2xl font-semibold leading-snug max-w-3xl">
              Not every idea should be released.
              <br />
              Some must prove they belong to reality.
            </p>

            <p className="mt-6 text-lg text-black/70 max-w-3xl">
              Inception is a trust-conditional execution layer where AI outputs
              exist in a controlled state — held, validated, and released only
              when they pass objective confidence thresholds.
            </p>

            {/* SESSION */}
            {session?.user?.name && (
              <div className="mt-8 flex items-center gap-4">
                <span className="px-3 py-1 text-sm font-bold border border-black">
                  {session.user.name}
                </span>
                <button
                  onClick={() => signOut({ callbackUrl: "/" })}
                  className="text-sm underline"
                >
                  Sign out
                </button>
              </div>
            )}

            {/* CTA */}
            <div className="mt-16 flex items-center gap-10">
              <Link
                href="/process"
                className="
                  border-4 border-black px-14 py-6 font-black uppercase
                  shadow-[8px_8px_0px_#000]
                  hover:translate-x-1 hover:translate-y-1
                  hover:shadow-[6px_6px_0px_#000]
                  transition-all bg-black text-white
                "
              >
                Enter the System
              </Link>

              <a href="/docs" className="font-semibold underline text-lg">
                Read the Architecture
              </a>

              <a href="/claim" className="font-semibold underline text-lg ml-6">
                Judge UI (Submit Claim)
              </a>
            </div>
          </motion.div>

          {/* RIGHT — TOTEM / VIDEO */}
          <motion.div
            className="lg:col-span-5 flex justify-center lg:justify-end"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <div className="relative w-[420px] h-[420px] border-4 border-black bg-black shadow-[12px_12px_0px_#000]">
              <BackgroundVideo
                src="/top.mp4"
                loop
                startMuted
                allowAudioUnlock={false}
                className="absolute inset-0 w-full h-full object-cover"
              />

              {/* Totem label */}
              <div className="absolute -top-4 -left-4 bg-white border-2 border-black px-3 py-1 text-xs font-black shadow-[4px_4px_0px_#000]">
                REALITY CHECK
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ================= LAYERS ================= */}
      <section className="max-w-7xl mx-auto px-10 py-32">
        <h2 className="font-black uppercase tracking-widest text-2xl md:text-3xl lg:text-4xl mb-20">
          Layers of Validation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-20">
          {[
            {
              layer: "Layer 01",
              title: "Lock",
              desc: "The output exists, but it is not real yet. It is isolated from action.",
            },
            {
              layer: "Layer 02",
              title: "Validate",
              desc: "Independent systems verify execution, agreement, and intent.",
            },
            {
              layer: "Layer 03",
              title: "Release",
              desc: "Only validated outputs cross into reality and trigger actions.",
            },
          ].map((l) => (
            <div key={l.layer} className="relative pl-10">
              <div className="absolute left-0 top-0 h-full w-[4px] bg-black" />

              <span className="text-xs font-bold">{l.layer}</span>
              <h3 className="mt-2 font-black uppercase tracking-wide">
                {l.title}
              </h3>
              <p className="mt-4 text-lg text-black/70 leading-relaxed">
                {l.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* BLENDED AI + SIMULATOR RESULT */}
      <section className="border-t-4 border-black">
        <div className="max-w-7xl mx-auto px-10 py-20">
          <h2 className="font-black uppercase mb-8">AI + Simulator — Blended View</h2>
          {/* @ts-ignore */}
          <BlendedResult />
        </div>
      </section>

      {/* ================= STATES ================= */}
      <section className="border-t-4 border-black">
        <div className="max-w-7xl mx-auto px-10 py-32">
          <motion.h2
            className="font-black uppercase tracking-widest text-2xl md:text-3xl lg:text-4xl mb-20"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            States
          </motion.h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-20">
            {[
              {
                state: "RELEASE",
                emoji: "✅",
                desc: "Consensus reached. Confidence proven. Output becomes real.",
              },
              {
                state: "REJECT",
                emoji: "❌",
                desc: "Validation failed. The idea collapses before execution.",
              },
              {
                state: "ESCALATE",
                emoji: "⚠️",
                desc: "Ambiguous state. Requires deeper inspection or human review.",
              },
            ].map((s, i) => (
              <motion.div
                id={`state-${s.state.toLowerCase().replace(/\s+/g, '-')}`}
                key={s.state}
                className="group border-4 border-black p-8 shadow-[6px_6px_0px_#000] bg-white"
                initial={{ opacity: 0, y: 18, scale: 0.98 }}
                whileInView={{ opacity: 1, y: 0, scale: 1 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.6, delay: i * 0.08, type: 'spring', stiffness: 80 }}
                whileHover={{ scale: 1.03, y: -6, rotate: 1 }}
                whileTap={{ scale: 0.98, rotate: -1 }}
              >
                <div className="flex items-center gap-3">
                  <h4 className="font-black text-xl tracking-widest flex items-center gap-3">
                    <span className="text-2xl" aria-hidden>
                      {s.emoji}
                    </span>
                    <span>{s.state}</span>
                  </h4>

                  {/* playful whoop emoji that scales on hover */}
                  
                </div>

                <p className="mt-4 text-black/70 text-lg leading-relaxed">
                  {s.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ================= FOOTER ================= */}
      <footer className="border-t-4 border-black py-12 text-center text-sm font-bold">
        INCEPTION · Trust-Conditional AI Execution · Built for Cortensor
      </footer>
    </main>
  );
}
