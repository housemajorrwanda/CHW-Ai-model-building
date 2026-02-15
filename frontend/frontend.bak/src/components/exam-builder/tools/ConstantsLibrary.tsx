import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Search } from 'lucide-react';
import { useState } from 'react';

interface Constant {
  symbol: string;
  name: string;
  value: string;
  unit: string;
  category: string;
  description: string;
}

const constants: Constant[] = [
  // Mathematical Constants
  { symbol: 'π', name: 'Pi', value: '3.14159265359', unit: '', category: 'math', description: 'Ratio of circumference to diameter' },
  { symbol: 'e', name: 'Euler\'s Number', value: '2.71828182846', unit: '', category: 'math', description: 'Base of natural logarithm' },
  { symbol: 'φ', name: 'Golden Ratio', value: '1.61803398875', unit: '', category: 'math', description: 'Golden ratio (phi)' },
  
  // Physical Constants
  { symbol: 'c', name: 'Speed of Light', value: '299792458', unit: 'm/s', category: 'physics', description: 'Speed of light in vacuum' },
  { symbol: 'G', name: 'Gravitational Constant', value: '6.67430 × 10⁻¹¹', unit: 'm³/(kg·s²)', category: 'physics', description: 'Newton\'s gravitational constant' },
  { symbol: 'g', name: 'Gravity (Earth)', value: '9.80665', unit: 'm/s²', category: 'physics', description: 'Standard gravity on Earth' },
  { symbol: 'h', name: 'Planck Constant', value: '6.62607015 × 10⁻³⁴', unit: 'J·s', category: 'physics', description: 'Planck constant' },
  { symbol: 'ℏ', name: 'Reduced Planck', value: '1.054571817 × 10⁻³⁴', unit: 'J·s', category: 'physics', description: 'h/2π' },
  { symbol: 'k', name: 'Boltzmann Constant', value: '1.380649 × 10⁻²³', unit: 'J/K', category: 'physics', description: 'Boltzmann constant' },
  { symbol: 'Nₐ', name: 'Avogadro\'s Number', value: '6.02214076 × 10²³', unit: 'mol⁻¹', category: 'chemistry', description: 'Avogadro constant' },
  { symbol: 'R', name: 'Gas Constant', value: '8.314462618', unit: 'J/(mol·K)', category: 'chemistry', description: 'Universal gas constant' },
  { symbol: 'e⁻', name: 'Elementary Charge', value: '1.602176634 × 10⁻¹⁹', unit: 'C', category: 'physics', description: 'Charge of an electron' },
  { symbol: 'mₑ', name: 'Electron Mass', value: '9.1093837015 × 10⁻³¹', unit: 'kg', category: 'physics', description: 'Mass of an electron' },
  { symbol: 'mₚ', name: 'Proton Mass', value: '1.67262192369 × 10⁻²⁷', unit: 'kg', category: 'physics', description: 'Mass of a proton' },
];

interface ConstantsLibraryProps {
  onSelect: (constant: Constant) => void;
}

export function ConstantsLibrary({ onSelect }: ConstantsLibraryProps) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');

  const filteredConstants = constants.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.symbol.toLowerCase().includes(search.toLowerCase()) ||
      c.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === 'all' || c.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="space-y-4 max-h-96 overflow-y-auto">
      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search constants..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8"
        />
      </div>

      {/* Category Tabs */}
      <Tabs value={selectedCategory} onValueChange={setSelectedCategory}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="all">All</TabsTrigger>
          <TabsTrigger value="math">Math</TabsTrigger>
          <TabsTrigger value="physics">Physics</TabsTrigger>
          <TabsTrigger value="chemistry">Chem</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Constants List */}
      <div className="space-y-2">
        {filteredConstants.map((constant) => (
          <Button
            key={constant.symbol}
            variant="outline"
            className="w-full h-auto p-3 flex flex-col items-start text-left hover:bg-primary/5"
            onClick={() => onSelect(constant)}
          >
            <div className="flex items-center justify-between w-full mb-1">
              <div className="flex items-center gap-2">
                <span className="text-lg font-mono font-bold">{constant.symbol}</span>
                <span className="text-sm font-semibold">{constant.name}</span>
              </div>
              <Badge variant="secondary" className="text-xs">
                {constant.category}
              </Badge>
            </div>
            <div className="text-sm text-muted-foreground mb-1">
              {constant.value} {constant.unit}
            </div>
            <div className="text-xs text-muted-foreground">
              {constant.description}
            </div>
          </Button>
        ))}
      </div>

      {filteredConstants.length === 0 && (
        <div className="text-center py-6 text-sm text-muted-foreground">
          No constants found
        </div>
      )}
    </div>
  );
}

