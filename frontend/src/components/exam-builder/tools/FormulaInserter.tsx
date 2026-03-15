import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
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
import { FunctionSquare, AlignCenter, AlignLeft, Pencil, Info } from 'lucide-react';
import { useLatexAutocomplete, LatexCompletionsList } from '@/components/ui/latex-autocomplete';
import { cn } from '@/lib/utils';

interface FormulaInserterProps {
  onInsert: (latex: string, displayMode: boolean) => void;
  compact?: boolean;
  /** Controlled open for edit mode: when opening to edit an equation, set open=true and initialLatex/initialDisplayMode */
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  initialLatex?: string;
  initialDisplayMode?: boolean;
  /** When set, dialog acts as editor: prefill from initialLatex and call onUpdate on submit instead of onInsert */
  onUpdate?: (latex: string, displayMode: boolean) => void;
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

const STRUCTURES: { latex: string; cursorOffset: number; label: string }[] = [
  { label: 'a/b', latex: '\\frac{}{}', cursorOffset: 6 },
  { label: 'x²', latex: '^{}', cursorOffset: 2 },
  { label: 'x₂', latex: '_{}', cursorOffset: 2 },
  { label: '√', latex: '\\sqrt{}', cursorOffset: 6 },
  { label: '∫', latex: '\\int_{}^{}', cursorOffset: 6 },
  { label: 'Σ', latex: '\\sum_{i=1}^{n}', cursorOffset: 10 },
  { label: '( )', latex: '\\left( \\right)', cursorOffset: 7 },
  { label: '2×2', latex: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}', cursorOffset: 22 },
];

const SYMBOLS_ROW1 = ['+', '−', '×', '÷', '=', '≠', '±', '≤', '≥', '∞', '°', '∠', '√', '∫', '∑', '∏', '∂', '∇'];
const SYMBOLS_ROW2 = ['α', 'β', 'γ', 'δ', 'ε', 'θ', 'λ', 'μ', 'π', 'σ', 'φ', 'ω', 'Δ', 'Σ', 'Ω'];

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
  if (!latex) return <span className="text-muted-foreground/80 text-sm">Preview</span>;
  return <div ref={ref} />;
}

export function FormulaInserter({
  onInsert,
  compact = false,
  open: controlledOpen,
  onOpenChange: controlledOnOpenChange,
  initialLatex,
  initialDisplayMode,
  onUpdate,
}: FormulaInserterProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = controlledOnOpenChange ?? setInternalOpen;

  const [latex, setLatex] = useState('');
  const [displayMode, setDisplayMode] = useState(true);
  const [error, setError] = useState('');
  const [cursorStart, setCursorStart] = useState(0);
  const [cursorEnd, setCursorEnd] = useState(0);
  const latexAutocomplete = useLatexAutocomplete(latex, setLatex);

  // When opening in edit mode, prefill from initialLatex / initialDisplayMode
  useEffect(() => {
    if (open && initialLatex !== undefined) {
      setLatex(initialLatex);
      setDisplayMode(initialDisplayMode ?? true);
      setError('');
    }
  }, [open, initialLatex, initialDisplayMode]);

  const insertAtCursor = useCallback(
    (insert: string, offset: number) => {
      const before = latex.slice(0, cursorStart);
      const after = latex.slice(cursorEnd);
      const newVal = before + insert + after;
      setLatex(newVal);
      setError('');
      const newPos = before.length + offset;
      setCursorStart(newPos);
      setCursorEnd(newPos);
      requestAnimationFrame(() => {
        const el = latexAutocomplete.ref.current;
        if (el) {
          el.focus();
          el.setSelectionRange(newPos, newPos);
        }
      });
    },
    [latex, cursorStart, cursorEnd, latexAutocomplete.ref]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      latexAutocomplete.onChange(e);
      setCursorStart(e.target.selectionStart);
      setCursorEnd(e.target.selectionEnd);
    },
    [latexAutocomplete]
  );

  const handleSelect = useCallback(() => {
    const el = latexAutocomplete.ref.current;
    if (el) {
      setCursorStart(el.selectionStart);
      setCursorEnd(el.selectionEnd);
    }
  }, []);

  const handleInsert = (formulaLatex?: string) => {
    const toInsert = (formulaLatex ?? latex).trim();
    if (!toInsert) {
      setError('Enter a formula');
      return;
    }
    if (onUpdate) {
      onUpdate(toInsert, displayMode);
    } else {
      onInsert(toInsert, displayMode);
    }
    setLatex('');
    setError('');
    setOpen(false);
  };

  const editOnly = controlledOpen !== undefined && onUpdate;
  const isEditing = Boolean(onUpdate && open && initialLatex !== undefined);

  const dialogContent = (
    <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader className="space-y-1">
          <DialogTitle className="text-lg flex items-center gap-2">
            {isEditing ? (
              <>
                <Pencil className="h-5 w-5 text-primary" />
                Edit equation
              </>
            ) : (
              <>
                <FunctionSquare className="h-5 w-5 text-primary" />
                Insert equation
              </>
            )}
          </DialogTitle>
          {!editOnly && (
            <p className="text-sm text-muted-foreground flex items-center gap-1.5 pt-0.5">
              <Info className="h-3.5 w-3.5 shrink-0" />
              Click any equation in the document to edit it later.
            </p>
          )}
        </DialogHeader>

        <div className="flex gap-2 p-1 bg-muted/50 rounded-lg w-fit">
          <button
            type="button"
            onClick={() => setDisplayMode(false)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors',
              !displayMode ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <AlignLeft className="h-3.5 w-3.5" />
            Inline
          </button>
          <button
            type="button"
            onClick={() => setDisplayMode(true)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded text-sm font-medium transition-colors',
              displayMode ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <AlignCenter className="h-3.5 w-3.5" />
            Block
          </button>
        </div>

        <Tabs defaultValue="write" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="write" className="text-sm">Write</TabsTrigger>
            <TabsTrigger value="common" className="text-sm">Templates</TabsTrigger>
          </TabsList>

          <TabsContent value="write" className="mt-3 space-y-3">
            <div className="relative space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">LaTeX</label>
              <Textarea
                ref={latexAutocomplete.ref}
                placeholder="Type equation here (e.g. x^2 + \\frac{1}{2})"
                value={latex}
                onChange={handleChange}
                onSelect={handleSelect}
                rows={3}
                className="font-mono text-sm resize-none placeholder:text-muted-foreground/70 border-muted-foreground/20 focus-visible:ring-1"
                onKeyDown={(e) => {
                  latexAutocomplete.onKeyDown(e);
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleInsert();
                }}
              />
              {latexAutocomplete.showList && (
                <LatexCompletionsList
                  completions={latexAutocomplete.completions}
                  selectedIndex={latexAutocomplete.selectedIndex}
                  onSelect={(snippet) => latexAutocomplete.apply(snippet)}
                />
              )}
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Structures</span>
              <div className="flex flex-wrap gap-1">
              {STRUCTURES.map((s) => (
                <Button
                  key={s.label}
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                  onClick={() => insertAtCursor(s.latex, s.cursorOffset)}
                >
                  {s.label}
                </Button>
              ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Symbols</span>
              <div className="flex flex-wrap gap-1">
                {SYMBOLS_ROW1.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
                    onClick={() => insertAtCursor(sym, sym.length)}
                  >
                    {sym}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap gap-1">
                {SYMBOLS_ROW2.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
                    onClick={() => insertAtCursor(sym, sym.length)}
                  >
                    {sym}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Live preview</span>
              <div className="min-h-[56px] py-3 px-4 rounded-lg border-2 border-dashed border-muted-foreground/20 bg-muted/30 flex items-center justify-center">
                {displayMode ? (
                  <FormulaRenderer latex={latex} displayMode={true} />
                ) : (
                  <span className="text-sm text-muted-foreground">
                    Sample: <FormulaRenderer latex={latex || 'x'} displayMode={false} />
                  </span>
                )}
              </div>
            </div>

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 px-2 py-1 rounded">{error}</p>
            )}
          </TabsContent>

          <TabsContent value="common" className="mt-3">
            <div className="grid grid-cols-1 gap-1.5 max-h-[320px] overflow-y-auto pr-1">
              {commonFormulas.map((formula, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between gap-4 p-2.5 rounded-md border border-muted-foreground/15 hover:bg-muted/40 cursor-pointer transition-colors"
                  onClick={() => setLatex(formula.latex)}
                >
                  <span className="text-sm font-medium shrink-0">{formula.label}</span>
                  <div className="flex-1 overflow-hidden text-right min-h-[28px] flex items-center justify-end">
                    {open && <FormulaRenderer latex={formula.latex} displayMode={false} />}
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    className="h-7 px-2.5 text-xs shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleInsert(formula.latex);
                    }}
                  >
                    Insert
                  </Button>
                </div>
              ))}
            </div>
            {latex && (
              <div className="mt-3 p-2.5 rounded-md border border-muted-foreground/15 bg-muted/20 min-h-[44px] flex items-center justify-center">
                <FormulaRenderer latex={latex} displayMode={displayMode} />
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter className="gap-2 pt-3 border-t">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={() => handleInsert()} disabled={!latex.trim()}>
            {onUpdate ? 'Update equation' : 'Insert equation'}
          </Button>
        </DialogFooter>
      </DialogContent>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {!editOnly && (
        <DialogTrigger asChild>
          {compact ? (
            <button
              type="button"
              title="Insert Formula"
              className="inline-flex items-center justify-center h-7 w-7 rounded text-sm transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              <FunctionSquare className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              type="button"
              title="Insert Formula"
              className="inline-flex items-center gap-1 h-8 px-2 rounded text-xs font-medium hover:bg-accent transition-colors"
            >
              <FunctionSquare className="h-4 w-4" /> Formula
            </button>
          )}
        </DialogTrigger>
      )}
      {dialogContent}
    </Dialog>
  );
}
