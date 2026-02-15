import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface CalculatorWidgetProps {
  onInsert: (value: string) => void;
}

export function CalculatorWidget({ onInsert }: CalculatorWidgetProps) {
  const [display, setDisplay] = useState('0');
  const [mode, setMode] = useState<'basic' | 'scientific'>('scientific');

  const handleNumber = (num: string) => {
    setDisplay(display === '0' ? num : display + num);
  };

  const handleOperation = (op: string) => {
    setDisplay(display + ' ' + op + ' ');
  };

  const handleClear = () => {
    setDisplay('0');
  };

  const handleInsert = () => {
    onInsert(display);
    setDisplay('0');
  };

  const scientificFunctions = [
    { label: 'sin', value: 'sin(' },
    { label: 'cos', value: 'cos(' },
    { label: 'tan', value: 'tan(' },
    { label: 'log', value: 'log(' },
    { label: 'ln', value: 'ln(' },
    { label: '√', value: '√(' },
    { label: 'x²', value: '^2' },
    { label: 'xⁿ', value: '^' },
    { label: 'π', value: 'π' },
    { label: 'e', value: 'e' },
    { label: '(', value: '(' },
    { label: ')', value: ')' },
  ];

  return (
    <div className="space-y-4">
      <div className="bg-muted p-3 rounded-lg font-mono text-right text-lg">
        {display || '0'}
      </div>

      <Tabs value={mode} onValueChange={(v) => setMode(v as any)}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="basic">Basic</TabsTrigger>
          <TabsTrigger value="scientific">Scientific</TabsTrigger>
        </TabsList>

        <TabsContent value="basic" className="space-y-2">
          <div className="grid grid-cols-4 gap-2">
            {[7, 8, 9, '/'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[4, 5, 6, '*'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[1, 2, 3, '-'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[0, '.', '=', '+'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                onClick={() => typeof btn === 'number' || btn === '.' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="scientific" className="space-y-2">
          <div className="grid grid-cols-4 gap-1">
            {scientificFunctions.map((func) => (
              <Button
                key={func.label}
                variant="outline"
                size="sm"
                onClick={() => setDisplay(display + func.value)}
              >
                {func.label}
              </Button>
            ))}
          </div>
          <div className="grid grid-cols-4 gap-2 mt-2">
            {[7, 8, 9, '/'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                size="sm"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[4, 5, 6, '*'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                size="sm"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[1, 2, 3, '-'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                size="sm"
                onClick={() => typeof btn === 'number' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
            {[0, '.', '=', '+'].map((btn) => (
              <Button
                key={btn}
                variant="outline"
                size="sm"
                onClick={() => typeof btn === 'number' || btn === '.' ? handleNumber(btn.toString()) : handleOperation(btn)}
              >
                {btn}
              </Button>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      <div className="flex gap-2">
        <Button variant="outline" onClick={handleClear} className="flex-1">
          Clear
        </Button>
        <Button onClick={handleInsert} className="flex-1">
          Insert
        </Button>
      </div>
    </div>
  );
}

