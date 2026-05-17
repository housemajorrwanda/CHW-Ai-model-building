import { useState, useRef, useEffect, useCallback } from 'react';
import { VisualMathField, type VisualMathFieldHandle } from './VisualMathField';
import { Button } from '@/components/ui/button';
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
import { Input } from '@/components/ui/input';
import {
  FunctionSquare,
  AlignCenter,
  AlignLeft,
  Pencil,
  ChevronDown,
  ChevronUp,
  PenLine,
  Keyboard,
  Info,
} from 'lucide-react';
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

type TemplateVar = { key: string; label: string; placeholder?: string };
const commonFormulas: { label: string; latex: string; variables?: TemplateVar[] }[] = [
  { label: 'Quadratic Formula', latex: 'x = \\frac{-{{b}} \\pm \\sqrt{{{b}}^2 - 4{{a}}{{c}}}}{2{{a}}}', variables: [{ key: 'a', label: 'a', placeholder: '1' }, { key: 'b', label: 'b', placeholder: '-3' }, { key: 'c', label: 'c', placeholder: '2' }] },
  { label: 'Pythagorean Theorem', latex: '{{a}}^2 + {{b}}^2 = {{c}}^2', variables: [{ key: 'a', label: 'a' }, { key: 'b', label: 'b' }, { key: 'c', label: 'c' }] },
  { label: 'Area of Circle', latex: 'A = \\pi {{r}}^2', variables: [{ key: 'r', label: 'r' }] },
  { label: 'Volume of Sphere', latex: 'V = \\frac{4}{3}\\pi {{r}}^3', variables: [{ key: 'r', label: 'r' }] },
  { label: 'Euler\'s Formula', latex: 'e^{i\\pi} + 1 = 0' },
  { label: 'Derivative', latex: '\\frac{d}{dx}f(x)' },
  { label: 'Integral', latex: '\\int_{{{a}}}^{{{b}}} f(x)\\,dx', variables: [{ key: 'a', label: 'a' }, { key: 'b', label: 'b' }] },
  { label: 'Sum', latex: '\\sum_{i=1}^{{{n}}} x_i', variables: [{ key: 'n', label: 'n' }] },
  { label: 'Limit', latex: '\\lim_{x \\to \\infty} f(x)' },
  { label: 'Binomial Coefficient', latex: '\\binom{{{n}}}{{{k}}} = \\frac{{{n}}!}{{{k}}!({{n}}-{{k}})!}', variables: [{ key: 'n', label: 'n' }, { key: 'k', label: 'k' }] },
  { label: 'Matrix (2×2)', latex: '\\begin{pmatrix} {{a}} & {{b}} \\\\ {{c}} & {{d}} \\end{pmatrix}', variables: [{ key: 'a', label: 'a' }, { key: 'b', label: 'b' }, { key: 'c', label: 'c' }, { key: 'd', label: 'd' }] },
  { label: 'Newton\'s Second Law', latex: 'F = {{m}} \\cdot {{a}}', variables: [{ key: 'm', label: 'm' }, { key: 'a', label: 'a' }] },
  { label: 'Einstein Mass-Energy', latex: 'E = {{m}}c^2', variables: [{ key: 'm', label: 'm' }] },
  { label: 'Ohm\'s Law', latex: 'V = {{I}}{{R}}', variables: [{ key: 'I', label: 'I' }, { key: 'R', label: 'R' }] },
  { label: 'Determinant', latex: '\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}' },
];

/** MathLive treats `#?` as fillable holes; empty `{}` often does nothing on insert. */
const STRUCTURES: { latex: string; cursorOffset: number; label: string }[] = [
  { label: 'a/b', latex: '\\frac{#?}{#?}', cursorOffset: 6 },
  { label: 'x²', latex: '^{#?}', cursorOffset: 2 },
  { label: 'x₂', latex: '_{#?}', cursorOffset: 2 },
  { label: '√', latex: '\\sqrt{#?}', cursorOffset: 6 },
  { label: '∫', latex: '\\int_{#?}^{#?}', cursorOffset: 6 },
  { label: 'Σ', latex: '\\sum_{#?}^{#?}', cursorOffset: 7 },
  { label: '( )', latex: '\\left(#?\\right)', cursorOffset: 6 },
  { label: '2×2', latex: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}', cursorOffset: 22 },
];
const BASIC_STRUCTURES = STRUCTURES.slice(0, 4);
const MORE_STRUCTURES = STRUCTURES.slice(4);

const SYMBOLS_ROW1 = ['+', '−', '×', '÷', '=', '≠', '±', '≤', '≥', '∞', '°', '∠', '√', '∫', '∑', '∏', '∂', '∇'];
const SYMBOLS_ROW2 = ['α', 'β', 'γ', 'δ', 'ε', 'θ', 'λ', 'μ', 'π', 'σ', 'φ', 'ω', 'Δ', 'Σ', 'Ω'];
const SYMBOLS_RELATIONS = ['≡', '≈', '≅', '∝', '∈', '∉', '∪', '∩', '⊂', '⊃', '⊆', '⊇', '⊥', '∥'];
const BASIC_SYMBOLS = ['+', '−', '×', '÷', '=', '≠', '±', '≤'];
const MORE_SYMBOLS_ROW1 = SYMBOLS_ROW1.slice(BASIC_SYMBOLS.length);
const MORE_SYMBOLS_ROW2 = SYMBOLS_ROW2;
const MORE_SYMBOLS_ROW3 = SYMBOLS_RELATIONS;

/** Brackets: basic pairs + more (with separators, floor/ceiling, absolute/norm) */
const BRACKETS_BASIC: { label: string; latex: string; cursorOffset: number }[] = [
  { label: '( )', latex: '\\left(#?\\right)', cursorOffset: 6 },
  { label: '[ ]', latex: '\\left[#?\\right]', cursorOffset: 6 },
  { label: '{ }', latex: '\\left\\{#?\\right\\}', cursorOffset: 7 },
  { label: '⟨ ⟩', latex: '\\langle#?\\rangle', cursorOffset: 8 },
];
const BRACKETS_MORE: { label: string; latex: string; cursorOffset: number }[] = [
  { label: '( | )', latex: '\\left(#?\\middle|#?\\right)', cursorOffset: 6 },
  { label: '{ | }', latex: '\\left\\{#?\\middle|#?\\right\\}', cursorOffset: 7 },
  { label: '⟨ | ⟩', latex: '\\langle#?\\middle|#?\\rangle', cursorOffset: 8 },
  { label: '⟨ | | ⟩', latex: '\\langle#?\\middle|#?\\middle|#?\\rangle', cursorOffset: 8 },
  { label: '⌊ ⌋', latex: '\\lfloor#?\\rfloor', cursorOffset: 8 },
  { label: '⌈ ⌉', latex: '\\lceil#?\\rceil', cursorOffset: 8 },
  { label: '| |', latex: '\\left|#?\\right|', cursorOffset: 7 },
  { label: '‖ ‖', latex: '\\left\\|#?\\right\\|', cursorOffset: 8 },
];

/** Functions: trig, inverse, hyperbolic */
const FUNCTIONS_BASIC: { label: string; latex: string; cursorOffset: number }[] = [
  { label: 'sin', latex: '\\sin\\left(#?\\right)', cursorOffset: 6 },
  { label: 'cos', latex: '\\cos\\left(#?\\right)', cursorOffset: 6 },
  { label: 'tan', latex: '\\tan\\left(#?\\right)', cursorOffset: 6 },
];
const FUNCTIONS_MORE: { label: string; latex: string; cursorOffset: number }[] = [
  { label: 'csc', latex: '\\csc\\left(#?\\right)', cursorOffset: 6 },
  { label: 'sec', latex: '\\sec\\left(#?\\right)', cursorOffset: 6 },
  { label: 'cot', latex: '\\cot\\left(#?\\right)', cursorOffset: 6 },
  { label: 'sin⁻¹', latex: '\\arcsin\\left(#?\\right)', cursorOffset: 9 },
  { label: 'cos⁻¹', latex: '\\arccos\\left(#?\\right)', cursorOffset: 9 },
  { label: 'tan⁻¹', latex: '\\arctan\\left(#?\\right)', cursorOffset: 9 },
  { label: 'sinh', latex: '\\sinh\\left(#?\\right)', cursorOffset: 7 },
  { label: 'cosh', latex: '\\cosh\\left(#?\\right)', cursorOffset: 7 },
  { label: 'tanh', latex: '\\tanh\\left(#?\\right)', cursorOffset: 7 },
];

/** Large operators with limits */
const LARGE_OPS_BASIC: { label: string; latex: string; cursorOffset: number }[] = [
  { label: '∫', latex: '\\int_{#?}^{#?}', cursorOffset: 6 },
  { label: 'Σ', latex: '\\sum_{#?}^{#?}', cursorOffset: 7 },
  { label: 'Π', latex: '\\prod_{#?}^{#?}', cursorOffset: 8 },
];
const LARGE_OPS_MORE: { label: string; latex: string; cursorOffset: number }[] = [
  { label: '∬', latex: '\\iint_{#?}^{#?}', cursorOffset: 9 },
  { label: '∭', latex: '\\iiint_{#?}^{#?}', cursorOffset: 10 },
  { label: '∮', latex: '\\oint_{#?}^{#?}', cursorOffset: 9 },
];

const FORMULA_INPUT_MODE_KEY = 'mathgrade:formula-input-mode';

const snippetOutlineBtn =
  'h-9 rounded-lg border border-border/80 bg-background px-2.5 text-xs font-medium text-foreground shadow-sm transition-colors hover:border-primary/35 hover:bg-accent/80';
const snippetSymbolBtn =
  'h-9 w-9 shrink-0 rounded-lg border border-border/80 bg-background text-sm font-medium shadow-sm transition-colors hover:border-primary/35 hover:bg-accent/80';
const snippetMoreBtn =
  'h-9 gap-1 rounded-lg px-2.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground';

/** MathLive uses `{#?}` / `#?` for holes; map to normal empty TeX groups for the LaTeX textarea. */
function mathLiveSnippetToPlainLatex(snippet: string): string {
  return snippet.replace(/\{#\?\}/g, '{}').replace(/#\?/g, '{}');
}

function getStoredFormulaInputMode(): 'visual' | 'latex' {
  try {
    const v = localStorage.getItem(FORMULA_INPUT_MODE_KEY);
    if (v === 'latex' || v === 'visual') return v;
  } catch {
    /* private mode */
  }
  return 'visual';
}

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
  if (!latex) return <span className="text-sm text-muted-foreground">Rendered output appears here</span>;
  return <div ref={ref} className="[&_.katex]:text-base [&_.katex-display]:my-1" />;
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
  const [showMoreStructures, setShowMoreStructures] = useState(false);
  const [showMoreSymbols, setShowMoreSymbols] = useState(false);
  const [showMoreBrackets, setShowMoreBrackets] = useState(false);
  const [showMoreFunctions, setShowMoreFunctions] = useState(false);
  const [showMoreLargeOps, setShowMoreLargeOps] = useState(false);
  const [templateVars, setTemplateVars] = useState<Record<string, string>>({});
  const [formulaInputMode, setFormulaInputMode] = useState<'visual' | 'latex'>(() =>
    typeof window !== 'undefined' ? getStoredFormulaInputMode() : 'visual'
  );
  const mathFieldRef = useRef<VisualMathFieldHandle>(null);
  const latexAutocomplete = useLatexAutocomplete(latex, setLatex);

  const persistFormulaInputMode = useCallback((mode: 'visual' | 'latex') => {
    setFormulaInputMode(mode);
    try {
      localStorage.setItem(FORMULA_INPUT_MODE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, []);

  const buildLatexFromTemplate = (templateLatex: string, vars: Record<string, string>) => {
    let out = templateLatex;
    Object.entries(vars).forEach(([key, value]) => {
      out = out.replace(new RegExp(`\\{\\{${key}\\}\\}`, 'g'), value || key);
    });
    return out.replace(/\{\{[^}]+\}\}/g, ''); // remove any unfilled
  };

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

  /** Palettes: visual editor uses MathLive insert; LaTeX tab uses textarea cursor. */
  const insertSnippet = useCallback(
    (snippet: string, textareaOffset: number) => {
      if (formulaInputMode === 'visual') {
        // Ref is always an object; real Mathfield mounts async — insert() returns false until ready.
        const ok = mathFieldRef.current?.insert(snippet);
        if (ok) {
          setError('');
          return;
        }
        setLatex((prev) => `${prev}${snippet}`);
        setError('');
        return;
      }
      insertAtCursor(mathLiveSnippetToPlainLatex(snippet), textareaOffset);
    },
    [formulaInputMode, insertAtCursor]
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

  const previewPanel = (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Preview</span>
        <span className="text-[10px] text-muted-foreground tabular-nums">
          {displayMode ? 'Block' : 'Inline'}
        </span>
      </div>
      <div
        className={cn(
          'flex min-h-[56px] items-center justify-center rounded-xl border border-dashed px-3 py-3',
          'border-muted-foreground/25 bg-muted/20',
          displayMode ? 'min-h-[72px]' : 'min-h-[56px]'
        )}
      >
        {displayMode ? (
          <FormulaRenderer latex={latex} displayMode={true} />
        ) : (
          <span className="inline-flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
            <span className="shrink-0">Inline sample:</span>
            <FormulaRenderer latex={latex || 'x'} displayMode={false} />
          </span>
        )}
      </div>
    </div>
  );

  const dialogContent = (
    <DialogContent
      className={cn(
        'flex max-h-[min(90vh,880px)] w-[calc(100vw-1.25rem)] max-w-3xl flex-col gap-0 overflow-hidden p-0',
        'sm:rounded-xl sm:w-full'
      )}
    >
      <div className="shrink-0 space-y-4 border-b border-border/60 bg-muted/15 px-5 pb-4 pt-5 pr-12 dark:bg-muted/10">
        <DialogHeader className="space-y-1.5 text-left">
          <DialogTitle className="flex items-center gap-2.5 text-xl font-semibold tracking-tight">
            {isEditing ? (
              <>
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Pencil className="h-4 w-4" />
                </span>
                Edit equation
              </>
            ) : (
              <>
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <FunctionSquare className="h-4 w-4" />
                </span>
                Insert equation
              </>
            )}
          </DialogTitle>
          <DialogDescription className="text-sm leading-relaxed text-muted-foreground">
            {displayMode
              ? 'Block equations sit on their own line. Use snippets below to insert structure at the cursor.'
              : 'Inline math flows with text. Switch to Block for large formulas or integrals.'}
          </DialogDescription>
        </DialogHeader>

        <div
          role="group"
          aria-label="Equation layout"
          className="grid h-11 w-full grid-cols-2 gap-1 rounded-xl border border-border/70 bg-muted/40 p-1 dark:bg-muted/30"
        >
          <button
            type="button"
            onClick={() => setDisplayMode(false)}
            className={cn(
              'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all',
              !displayMode
                ? 'bg-background text-foreground shadow-sm ring-1 ring-border/80'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <AlignLeft className="h-4 w-4 opacity-70" />
            Inline
          </button>
          <button
            type="button"
            onClick={() => setDisplayMode(true)}
            className={cn(
              'inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all',
              displayMode
                ? 'bg-background text-foreground shadow-sm ring-1 ring-border/80'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <AlignCenter className="h-4 w-4 opacity-70" />
            Block
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4">
        <Tabs defaultValue="write" className="w-full">
          <TabsList className="mb-4 grid h-11 w-full grid-cols-2 rounded-xl border border-border/70 bg-muted/40 p-1 dark:bg-muted/30">
            <TabsTrigger
              value="write"
              className="rounded-lg text-sm font-medium data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border/60"
            >
              Write
            </TabsTrigger>
            <TabsTrigger
              value="common"
              className="rounded-lg text-sm font-medium data-[state=active]:bg-background data-[state=active]:shadow-sm data-[state=active]:ring-1 data-[state=active]:ring-border/60"
            >
              Templates
            </TabsTrigger>
          </TabsList>

          <TabsContent value="write" className="mt-0 space-y-4 focus-visible:outline-none">
            <div className="rounded-xl border border-border/60 bg-card/50 p-3 shadow-sm dark:bg-card/30">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div
                  role="group"
                  aria-label="Input mode"
                  className="inline-flex gap-1 rounded-lg border border-border/50 bg-muted/30 p-1"
                >
                  <button
                    type="button"
                    onClick={() => persistFormulaInputMode('visual')}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-all sm:text-sm',
                      formulaInputMode === 'visual'
                        ? 'bg-background text-foreground shadow-sm ring-1 ring-border/60'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <PenLine className="h-3.5 w-3.5 shrink-0" />
                    Visual
                  </button>
                  <button
                    type="button"
                    onClick={() => persistFormulaInputMode('latex')}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md px-3 py-2 text-xs font-medium transition-all sm:text-sm',
                      formulaInputMode === 'latex'
                        ? 'bg-background text-foreground shadow-sm ring-1 ring-border/60'
                        : 'text-muted-foreground hover:text-foreground'
                    )}
                  >
                    <Keyboard className="h-3.5 w-3.5 shrink-0" />
                    LaTeX
                  </button>
                </div>
                <span
                  className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground"
                  title="Visual vs LaTeX preference is saved in this browser for next time."
                >
                  <Info className="h-3.5 w-3.5 shrink-0 opacity-70" aria-hidden />
                  <span className="hidden sm:inline">Saved locally</span>
                </span>
              </div>

              {formulaInputMode === 'visual' ? (
                <div className="space-y-4">
                  <VisualMathField
                    ref={mathFieldRef}
                    value={latex}
                    onChange={(v) => {
                      setLatex(v);
                      setError('');
                    }}
                    className="w-full"
                  />
                  {previewPanel}
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="relative space-y-1.5">
                    <label htmlFor="formula-latex-input" className="text-xs font-medium text-muted-foreground">
                      LaTeX source
                    </label>
                    <Textarea
                      id="formula-latex-input"
                      ref={latexAutocomplete.ref}
                      placeholder={'e.g. x^2 + \\frac{1}{2}'}
                      value={latex}
                      onChange={handleChange}
                      onSelect={handleSelect}
                      rows={5}
                      className="resize-y font-mono text-sm placeholder:text-muted-foreground/50 min-h-[120px] border-border/80 focus-visible:ring-1"
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
                  <p className="text-[11px] text-muted-foreground">Tip: Ctrl or ⌘ + Enter inserts from this dialog.</p>
                  {previewPanel}
                </div>
              )}
            </div>

            <div className="rounded-xl border border-border/60 bg-muted/10 p-4 dark:bg-muted/5">
              <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                Snippets — insert at cursor
              </p>
              <div className="space-y-4">
                <div className="space-y-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/90">
                    Structures
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {BASIC_STRUCTURES.map((s) => (
                      <Button
                        key={s.label}
                        type="button"
                        variant="outline"
                        className={snippetOutlineBtn}
                        onClick={() => insertSnippet(s.latex, s.cursorOffset)}
                      >
                        {s.label}
                      </Button>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      className={snippetMoreBtn}
                      onClick={() => setShowMoreStructures((v) => !v)}
                    >
                      {showMoreStructures ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {showMoreStructures ? 'Less' : 'More'}
                    </Button>
                  </div>
                  {showMoreStructures && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {MORE_STRUCTURES.map((s) => (
                        <Button
                          key={s.label}
                          type="button"
                          variant="outline"
                          className={snippetOutlineBtn}
                          onClick={() => insertSnippet(s.latex, s.cursorOffset)}
                        >
                          {s.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/90">
                    Brackets
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {BRACKETS_BASIC.map((b) => (
                      <Button
                        key={b.label}
                        type="button"
                        variant="outline"
                        className={snippetOutlineBtn}
                        onClick={() => insertSnippet(b.latex, b.cursorOffset)}
                      >
                        {b.label}
                      </Button>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      className={snippetMoreBtn}
                      onClick={() => setShowMoreBrackets((v) => !v)}
                    >
                      {showMoreBrackets ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {showMoreBrackets ? 'Less' : 'More'}
                    </Button>
                  </div>
                  {showMoreBrackets && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {BRACKETS_MORE.map((b) => (
                        <Button
                          key={b.label}
                          type="button"
                          variant="outline"
                          className={snippetOutlineBtn}
                          onClick={() => insertSnippet(b.latex, b.cursorOffset)}
                        >
                          {b.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/90">
                    Functions
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {FUNCTIONS_BASIC.map((f) => (
                      <Button
                        key={f.label}
                        type="button"
                        variant="outline"
                        className={snippetOutlineBtn}
                        onClick={() => insertSnippet(f.latex, f.cursorOffset)}
                      >
                        {f.label}
                      </Button>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      className={snippetMoreBtn}
                      onClick={() => setShowMoreFunctions((v) => !v)}
                    >
                      {showMoreFunctions ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {showMoreFunctions ? 'Less' : 'More'}
                    </Button>
                  </div>
                  {showMoreFunctions && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {FUNCTIONS_MORE.map((f) => (
                        <Button
                          key={f.label}
                          type="button"
                          variant="outline"
                          className={snippetOutlineBtn}
                          onClick={() => insertSnippet(f.latex, f.cursorOffset)}
                        >
                          {f.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/90">
                    Operators
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {LARGE_OPS_BASIC.map((op) => (
                      <Button
                        key={op.label}
                        type="button"
                        variant="outline"
                        className={snippetOutlineBtn}
                        onClick={() => insertSnippet(op.latex, op.cursorOffset)}
                      >
                        {op.label}
                      </Button>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      className={snippetMoreBtn}
                      onClick={() => setShowMoreLargeOps((v) => !v)}
                    >
                      {showMoreLargeOps ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {showMoreLargeOps ? 'Less' : 'More'}
                    </Button>
                  </div>
                  {showMoreLargeOps && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {LARGE_OPS_MORE.map((op) => (
                        <Button
                          key={op.label}
                          type="button"
                          variant="outline"
                          className={snippetOutlineBtn}
                          onClick={() => insertSnippet(op.latex, op.cursorOffset)}
                        >
                          {op.label}
                        </Button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/90">
                    Symbols
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {BASIC_SYMBOLS.map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        className={snippetSymbolBtn}
                        onClick={() => insertSnippet(sym, sym.length)}
                      >
                        {sym}
                      </button>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      className={snippetMoreBtn}
                      onClick={() => setShowMoreSymbols((v) => !v)}
                    >
                      {showMoreSymbols ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                      {showMoreSymbols ? 'Less' : 'More'}
                    </Button>
                  </div>
                  {showMoreSymbols && (
                    <div className="space-y-2 pt-0.5">
                      <div className="flex flex-wrap gap-1.5">
                        {MORE_SYMBOLS_ROW1.map((sym) => (
                          <button
                            key={sym}
                            type="button"
                            className={snippetSymbolBtn}
                            onClick={() => insertSnippet(sym, sym.length)}
                          >
                            {sym}
                          </button>
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {MORE_SYMBOLS_ROW2.map((sym) => (
                          <button
                            key={sym}
                            type="button"
                            className={snippetSymbolBtn}
                            onClick={() => insertSnippet(sym, sym.length)}
                          >
                            {sym}
                          </button>
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        <span className="mr-1 self-center text-[10px] font-medium uppercase text-muted-foreground">
                          Rel.
                        </span>
                        {MORE_SYMBOLS_ROW3.map((sym) => (
                          <button
                            key={sym}
                            type="button"
                            className={snippetSymbolBtn}
                            onClick={() => insertSnippet(sym, sym.length)}
                          >
                            {sym}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
              >
                {error}
              </p>
            )}
          </TabsContent>

          <TabsContent value="common" className="mt-0 focus-visible:outline-none">
            <p className="mb-3 text-sm text-muted-foreground">
              Pick a common identity, fill any variables, then insert—or tap a row to load it into Write.
            </p>
            <div className="grid max-h-[min(52vh,420px)] grid-cols-1 gap-2 overflow-y-auto overscroll-contain pr-1">
              {commonFormulas.map((formula, idx) => (
                <div key={idx} className="space-y-1.5">
                  {formula.variables ? (
                    <div className="space-y-2 rounded-xl border border-border/60 bg-card/60 p-3 shadow-sm dark:bg-card/40">
                      <span className="text-sm font-semibold">{formula.label}</span>
                      <div className="flex flex-wrap items-center gap-2">
                        {formula.variables.map((v) => (
                          <div key={v.key} className="flex items-center gap-1">
                            <label className="text-xs text-muted-foreground">{v.label}=</label>
                            <Input
                              placeholder={v.placeholder ?? v.key}
                              className="h-9 w-20 font-mono text-sm"
                              value={templateVars[v.key] ?? ''}
                              onChange={(e) => setTemplateVars((prev) => ({ ...prev, [v.key]: e.target.value }))}
                            />
                          </div>
                        ))}
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          className="h-9 text-xs"
                          onClick={() => {
                            const built = buildLatexFromTemplate(formula.latex, templateVars);
                            if (built.trim()) {
                              handleInsert(built);
                              setTemplateVars({});
                            }
                          }}
                        >
                          Insert
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div
                      className="flex cursor-pointer items-center justify-between gap-4 rounded-xl border border-border/60 bg-card/40 p-3 shadow-sm transition-colors hover:border-primary/25 hover:bg-accent/30 dark:bg-card/25"
                      onClick={() => setLatex(formula.latex)}
                    >
                      <span className="shrink-0 text-sm font-semibold">{formula.label}</span>
                      <div className="flex min-h-[32px] flex-1 items-center justify-end overflow-hidden text-right">
                        {open && <FormulaRenderer latex={formula.latex} displayMode={false} />}
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        className="h-8 shrink-0 px-3 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleInsert(formula.latex);
                        }}
                      >
                        Insert
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {latex && (
              <div className="mt-4 rounded-xl border border-dashed border-border/80 bg-muted/20 p-4">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Live preview</p>
                <div className="flex min-h-[48px] items-center justify-center">
                  <FormulaRenderer latex={latex} displayMode={displayMode} />
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <DialogFooter className="shrink-0 gap-2 border-t border-border/60 bg-muted/10 px-5 py-4 dark:bg-muted/5">
        <Button type="button" variant="outline" onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button type="button" onClick={() => handleInsert()} disabled={!latex.trim()}>
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
