import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { GraphData, BookNode, BookLink, NodeType } from '../types';
import { COLORS } from '../constants';

interface NetworkGraphProps {
  data: GraphData;
  onNodeClick: (node: BookNode) => void;
}

const NetworkGraph: React.FC<NetworkGraphProps> = ({ data, onNodeClick }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Handle Resize
  useEffect(() => {
    const handleResize = () => {
      if (wrapperRef.current) {
        setDimensions({
          width: wrapperRef.current.offsetWidth,
          height: wrapperRef.current.offsetHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Initialize D3 Graph
  useEffect(() => {
    if (!svgRef.current || data.nodes.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear previous render

    const { width, height } = dimensions;

    // Zoom behavior
    const zoomGroup = svg.append("g");
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        zoomGroup.attr("transform", event.transform);
      });
    
    svg.call(zoom);

    // Deep copy data to prevent D3 from mutating strict React props
    const nodes: BookNode[] = JSON.parse(JSON.stringify(data.nodes));
    const links: BookLink[] = JSON.parse(JSON.stringify(data.links));

    // Simulation Setup
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(150)) // Spring length
      .force("charge", d3.forceManyBody().strength(-400)) // Repulsion
      .force("center", d3.forceCenter(width / 2, height / 2)) // Center gravity
      .force("collide", d3.forceCollide().radius((d: any) => d.type === NodeType.SEED ? 60 : 40).iterations(2));

    // 1. Defs for markers (arrows)
    const defs = svg.append("defs");
    defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 25) // Position relative to node center, adjusted later manually if needed
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#64748b"); // Slate-500

    // 2. Links (Lines)
    const linkGroup = zoomGroup.append("g").attr("class", "links");
    
    const link = linkGroup
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke", "#475569") // Slate-600
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrowhead)");

    // 3. Link Labels (Text on lines)
    const linkLabel = zoomGroup.append("g")
      .attr("class", "link-labels")
      .selectAll("text")
      .data(links)
      .enter()
      .append("text")
      .text(d => d.relation)
      .attr("font-size", "10px")
      .attr("fill", "#94a3b8") // Slate-400
      .attr("text-anchor", "middle")
      .attr("dy", -5) // Shift slightly above the line
      .style("pointer-events", "none") // Let clicks pass through
      .style("text-shadow", "0px 1px 2px #0f172a");

    // 4. Nodes (Circles)
    const nodeGroup = zoomGroup.append("g").attr("class", "nodes");

    const node = nodeGroup
      .selectAll("g")
      .data(nodes)
      .enter()
      .append("g")
      .call(d3.drag<SVGGElement, BookNode>()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Node Circles
    node.append("circle")
      .attr("r", d => d.type === NodeType.SEED ? 30 : 18)
      .attr("fill", d => COLORS[d.group % COLORS.length])
      .attr("stroke", "#f8fafc")
      .attr("stroke-width", d => d.type === NodeType.SEED ? 3 : 1.5)
      .attr("class", "cursor-pointer transition-all duration-200 hover:opacity-90")
      .style("filter", "drop-shadow(0px 4px 6px rgba(0,0,0,0.5))")
      .on("click", (event, d) => {
        event.stopPropagation();
        onNodeClick(d);
      });

    // Node Labels (Book Titles)
    node.append("text")
      .text(d => d.label)
      .attr("x", 0)
      .attr("y", d => d.type === NodeType.SEED ? 45 : 32)
      .attr("text-anchor", "middle")
      .attr("fill", "#e2e8f0")
      .attr("font-size", d => d.type === NodeType.SEED ? "14px" : "11px")
      .attr("font-weight", d => d.type === NodeType.SEED ? "bold" : "normal")
      .style("pointer-events", "none")
      .style("text-shadow", "0px 2px 4px #000");


    // Simulation Tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      linkLabel
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

      node
        .attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Drag Functions
    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [data, dimensions, onNodeClick]);

  return (
    <div ref={wrapperRef} className="w-full h-full relative overflow-hidden bg-slate-900 rounded-xl shadow-inner border border-slate-800">
       {/* Background Grid Pattern (Optional visual flair) */}
       <div className="absolute inset-0 opacity-10 pointer-events-none" 
            style={{ 
              backgroundImage: 'radial-gradient(#475569 1px, transparent 1px)', 
              backgroundSize: '20px 20px' 
            }} 
       />
      <svg ref={svgRef} width="100%" height="100%" className="cursor-move touch-none"></svg>
      
      {/* Legend */}
      <div className="absolute top-4 left-4 bg-slate-900/80 backdrop-blur p-3 rounded-lg border border-slate-700 pointer-events-none select-none">
        <div className="text-xs text-slate-400 font-bold mb-2 uppercase">Legend</div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[0]}}></div>
          <span className="text-xs text-slate-300">Seed Group 1</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[1]}}></div>
          <span className="text-xs text-slate-300">Seed Group 2</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full" style={{backgroundColor: COLORS[2]}}></div>
          <span className="text-xs text-slate-300">Seed Group 3</span>
        </div>
      </div>
    </div>
  );
};

export default NetworkGraph;
