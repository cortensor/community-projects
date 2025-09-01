"use client"

import { motion } from "framer-motion"
import { Search, Users, Shield, CheckCircle } from "lucide-react"

const steps = [
  {
    icon: Search,
    title: "Submit Your Query",
    description: "Ask any question and our system distributes it to multiple AI miners across the Cortensor network.",
    step: "01",
  },
  {
    icon: Users,
    title: "Parallel Processing",
    description: "Independent AI miners process your query simultaneously, each providing their own response.",
    step: "02",
  },
  {
    icon: Shield,
    title: "Consensus Verification",
    description: "Advanced algorithms analyze all responses, detecting inconsistencies and potential hallucinations.",
    step: "03",
  },
  {
    icon: CheckCircle,
    title: "Verified Truth",
    description: "You receive the most accurate, consensus-verified answer with confidence scores and source tracking.",
    step: "04",
  },
]

export function HowItWorksSection() {
  return (
    <section className="py-24 bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-6 text-balance">
            How <span className="bg-gradient-to-r from-primary to-blue-500 bg-clip-text text-transparent">It Works</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
            Our decentralized truth verification process ensures you get the most accurate and reliable AI responses.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
              viewport={{ once: true }}
              className="relative"
            >
              {/* Connection Line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-16 left-full w-full h-0.5 bg-gradient-to-r from-primary/30 to-blue-500 transform translate-x-4" />
              )}

              <div className="text-center">
                <div className="relative inline-flex items-center justify-center w-16 h-16 bg-primary/10 rounded-2xl border border-primary/20 mb-6">
                  <step.icon className="w-8 h-8 text-primary" />
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-xs font-bold">
                    {step.step}
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-foreground mb-4">{step.title}</h3>

                <p className="text-muted-foreground leading-relaxed">{step.description}</p>
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="inline-flex items-center px-6 py-3 bg-accent/10 rounded-full border border-accent/20">
            <Shield className="w-5 h-5 text-accent mr-3" />
            <span className="text-foreground font-medium">99.2% accuracy through decentralized consensus</span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
