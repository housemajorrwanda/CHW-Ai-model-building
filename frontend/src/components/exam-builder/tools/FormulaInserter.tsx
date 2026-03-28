import { useState, useRef, useEffect, useCallback } from 'react';
import { VisualMathField, type VisualMathFieldHandle } from './VisualMathField';
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
import { Input } from '@/components/ui/input';
import { FunctionSquare, AlignCenter, AlignLeft, Pencil, Info, ChevronDown, ChevronUp, PenLine, Keyboard } from 'lucide-react';
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

  const dialogContent = (
    <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
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
            <p className="text-sm text-muted-foreground flex items-start gap-1.5 pt-0.5">
              <Info className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>
                Use the <strong>Visual editor</strong> (Word-style) or <strong>LaTeX</strong> tab — your choice is
                remembered on this device. Click any equation in the document to edit it later.
              </span>
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
            {/* Visual (Word-like) vs LaTeX — preference saved on this device */}
            <Tabs
              value={formulaInputMode}
              onValueChange={(v) => persistFormulaInputMode(v === 'latex' ? 'latex' : 'visual')}
              className="w-full"
            >
              <TabsList className="grid w-full grid-cols-2 h-auto p-1 gap-1">
                <TabsTrigger value="visual" className="text-xs sm:text-sm gap-2 py-2">
                  <PenLine className="h-3.5 w-3.5 shrink-0" />
                  Visual editor
                </TabsTrigger>
                <TabsTrigger value="latex" className="text-xs sm:text-sm gap-2 py-2">
                  <Keyboard className="h-3.5 w-3.5 shrink-0" />
                  LaTeX (advanced)
                </TabsTrigger>
              </TabsList>
              <TabsContent value="visual" className="mt-3 space-y-3">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Build equations like in Microsoft Word: tap the box below, use the on-screen keyboard, or use the
                  structure buttons under this section. No LaTeX knowledge needed. Pasting <strong>LaTeX</strong>{' '}
                  (with backslashes, e.g. <code className="text-xs">\frac</code>) is detected and kept; rich text from
                  Word or the web is usually plain characters only — use the LaTeX tab or type here for full control.
                </p>
                <VisualMathField
                  ref={mathFieldRef}
                  value={latex}
                  onChange={(v) => {
                    setLatex(v);
                    setError('');
                  }}
                  className="w-full"
                />
                <div className="space-y-1.5">
                  <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    How it appears in the exam (KaTeX)
                  </span>
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
              </TabsContent>
              <TabsContent value="latex" className="mt-3">
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Type LaTeX commands directly. Use the buttons below to insert snippets, or switch back to the visual
                  editor anytime.
                </p>
              </TabsContent>
            </Tabs>

            <div className="space-y-3 pt-1 border-t">
            <p className="text-xs text-muted-foreground">
              Structures &amp; symbols — tap to insert into the{' '}
              {formulaInputMode === 'visual'
                ? 'visual editor (top).'
                : 'LaTeX box (below), at your cursor.'}
            </p>

            {/* Structures first (basic + … more) */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Structures</span>
              <div className="flex flex-wrap gap-1 items-center">
                {BASIC_STRUCTURES.map((s) => (
                  <Button
                    key={s.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                    onClick={() => insertSnippet(s.latex, s.cursorOffset)}
                  >
                    {s.label}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground"
                  onClick={() => setShowMoreStructures((v) => !v)}
                >
                  {showMoreStructures ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  {showMoreStructures ? 'Less' : 'More'}
                </Button>
              </div>
              {showMoreStructures && (
                <div className="flex flex-wrap gap-1">
                  {MORE_STRUCTURES.map((s) => (
                    <Button
                      key={s.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                      onClick={() => insertSnippet(s.latex, s.cursorOffset)}
                    >
                      {s.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Brackets (basic + … more) */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Brackets</span>
              <div className="flex flex-wrap gap-1 items-center">
                {BRACKETS_BASIC.map((b) => (
                  <Button
                    key={b.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                    onClick={() => insertSnippet(b.latex, b.cursorOffset)}
                  >
                    {b.label}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground"
                  onClick={() => setShowMoreBrackets((v) => !v)}
                >
                  {showMoreBrackets ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  {showMoreBrackets ? 'Less' : 'More'}
                </Button>
              </div>
              {showMoreBrackets && (
                <div className="flex flex-wrap gap-1">
                  {BRACKETS_MORE.map((b) => (
                    <Button
                      key={b.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                      onClick={() => insertSnippet(b.latex, b.cursorOffset)}
                    >
                      {b.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Functions (basic + … more) */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Functions</span>
              <div className="flex flex-wrap gap-1 items-center">
                {FUNCTIONS_BASIC.map((f) => (
                  <Button
                    key={f.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                    onClick={() => insertSnippet(f.latex, f.cursorOffset)}
                  >
                    {f.label}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground"
                  onClick={() => setShowMoreFunctions((v) => !v)}
                >
                  {showMoreFunctions ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  {showMoreFunctions ? 'Less' : 'More'}
                </Button>
              </div>
              {showMoreFunctions && (
                <div className="flex flex-wrap gap-1">
                  {FUNCTIONS_MORE.map((f) => (
                    <Button
                      key={f.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                      onClick={() => insertSnippet(f.latex, f.cursorOffset)}
                    >
                      {f.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Large operators (basic + … more) */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Large operators</span>
              <div className="flex flex-wrap gap-1 items-center">
                {LARGE_OPS_BASIC.map((op) => (
                  <Button
                    key={op.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                    onClick={() => insertSnippet(op.latex, op.cursorOffset)}
                  >
                    {op.label}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground"
                  onClick={() => setShowMoreLargeOps((v) => !v)}
                >
                  {showMoreLargeOps ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  {showMoreLargeOps ? 'Less' : 'More'}
                </Button>
              </div>
              {showMoreLargeOps && (
                <div className="flex flex-wrap gap-1">
                  {LARGE_OPS_MORE.map((op) => (
                    <Button
                      key={op.label}
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground border-muted-foreground/25"
                      onClick={() => insertSnippet(op.latex, op.cursorOffset)}
                    >
                      {op.label}
                    </Button>
                  ))}
                </div>
              )}
            </div>

            {/* Symbols (basic + … more) */}
            <div className="space-y-1.5">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Symbols</span>
              <div className="flex flex-wrap gap-1 items-center">
                {BASIC_SYMBOLS.map((sym) => (
                  <button
                    key={sym}
                    type="button"
                    className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
                    onClick={() => insertSnippet(sym, sym.length)}
                  >
                    {sym}
                  </button>
                ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground"
                  onClick={() => setShowMoreSymbols((v) => !v)}
                >
                  {showMoreSymbols ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  {showMoreSymbols ? 'Less' : 'More'}
                </Button>
              </div>
              {showMoreSymbols && (
                <div className="space-y-1">
                  <div className="flex flex-wrap gap-1">
                    {MORE_SYMBOLS_ROW1.map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
                        onClick={() => insertSnippet(sym, sym.length)}
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {MORE_SYMBOLS_ROW2.map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
                        onClick={() => insertSnippet(sym, sym.length)}
                      >
                        {sym}
                      </button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <span className="text-xs text-muted-foreground self-center mr-1">Relations:</span>
                    {MORE_SYMBOLS_ROW3.map((sym) => (
                      <button
                        key={sym}
                        type="button"
                        className="h-8 w-8 rounded border border-muted-foreground/20 bg-muted/30 hover:bg-muted/60 text-sm font-medium transition-colors"
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

            {formulaInputMode === 'latex' && (
              <>
                {/* LaTeX input */}
                <div className="relative space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">LaTeX</label>
                  <Textarea
                    ref={latexAutocomplete.ref}
                    placeholder="Type equation here (e.g. x^2 + \\frac{1}{2})"
                    value={latex}
                    onChange={handleChange}
                    onSelect={handleSelect}
                    rows={4}
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

                {/* Live preview */}
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
              </>
            )}

            {error && (
              <p className="text-sm text-destructive bg-destructive/10 px-2 py-1 rounded">{error}</p>
            )}
          </TabsContent>

          <TabsContent value="common" className="mt-3">
            <div className="grid grid-cols-1 gap-1.5 max-h-[320px] overflow-y-auto pr-1">
              {commonFormulas.map((formula, idx) => (
                <div key={idx} className="space-y-1.5">
                  {formula.variables ? (
                    <div className="p-2.5 rounded-md border border-muted-foreground/15 bg-muted/20 space-y-2">
                      <span className="text-sm font-medium">{formula.label}</span>
                      <div className="flex flex-wrap gap-2 items-center">
                        {formula.variables.map((v) => (
                          <div key={v.key} className="flex items-center gap-1">
                            <label className="text-xs text-muted-foreground">{v.label}=</label>
                            <Input
                              placeholder={v.placeholder ?? v.key}
                              className="h-8 w-20 text-sm font-mono"
                              value={templateVars[v.key] ?? ''}
                              onChange={(e) => setTemplateVars((prev) => ({ ...prev, [v.key]: e.target.value }))}
                            />
                          </div>
                        ))}
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-8 text-xs"
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
                  )}
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
