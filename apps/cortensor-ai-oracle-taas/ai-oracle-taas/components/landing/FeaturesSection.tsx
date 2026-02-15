"use client"

import { motion } from "framer-motion"
import { Shield, Network, Zap, Brain, CheckCircle, TrendingUp, Lock, Globe, Clock } from "lucide-react"

const features = [
  {
    icon: Shield,
    title: "Hallucination Detection",
    description:
      "Advanced algorithms detect and eliminate AI hallucinations through cross-validation and consensus mechanisms.",
    color: "text-green-400",
  },
  {
    icon: Network,
    title: "Decentralized Consensus",
    description: "Multiple independent AI miners provide responses, ensuring no single point of failure or bias.",
    color: "text-blue-400",
  },
  {
    icon: Brain,
    title: "Multi-Algorithm Verification",
    description: "Semantic similarity, reputation weighting, and confidence analysis combine for ultimate accuracy.",
    color: "text-purple-400",
  },
  {
    icon: Zap,
    title: "Real-time Processing",
    description: "Get verified answers in seconds with parallel processing across the Cortensor network.",
    color: "text-yellow-400",
  },
  {
    icon: TrendingUp,
    title: "Reputation System",
    description: "Miners are ranked by accuracy and reliability, ensuring the best responses rise to the top.",
    color: "text-orange-400",
  },
  {
    icon: Lock,
    title: "Blockchain Logging",
    description: "All truth verifications are immutably recorded on-chain for transparency and auditability.",
    color: "text-cyan-400",
  },
  {
    icon: Globe,
    title: "Global Network",
    description: "Distributed miners worldwide provide diverse perspectives and eliminate regional biases.",
    color: "text-pink-400",
  },
  {
    icon: Clock,
    title: "Historical Tracking",
    description: "Track truth accuracy over time and identify patterns in AI model performance.",
    color: "text-indigo-400",
  },
  {
    icon: CheckCircle,
    title: "Quality Assurance",
    description: "Multi-layer verification ensures only the highest quality, most accurate responses.",
    color: "text-emerald-400",
  },
]

export function FeaturesSection() {
  return (
    <section className="py-24 bg-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Why Choose{" "}
            <span className="bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              AI Oracle
            </span>
          </h2>
          <p className="text-xl text-slate-300 max-w-3xl mx-auto">
            Revolutionary truth verification technology that eliminates AI hallucinations through decentralized
            consensus and advanced verification algorithms.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              viewport={{ once: true }}
              className="group relative"
            >
              <div className="h-full p-8 bg-slate-800/50 rounded-2xl border border-slate-700 hover:border-slate-600 transition-all duration-300 hover:bg-slate-800/70">
                <div
                  className={`inline-flex p-3 rounded-xl bg-slate-700/50 ${feature.color} mb-6 group-hover:scale-110 transition-transform duration-300`}
                >
                  <feature.icon className="w-6 h-6" />
                </div>

                <h3 className="text-xl font-semibold text-white mb-4 group-hover:text-purple-300 transition-colors duration-300">
                  {feature.title}
                </h3>

                <p className="text-slate-400 leading-relaxed group-hover:text-slate-300 transition-colors duration-300">
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          viewport={{ once: true }}
          className="text-center mt-16"
        >
          <div className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-purple-600/20 to-blue-600/20 rounded-full border border-purple-500/30">
            <CheckCircle className="w-5 h-5 text-green-400 mr-3" />
            <span className="text-slate-200 font-medium">
              Trusted by researchers, developers, and enterprises worldwide
            </span>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
