"use client";

import { motion } from "motion/react";
import { cn } from "@/lib/utils";

type ComicTextProps = {
  children: string;
  className?: string;
  fontSize?: number;
  style?: JSX.IntrinsicElements["div"]["style"];
};

export function ComicText({
  children,
  className,
  fontSize = 4,
  style,
}: ComicTextProps) {
  if (typeof children !== "string") {
    throw new Error("ComicText children must be a string");
  }

  const dotColor = "#ffdd00ff";
  const backgroundColor = "#ffdd00ff";

  return (
    <motion.div
      className={cn("select-none text-left", className)}
      style={{
        fontSize: `${fontSize}rem`,
        fontFamily: "'Bangers', 'Impact', 'Arial Black', sans-serif",
        fontWeight: 1200,
        letterSpacing: "0.04em",
        textTransform: "uppercase",

        WebkitTextStroke: `${fontSize * 0.55}px #000`,
        color: "transparent",

        backgroundColor,
        backgroundImage: `radial-gradient(circle at 1px 1px, ${dotColor} 1px, transparent 0)`,
        backgroundSize: "8px 8px",
        backgroundClip: "text",
        WebkitBackgroundClip: "text",

        filter: `
          drop-shadow(5px 5px 0px #ffffffff)
          drop-shadow(2px 2px 0px #ffffffff)
        `,
        transform: "skewX(-10deg)",
        ...style,
      }}
      initial={{ opacity: 0, scale: 0.85, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{
        duration: 0.5,
        ease: [0.175, 0.885, 0.32, 1.275],
      }}
    >
      {children}
    </motion.div>
  );
}
