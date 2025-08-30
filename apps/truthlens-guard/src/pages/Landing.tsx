import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  Shield, 
  Zap, 
  Network, 
  Eye, 
  ArrowRight, 
  Play, 
  CheckCircle, 
  Star,
  Users,
  Award,
  Sparkles,
  Brain,
  Globe,
  Target
} from 'lucide-react';
import { motion } from 'framer-motion';

const features = [
  {
    icon: Network,
    title: 'Decentralized AI Consensus',
    description: 'Leverages Cortensor\'s distributed inference network with multiple independent AI miners for unbiased fact-checking.',
    badge: 'Cortensor AI'
  },
  {
    icon: Eye,
    title: 'Transparent & Explainable',
    description: 'See exactly how each AI miner reached their conclusion with detailed reasoning and source citations.',
    badge: 'Full Transparency'
  },
  {
    icon: Brain,
    title: 'Multi-Specialist Analysis',
    description: 'Different AI miners specialize in fact-checking, source validation, bias detection, and research analysis.',
    badge: 'Specialized AI'
  },
  {
    icon: Globe,
    title: 'Real-time Verification',
    description: 'Get instant credibility scores with confidence intervals from the global decentralized AI network.',
    badge: 'Instant Results'
  }
];

const stats = [
  { label: 'AI Miners', value: '12-20', icon: Users },
  { label: 'Accuracy Rate', value: '94%', icon: Award },
  { label: 'Processing Speed', value: '2-6s', icon: Zap },
  { label: 'Availability', value: '24/7', icon: Globe }
];

const testimonials = [
  {
    name: 'Dr. Sarah Chen',
    role: 'Information Security Researcher',
    content: 'TruthLens provides unprecedented transparency in fact-checking through decentralized AI consensus.',
    rating: 5
  },
  {
    name: 'Marcus Webb',
    role: 'Digital Media Analyst',
    content: 'The multi-miner approach eliminates bias and provides reliable verification I can trust.',
    rating: 5
  }
];

export default function Landing() {
  const navigate = useNavigate();
  const [hoveredFeature, setHoveredFeature] = useState<number | null>(null);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="relative overflow-hidden cyber-grid">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center">        
        <div className="container relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center max-w-4xl mx-auto"
          >
            <Badge variant="secondary" className="mb-6 px-4 py-2 bg-gradient-primary text-background">
              <Sparkles className="mr-2 h-4 w-4" />
              Powered by Cortensor Decentralized AI
            </Badge>
            
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 tracking-tight">
              <span className="gradient-text">TruthLens</span>
              <br className="hidden md:block" />
              AI Fact-Checker
            </h1>
            
            <p className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto leading-relaxed">
              Verify claims using Cortensor's decentralized inference network. 
              Multiple independent AI miners analyze content to deliver transparent, 
              bias-resistant credibility scores.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button 
                size="lg" 
                className="px-8 py-6 text-lg font-semibold btn-cyber hover:shadow-glow transition-all duration-300"
                onClick={() => navigate('/dashboard')}
              >
                <Shield className="mr-2 h-5 w-5" />
                Start Fact-Checking
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              
              <Button 
                variant="outline" 
                size="lg"
                className="px-8 py-6 text-lg glassmorphism hover:bg-muted/50"
                onClick={() => navigate('/history')}
              >
                <Eye className="mr-2 h-5 w-5" />
                View Examples
              </Button>
            </div>
          </motion.div>
        </div>

        {/* Floating Status Cards */}
        <motion.div
          animate={{ y: [-10, 10, -10] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          className="absolute top-20 right-10 hidden lg:block"
        >
          <div className="card-cyber p-4 bg-card/80 backdrop-blur">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-medium">Cortensor Network</span>
            </div>
            <p className="text-xs text-muted-foreground">15 Miners Active</p>
          </div>
        </motion.div>

        <motion.div
          animate={{ y: [10, -10, 10] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 3 }}
          className="absolute bottom-32 left-10 hidden lg:block"
        >
          <div className="card-cyber p-4 bg-card/80 backdrop-blur">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-sm font-medium">Analysis Complete</span>
            </div>
            <p className="text-xs text-muted-foreground">Credibility: 87.3%</p>
          </div>
        </motion.div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-muted/30">
        <div className="container">
          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-2 lg:grid-cols-4 gap-8"
          >
            {stats.map((stat, index) => (
              <motion.div
                key={stat.label}
                variants={itemVariants}
                className="text-center"
              >
                <div className="card-cyber p-6 bg-card/50 backdrop-blur hover:shadow-glow transition-all duration-300">
                  <stat.icon className="h-8 w-8 text-primary mx-auto mb-3" />
                  <p className="text-3xl font-bold gradient-text mb-1">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <Badge variant="outline" className="mb-4 border-primary/30">
              Cortensor Integration
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Decentralized <span className="gradient-text">AI Consensus</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Unlike centralized fact-checkers, TruthLens uses Cortensor's distributed 
              AI inference to eliminate bias and ensure transparent verification.
            </p>
          </motion.div>

          <motion.div
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 gap-8"
          >
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                variants={itemVariants}
                onHoverStart={() => setHoveredFeature(index)}
                onHoverEnd={() => setHoveredFeature(null)}
              >
                <Card className="card-cyber h-full hover:shadow-glow transition-all duration-300 border-0">
                  <CardHeader>
                    <div className="flex items-center gap-3 mb-3">
                      <div className="p-3 rounded-lg bg-gradient-primary/20">
                        <feature.icon className="h-6 w-6 text-primary" />
                      </div>
                      <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/30">
                        {feature.badge}
                      </Badge>
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20 bg-muted/20">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              How <span className="gradient-text">Decentralized Fact-Checking</span> Works
            </h2>
            <p className="text-lg text-muted-foreground">
              Experience the power of distributed AI consensus
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: "1",
                title: "Submit Claim",
                description: "Enter any claim or URL you want to verify. TruthLens sends it to Cortensor's decentralized network.",
                icon: Target
              },
              {
                step: "2", 
                title: "AI Miners Analyze",
                description: "Multiple independent AI miners with different specializations analyze the claim simultaneously across the network.",
                icon: Users
              },
              {
                step: "3",
                title: "Consensus & Results",
                description: "Results are aggregated using robust consensus algorithms, providing transparent credibility scores and explanations.",
                icon: CheckCircle
              }
            ].map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.2 }}
              >
                <Card className="card-cyber text-center h-full">
                  <CardHeader>
                    <div className="w-16 h-16 rounded-full bg-gradient-primary flex items-center justify-center mx-auto mb-4">
                      <step.icon className="w-8 h-8 text-background" />
                    </div>
                    <div className="text-sm font-medium text-primary mb-2">
                      Step {step.step}
                    </div>
                    <CardTitle className="text-xl">{step.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base">
                      {step.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="py-20">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Trusted by <span className="gradient-text">Researchers</span>
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={testimonial.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="card-cyber border-0 h-full">
                  <CardContent className="p-6">
                    <div className="flex mb-4">
                      {[...Array(testimonial.rating)].map((_, i) => (
                        <Star key={i} className="h-5 w-5 text-yellow-400 fill-current" />
                      ))}
                    </div>
                    <blockquote className="text-lg mb-4 leading-relaxed">
                      "{testimonial.content}"
                    </blockquote>
                    <div>
                      <p className="font-semibold">{testimonial.name}</p>
                      <p className="text-sm text-muted-foreground">{testimonial.role}</p>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-primary/10">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="card-cyber p-12 text-center bg-gradient-subtle"
          >
            <h2 className="text-3xl md:text-4xl font-bold mb-6">
              Experience <span className="gradient-text">Decentralized Truth</span>
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join the fight against misinformation with transparent, decentralized AI consensus. 
              No bias, no censorship, just facts.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button 
                size="lg"
                className="px-12 py-6 text-lg btn-cyber hover:shadow-glow transition-all duration-300"
                onClick={() => navigate('/dashboard')}
              >
                <Shield className="mr-2 h-5 w-5" />
                Try TruthLens Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
              <Button 
                variant="outline" 
                size="lg"
                className="px-8 py-6 text-lg border-primary/50 hover:bg-primary/10"
                onClick={() => window.open('https://docs.cortensor.network', '_blank')}
              >
                <Network className="mr-2 h-5 w-5" />
                Learn About Cortensor
              </Button>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}

