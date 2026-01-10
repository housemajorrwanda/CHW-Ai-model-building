import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";

interface ScientificKeyboardProps {
  onInsert: (symbol: string) => void;
}

const ScientificKeyboard = ({ onInsert }: ScientificKeyboardProps) => {
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

  const renderSymbolGrid = (symbols: { symbol: string; label: string }[]) => (
    <div className="grid grid-cols-8 gap-2">
      {symbols.map((item, idx) => (
        <Button
          key={idx}
          variant="outline"
          size="sm"
          className="h-10 text-lg font-medium hover:bg-primary hover:text-primary-foreground"
          onClick={() => onInsert(item.symbol)}
        >
          {item.label}
        </Button>
      ))}
    </div>
  );

  return (
    <Card className="p-4">
      <Tabs defaultValue="basic" className="w-full">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="basic">Basic</TabsTrigger>
          <TabsTrigger value="advanced">Advanced</TabsTrigger>
          <TabsTrigger value="greek">Greek</TabsTrigger>
          <TabsTrigger value="sets">Sets</TabsTrigger>
          <TabsTrigger value="arrows">Arrows</TabsTrigger>
          <TabsTrigger value="brackets">Brackets</TabsTrigger>
        </TabsList>

        <ScrollArea className="h-[180px] mt-4">
          <TabsContent value="basic" className="space-y-4 mt-0">
            {renderSymbolGrid(basicOperators)}
          </TabsContent>

          <TabsContent value="advanced" className="space-y-4 mt-0">
            {renderSymbolGrid(advancedMath)}
          </TabsContent>

          <TabsContent value="greek" className="space-y-4 mt-0">
            {renderSymbolGrid(greekLetters)}
          </TabsContent>

          <TabsContent value="sets" className="space-y-4 mt-0">
            {renderSymbolGrid(setTheory)}
          </TabsContent>

          <TabsContent value="arrows" className="space-y-4 mt-0">
            {renderSymbolGrid(arrows)}
          </TabsContent>

          <TabsContent value="brackets" className="space-y-4 mt-0">
            {renderSymbolGrid(brackets)}
          </TabsContent>
        </ScrollArea>
      </Tabs>
    </Card>
  );
};

export default ScientificKeyboard;

