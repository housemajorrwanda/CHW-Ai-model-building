import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { FunctionSquare } from 'lucide-react';

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
  { label: 'Integral', latex: '\\int_{a}^{b} f(x) dx' },
  { label: 'Sum', latex: '\\sum_{i=1}^{n} x_i' },
  { label: 'Limit', latex: '\\lim_{x \\to \\infty} f(x)' },
  { label: 'Binomial', latex: '\\binom{n}{k} = \\frac{n!}{k!(n-k)!}' },
];

function FormulaRenderer({ latex, displayMode }: { latex: string; displayMode: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const [katexLib, setKatexLib] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Dynamically import katex only when component mounts
    import('katex').then((module) => {
      setKatexLib(module.default);
      import('katex/dist/katex.min.css').catch(() => {});
      setLoading(false);
    }).catch((e) => {
      console.warn('KaTeX failed to load:', e);
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
    
    // Clear previous content
    if (ref.current) {
      ref.current.innerHTML = '';
    }
    
    try {
      katexLib.render(latex, ref.current, {
        throwOnError: false,
        displayMode: displayMode,
        errorColor: '#cc0000',
      });
    } catch (e: any) {
      if (ref.current) {
        ref.current.textContent = '[Invalid formula]';
        ref.current.style.color = '#cc0000';
      }
    }
  }, [latex, displayMode, katexLib, loading]);

  if (!latex) {
    return <div className="text-muted-foreground italic text-sm">[No formula]</div>;
  }

  if (loading) {
    return <div className="text-muted-foreground text-sm">Loading...</div>;
  }

  if (!katexLib) {
    return <div className="text-muted-foreground text-sm">KaTeX unavailable</div>;
  }

  return <div ref={ref} />;
}

export function FormulaInserter({ onInsert }: FormulaInserterProps) {
  const [open, setOpen] = useState(false);
  const [latex, setLatex] = useState('');
  const [displayMode, setDisplayMode] = useState(true);
  const [error, setError] = useState('');

  const handleInsert = () => {
    if (!latex.trim()) {
      setError('Please enter a formula');
      return;
    }

    try {
      onInsert(latex.trim(), displayMode);
      setLatex('');
      setError('');
      setOpen(false);
    } catch (e) {
      setError('Invalid LaTeX syntax. Please check your formula.');
    }
  };

  const handleFormulaSelect = (formulaLatex: string) => {
    setLatex(formulaLatex);
    setError('');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" type="button">
          <FunctionSquare className="h-4 w-4 mr-2" />
          Formula
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Insert Mathematical Formula</DialogTitle>
          <DialogDescription>
            Enter LaTeX syntax or select from common formulas.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="custom" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="custom">Custom Formula</TabsTrigger>
            <TabsTrigger value="common">Common Formulas</TabsTrigger>
          </TabsList>

          <TabsContent value="custom" className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="latex-input">LaTeX Formula</Label>
              <Textarea
                id="latex-input"
                placeholder="e.g., x^2 + y^2 = r^2 or \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}"
                value={latex}
                onChange={(e) => {
                  setLatex(e.target.value);
                  setError('');
                }}
                rows={4}
                className="font-mono text-sm"
              />
              <p className="text-xs text-muted-foreground">
                Examples: x^2, \\frac&#123;a&#125;&#123;b&#125;, \\sqrt&#123;x&#125;
              </p>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="display-mode"
                checked={displayMode}
                onChange={(e) => setDisplayMode(e.target.checked)}
                className="rounded"
              />
              <Label htmlFor="display-mode" className="cursor-pointer">
                Display mode (centered, larger)
              </Label>
            </div>

            {latex && open && (
              <div className="p-4 border rounded-lg bg-muted/50">
                <Label className="text-xs text-muted-foreground mb-2 block">Preview:</Label>
                <div className="min-h-[60px] flex items-center justify-center">
                  <FormulaRenderer latex={latex} displayMode={displayMode} />
                </div>
              </div>
            )}

            {error && (
              <div className="text-sm text-destructive bg-destructive/10 p-2 rounded">
                {error}
              </div>
            )}
          </TabsContent>

          <TabsContent value="common" className="space-y-4">
            <div className="grid grid-cols-1 gap-2 max-h-[300px] overflow-y-auto">
              {commonFormulas.map((formula, idx) => (
                <div
                  key={idx}
                  className="p-3 border rounded-lg hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => handleFormulaSelect(formula.latex)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-sm font-medium">{formula.label}</span>
                    <div className="flex-1 min-w-0 overflow-hidden">
                      {open && <FormulaRenderer latex={formula.latex} displayMode={true} />}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {latex && open && (
              <div className="p-4 border rounded-lg bg-muted/50">
                <Label className="text-xs text-muted-foreground mb-2 block">Selected Formula Preview:</Label>
                <div className="min-h-[60px] flex items-center justify-center">
                  <FormulaRenderer latex={latex} displayMode={true} />
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleInsert} disabled={!latex.trim()}>
            Insert Formula
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
