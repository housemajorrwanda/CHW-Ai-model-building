import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { useState } from 'react';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Element {
  symbol: string;
  name: string;
  atomicNumber: number;
  atomicMass: number;
  category: string;
}

const elements: Element[] = [
  { symbol: 'H', name: 'Hydrogen', atomicNumber: 1, atomicMass: 1.008, category: 'nonmetal' },
  { symbol: 'He', name: 'Helium', atomicNumber: 2, atomicMass: 4.003, category: 'noble-gas' },
  { symbol: 'Li', name: 'Lithium', atomicNumber: 3, atomicMass: 6.941, category: 'alkali' },
  { symbol: 'Be', name: 'Beryllium', atomicNumber: 4, atomicMass: 9.012, category: 'alkaline-earth' },
  { symbol: 'B', name: 'Boron', atomicNumber: 5, atomicMass: 10.81, category: 'metalloid' },
  { symbol: 'C', name: 'Carbon', atomicNumber: 6, atomicMass: 12.01, category: 'nonmetal' },
  { symbol: 'N', name: 'Nitrogen', atomicNumber: 7, atomicMass: 14.01, category: 'nonmetal' },
  { symbol: 'O', name: 'Oxygen', atomicNumber: 8, atomicMass: 16.00, category: 'nonmetal' },
  { symbol: 'F', name: 'Fluorine', atomicNumber: 9, atomicMass: 19.00, category: 'halogen' },
  { symbol: 'Ne', name: 'Neon', atomicNumber: 10, atomicMass: 20.18, category: 'noble-gas' },
  { symbol: 'Na', name: 'Sodium', atomicNumber: 11, atomicMass: 22.99, category: 'alkali' },
  { symbol: 'Mg', name: 'Magnesium', atomicNumber: 12, atomicMass: 24.31, category: 'alkaline-earth' },
  { symbol: 'Al', name: 'Aluminum', atomicNumber: 13, atomicMass: 26.98, category: 'post-transition' },
  { symbol: 'Si', name: 'Silicon', atomicNumber: 14, atomicMass: 28.09, category: 'metalloid' },
  { symbol: 'P', name: 'Phosphorus', atomicNumber: 15, atomicMass: 30.97, category: 'nonmetal' },
  { symbol: 'S', name: 'Sulfur', atomicNumber: 16, atomicMass: 32.07, category: 'nonmetal' },
  { symbol: 'Cl', name: 'Chlorine', atomicNumber: 17, atomicMass: 35.45, category: 'halogen' },
  { symbol: 'Ar', name: 'Argon', atomicNumber: 18, atomicMass: 39.95, category: 'noble-gas' },
  { symbol: 'K', name: 'Potassium', atomicNumber: 19, atomicMass: 39.10, category: 'alkali' },
  { symbol: 'Ca', name: 'Calcium', atomicNumber: 20, atomicMass: 40.08, category: 'alkaline-earth' },
  // Add more elements as needed
];

interface PeriodicTableSelectorProps {
  onSelect: (element: Element) => void;
}

export function PeriodicTableSelector({ onSelect }: PeriodicTableSelectorProps) {
  const [search, setSearch] = useState('');
  const [selectedElement, setSelectedElement] = useState<Element | null>(null);

  const filteredElements = elements.filter(
    (el) =>
      el.symbol.toLowerCase().includes(search.toLowerCase()) ||
      el.name.toLowerCase().includes(search.toLowerCase())
  );

  const categoryColors: Record<string, string> = {
    'nonmetal': 'bg-green-100 hover:bg-green-200 border-green-300',
    'noble-gas': 'bg-purple-100 hover:bg-purple-200 border-purple-300',
    'alkali': 'bg-red-100 hover:bg-red-200 border-red-300',
    'alkaline-earth': 'bg-orange-100 hover:bg-orange-200 border-orange-300',
    'metalloid': 'bg-yellow-100 hover:bg-yellow-200 border-yellow-300',
    'halogen': 'bg-blue-100 hover:bg-blue-200 border-blue-300',
    'post-transition': 'bg-gray-100 hover:bg-gray-200 border-gray-300',
  };

  return (
    <div className="space-y-4 max-h-96 overflow-y-auto">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search elements..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8"
        />
      </div>

      {/* Elements Grid */}
      <div className="grid grid-cols-6 gap-1">
        {filteredElements.slice(0, 36).map((element) => (
          <Button
            key={element.symbol}
            variant="outline"
            size="sm"
            className={cn(
              'h-14 flex flex-col items-center justify-center p-1 border-2',
              categoryColors[element.category] || 'bg-gray-100 hover:bg-gray-200',
              selectedElement?.symbol === element.symbol && 'ring-2 ring-primary'
            )}
            onClick={() => {
              setSelectedElement(element);
              onSelect(element);
            }}
          >
            <div className="text-xs text-muted-foreground">{element.atomicNumber}</div>
            <div className="text-sm font-bold">{element.symbol}</div>
          </Button>
        ))}
      </div>

      {/* Selected Element Info */}
      {selectedElement && (
        <Card className="p-3 bg-primary/5 border-primary/20">
          <div className="text-sm">
            <p className="font-bold">{selectedElement.name}</p>
            <p className="text-muted-foreground">
              Atomic Number: {selectedElement.atomicNumber}
            </p>
            <p className="text-muted-foreground">
              Atomic Mass: {selectedElement.atomicMass}
            </p>
          </div>
        </Card>
      )}

      {/* Legend */}
      <div className="text-xs space-y-1 pt-2 border-t">
        <p className="font-semibold mb-2">Categories:</p>
        <div className="flex flex-wrap gap-2">
          <Badge className="bg-green-100 text-green-800 border-green-300">Nonmetal</Badge>
          <Badge className="bg-red-100 text-red-800 border-red-300">Alkali Metal</Badge>
          <Badge className="bg-blue-100 text-blue-800 border-blue-300">Halogen</Badge>
          <Badge className="bg-purple-100 text-purple-800 border-purple-300">Noble Gas</Badge>
        </div>
      </div>
    </div>
  );
}

