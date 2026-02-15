import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useState } from "react";
import { CheckCircle2 } from "lucide-react";

interface ScientificKeyboardProps {
  onInsert: (symbol: string) => void;
}

const ScientificKeyboard = ({ onInsert }: ScientificKeyboardProps) => {
  const [lastInserted, setLastInserted] = useState<string | null>(null);

  const handleInsert = (symbol: string) => {
    onInsert(symbol);
    setLastInserted(symbol);
    setTimeout(() => setLastInserted(null), 500);
  };

  const basicOperators = [
    { symbol: "+", label: "+" },
    { symbol: "−", label: "−" },
    { symbol: "×", label: "×" },
    { symbol: "÷", label: "÷" },
    { symbol: "=", label: "=" },
    { symbol: "≠", label: "≠" },
    { symbol: "≈", label: "≈" },
    { symbol: "±", label: "±" },
    { symbol: "<", label: "<" },
    { symbol: ">", label: ">" },
    { symbol: "≤", label: "≤" },
    { symbol: "≥", label: "≥" },
    { symbol: "∞", label: "∞" },
    { symbol: "%", label: "%" },
    { symbol: "°", label: "°" },
    { symbol: "∠", label: "∠" },
  ];

  const advancedMath = [
    { symbol: "√", label: "√" },
    { symbol: "∛", label: "∛" },
    { symbol: "∜", label: "∜" },
    { symbol: "²", label: "²" },
    { symbol: "³", label: "³" },
    { symbol: "ⁿ", label: "ⁿ" },
    { symbol: "₁", label: "₁" },
    { symbol: "₂", label: "₂" },
    { symbol: "₃", label: "₃" },
    { symbol: "ₙ", label: "ₙ" },
    { symbol: "∑", label: "∑" },
    { symbol: "∏", label: "∏" },
    { symbol: "∫", label: "∫" },
    { symbol: "∂", label: "∂" },
    { symbol: "∇", label: "∇" },
    { symbol: "Δ", label: "Δ" },
  ];

  const greekLetters = [
    { symbol: "α", label: "α" },
    { symbol: "β", label: "β" },
    { symbol: "γ", label: "γ" },
    { symbol: "δ", label: "δ" },
    { symbol: "ε", label: "ε" },
    { symbol: "ζ", label: "ζ" },
    { symbol: "η", label: "η" },
    { symbol: "θ", label: "θ" },
    { symbol: "ι", label: "ι" },
    { symbol: "κ", label: "κ" },
    { symbol: "λ", label: "λ" },
    { symbol: "μ", label: "μ" },
    { symbol: "ν", label: "ν" },
    { symbol: "ξ", label: "ξ" },
    { symbol: "π", label: "π" },
    { symbol: "ρ", label: "ρ" },
    { symbol: "σ", label: "σ" },
    { symbol: "τ", label: "τ" },
    { symbol: "υ", label: "υ" },
    { symbol: "φ", label: "φ" },
    { symbol: "χ", label: "χ" },
    { symbol: "ψ", label: "ψ" },
    { symbol: "ω", label: "ω" },
    { symbol: "Γ", label: "Γ" },
    { symbol: "Θ", label: "Θ" },
    { symbol: "Λ", label: "Λ" },
    { symbol: "Ξ", label: "Ξ" },
    { symbol: "Π", label: "Π" },
    { symbol: "Σ", label: "Σ" },
    { symbol: "Φ", label: "Φ" },
    { symbol: "Ψ", label: "Ψ" },
    { symbol: "Ω", label: "Ω" },
  ];

  const setTheory = [
    { symbol: "∈", label: "∈" },
    { symbol: "∉", label: "∉" },
    { symbol: "⊂", label: "⊂" },
    { symbol: "⊃", label: "⊃" },
    { symbol: "⊆", label: "⊆" },
    { symbol: "⊇", label: "⊇" },
    { symbol: "∪", label: "∪" },
    { symbol: "∩", label: "∩" },
    { symbol: "∅", label: "∅" },
    { symbol: "ℕ", label: "ℕ" },
    { symbol: "ℤ", label: "ℤ" },
    { symbol: "ℚ", label: "ℚ" },
    { symbol: "ℝ", label: "ℝ" },
    { symbol: "ℂ", label: "ℂ" },
    { symbol: "∀", label: "∀" },
    { symbol: "∃", label: "∃" },
  ];

  const arrows = [
    { symbol: "→", label: "→" },
    { symbol: "←", label: "←" },
    { symbol: "↑", label: "↑" },
    { symbol: "↓", label: "↓" },
    { symbol: "↔", label: "↔" },
    { symbol: "⇒", label: "⇒" },
    { symbol: "⇐", label: "⇐" },
    { symbol: "⇔", label: "⇔" },
  ];

  const brackets = [
    { symbol: "(", label: "(" },
    { symbol: ")", label: ")" },
    { symbol: "[", label: "[" },
    { symbol: "]", label: "]" },
    { symbol: "{", label: "{" },
    { symbol: "}", label: "}" },
    { symbol: "⌈", label: "⌈" },
    { symbol: "⌉", label: "⌉" },
    { symbol: "⌊", label: "⌊" },
    { symbol: "⌋", label: "⌋" },
    { symbol: "⟨", label: "⟨" },
    { symbol: "⟩", label: "⟩" },
  ];

  const trigonometric = [
    { symbol: "sin(", label: "sin", latex: "\\sin(" },
    { symbol: "cos(", label: "cos", latex: "\\cos(" },
    { symbol: "tan(", label: "tan", latex: "\\tan(" },
    { symbol: "sec(", label: "sec", latex: "\\sec(" },
    { symbol: "csc(", label: "csc", latex: "\\csc(" },
    { symbol: "cot(", label: "cot", latex: "\\cot(" },
    { symbol: "arcsin(", label: "arcsin", latex: "\\arcsin(" },
    { symbol: "arccos(", label: "arccos", latex: "\\arccos(" },
    { symbol: "arctan(", label: "arctan", latex: "\\arctan(" },
    { symbol: "sin⁻¹(", label: "sin⁻¹", latex: "\\sin^{-1}(" },
    { symbol: "cos⁻¹(", label: "cos⁻¹", latex: "\\cos^{-1}(" },
    { symbol: "tan⁻¹(", label: "tan⁻¹", latex: "\\tan^{-1}(" },
  ];

  const exponential = [
    { symbol: "e^", label: "eˣ", latex: "e^{" },
    { symbol: "10^", label: "10ˣ", latex: "10^{" },
    { symbol: "a^", label: "aˣ", latex: "a^{" },
    { symbol: "exp(", label: "exp", latex: "\\exp(" },
    { symbol: "ln(", label: "ln", latex: "\\ln(" },
    { symbol: "log(", label: "log", latex: "\\log(" },
    { symbol: "log₁₀(", label: "log₁₀", latex: "\\log_{10}(" },
    { symbol: "log₂(", label: "log₂", latex: "\\log_{2}(" },
  ];

  const matrices = [
    { symbol: "\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}", label: "2×2", latex: "\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}" },
    { symbol: "\\begin{pmatrix} a & b & c \\\\ d & e & f \\\\ g & h & i \\end{pmatrix}", label: "3×3", latex: "\\begin{pmatrix} a & b & c \\\\ d & e & f \\\\ g & h & i \\end{pmatrix}" },
    { symbol: "\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}", label: "[2×2]", latex: "\\begin{bmatrix} a & b \\\\ c & d \\end{bmatrix}" },
    { symbol: "\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}", label: "|2×2|", latex: "\\begin{vmatrix} a & b \\\\ c & d \\end{vmatrix}" },
    { symbol: "\\begin{pmatrix} a \\\\ b \\end{pmatrix}", label: "2×1", latex: "\\begin{pmatrix} a \\\\ b \\end{pmatrix}" },
    { symbol: "\\begin{pmatrix} a & b \\end{pmatrix}", label: "1×2", latex: "\\begin{pmatrix} a & b \\end{pmatrix}" },
  ];

  const renderSymbolGrid = (symbols: { symbol: string; label: string; latex?: string }[]) => (
    <div className="grid grid-cols-8 gap-2 p-2">
      {symbols.map((item, idx) => (
        <Button
          key={idx}
          variant="outline"
          size="sm"
          type="button"
          className={`h-12 text-xs font-medium hover:bg-primary hover:text-primary-foreground transition-all active:scale-95 relative ${
            lastInserted === item.symbol ? 'ring-2 ring-primary bg-primary text-primary-foreground' : ''
          }`}
          onClick={() => {
            // Insert as LaTeX if available, otherwise use symbol
            const toInsert = item.latex ? `$$${item.latex}$$` : item.symbol;
            handleInsert(toInsert);
          }}
          title={`Insert ${item.label}`}
        >
          {item.label}
          {lastInserted === item.symbol && (
            <CheckCircle2 className="h-3 w-3 absolute top-1 right-1 animate-in fade-in zoom-in" />
          )}
        </Button>
      ))}
    </div>
  );

  return (
    <Card className="p-4 border-2">
      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-9 h-auto">
          <TabsTrigger value="basic" className="text-xs py-2">Basic</TabsTrigger>
          <TabsTrigger value="advanced" className="text-xs py-2">Advanced</TabsTrigger>
          <TabsTrigger value="trig" className="text-xs py-2">Trig</TabsTrigger>
          <TabsTrigger value="exp" className="text-xs py-2">Exp</TabsTrigger>
          <TabsTrigger value="matrix" className="text-xs py-2">Matrix</TabsTrigger>
          <TabsTrigger value="greek" className="text-xs py-2">Greek</TabsTrigger>
          <TabsTrigger value="sets" className="text-xs py-2">Sets</TabsTrigger>
          <TabsTrigger value="arrows" className="text-xs py-2">Arrows</TabsTrigger>
          <TabsTrigger value="brackets" className="text-xs py-2">Brackets</TabsTrigger>
        </TabsList>

        <ScrollArea className="h-[200px] mt-4">
          <TabsContent value="basic" className="mt-0">
            {renderSymbolGrid(basicOperators)}
          </TabsContent>

          <TabsContent value="advanced" className="mt-0">
            {renderSymbolGrid(advancedMath)}
          </TabsContent>

          <TabsContent value="trig" className="mt-0">
            {renderSymbolGrid(trigonometric)}
          </TabsContent>

          <TabsContent value="exp" className="mt-0">
            {renderSymbolGrid(exponential)}
          </TabsContent>

          <TabsContent value="matrix" className="mt-0">
            <div className="grid grid-cols-3 gap-2 p-2">
              {matrices.map((item, idx) => (
                <Button
                  key={idx}
                  variant="outline"
                  size="sm"
                  type="button"
                  className={`h-12 text-xs font-medium hover:bg-primary hover:text-primary-foreground transition-all active:scale-95 relative ${
                    lastInserted === item.symbol ? 'ring-2 ring-primary bg-primary text-primary-foreground' : ''
                  }`}
                  onClick={() => {
                    const toInsert = item.latex ? `$$${item.latex}$$` : item.symbol;
                    handleInsert(toInsert);
                  }}
                  title={`Insert ${item.label} matrix`}
                >
                  {item.label}
                  {lastInserted === item.symbol && (
                    <CheckCircle2 className="h-3 w-3 absolute top-1 right-1 animate-in fade-in zoom-in" />
                  )}
                </Button>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="greek" className="mt-0">
            {renderSymbolGrid(greekLetters)}
          </TabsContent>

          <TabsContent value="sets" className="mt-0">
            {renderSymbolGrid(setTheory)}
          </TabsContent>

          <TabsContent value="arrows" className="mt-0">
            {renderSymbolGrid(arrows)}
          </TabsContent>

          <TabsContent value="brackets" className="mt-0">
            {renderSymbolGrid(brackets)}
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </Card>
  );
};

export default ScientificKeyboard;

