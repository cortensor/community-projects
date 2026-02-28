/**
 * ContextHandoff.ts
 * Manages the memory state between execution layers. Injects the raw output 
 * of an upstream node into the required system prompt/parameters of a downstream node.
 */

import { DAGNode, DAGEdge } from "@/lib/engine/execution/TopologicalSorter";

// A global executing memory state for a given swarm run
export type ExecutionState = Record<string, string>; // { nodeId: "raw output block" }

export class ContextHandoff {
  private state: ExecutionState = {};
  private edges: DAGEdge[];

  constructor(edges: DAGEdge[]) {
    this.edges = edges;
  }

  /**
   * Commits the output of a completed node to the memory layer.
   */
  public commit(nodeId: string, output: string) {
    this.state[nodeId] = output;
  }

  /**
   * Hydrates a downstream node by pulling outputs from all of its upstream connections.
   * Returns a merged context string.
   */
  public hydrate(nodeId: string): string {
    const incomingEdges = this.edges.filter((e) => e.target === nodeId);
    
    if (incomingEdges.length === 0) return "";

    let aggregatedContext = "";
    incomingEdges.forEach((edge, index) => {
      const upstreamOutput = this.state[edge.source];
      if (upstreamOutput) {
        aggregatedContext += `\n--- [UPSTREAM CONTEXT: Node ${edge.source}] ---\n${upstreamOutput}\n`;
      }
    });

    return aggregatedContext.trim();
  }

  /**
   * Returns the absolute memory payload (useful for final IPFS commit).
   */
  public getSnapshot(): ExecutionState {
    return this.state;
  }
}
