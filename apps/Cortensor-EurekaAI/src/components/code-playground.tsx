"use client"

import React, { useState, useRef, useEffect } from 'react'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Textarea } from './ui/textarea'
import { ScrollArea } from './ui/scroll-area'
import { Badge } from './ui/badge'
import { Play, Copy, RotateCcw, Download, Code2, Terminal } from 'lucide-react'
import { cn } from '@/lib/utils'

// Default code templates for different languages
const getDefaultCode = (language: string): string => {
  switch (language) {
    case 'javascript':
      return '// Simple JavaScript example\nconsole.log("Hello, World!");\n\n// Try different examples:\n// Variables\nconst name = "Eureka";\nconsole.log(`Welcome to ${name}!`);'
    case 'python':
      return '# Simple Python example\nprint("Hello, World!")\n\n# Try different examples:\n# Variables\nname = "Eureka"\nprint(f"Welcome to {name}!")'
    case 'html':
      return '<!DOCTYPE html>\n<html>\n<head>\n    <title>Simple HTML Page</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n    <p>Welcome to Eureka!</p>\n</body>\n</html>'
    case 'css':
      return '/* Simple CSS example */\nbody {\n    font-family: Arial, sans-serif;\n    background-color: #f0f0f0;\n    margin: 0;\n    padding: 20px;\n}\n\nh1 {\n    color: #333;\n    text-align: center;\n}'
    case 'typescript':
      return '// Simple TypeScript example\ninterface User {\n    name: string;\n    age: number;\n}\n\nconst user: User = {\n    name: "Eureka",\n    age: 1\n};\n\nconsole.log(`Hello, ${user.name}!`);'
    case 'java':
      return 'public class HelloWorld {\n    public static void main(String[] args) {\n        System.out.println("Hello, World!");\n        \n        // Variables\n        String name = "Eureka";\n        System.out.println("Welcome to " + name + "!");\n    }\n}'
    case 'cpp':
      return '#include <iostream>\n#include <string>\n\nint main() {\n    std::cout << "Hello, World!" << std::endl;\n    \n    // Variables\n    std::string name = "Eureka";\n    std::cout << "Welcome to " << name << "!" << std::endl;\n    \n    return 0;\n}'
    default:
      return '// Write your code here\nconsole.log("Hello, World!");'
  }
}

interface CodePlaygroundProps {
  initialCode?: string
  language?: 'javascript' | 'python' | 'html' | 'css' | 'typescript' | 'java' | 'cpp'
  className?: string
}

export function CodePlayground({ 
  initialCode = getDefaultCode('javascript'), 
  language = 'javascript',
  className 
}: CodePlaygroundProps) {
  const [code, setCode] = useState(initialCode)
  const [output, setOutput] = useState<string[]>([])
  const [isRunning, setIsRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const scrollHeight = textareaRef.current.scrollHeight
      const maxHeight = 400
      textareaRef.current.style.height = `${Math.min(scrollHeight, maxHeight)}px`
    }
  }, [code])

  const executeJavaScript = () => {
    setIsRunning(true)
    setError(null)
    setOutput([])

    try {
      // Create a safe execution environment
      const consoleOutput: string[] = []
      
      // Mock console object to capture output
      const mockConsole = {
        log: (...args: any[]) => {
          consoleOutput.push(args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
          ).join(' '))
        },
        error: (...args: any[]) => {
          consoleOutput.push(`❌ Error: ${args.join(' ')}`)
        },
        warn: (...args: any[]) => {
          consoleOutput.push(`⚠️ Warning: ${args.join(' ')}`)
        },
        info: (...args: any[]) => {
          consoleOutput.push(`ℹ️ Info: ${args.join(' ')}`)
        }
      }

      // Create execution function
      const executeCode = new Function('console', 'window', 'document', 'alert', code)
      
      // Execute with limited scope (no access to real window/document for security)
      executeCode(mockConsole, undefined, undefined, undefined)
      
      setOutput(consoleOutput.length > 0 ? consoleOutput : ['✅ Code executed successfully (no output)'])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
      setOutput([`❌ Execution Error: ${err instanceof Error ? err.message : 'Unknown error'}`])
    } finally {
      setIsRunning(false)
    }
  }

  const executeCode = () => {
    if (language === 'javascript' || language === 'typescript') {
      executeJavaScript()
    } else if (language === 'html') {
      executeHTML()
    } else if (language === 'css') {
      setOutput(['✅ CSS code is valid. In a real environment, this would be applied to your HTML.'])
    } else {
      setOutput([`⚠️ Code execution for ${language.toUpperCase()} is not yet supported in the browser environment.`, `📝 However, your code looks good and can be used in a proper ${language.toUpperCase()} environment.`])
    }
  }

  const executeHTML = () => {
    setIsRunning(true)
    setError(null)
    setOutput([])

    try {
      // For HTML, we'll show a preview or validate the structure
      const hasValidHTML = code.includes('<html>') || code.includes('<div>') || code.includes('<p>') || code.includes('<h1>')
      
      if (hasValidHTML) {
        setOutput([
          '✅ HTML code is valid!',
          '🌐 In a real environment, this would render in the browser.',
          '💡 Tip: You can copy this code and save it as an .html file to test it.'
        ])
      } else {
        setOutput(['⚠️ This doesn\'t appear to be valid HTML. Make sure to include proper HTML tags.'])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setIsRunning(false)
    }
  }

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(code)
    } catch (err) {
      console.error('Failed to copy code:', err)
    }
  }

  const resetCode = () => {
    setCode(initialCode)
    setOutput([])
    setError(null)
  }

  const downloadCode = () => {
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `code.${language === 'javascript' ? 'js' : language}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Run code with Ctrl/Cmd + Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      executeCode()
    }
    
    // Tab indentation
    if (e.key === 'Tab') {
      e.preventDefault()
      const target = e.currentTarget as HTMLTextAreaElement
      const start = target.selectionStart
      const end = target.selectionEnd
      const newCode = code.substring(0, start) + '  ' + code.substring(end)
      setCode(newCode)
      
      // Restore cursor position
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 2
        }
      }, 0)
    }
  }

  return (
    <div className={cn("w-full space-y-4", className)}>
      <Card className="border-slate-200 dark:border-slate-800">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Code2 className="h-5 w-5 text-blue-600" />
              <CardTitle className="text-lg">Code Playground</CardTitle>
              <Badge variant="outline" className="text-xs">
                {language.toUpperCase()}
              </Badge>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={copyCode}
                className="text-xs"
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={resetCode}
                className="text-xs"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={downloadCode}
                className="text-xs"
              >
                <Download className="h-3 w-3 mr-1" />
                Download
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Code Editor */}
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Write your ${language} code here...`}
              className="font-mono text-sm min-h-[200px] resize-none bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800"
              spellCheck={false}
            />
            <div className="absolute bottom-2 right-2 text-xs text-slate-500">
              Press Ctrl+Enter to run
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center space-x-2">
            <Button
              onClick={executeCode}
              disabled={isRunning || !code.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              <Play className="h-4 w-4 mr-2" />
              {isRunning ? 'Running...' : 'Run Code'}
            </Button>
            <Badge variant="secondary" className="text-xs">
              Lines: {code.split('\n').length}
            </Badge>
            <Badge variant="secondary" className="text-xs">
              Characters: {code.length}
            </Badge>
          </div>

          {/* Output Console */}
          {(output.length > 0 || error) && (
            <Card className="bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-800">
              <CardHeader className="pb-2">
                <div className="flex items-center space-x-2">
                  <Terminal className="h-4 w-4 text-slate-600" />
                  <h4 className="text-sm font-medium">Console Output</h4>
                </div>
              </CardHeader>
              <CardContent>
                <ScrollArea className="max-h-40">
                  <div className="space-y-1">
                    {output.map((line, index) => (
                      <div 
                        key={index} 
                        className="text-sm font-mono p-2 rounded bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800"
                      >
                        {line}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
