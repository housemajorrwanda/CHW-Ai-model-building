import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Plus, X, GripVertical, CheckCircle2, ChevronDown, ChevronUp, Calculator, Atom, Ruler, Pi } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ScientificKeyboard from '../exam-taker/ScientificKeyboard';
import { CalculatorWidget } from './tools/CalculatorWidget';
import { PeriodicTableSelector } from './tools/PeriodicTableSelector';
import { UnitConverter } from './tools/UnitConverter';
import { ConstantsLibrary } from './tools/ConstantsLibrary';
import { FormulaInserter } from './tools/FormulaInserter';
import { MathText } from '@/components/ui/MathText';
import { useLatexAutocomplete, LatexCompletionsList } from '@/components/ui/latex-autocomplete';
import type { GoldStep } from './QuestionBuilder';
import { toast } from 'sonner';

interface GoldSolutionEditorProps {
  steps: GoldStep[];
  finalAnswer: string;
  finalAnswerLatex: string;
  onUpdate: (updates: {
    goldSolutionSteps?: GoldStep[];
    finalAnswer?: string;
    finalAnswerLatex?: string;
  }) => void;
}

type FieldKey = 'description' | 'expression' | 'latex' | 'finalAnswer' | 'finalAnswerLatex';

export function GoldSolutionEditor({ steps, finalAnswer, finalAnswerLatex, onUpdate }: GoldSolutionEditorProps) {
  const [showForm, setShowForm] = useState(false);
  const [showTools, setShowTools] = useState(false);
  const [activeField, setActiveField] = useState<FieldKey>('expression');

  const [newStep, setNewStep] = useState<Partial<GoldStep>>({
    stepNumber: steps.length + 1,
    description: '',
    expression: '',
    latex: '',
    points: 5,
    required: true,
  });

  // Refs for each input so we can insert at cursor
  const inputRefs = useRef<Partial<Record<FieldKey, HTMLInputElement | null>>>({});
  const latexAcNewStep = useLatexAutocomplete(newStep.latex ?? '', (v) => setNewStep((s) => ({ ...s, latex: v })));
  const latexAcFinal = useLatexAutocomplete(finalAnswerLatex, (v) => onUpdate({ finalAnswerLatex: v }));

  /** Insert text at cursor position of the active field */
  const insertAtCursor = (symbol: string) => {
    const el = inputRefs.current[activeField];
    if (!el) return;

    const start = el.selectionStart ?? el.value.length;
    const end = el.selectionEnd ?? el.value.length;
    const before = el.value.slice(0, start);
    const after = el.value.slice(end);
    const newVal = before + symbol + after;

    // Update state
    if (activeField === 'finalAnswer') {
      onUpdate({ finalAnswer: newVal });
    } else if (activeField === 'finalAnswerLatex') {
      onUpdate({ finalAnswerLatex: newVal });
    } else {
      setNewStep((s) => ({ ...s, [activeField]: newVal }));
    }

    // Restore focus and cursor position after React re-render
    requestAnimationFrame(() => {
      el.focus();
      const pos = start + symbol.length;
      el.setSelectionRange(pos, pos);
    });
  };

  const handleAddStep = () => {
    if (!newStep.expression) {
      toast.error('Expression is required');
      return;
    }
    const step: GoldStep = {
      stepNumber: steps.length + 1,
      description: newStep.description || '',
      expression: newStep.expression || '',
      latex: newStep.latex || '',
      points: newStep.points || 5,
      required: newStep.required !== false,
    };
    onUpdate({ goldSolutionSteps: [...steps, step] });
    setNewStep({ stepNumber: steps.length + 2, description: '', expression: '', latex: '', points: 5, required: true });
    setShowForm(false);
    setShowTools(false);
    toast.success('Step added');
  };

  const removeStep = (stepNumber: number) => {
    const updatedSteps = steps
      .filter((s) => s.stepNumber !== stepNumber)
      .map((s, idx) => ({ ...s, stepNumber: idx + 1 }));
    onUpdate({ goldSolutionSteps: updatedSteps });
  };

  const updateStep = (stepNumber: number, updates: Partial<GoldStep>) => {
    onUpdate({ goldSolutionSteps: steps.map((s) => (s.stepNumber === stepNumber ? { ...s, ...updates } : s)) });
  };

  /** Shared ref callback */
  const setRef = (field: FieldKey) => (el: HTMLInputElement | null) => {
    inputRefs.current[field] = el;
  };

  /** Insert a formula (LaTeX) into the active field */
  const handleFormulaInsert = (latex: string, displayMode: boolean) => {
    const wrapped = displayMode ? `$$${latex}$$` : `$${latex}$`;
    insertAtCursor(wrapped);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Gold Solution Steps
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { setShowForm(!showForm); if (!showForm) setShowTools(false); }}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Step
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Add Step Form */}
        {showForm && (
          <div className="border rounded-lg bg-muted/20 space-y-3 overflow-hidden">
            {/* Fields */}
            <div className="p-4 space-y-3">
              <div className="grid grid-cols-4 gap-3">
                <div className="col-span-3">
                  <Label className="text-xs">Description</Label>
                  <Input
                    ref={setRef('description')}
                    value={newStep.description}
                    onChange={(e) => setNewStep({ ...newStep, description: e.target.value })}
                    onFocus={() => setActiveField('description')}
                    placeholder="e.g., Convert work function into joules"
                  />
                </div>
                <div>
                  <Label className="text-xs">Points</Label>
                  <Input
                    type="number"
                    value={newStep.points}
                    onChange={(e) => setNewStep({ ...newStep, points: parseInt(e.target.value) || 0 })}
                    min={0}
                  />
                </div>
              </div>

              <div>
                <Label className="text-xs">Expression / Equation</Label>
                <Input
                  ref={setRef('expression')}
                  value={newStep.expression}
                  onChange={(e) => setNewStep({ ...newStep, expression: e.target.value })}
                  onFocus={() => setActiveField('expression')}
                  placeholder="e.g., φ = 4.8 × 1.6×10⁻¹⁹ J"
                  className={activeField === 'expression' ? 'ring-2 ring-primary/40' : ''}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="text-xs">LaTeX (optional)</Label>
                  <FormulaInserter onInsert={handleFormulaInsert} />
                </div>
                <div className="relative">
                  <Input
                    ref={(el) => {
                      setRef('latex')(el);
                      (latexAcNewStep.ref as React.MutableRefObject<HTMLInputElement | null>).current = el;
                    }}
                    value={latexAcNewStep.value}
                    onChange={(e) => { latexAcNewStep.onChange(e); }}
                    onKeyDown={latexAcNewStep.onKeyDown}
                    onFocus={() => setActiveField('latex')}
                    placeholder="e.g., \phi = 4.8 \times 1.6 \times 10^{-19}"
                    className={`font-mono text-sm ${activeField === 'latex' ? 'ring-2 ring-primary/40' : ''}`}
                  />
                  {latexAcNewStep.showList && (
                    <LatexCompletionsList
                      completions={latexAcNewStep.completions}
                      selectedIndex={latexAcNewStep.selectedIndex}
                      onSelect={(s) => latexAcNewStep.apply(s)}
                    />
                  )}
                </div>
                {newStep.latex && (
                  <div className="mt-1 p-2 bg-blue-50 border border-blue-200 rounded text-center">
                    <MathText
                      text={newStep.latex.includes('$') ? newStep.latex : `$$${newStep.latex}$$`}
                      className="text-sm"
                    />
                  </div>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Checkbox
                  checked={newStep.required !== false}
                  onCheckedChange={(checked) => setNewStep({ ...newStep, required: !!checked })}
                  id="step-required"
                />
                <Label htmlFor="step-required" className="text-xs cursor-pointer">
                  This step is required for full credit
                </Label>
              </div>
            </div>

            {/* Scientific Tools — collapsible */}
            <div className="border-t">
              <button
                type="button"
                onClick={() => setShowTools(!showTools)}
                className="w-full flex items-center justify-between px-4 py-2 text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <Calculator className="h-4 w-4" />
                  Scientific Tools
                  <span className="text-xs text-muted-foreground font-normal">
                    — inserting into: <span className="font-semibold text-primary">{activeField}</span>
                  </span>
                </span>
                {showTools ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showTools && (
                <div className="border-t bg-background">
                  <Tabs defaultValue="keyboard" className="w-full">
                    <TabsList className="w-full grid grid-cols-5 rounded-none border-b h-9">
                      <TabsTrigger value="keyboard" className="text-xs rounded-none">
                        Keyboard
                      </TabsTrigger>
                      <TabsTrigger value="calculator" className="rounded-none">
                        <Calculator className="h-3.5 w-3.5" />
                      </TabsTrigger>
                      <TabsTrigger value="periodic" className="rounded-none">
                        <Atom className="h-3.5 w-3.5" />
                      </TabsTrigger>
                      <TabsTrigger value="units" className="rounded-none">
                        <Ruler className="h-3.5 w-3.5" />
                      </TabsTrigger>
                      <TabsTrigger value="constants" className="rounded-none">
                        <Pi className="h-3.5 w-3.5" />
                      </TabsTrigger>
                    </TabsList>

                    <div className="max-h-64 overflow-y-auto">
                      <TabsContent value="keyboard" className="p-3 mt-0">
                        <ScientificKeyboard onInsert={insertAtCursor} />
                      </TabsContent>
                      <TabsContent value="calculator" className="p-3 mt-0">
                        <CalculatorWidget onInsert={insertAtCursor} />
                      </TabsContent>
                      <TabsContent value="periodic" className="p-3 mt-0">
                        <PeriodicTableSelector onSelect={(el) => insertAtCursor(el.symbol)} />
                      </TabsContent>
                      <TabsContent value="units" className="p-3 mt-0">
                        <UnitConverter onInsert={insertAtCursor} />
                      </TabsContent>
                      <TabsContent value="constants" className="p-3 mt-0">
                        <ConstantsLibrary onSelect={(c) => insertAtCursor(`${c.symbol} = ${c.value}`)} />
                      </TabsContent>
                    </div>
                  </Tabs>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-2 px-4 pb-4">
              <Button onClick={handleAddStep} size="sm" className="flex-1">
                Add Step
              </Button>
              <Button variant="outline" size="sm" onClick={() => { setShowForm(false); setShowTools(false); }}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        {/* Steps List */}
        {steps.length > 0 ? (
          <div className="space-y-2">
            {steps.map((step) => (
              <div
                key={step.stepNumber}
                className="flex items-start gap-2 p-3 border rounded-lg bg-card hover:bg-muted/30 transition-colors"
              >
                <GripVertical className="h-5 w-5 text-muted-foreground mt-0.5 cursor-move shrink-0" />
                <div className="flex-1 space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary">
                      Step {step.stepNumber}
                    </span>
                    <span className="text-xs text-muted-foreground">{step.points} pts</span>
                    {step.required && (
                      <span className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800">Required</span>
                    )}
                  </div>
                  {step.description && (
                    <p className="text-sm text-muted-foreground">{step.description}</p>
                  )}
                  {step.latex ? (
                    <div className="bg-muted px-2 py-1 rounded text-center">
                      {/* If user typed raw LaTeX (no $ delimiters), wrap for block render */}
                      <MathText
                        text={step.latex.includes('$') ? step.latex : `$$${step.latex}$$`}
                        className="text-sm"
                      />
                    </div>
                  ) : (
                    <div className="bg-muted px-2 py-1 rounded">
                      <MathText text={step.expression} className="text-sm" />
                    </div>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive hover:text-destructive shrink-0"
                  onClick={() => removeStep(step.stepNumber)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          !showForm && (
            <p className="text-sm text-muted-foreground text-center py-4">No solution steps added yet</p>
          )
        )}

        {/* Final Answer */}
        <div className="pt-4 border-t space-y-3">
          <Label className="text-sm font-semibold">Final Answer</Label>
          <div className="space-y-2">
            <div>
              <Label className="text-xs">Answer</Label>
              <Input
                ref={setRef('finalAnswer')}
                value={finalAnswer}
                onChange={(e) => onUpdate({ finalAnswer: e.target.value })}
                onFocus={() => setActiveField('finalAnswer')}
                placeholder="Final answer"
              />
            </div>
            <div>
              <Label className="text-xs">LaTeX (optional)</Label>
              <div className="relative">
                <Input
                  ref={(el) => {
                    setRef('finalAnswerLatex')(el);
                    (latexAcFinal.ref as React.MutableRefObject<HTMLInputElement | null>).current = el;
                  }}
                  value={latexAcFinal.value}
                  onChange={latexAcFinal.onChange}
                  onKeyDown={latexAcFinal.onKeyDown}
                  onFocus={() => setActiveField('finalAnswerLatex')}
                  placeholder="LaTeX representation"
                  className="font-mono text-sm"
                />
                {latexAcFinal.showList && (
                  <LatexCompletionsList
                    completions={latexAcFinal.completions}
                    selectedIndex={latexAcFinal.selectedIndex}
                    onSelect={(s) => latexAcFinal.apply(s)}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
