import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { ArrowRight } from 'lucide-react';

interface UnitConverterProps {
  onInsert: (value: string) => void;
}

const unitCategories = {
  Length: {
    units: ['meter', 'kilometer', 'centimeter', 'millimeter', 'mile', 'yard', 'foot', 'inch'],
    conversions: {
      meter: 1,
      kilometer: 0.001,
      centimeter: 100,
      millimeter: 1000,
      mile: 0.000621371,
      yard: 1.09361,
      foot: 3.28084,
      inch: 39.3701,
    },
  },
  Mass: {
    units: ['kilogram', 'gram', 'milligram', 'pound', 'ounce'],
    conversions: {
      kilogram: 1,
      gram: 1000,
      milligram: 1000000,
      pound: 2.20462,
      ounce: 35.274,
    },
  },
  Time: {
    units: ['second', 'minute', 'hour', 'day', 'week'],
    conversions: {
      second: 1,
      minute: 1/60,
      hour: 1/3600,
      day: 1/86400,
      week: 1/604800,
    },
  },
  Temperature: {
    units: ['celsius', 'fahrenheit', 'kelvin'],
    conversions: {}, // Special handling needed
  },
  Volume: {
    units: ['liter', 'milliliter', 'gallon', 'quart', 'cup'],
    conversions: {
      liter: 1,
      milliliter: 1000,
      gallon: 0.264172,
      quart: 1.05669,
      cup: 4.22675,
    },
  },
};

export function UnitConverter({ onInsert }: UnitConverterProps) {
  const [category, setCategory] = useState<string>('Length');
  const [fromUnit, setFromUnit] = useState<string>('meter');
  const [toUnit, setToUnit] = useState<string>('kilometer');
  const [value, setValue] = useState<string>('1');
  const [result, setResult] = useState<number | null>(null);

  const convert = () => {
    const val = parseFloat(value);
    if (isNaN(val)) return;

    const cat = unitCategories[category as keyof typeof unitCategories];
    
    if (category === 'Temperature') {
      // Special temperature conversion
      let celsius = 0;
      if (fromUnit === 'celsius') celsius = val;
      else if (fromUnit === 'fahrenheit') celsius = (val - 32) * 5/9;
      else if (fromUnit === 'kelvin') celsius = val - 273.15;

      let converted = 0;
      if (toUnit === 'celsius') converted = celsius;
      else if (toUnit === 'fahrenheit') converted = celsius * 9/5 + 32;
      else if (toUnit === 'kelvin') converted = celsius + 273.15;

      setResult(converted);
    } else {
      const fromFactor = cat.conversions[fromUnit as keyof typeof cat.conversions] || 1;
      const toFactor = cat.conversions[toUnit as keyof typeof cat.conversions] || 1;
      const converted = val / fromFactor * toFactor;
      setResult(converted);
    }
  };

  const insertResult = () => {
    if (result !== null) {
      onInsert(`${value} ${fromUnit} = ${result.toFixed(4)} ${toUnit}`);
    }
  };

  const currentCategory = unitCategories[category as keyof typeof unitCategories];

  return (
    <div className="space-y-4">
      {/* Category Selection */}
      <div>
        <Label>Category</Label>
        <Select value={category} onValueChange={(v) => {
          setCategory(v);
          setFromUnit(unitCategories[v as keyof typeof unitCategories].units[0]);
          setToUnit(unitCategories[v as keyof typeof unitCategories].units[1] || unitCategories[v as keyof typeof unitCategories].units[0]);
          setResult(null);
        }}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.keys(unitCategories).map((cat) => (
              <SelectItem key={cat} value={cat}>{cat}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Conversion */}
      <div className="grid grid-cols-5 gap-2 items-end">
        <div className="col-span-2">
          <Label className="text-xs">From</Label>
          <Input
            type="number"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Value"
          />
        </div>
        <div className="col-span-2">
          <Label className="text-xs">Unit</Label>
          <Select value={fromUnit} onValueChange={setFromUnit}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {currentCategory.units.map((unit) => (
                <SelectItem key={unit} value={unit}>{unit}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button onClick={convert} variant="outline" size="sm">
          <ArrowRight className="h-4 w-4" />
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <Label className="text-xs">To</Label>
          <Select value={toUnit} onValueChange={setToUnit}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {currentCategory.units.map((unit) => (
                <SelectItem key={unit} value={unit}>{unit}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Result */}
      {result !== null && (
        <div className="p-3 bg-primary/5 rounded-lg border border-primary/20">
          <p className="text-sm font-medium">Result:</p>
          <p className="text-lg font-mono">
            {value} {fromUnit} = <strong>{result.toFixed(4)}</strong> {toUnit}
          </p>
          <Button onClick={insertResult} size="sm" className="mt-2 w-full">
            Insert into Question
          </Button>
        </div>
      )}

      {/* Quick Reference */}
      <div className="text-xs text-muted-foreground space-y-1 pt-2 border-t">
        <p className="font-semibold">Common Conversions:</p>
        <p>• 1 km = 1000 m</p>
        <p>• 1 kg = 1000 g</p>
        <p>• 1 hr = 3600 s</p>
        <p>• 0°C = 273.15 K</p>
      </div>
    </div>
  );
}

