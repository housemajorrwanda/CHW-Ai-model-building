import { Node, mergeAttributes } from '@tiptap/core';
import { ReactRenderer } from '@tiptap/react';
import { NodeViewWrapper } from '@tiptap/react';
import React from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

const GraphComponent = ({ node }: { node: any }) => {
  const { graphType, data, title, xLabel, yLabel } = node.attrs;

  const parsedData = Array.isArray(data) ? data : [];

  const renderChart = () => {
    if (parsedData.length === 0) {
      return (
        <div className="flex items-center justify-center h-48 text-muted-foreground">
          No data available
        </div>
      );
    }

    return (
      <ResponsiveContainer width="100%" height={200}>
        {graphType === 'line' && (
          <LineChart data={parsedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" label={{ value: xLabel, position: 'insideBottom', offset: -5 }} />
            <YAxis label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2} />
          </LineChart>
        )}
        {graphType === 'bar' && (
          <BarChart data={parsedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        )}
        {graphType === 'pie' && (
          <PieChart>
            <Pie
              data={parsedData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              outerRadius={60}
              label
            >
              {parsedData.map((entry: any, index: number) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        )}
      </ResponsiveContainer>
    );
  };

  return (
    <NodeViewWrapper className="graph-node my-4 border border-border rounded-lg p-4 bg-background">
      {title && <h4 className="text-sm font-semibold mb-2">{title}</h4>}
      {renderChart()}
      <div className="text-xs text-muted-foreground mt-2">
        X: {xLabel} | Y: {yLabel}
      </div>
    </NodeViewWrapper>
  );
};

export const GraphExtension = Node.create({
  name: 'graph',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,
  inline: false,

  addAttributes() {
    return {
      graphType: {
        default: 'line',
      },
      data: {
        default: [],
      },
      title: {
        default: 'Graph',
      },
      xLabel: {
        default: 'X Axis',
      },
      yLabel: {
        default: 'Y Axis',
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-type="graph"]',
        getAttrs: (element) => {
          if (typeof element === 'string') return false;
          const el = element as HTMLElement;
          try {
            const dataStr = el.getAttribute('data-graph-data');
            const data = dataStr ? JSON.parse(dataStr) : [];
            return {
              graphType: el.getAttribute('data-graph-type') || 'line',
              data: data,
              title: el.getAttribute('data-graph-title') || 'Graph',
              xLabel: el.getAttribute('data-graph-xlabel') || 'X Axis',
              yLabel: el.getAttribute('data-graph-ylabel') || 'Y Axis',
            };
          } catch {
            return {
              graphType: 'line',
              data: [],
              title: 'Graph',
              xLabel: 'X Axis',
              yLabel: 'Y Axis',
            };
          }
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'graph' }), 0];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('div');
      dom.className = 'graph-node-wrapper';

      const component = new ReactRenderer(GraphComponent, {
        editor,
        props: {
          node,
        },
        dom,
      });

      return {
        dom,
        contentDOM: null,
        update: (updatedNode) => {
          if (updatedNode.type.name !== this.name) {
            return false;
          }
          component.updateProps({ node: updatedNode });
          return true;
        },
        destroy: () => {
          component.destroy();
        },
      };
    };
  },

  addCommands() {
    return {
      insertGraph: (options: any) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: options,
        });
      },
    };
  },
});

