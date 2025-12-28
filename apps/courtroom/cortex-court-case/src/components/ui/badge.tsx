import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground shadow-lg shadow-primary/20",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground shadow-lg shadow-destructive/20",
        outline: "text-foreground border-border",
        cyber:
          "border-primary/50 bg-primary/10 text-primary shadow-[0_0_10px_hsl(var(--primary)/0.3)]",
        success:
          "border-success/50 bg-success/10 text-success shadow-[0_0_10px_hsl(var(--success)/0.3)]",
        warning:
          "border-warning/50 bg-warning/10 text-warning shadow-[0_0_10px_hsl(var(--warning)/0.3)]",
        dispute:
          "border-destructive/50 bg-destructive/10 text-destructive shadow-[0_0_10px_hsl(var(--destructive)/0.3)] animate-pulse",
        gold:
          "border-accent/50 bg-accent/10 text-accent shadow-[0_0_10px_hsl(var(--accent)/0.3)]",
        miner:
          "border-[hsl(270,80%,60%)]/50 bg-[hsl(270,80%,60%)]/10 text-[hsl(270,80%,60%)]",
        judge:
          "border-accent/50 bg-accent/10 text-accent",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
