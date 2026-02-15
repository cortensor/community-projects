"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { ArrowRight, CheckCircle, Zap } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Link from "next/link"

export function CTASection() {
  const [email, setEmail] = useState("")

  const benefits = [
    "Access to decentralized AI network",
    "99.2% truth accuracy guarantee",
    "Real-time verification results",
    "Enterprise-grade security",
    "24/7 technical support",
  ]

  return (
    <section className="py-24 bg-gradient-to-br from-pink-500 via-background to-blue-500">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="space-y-8"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
              viewport={{ once: true }}
              className="inline-flex items-center px-4 py-2 rounded-full bg-white border border-primary/20 text-primary text-sm font-medium"
            >
              <Zap className="w-4 h-4 mr-2" />
              Join the Truth Revolution
            </motion.div>

            {/* Main Heading */}
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3, duration: 0.8 }}
              viewport={{ once: true }}
              className="text-4xl md:text-6xl font-bold text-foreground leading-tight text-balance"
            >
              Ready to Experience{" "}
              <span className="bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                Verified Truth
              </span>
              ?
            </motion.h2>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.8 }}
              viewport={{ once: true }}
              className="text-md text-muted-foreground max-w-3xl mx-auto text-pretty"
            >
              Join thousands of researchers, developers, and enterprises who trust our decentralized AI network for
              accurate, hallucination-free responses.
            </motion.p>

            {/* Benefits List */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.8 }}
              viewport={{ once: true }}
              className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl mx-auto text-left"
            >
              {benefits.map((benefit, index) => (
                <div key={benefit} className="flex items-center space-x-3">
                  <CheckCircle className="w-5 h-5 text-primary flex-shrink-0" />
                  <span className="text-foreground">{benefit}</span>
                </div>
              ))}
            </motion.div>

            {/* CTA Form */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.8 }}
              viewport={{ once: true }}
              className="space-y-6"
            >
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center max-w-md mx-auto">
                <Input
                  type="email"
                  placeholder="Enter your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-white border-border text-foreground placeholder-muted-foreground focus:border-primary"
                />
                <Button
                  size="lg"
                  className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 whitespace-nowrap"
                >
                  Start Free Trial
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </div>

              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link href="/oracle">
                  <Button
                    variant="outline"
                    size="lg"
                    className="border-border text-foreground hover:bg-accent hover:text-accent-foreground bg-transparent"
                  >
                    Try Demo First
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button
                    variant="ghost"
                    size="lg"
                    className="text-muted-foreground hover:text-foreground hover:bg-muted"
                  >
                    View Pricing
                  </Button>
                </Link>
              </div>

              <p className="text-sm text-muted-foreground">
                No credit card required • 14-day free trial • Cancel anytime
              </p>
            </motion.div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
