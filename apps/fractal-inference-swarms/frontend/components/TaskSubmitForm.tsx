'use client';

import React, { useState } from 'react';
import { submitTask } from '@/lib/api';

interface TaskSubmitFormProps {
  onSubmitted: () => void;
}

const PRESET_TASKS = [
  {
    title: 'Market Analysis: AI Infrastructure',
    description: 'Analyze the current state of AI infrastructure market including cloud providers, edge computing, and specialized hardware. Evaluate key players, market trends, pricing models, and predict growth trajectories for the next 5 years.',
    priority: 'high' as const,
    swarmSize: 5,
  },
  {
    title: 'Security Audit: Microservices Architecture',
    description: 'Conduct a comprehensive security audit of a microservices architecture. Evaluate authentication flows, inter-service communication, data encryption, API gateway vulnerabilities, and container orchestration security posture.',
    priority: 'critical' as const,
    swarmSize: 6,
  },
  {
    title: 'Research: Quantum-Resistant Cryptography',
    description: 'Research the latest developments in post-quantum cryptographic algorithms. Compare lattice-based, hash-based, and code-based approaches. Evaluate NIST standardization candidates and implementation readiness for production systems.',
    priority: 'medium' as const,
    swarmSize: 4,
  },
  {
    title: 'Design System: Component Architecture',
    description: 'Design a scalable component architecture for a design system supporting web and mobile platforms. Define token systems, composability patterns, accessibility requirements, and theming capabilities with performance constraints.',
    priority: 'medium' as const,
    swarmSize: 5,
  },
];

export default function TaskSubmitForm({ onSubmitted }: TaskSubmitFormProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<string>('medium');
  const [swarmSize, setSwarmSize] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPresets, setShowPresets] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      await submitTask({ title: title.trim(), description: description.trim(), priority, swarmSize });
      setTitle('');
      setDescription('');
      setPriority('medium');
      setSwarmSize(5);
      onSubmitted();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  function loadPreset(preset: typeof PRESET_TASKS[number]) {
    setTitle(preset.title);
    setDescription(preset.description);
    setPriority(preset.priority);
    setSwarmSize(preset.swarmSize);
    setShowPresets(false);
  }

  return (
    <div className="bg-swarm-card border border-swarm-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-swarm-text">Submit Task to Swarm</h2>
        <button
          onClick={() => setShowPresets(!showPresets)}
          className="text-xs px-3 py-1.5 bg-swarm-surface border border-swarm-border rounded-lg text-swarm-muted hover:text-swarm-accent hover:border-swarm-accent/40 transition-colors"
        >
          {showPresets ? 'Hide Presets' : 'Load Preset'}
        </button>
      </div>

      {showPresets && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
          {PRESET_TASKS.map((preset, i) => (
            <button
              key={i}
              onClick={() => loadPreset(preset)}
              className="text-left p-3 bg-swarm-surface border border-swarm-border rounded-lg hover:border-swarm-accent/50 transition-all group"
            >
              <div className="text-sm font-medium text-swarm-text group-hover:text-swarm-accent transition-colors">{preset.title}</div>
              <div className="text-xs text-swarm-muted mt-1 line-clamp-2">{preset.description}</div>
              <div className="flex gap-2 mt-2">
                <span className="text-xs px-1.5 py-0.5 bg-swarm-border/50 rounded text-swarm-muted">{preset.priority}</span>
                <span className="text-xs px-1.5 py-0.5 bg-swarm-border/50 rounded text-swarm-muted">{preset.swarmSize} agents</span>
              </div>
            </button>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Task title..."
          className="w-full px-4 py-2.5 bg-swarm-surface border border-swarm-border rounded-lg text-swarm-text placeholder-swarm-muted focus:outline-none focus:border-swarm-accent/60 focus:ring-1 focus:ring-swarm-accent/30 transition-all text-sm"
          required
        />
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Describe the task in detail. The orchestrator will decompose this into subtasks and assign them to swarm agents..."
          rows={3}
          className="w-full px-4 py-2.5 bg-swarm-surface border border-swarm-border rounded-lg text-swarm-text placeholder-swarm-muted focus:outline-none focus:border-swarm-accent/60 focus:ring-1 focus:ring-swarm-accent/30 transition-all text-sm resize-none"
          required
        />
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="text-xs text-swarm-muted block mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full px-3 py-2 bg-swarm-surface border border-swarm-border rounded-lg text-swarm-text text-sm focus:outline-none focus:border-swarm-accent/60"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="text-xs text-swarm-muted block mb-1">Swarm Size: {swarmSize}</label>
            <input
              type="range"
              min={2}
              max={12}
              value={swarmSize}
              onChange={(e) => setSwarmSize(Number(e.target.value))}
              className="w-full h-9 accent-swarm-accent"
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={submitting || !title.trim() || !description.trim()}
              className="px-6 py-2 bg-swarm-accent hover:bg-blue-600 disabled:bg-swarm-border disabled:text-swarm-muted text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            >
              {submitting ? 'Deploying...' : 'Deploy Swarm'}
            </button>
          </div>
        </div>
        {error && <div className="text-red-400 text-xs bg-red-900/20 border border-red-800/40 rounded-lg p-2">{error}</div>}
      </form>
    </div>
  );
}