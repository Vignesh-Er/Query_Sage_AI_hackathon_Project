import React, { useMemo } from 'react';
import { ReactFlow, Handle, Position, Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { TOKENS } from '../../design-system/tokens';

const CustomPlanNode = ({ data }: any) => {
  const { nodeType, relationName, rowsEstimated, rowsActual, costTotal, cacheHitRatio, hasSortSpill, rootCost } = data;

  // Calculate cost percentage relative to root node
  const costPercent = rootCost > 0 ? (costTotal / rootCost) * 100 : 0;
  
  // Left border color based on cost severity
  let borderLeftColor: string = TOKENS.colors.glacier; // Glacier if below 20%
  if (costPercent > 50) {
    borderLeftColor = TOKENS.colors.cinder; // Cinder if > 50%
  } else if (costPercent >= 20) {
    borderLeftColor = TOKENS.colors.sulfur; // Sulfur if 20% to 50%
  }

  return (
    <div 
      style={{
        background: TOKENS.colors.pitch,
        border: `1px solid ${TOKENS.colors.border}`,
        borderLeft: `4px solid ${borderLeftColor}`,
        borderRadius: TOKENS.radii.md,
        padding: '10px 14px',
        width: '260px',
        color: TOKENS.colors.text.primary,
        fontFamily: TOKENS.fonts.ui,
        boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: borderLeftColor }} />
      
      <div 
        style={{ 
          fontSize: '11px', 
          fontWeight: 'bold', 
          textTransform: 'uppercase', 
          color: TOKENS.colors.text.secondary,
          marginBottom: '6px',
          letterSpacing: '0.05em'
        }}
      >
        {nodeType}
      </div>

      {relationName && (
        <div style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '8px', color: TOKENS.colors.ember }}>
          {relationName}
        </div>
      )}

      <div style={{ fontFamily: TOKENS.fonts.code, fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: TOKENS.colors.text.secondary }}>Est / Act Rows:</span>
          <span>{rowsEstimated} / {rowsActual}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: TOKENS.colors.text.secondary }}>Cost / %:</span>
          <span>{costTotal} ({costPercent.toFixed(1)}%)</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: TOKENS.colors.text.secondary }}>Cache Hit:</span>
          <span>{(cacheHitRatio * 100).toFixed(0)}%</span>
        </div>
        {hasSortSpill && (
          <div style={{ color: TOKENS.colors.cinder, fontWeight: 'bold', marginTop: '4px' }}>
            ⚠️ Sort Spilled to Disk
          </div>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ background: borderLeftColor }} />
    </div>
  );
};

// Map ReactFlow custom node types
const nodeTypes = {
  custom: CustomPlanNode,
};

interface PlanTreeVisualizerProps {
  planJson: any;
}

export const PlanTreeVisualizer: React.FC<PlanTreeVisualizerProps> = ({ planJson }) => {
  const { nodes, edges } = useMemo(() => {
    if (!planJson) return { nodes: [], edges: [] };

    const nodesList: Node[] = [];
    const edgesList: Edge[] = [];
    let nodeCounter = 0;

    const rootCost = planJson.cost_total || 1.0;

    function traverse(node: any, depth: number, parentId: string | null): string {
      const id = `node-${nodeCounter++}`;
      
      nodesList.push({
        id,
        type: 'custom',
        data: {
          nodeType: node.node_type,
          relationName: node.relation_name,
          alias: node.alias,
          rowsEstimated: node.rows_estimated,
          rowsActual: node.rows_actual,
          costTotal: node.cost_total,
          cacheHitRatio: (node.shared_blocks_hit || 0) + (node.shared_blocks_read || 0) > 0 
            ? (node.shared_blocks_hit / (node.shared_blocks_hit + node.shared_blocks_read))
            : 1.0,
          hasSortSpill: (node.temp_blocks_written || 0) > 0,
          rootCost
        },
        position: { x: 0, y: depth * 160 }
      });

      if (parentId) {
        edgesList.push({
          id: `edge-${parentId}-${id}`,
          source: parentId,
          target: id,
          type: 'smoothstep',
          style: { stroke: TOKENS.colors.border, strokeWidth: 2 }
        });
      }

      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any) => {
          traverse(child, depth + 1, id);
        });
      }

      return id;
    }

    traverse(planJson, 0, null);

    // Apply X coordinate layout to avoid overlaps
    const levelOffsets: Record<number, number> = {};

    function layout(nodeId: string, depth: number) {
      const nodeObj = nodesList.find(n => n.id === nodeId);
      if (!nodeObj) return;

      const childEdges = edgesList.filter(e => e.source === nodeId);
      const childIds = childEdges.map(e => e.target);

      if (childIds.length > 0) {
        childIds.forEach(cid => layout(cid, depth + 1));
        
        const childNodes = nodesList.filter(n => childIds.includes(n.id));
        const minX = Math.min(...childNodes.map(c => c.position.x));
        const maxX = Math.max(...childNodes.map(c => c.position.x));
        const averageChildrenX = minX + (maxX - minX) / 2;

        const currentOffset = levelOffsets[depth] || 0;
        nodeObj.position.x = Math.max(currentOffset, averageChildrenX);
        levelOffsets[depth] = nodeObj.position.x + 300;
      } else {
        const currentOffset = levelOffsets[depth] || 0;
        nodeObj.position.x = currentOffset;
        levelOffsets[depth] = currentOffset + 300;
      }
    }

    if (nodesList.length > 0) {
      layout(nodesList[0].id, 0);
    }

    return { nodes: nodesList, edges: edgesList };
  }, [planJson]);

  if (!planJson) return null;

  return (
    <div style={{ height: '400px', width: '100%', border: `1px solid ${TOKENS.colors.border}`, borderRadius: TOKENS.radii.lg, overflow: 'hidden', background: TOKENS.colors.abyss }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
      />
    </div>
  );
};

export default PlanTreeVisualizer;
