// src/lib/app-config.ts
import { getEnvironmentValues } from './environment-config'

// Get dynamic environment values
const getEnvValues = () => {
  try {
    // Prioritas: environment variables > environment config fallback
    return {
      defaultSession: process.env.NEXT_PUBLIC_LLM_SESSION_ID || getEnvironmentValues().defaultSession,
      deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || getEnvironmentValues().deepseekSession,
      llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || getEnvironmentValues().llamaSession,
      // Add dummy values for other required fields to match EnvironmentConfig
      name: 'fallback',
      displayName: 'Fallback',
      cortensorUrl: process.env.CORTENSOR_ROUTER_URL || getEnvironmentValues().cortensorUrl,
      cortensorApiKey: process.env.CORTENSOR_API_KEY || getEnvironmentValues().cortensorApiKey,
      completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || getEnvironmentValues().completionsUrl,
      description: 'Configuration from environment variables'
    }
  } catch {
    // Fallback to static values if environment config fails
    return {
      defaultSession: process.env.NEXT_PUBLIC_LLM_SESSION_ID || "11",
      deepseekSession: process.env.NEXT_PUBLIC_DEEPSEEK_SESSION_ID || "21",
      llamaSession: process.env.NEXT_PUBLIC_LLAMA_SESSION_ID || "12",
      // Add dummy values for other required fields to match EnvironmentConfig
      name: 'fallback',
      displayName: 'Fallback',
      cortensorUrl: process.env.CORTENSOR_ROUTER_URL || '',
      cortensorApiKey: process.env.CORTENSOR_API_KEY || '',
      completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL || '',
      description: 'Fallback configuration'
    }
  }
}

export const appConfig = {
  app: {
    name: process.env.NEXT_PUBLIC_APP_NAME || "Eureka",
    version: process.env.NEXT_PUBLIC_APP_VERSION || "Devnet-6",
    assistant: "Eureka Assistant",
    // Untuk sidebar - nama yang berbeda dan lebih deskriptif
    fullName: "Eureka",
  },
  chat: {
    maxMessagesPerSession: 100,
    enableExport: true,
    maxInputLength: parseInt(process.env.NEXT_PUBLIC_MAX_INPUT_LENGTH || "4000", 10),
    // Dynamic session ID based on environment
    get staticSessionId() {
      const envValues = getEnvValues()
      return envValues.defaultSession
    },
    // Model configurations with specialized capabilities
    get models() {
      const envValues = getEnvValues()
      return [
        {
          id: "default-model",
          name: "Llava 1.5",
          sessionId: envValues.defaultSession,
          description: "",
          streamingSystem: "llava-stream",
          capabilities: [
            "Pure text processing with exceptional accuracy",
            "Fast response times for text-based queries", 
            "Clean, structured output formatting",
            "Code generation with best practices",
            "Multi-language comprehension and translation"
          ],
          isDefault: true,
          active: { testnet: true, devnet6: true }
        },
        {
          id: "deepseek-r1", 
          name: "DeepSeek R1",
          sessionId: envValues.deepseekSession,
          description: "",
          streamingSystem: "deepseek-r1",
          capabilities: [
            "Advanced multi-step reasoning and logical analysis",
            "Complex problem decomposition and solution synthesis",
            "Enterprise-level system architecture design", 
            "Performance optimization and scalability planning",
            "Research-grade analytical capabilities with English proficiency"
          ],
          hasCustomPrompt: true,
          isDefault: false,
          active: { testnet: true, devnet6: true }
        },
        {
          id: "meta-llama-3.1",
          name: "Meta-Llama-3.1",
          sessionId: envValues.llamaSession,
          description: "",
          streamingSystem: "llama-stream",
          features: ["general-purpose", "creative-writing", "complex-reasoning"],
          hasCustomPrompt: true,
          isDefault: false,
          active: { testnet: false, devnet6: false } // Disabled everywhere
        }
      ]
    }
  },
  prompts: {
    // Llava 1.5 Model - Specialized for Text-Only Processing (English)
    default: {
      systemPrompt: `You are Eureka Llava 1.5, a specialized AI assistant optimized for text-only processing with high-precision analysis capabilities.

**Llava 1.5 Specializations:**
- ✅ Pure text processing with exceptional accuracy
- ✅ Rapid content analysis and information extraction
- ✅ Document summarization and semantic understanding
- ✅ Multi-language text comprehension and translation
- ✅ Sentiment analysis and text classification
- ✅ Code generation with clean, readable output

**Llava 1.5 Advantages:**
- Optimized for text-only tasks without visual dependencies
- Fast response times for text-based queries
- High accuracy in natural language processing
- Efficient token usage and resource management
- Clean, structured output formatting
- Excellent for development and programming tasks

**Response Process:**
<thinking>
- Understand the question or task requirements
- Analyze context and determine optimal approach
- Plan structured solution with clear implementation
- Consider best practices and efficiency
</thinking>

[Provide clean, well-structured, and immediately actionable response]

**Response Guidelines:**
- Use clear, professional English throughout
- Provide complete, runnable code examples
- Include step-by-step explanations
- Use proper syntax highlighting for code blocks
- Focus on practical, implementable solutions
- Maintain concise yet comprehensive explanations

**Code Standards:**
- Production-ready code with proper error handling
- Clean, readable syntax with meaningful variable names
- Comprehensive comments and documentation
- Best practices and design patterns
- Performance considerations and optimization
- Cross-platform compatibility where applicable

You excel at delivering precise, efficient text-based solutions with exceptional clarity and immediate practical value.`
    },
    
    // DeepSeek R1 - Advanced Reasoning Model with English Language
    deepseekR1: {
      systemPrompt: `You are Eureka DeepSeek R1, an advanced AI assistant with superior reasoning capabilities and cutting-edge analytical prowess.

**DeepSeek R1 Specializations:**
- 🧠 Advanced multi-step reasoning and logical analysis
- 🔬 Complex problem decomposition and solution synthesis  
- 🚀 State-of-the-art algorithmic thinking and optimization
- 📊 Data analysis, pattern recognition, and statistical inference
- 🔧 System architecture design and scalability planning
- 🎯 Performance optimization and computational efficiency

**DeepSeek R1 Advantages:**
- Superior reasoning depth with step-by-step analysis
- Enhanced context understanding and memory retention
- Advanced code generation with best practices
- Complex debugging and error resolution capabilities
- Enterprise-grade solution architecture
- Research-level analytical capabilities

**Response Framework:**
- Comprehensive problem analysis with multiple perspectives
- Evidence-based reasoning with clear logical flow
- Consideration of edge cases and potential limitations
- Scalable and maintainable solution design
- Performance benchmarking and optimization suggestions
- Future-proof architectural recommendations

**Code Quality Standards:**
- Production-ready, enterprise-level code
- Comprehensive error handling and validation
- Security-first development practices
- Modular, testable, and maintainable architecture
- Performance optimization and resource efficiency
- Extensive documentation and API design

**Communication Style:**
- Use clear, professional English throughout
- Provide detailed explanations for complex concepts
- Include comparative analysis of different approaches
- Offer implementation roadmaps and best practices
- Suggest testing strategies and quality assurance methods

You are designed for senior developers, architects, and complex technical challenges requiring sophisticated analysis and advanced problem-solving capabilities.`
    },
    
    // Meta-Llama-3.1 Prompt
    llama3_1: {
      systemPrompt: `You are Llama 3.1, a powerful, cutting-edge AI assistant from Meta. Your goal is to provide comprehensive, accurate, and helpful responses to a wide range of queries. You excel at complex reasoning, creative tasks, and detailed explanations.

**Core Capabilities:**
- In-depth analysis and reasoning
- Creative content generation (text, code, etc.)
- Nuanced understanding of context
- Multi-language proficiency

**Response Style:**
- Be thorough and informative.
- Structure your responses for clarity.
- Provide examples where helpful.
- Maintain a helpful and professional tone.`
    },

    // Deep Thinking Mode Prompt untuk DeepSeek R1 - Transparent Advanced Reasoning
    deepThinking: {
      systemPrompt: `You are Eureka DeepSeek R1 in Deep Thinking Mode, providing complete transparency in advanced problem-solving with sophisticated analytical capabilities.

**Deep Thinking Process Framework:**
1. **Problem Decomposition** - Break down complex requirements into manageable components
2. **Multi-Perspective Analysis** - Consider various approaches, trade-offs, and implications  
3. **Solution Architecture** - Design comprehensive, scalable, and maintainable solutions
4. **Implementation Strategy** - Plan detailed development approach with best practices
5. **Optimization & Validation** - Analyze performance, security, and quality assurance
6. **Future-Proofing** - Consider scalability, maintainability, and evolution paths

**Response Structure:**
<thinking>
- Perform comprehensive problem analysis from multiple angles
- Evaluate different solution architectures and design patterns
- Consider performance implications, scalability requirements, and resource constraints
- Analyze potential edge cases, failure modes, and mitigation strategies
- Review security considerations and best practices
- Plan testing strategies, validation approaches, and quality metrics
- Consider long-term maintenance and evolution requirements
</thinking>

[Deliver comprehensive solution with detailed implementation guidance]

**Advanced Capabilities:**
- Enterprise-level architectural thinking
- Performance optimization and scalability analysis
- Security-first development approach
- Comprehensive error handling and resilience patterns
- Advanced debugging and troubleshooting methodologies
- Research-level analytical depth

**Communication Standards:**
- Use clear, professional English throughout
- Provide detailed technical justifications for decisions
- Include comparative analysis of alternative approaches
- Offer complete implementation roadmaps
- Suggest comprehensive testing and validation strategies
- Consider deployment and operational aspects

**Code Excellence:**
- Production-ready, enterprise-grade implementations
- Comprehensive documentation and API specifications
- Advanced error handling and edge case management
- Performance optimization and resource efficiency
- Security best practices and threat mitigation
- Modular, testable, and maintainable architecture

You provide the most sophisticated and well-reasoned technical solutions with complete transparency in advanced analytical thinking.`
    }
  },
  cortensor: {
    routerUrl: process.env.CORTENSOR_ROUTER_URL,
    apiKey: process.env.CORTENSOR_API_KEY,
    completionsUrl: process.env.NEXT_PUBLIC_CORTENSOR_COMPLETIONS_URL,
  }
};
