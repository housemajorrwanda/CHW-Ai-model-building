import { Node, mergeAttributes } from '@tiptap/core';
import { ReactRenderer } from '@tiptap/react';
import { NodeViewWrapper } from '@tiptap/react';
import React from 'react';

const ShapeComponent = ({ node }: { node: any }) => {
  const { type, width, height, color, strokeWidth } = node.attrs;

  const renderShape = () => {
    const w = parseInt(width) || 100;
    const h = parseInt(height) || 100;
    const c = color || '#3b82f6';
    const sw = parseInt(strokeWidth) || 2;

    switch (type) {
      case 'circle':
        return (
          <svg width={w} height={h} xmlns="http://www.w3.org/2000/svg">
            <circle
              cx={w / 2}
              cy={h / 2}
              r={Math.min(w, h) / 2 - 5}
              fill="none"
              stroke={c}
              strokeWidth={sw}
            />
          </svg>
        );
      case 'square':
        return (
          <svg width={w} height={h} xmlns="http://www.w3.org/2000/svg">
            <rect
              x="5"
              y="5"
              width={w - 10}
              height={w - 10}
              fill="none"
              stroke={c}
              strokeWidth={sw}
            />
          </svg>
        );
      case 'rectangle':
        return (
          <svg width={w} height={h} xmlns="http://www.w3.org/2000/svg">
            <rect
              x="5"
              y="5"
              width={w - 10}
              height={h - 10}
              fill="none"
              stroke={c}
              strokeWidth={sw}
            />
          </svg>
        );
      case 'triangle':
        return (
          <svg width={w} height={h} xmlns="http://www.w3.org/2000/svg">
            <polygon
              points={`${w / 2},5 ${w - 5},${h - 5} 5,${h - 5}`}
              fill="none"
              stroke={c}
              strokeWidth={sw}
            />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <NodeViewWrapper className="shape-node inline-block my-2">
      {renderShape()}
    </NodeViewWrapper>
  );
};

export const ShapeExtension = Node.create({
  name: 'shape',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,
  inline: false,

  addAttributes() {
    return {
      type: {
        default: 'circle',
      },
      width: {
        default: 100,
      },
      height: {
        default: 100,
      },
      color: {
        default: '#3b82f6',
      },
      strokeWidth: {
        default: 2,
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'div[data-type="shape"]',
        getAttrs: (element) => {
          if (typeof element === 'string') return false;
          const el = element as HTMLElement;
          return {
            type: el.getAttribute('data-shape-type') || 'circle',
            width: parseInt(el.getAttribute('data-width') || '100'),
            height: parseInt(el.getAttribute('data-height') || '100'),
            color: el.getAttribute('data-color') || '#3b82f6',
            strokeWidth: parseInt(el.getAttribute('data-stroke-width') || '2'),
          };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return ['div', mergeAttributes(HTMLAttributes, { 'data-type': 'shape' }), 0];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('div');
      dom.className = 'shape-node-wrapper';

      const component = new ReactRenderer(ShapeComponent, {
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
      insertShape: (options: any) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: options,
        });
      },
    };
  },
});

