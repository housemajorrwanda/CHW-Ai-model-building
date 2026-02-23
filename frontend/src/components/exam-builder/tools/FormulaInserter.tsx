import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { FunctionSquare, AlignCenter, AlignLeft } from 'lucide-react';

interface FormulaInserterProps {
  onInsert: (latex: string, displayMode: boolean) => void;
}

const commonFormulas = [
  { label: 'Quadratic Formula', latex: 'x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}' },
  { label: 'Pythagorean Theorem', latex: 'a^2 + b^2 = c^2' },
  { label: 'Area of Circle', latex: 'A = \\pi r^2' },
  { label: 'Volume of Sphere', latex: 'V = \\frac{4}{3}\\pi r^3' },
  { label: 'Euler\'s Formula', latex: 'e^{i\\pi} + 1 = 0' },
  { label: 'Derivative', latex: '\\frac{d}{dx}f(x)' },
  { label: 'Integral', latex: '\\int_{a}^{b} f(x)\\,dx' },
  { label: 'Sum', latex: '\\sum_{i=1}^{n} x_i' },
  { label: 'Limit', latex: '\\lim_{x \\to \\infty} f(x)' },
  { label: 'Binomial Coefficient', latex: '\\binom{n}{k} = \\frac{n!}{k!(n-k)!}' },
  { label: 'Matrix (2×2)', latex: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}' },
  { label: 'Determinant', latex: '\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}' },
  { label: 'Newton\'s Second Law', latex: 'F = ma' },
  { label: 'Einstein Mass-Energy', latex: 'E = mc^2' },
  { label: 'Ohm\'s Law', latex: 'V = IR' },
];

function FormulaRenderer({ latex, displayMode }: { latex: string; displayMode: boolean }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || !latex) {
      if (ref.current) ref.current.innerHTML = '';
      return;
    }
    import('katex').then((m) => {
      try {
        m.default.render(latex, ref.current!, {
          throwOnError: false,
          displayMode,
          errorColor: '#cc0000',
        });
      } catch {
        if (ref.current) ref.current.textContent = '[Invalid formula]';
      }
    });
  }, [latex, displayMode]);

  if (!latex) return <span className="text-muted-foreground italic text-sm">Preview appears here</span>;
  return <div ref={ref} />;
}

export function FormulaInserter({ onInsert }: FormulaInserterProps) {
  const [open, setOpen] = useState(false);
  const [latex, setLatex] = useState('');
  const [displayMode, setDisplayMode] = useState(true);
  const [error, setError] = useState('');

  const handleInsert = (formulaLatex?: string) => {
    const toInsert = (formulaLatex ?? latex).trim();
    if (!toInsert) {
      setError('Please enter a formula');
      return;
    }
    onInsert(toInsert, displayMode);
    setLatex('');
    setError('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 px-2" type="button">
          <FunctionSquare className="h-4 w-4 mr-1" />
          Formula
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Insert Mathematical Formula</DialogTitle>
        </DialogHeader>

        {/* Inline vs Block toggle — the key UX */}
        <div className="flex gap-2 p-1 bg-muted rounded-lg w-fit">
          <button
            onClick={() => setDisplayMode(false)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              !displayMode
                ? 'bg-background shadow text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <AlignLeft className="h-4 w-4" />
            Inline
            <Badge variant="outline" className="font-mono text-[10px] px-1">$…$</Badge>
          </button>
          <button
            onClick={() => setDisplayMode(true)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              displayMode
                ? 'bg-background shadow text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            <AlignCenter className="h-4 w-4" />
            Block (centered)
            <Badge variant="outline" className="font-mono text-[10px] px-1">$$…$$</Badge>
          </button>
        </div>

        <Tabs defaultValue="custom" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="custom">Custom</TabsTrigger>
            <TabsTrigger value="common">Common Formulas</TabsTrigger>
          </TabsList>

          {/* Custom tab */}
          <TabsContent value="custom" className="space-y-3 mt-3">
            <div className="space-y-1.5">
              <Label htmlFor="latex-input" className="text-sm">LaTeX</Label>
              <Textarea
                id="latex-input"
                placeholder={displayMode
                  ? 'e.g.  \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}'
                  : 'e.g.  x^2 + y^2  or  \\frac{a}{b}'}
                value={latex}
                onChange={(e) => { setLatex(e.target.value); setError(''); }}
                rows={3}
                className="font-mono text-sm"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleInsert();
                }}
              />
              <p className="text-xs text-muted-foreground">
                Tip: you can also type <span className="font-mono bg-muted px-1 rounded">$formula$</span> or <span className="font-mono bg-muted px-1 rounded">$$formula$$</span> directly in the editor and press <kbd className="px-1 border rounded text-[10px]">Space</kbd> or <kbd className="px-1 border rounded text-[10px]">Enter</kbd> to render.
              </p>
            </div>

            {/* Live preview */}
            <div className="p-4 border rounded-lg bg-muted/40 min-h-[70px] flex items-center justify-center">
              {displayMode ? (
                <FormulaRenderer latex={latex} displayMode={true} />
              ) : (
                <span className="text-sm">
                  The number <FormulaRenderer latex={latex || 'x'} displayMode={false} /> in a sentence.
                </span>
              )}
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 p-2 rounded">{error}</p>
            )}
          </TabsContent>

          {/* Common formulas tab */}
          <TabsContent value="common" className="mt-3">
            <div className="grid grid-cols-1 gap-1.5 max-h-[320px] overflow-y-auto pr-1">
              {commonFormulas.map((formula, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between gap-4 p-3 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => { setLatex(formula.latex); setError(''); }}
                >
                  <span className="text-sm font-medium shrink-0">{formula.label}</span>
                  <div className="flex-1 overflow-hidden text-right">
                    {open && <FormulaRenderer latex={formula.latex} displayMode={false} />}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-7 px-3 text-xs shrink-0"
                    onClick={(e) => { e.stopPropagation(); handleInsert(formula.latex); }}
                  >
                    Insert
                  </Button>
                </div>
              ))}
            </div>
            {latex && (
              <div className="mt-3 p-3 border rounded-lg bg-muted/40">
                <p className="text-xs text-muted-foreground mb-2">Selected:</p>
                <div className="flex items-center justify-center min-h-[50px]">
                  <FormulaRenderer latex={latex} displayMode={displayMode} />
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={() => handleInsert()} disabled={!latex.trim()}>
            Insert {displayMode ? 'Block' : 'Inline'} Formula
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
