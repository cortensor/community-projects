/**
 * TopologicalSorter.ts
 * Implements Kahn's Algorithm to securely sequence the Directed Acyclic Graph (DAG)
 * from the React Flow frontend into a deterministic execution array.
 */

export interface DAGNode {
  id: string;
  type: string;
  data: Record<string, any>;
}

export interface DAGEdge {
  id: string;
  source: string;
  target: string;
}

export function sortDAG(nodes: DAGNode[], edges: DAGEdge[]): DAGNode[][] {
  const adjacencyList = new Map<string, string[]>();
  const inDegree = new Map<string, number>();

  // Initialize maps
  nodes.forEach((node) => {
    adjacencyList.set(node.id, []);
    inDegree.set(node.id, 0);
  });

  // Populate edges and calculate in-degrees
  edges.forEach((edge) => {
    if (adjacencyList.has(edge.source) && inDegree.has(edge.target)) {
      adjacencyList.get(edge.source)!.push(edge.target);
      inDegree.set(edge.target, inDegree.get(edge.target)! + 1);
    }
  });

  // Kahn's Algorithm - sorted into concurrent execution layers
  const executionLayers: DAGNode[][] = [];
  let queue: string[] = [];

  // Find all nodes with 0 in-degree (Roots)
  inDegree.forEach((degree, nodeId) => {
    if (degree === 0) queue.push(nodeId);
  });

  let processedNodesCount = 0;

  while (queue.length > 0) {
    const currentLayer: DAGNode[] = [];
    const nextQueue: string[] = [];

    // Process all nodes in the current layer simultaneously
    for (const nodeId of queue) {
      const node = nodes.find((n) => n.id === nodeId);
      if (node) {
        currentLayer.push(node);
        processedNodesCount++;
      }

      const neighbors = adjacencyList.get(nodeId) || [];
      for (const neighborId of neighbors) {
        const currentInDegree = inDegree.get(neighborId)! - 1;
        inDegree.set(neighborId, currentInDegree);
        if (currentInDegree === 0) {
          nextQueue.push(neighborId);
        }
      }
    }

    executionLayers.push(currentLayer);
    queue = nextQueue;
  }

  // Cycle detection (if we didn't process all nodes, there's a loop)
  if (processedNodesCount !== nodes.length) {
    throw new Error("Cyclic Dependency Detected. Execution engine requires a strict DAG.");
  }

  return executionLayers;
}
