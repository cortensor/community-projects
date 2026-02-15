"use client"

import { motion } from "framer-motion"
import { TrendingUp, Users, Zap, Shield, Globe, Clock } from "lucide-react"

const stats = [
  {
    icon: Shield,
    value: "99.2%",
    label: "Truth Accuracy",
    description: "Verified through consensus",
  },
  {
    icon: Users,
    value: "50+",
    label: "Active Miners",
    description: "Distributed globally",
  },
  {
    icon: Clock,
    value: "2.3s",
    label: "Response Time",
    description: "Average processing speed",
  },
  {
    icon: TrendingUp,
    value: "1M+",
    label: "Queries Processed",
    description: "Since network launch",
  },
  {
    icon: Globe,
    value: "25+",
    label: "Countries",
    description: "Network coverage",
  },
  {
    icon: Zap,
    value: "99.9%",
    label: "Uptime",
    description: "Network reliability",
  },
]

export function StatsSection() {
  return (
    <section className="py-24 bg-muted/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-6 text-balance">
            Trusted by{" "}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">Thousands</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
            Our network continues to grow, delivering verified truth to users worldwide with unprecedented accuracy.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className="bg-card rounded-2xl border border-border p-8 hover:border-primary/20 transition-all duration-300 hover:shadow-lg">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl border border-primary/20 mb-6">
                  <stat.icon className="w-8 h-8 text-primary" />
                </div>

                <div className="text-4xl md:text-5xl font-bold text-foreground mb-2">{stat.value}</div>

                <div className="text-lg font-semibold text-card-foreground mb-2">{stat.label}</div>

                <div className="text-muted-foreground">{stat.description}</div>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="max-w-4xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="text-2xl font-bold text-primary mb-2">Enterprise Ready</div>
                <div className="text-muted-foreground">Scalable infrastructure for any workload</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-accent mb-2">Open Source</div>
                <div className="text-muted-foreground">Transparent and auditable algorithms</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-primary mb-2">24/7 Support</div>
                <div className="text-muted-foreground">Expert assistance when you need it</div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
