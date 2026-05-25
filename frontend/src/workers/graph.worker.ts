// Web Worker running D3 force layouts for schema dependency graph computations
import * as d3 from "d3-force";

interface Node {
  id: string;
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

interface Link {
  source: string;
  target: string;
}

self.onmessage = (event: MessageEvent) => {
  const { type, nodes, links, width, height } = event.data;

  if (type === "init") {
    // Run D3 force simulation
    const simulation = d3.forceSimulation<Node>(nodes)
      .force("link", d3.forceLink<Node, Link>(links).id((d) => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-150))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(35));

    simulation.on("tick", () => {
      // Post coordinates update back to main thread
      self.postMessage({
        type: "tick",
        nodes: nodes.map((n: Node) => ({ id: n.id, x: n.x, y: n.y })),
        links: links.map((l: any) => ({
          source: typeof l.source === "object" ? l.source.id : l.source,
          target: typeof l.target === "object" ? l.target.id : l.target
        }))
      });
    });

    simulation.on("end", () => {
      self.postMessage({
        type: "end",
        nodes: nodes.map((n: Node) => ({ id: n.id, x: n.x, y: n.y })),
        links: links.map((l: any) => ({
          source: typeof l.source === "object" ? l.source.id : l.source,
          target: typeof l.target === "object" ? l.target.id : l.target
        }))
      });
    });
  }
};
