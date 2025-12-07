export enum NodeType {
  SEED = 'SEED',
  RECOMMENDED = 'RECOMMENDED'
}

export interface BookNode {
  id: string; // The book title serves as ID
  label: string;
  author: string;
  type: NodeType;
  group: number; // 0, 1, 2 corresponding to the 3 seed inputs
  description: string;
  reason?: string; // Why it was recommended (if type is RECOMMENDED)
  // Simulation properties
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface BookLink {
  source: string | BookNode; // D3 converts string ID to object ref
  target: string | BookNode;
  relation: string; // The edge label (e.g., "Complex Prose")
}

export interface GraphData {
  nodes: BookNode[];
  links: BookLink[];
}

export interface AnalysisResponse {
  nodes: {
    id: string;
    title: string;
    author: string;
    type: 'SEED' | 'RECOMMENDED';
    originSeedIndex: number; // 0, 1, or 2. If it connects to multiple, pick primary.
    description: string;
  }[];
  links: {
    source: string;
    target: string;
    label: string;
  }[];
}
