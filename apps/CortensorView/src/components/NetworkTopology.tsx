import { useEffect, useRef, useState } from 'react';
import type { NodeData } from '../types/cortensor';

interface NetworkTopologyProps {
  nodes: NodeData[];
  height?: number;
}

interface Node {
  id: string;
  x: number;
  y: number;
  radius: number;
  status: string;
  connections: number;
}

export default function NetworkTopology({ nodes, height = 400 }: NetworkTopologyProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [networkNodes, setNetworkNodes] = useState<Node[]>([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const centerX = width / 2;
    const centerY = height / 2;

    // Create network nodes with positions
    const processedNodes: Node[] = nodes.slice(0, 20).map((node, idx) => {
      const angle = (idx / Math.min(nodes.length, 20)) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.35;
      
      return {
        id: node.hotkey || node.id || `node-${idx}`,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        radius: 8 + (node.stake ? Math.min(node.stake / 10000, 12) : 8),
        status: node.status || 'active',
        connections: Math.floor(Math.random() * 10) + 3,
      };
    });

    setNetworkNodes(processedNodes);

    // Animation frame
    let animationFrame: number;
    let time = 0;

    const animate = () => {
      ctx.clearRect(0, 0, width, height);
      time += 0.01;

      // Draw connections
      ctx.strokeStyle = '#e5e7eb';
      ctx.lineWidth = 1;
      processedNodes.forEach((node, i) => {
        processedNodes.slice(i + 1).forEach((otherNode) => {
          if (Math.random() > 0.7) {
            ctx.beginPath();
            ctx.moveTo(node.x, node.y);
            ctx.lineTo(otherNode.x, otherNode.y);
            ctx.stroke();
          }
        });
      });

      // Draw center hub
      ctx.beginPath();
      ctx.arc(centerX, centerY, 20, 0, 2 * Math.PI);
      ctx.fillStyle = '#111827';
      ctx.fill();
      ctx.strokeStyle = '#3b82f6';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw connections to center
      ctx.strokeStyle = '#9ca3af';
      ctx.lineWidth = 1;
      processedNodes.forEach((node) => {
        ctx.beginPath();
        ctx.moveTo(centerX, centerY);
        ctx.lineTo(node.x, node.y);
        ctx.stroke();
      });

      // Draw nodes
      processedNodes.forEach((node) => {
        const isHovered = hoveredNode === node.id;
        const pulse = Math.sin(time * 2) * 2;

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius + (isHovered ? pulse : 0), 0, 2 * Math.PI);
        
        // Color based on status
        if (node.status === 'active') {
          ctx.fillStyle = isHovered ? '#10b981' : '#34d399';
        } else if (node.status === 'inactive') {
          ctx.fillStyle = isHovered ? '#6b7280' : '#9ca3af';
        } else {
          ctx.fillStyle = isHovered ? '#f59e0b' : '#fbbf24';
        }
        
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2;
        ctx.stroke();

        // Draw activity indicator
        if (node.status === 'active') {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 4, 0, 2 * Math.PI);
          ctx.strokeStyle = '#10b981';
          ctx.lineWidth = 1;
          ctx.globalAlpha = 0.3 + Math.sin(time * 3) * 0.3;
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
      });

      animationFrame = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [nodes, height, hoveredNode]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const hoveredNode = networkNodes.find((node) => {
      const distance = Math.sqrt((x - node.x) ** 2 + (y - node.y) ** 2);
      return distance < node.radius + 5;
    });

    setHoveredNode(hoveredNode?.id || null);
  };

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={800}
        height={height}
        className="w-full rounded-lg"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredNode(null)}
      />
      {hoveredNode && (
        <div className="absolute top-4 right-4 bg-white border border-gray-200 rounded-lg p-3 shadow-lg text-xs">
          <p className="font-semibold text-gray-900">Node: {hoveredNode.slice(0, 12)}...</p>
          <p className="text-gray-600 mt-1">
            Status: <span className="font-medium">Active</span>
          </p>
        </div>
      )}
    </div>
  );
}
