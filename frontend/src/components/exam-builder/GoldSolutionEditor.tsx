import { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Plus, X, GripVertical, CheckCircle2, Calculator } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { Toggle } from '@/components/ui/toggle';
import ScientificKeyboard from '../exam-taker/ScientificKeyboard';
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

export function GoldSolutionEditor({ steps, finalAnswer, finalAnswerLatex, onUpdate }: GoldSolutionEditorProps) {
  const [showForm, setShowForm] = useState(false);
  const [showKeyboard, setShowKeyboard] = useState(false);
  const [activeField, setActiveField] = useState<'description' | 'expression' | 'latex' | 'finalAnswer' | 'finalAnswerLatex' | null>(null);
  const inputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({});
  
  const [newStep, setNewStep] = useState<Partial<GoldStep>>({
    stepNumber: steps.length + 1,
    description: '',
    expression: '',
    latex: '',
    points: 5,
    required: true,
  });

  const insertSymbol = (symbol: string) => {
    if (!activeField) return;
    
    if (activeField === 'description' || activeField === 'expression' || activeField === 'latex') {
      setNewStep({ ...newStep, [activeField]: (newStep[activeField] || '') + symbol });
    } else if (activeField === 'finalAnswer') {
      onUpdate({ finalAnswer: finalAnswer + symbol });
    } else if (activeField === 'finalAnswerLatex') {
      onUpdate({ finalAnswerLatex: finalAnswerLatex + symbol });
    }
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
    setNewStep({
      stepNumber: steps.length + 2,
      description: '',
      expression: '',
      latex: '',
      points: 5,
      required: true,
    });
    setShowForm(false);
    toast.success('Step added');
  };

  const removeStep = (stepNumber: number) => {
    const updatedSteps = steps
      .filter((s) => s.stepNumber !== stepNumber)
      .map((s, idx) => ({ ...s, stepNumber: idx + 1 }));
    onUpdate({ goldSolutionSteps: updatedSteps });
  };

  const updateStep = (stepNumber: number, updates: Partial<GoldStep>) => {
    const updatedSteps = steps.map((s) =>
      s.stepNumber === stepNumber ? { ...s, ...updates } : s
    );
    onUpdate({ goldSolutionSteps: updatedSteps });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4" />
            Gold Solution Steps
          </CardTitle>
          <div className="flex items-center gap-2">
            <Toggle
              size="sm"
              pressed={showKeyboard}
              onPressedChange={setShowKeyboard}
              aria-label="Scientific Keyboard"
            >
              <Calculator className="h-4 w-4" />
            </Toggle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowForm(!showForm)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Step
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Scientific Keyboard */}
        {showKeyboard && (
          <ScientificKeyboard onInsert={insertSymbol} />
        )}
        
        {/* Add Step Form */}
        {showForm && (
          <div className="p-4 border rounded-lg bg-muted/30 space-y-3">
            <div className="grid grid-cols-4 gap-3">
              <div className="col-span-3">
                <Label className="text-xs">Description</Label>
                <Input
                  value={newStep.description}
                  onChange={(e) => setNewStep({ ...newStep, description: e.target.value })}
                  onFocus={() => setActiveField('description')}
                  placeholder="Brief description of this step"
                />
              </div>
              <div>
                <Label className="text-xs">Points</Label>
                <Input
                  type="number"
                  value={newStep.points}
                  onChange={(e) => setNewStep({ ...newStep, points: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">Expression/Equation</Label>
              <Input
                value={newStep.expression}
                onChange={(e) => setNewStep({ ...newStep, expression: e.target.value })}
                onFocus={() => setActiveField('expression')}
                placeholder="e.g., x = 5 + 3"
              />
            </div>
            <div>
              <Label className="text-xs">LaTeX (optional)</Label>
              <Input
                value={newStep.latex}
                onChange={(e) => setNewStep({ ...newStep, latex: e.target.value })}
                onFocus={() => setActiveField('latex')}
                placeholder="e.g., x = 5 + 3"
              />
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                checked={newStep.required !== false}
                onCheckedChange={(checked) => setNewStep({ ...newStep, required: !!checked })}
                id="required"
              />
              <Label htmlFor="required" className="text-xs cursor-pointer">
                This step is required for full credit
              </Label>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleAddStep} size="sm" className="flex-1">
                Add Step
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowForm(false)}
              >
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
                <GripVertical className="h-5 w-5 text-muted-foreground mt-0.5 cursor-move" />
                <div className="flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded bg-primary/10 text-primary">
                      Step {step.stepNumber}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {step.points} pts
                    </span>
                    {step.required && (
                      <span className="text-xs px-2 py-0.5 rounded bg-orange-100 text-orange-800">
                        Required
                      </span>
                    )}
                  </div>
                  {step.description && (
                    <p className="text-sm text-muted-foreground">{step.description}</p>
                  )}
                  <p className="text-sm font-mono bg-muted px-2 py-1 rounded">
                    {step.expression}
                  </p>
                  {step.latex && (
                    <p className="text-xs text-muted-foreground font-mono">
                      LaTeX: {step.latex}
                    </p>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-destructive hover:text-destructive"
                  onClick={() => removeStep(step.stepNumber)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          !showForm && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No solution steps added yet
            </p>
          )
        )}

        {/* Final Answer */}
        <div className="pt-4 border-t space-y-3">
          <Label className="text-sm font-semibold">Final Answer</Label>
          <div className="space-y-2">
            <div>
              <Label className="text-xs">Answer</Label>
              <Input
                value={finalAnswer}
                onChange={(e) => onUpdate({ finalAnswer: e.target.value })}
                onFocus={() => setActiveField('finalAnswer')}
                placeholder="Final answer"
              />
            </div>
            <div>
              <Label className="text-xs">LaTeX (optional)</Label>
              <Input
                value={finalAnswerLatex}
                onChange={(e) => onUpdate({ finalAnswerLatex: e.target.value })}
                onFocus={() => setActiveField('finalAnswerLatex')}
                placeholder="LaTeX representation"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

