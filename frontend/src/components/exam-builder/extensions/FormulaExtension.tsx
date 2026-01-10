import { Node, mergeAttributes } from '@tiptap/core';
import { ReactRenderer } from '@tiptap/react';
import { NodeViewWrapper } from '@tiptap/react';
import React, { useEffect, useRef, useState } from 'react';

const FormulaComponent = ({ node }: { node: any }) => {
  const { latex, display } = node.attrs;
  const ref = useRef<HTMLDivElement>(null);
  const [katexLib, setKatexLib] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Dynamically import katex
    import('katex').then((module) => {
      setKatexLib(module.default);
      import('katex/dist/katex.min.css').catch(() => {});
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!ref.current || !latex || !katexLib || loading) {
      if (ref.current && !loading) {
        ref.current.innerHTML = '';
      }
      return;
    }
    
    try {
      katexLib.render(latex, ref.current, {
        throwOnError: false,
        displayMode: display,
      });
    } catch (e) {
      if (ref.current) {
        ref.current.textContent = '[Invalid formula]';
      }
    }
  }, [latex, display, katexLib, loading]);

  if (!latex) {
    return (
      <NodeViewWrapper className="formula-node-wrapper">
        <span className="text-muted-foreground italic">[Formula]</span>
      </NodeViewWrapper>
    );
  }

  return (
    <NodeViewWrapper className="formula-node-wrapper" style={{ display: display ? 'block' : 'inline' }}>
      {display ? (
        <div style={{ textAlign: 'center', margin: '1em 0' }}>
          <div ref={ref} />
        </div>
      ) : (
        <span ref={ref} />
      )}
    </NodeViewWrapper>
  );
};

export const FormulaExtension = Node.create({
  name: 'formula',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,
  inline: false,

  addAttributes() {
    return {
      latex: {
        default: '',
      },
      display: {
        default: true,
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-type="formula"]',
        getAttrs: (element) => {
          if (typeof element === 'string') return false;
          const el = element as HTMLElement;
          return {
            latex: el.getAttribute('data-latex') || '',
            display: el.getAttribute('data-display') === 'true',
          };
        },
      },
      {
        tag: 'span.katex-formula',
        getAttrs: (element) => {
          if (typeof element === 'string') return false;
          const el = element as HTMLElement;
          return {
            latex: el.getAttribute('data-latex') || '',
            display: el.getAttribute('data-display') === 'true',
          };
        },
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-type': 'formula',
        'data-latex': HTMLAttributes.latex || '',
        'data-display': HTMLAttributes.display ? 'true' : 'false',
      }),
      0,
    ];
  },

  addNodeView() {
    return ({ node, editor }) => {
      const dom = document.createElement('span');
      dom.className = 'formula-node-wrapper';

      const component = new ReactRenderer(FormulaComponent, {
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
      insertFormula: (options: { latex: string; display?: boolean }) => ({ commands }) => {
        return commands.insertContent({
          type: this.name,
          attrs: {
            latex: options.latex,
            display: options.display !== false,
          },
        });
      },
    };
  },
});

