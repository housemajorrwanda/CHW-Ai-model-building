import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, X, BookOpen } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Theory } from './QuestionBuilder';
import { toast } from 'sonner';

interface TheoryManagerProps {
  theories: Theory[];
  onUpdate: (theories: Theory[]) => void;
}

export function TheoryManager({ theories, onUpdate }: TheoryManagerProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [unit, setUnit] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('physics');

  const handleAdd = () => {
    if (!name || !value) {
      toast.error('Name and value are required');
      return;
    }

    const newTheory: Theory = {
      id: crypto.randomUUID(),
      name,
      value,
      unit,
      description,
      category,
    };

    onUpdate([...theories, newTheory]);
    setName('');
    setValue('');
    setUnit('');
    setDescription('');
    setShowForm(false);
    toast.success('Theory/Constant added');
  };

  const removeTheory = (id: string) => {
    onUpdate(theories.filter((t) => t.id !== id));
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Theory & Constants
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowForm(!showForm)}
          >
            <Plus className="h-4 w-4 mr-2" />
            Add
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Add Form */}
        {showForm && (
          <div className="p-4 border rounded-lg bg-muted/30 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Newton's Second Law"
                />
              </div>
              <div>
                <Label className="text-xs">Category</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="physics">Physics</SelectItem>
                    <SelectItem value="chemistry">Chemistry</SelectItem>
                    <SelectItem value="mathematics">Mathematics</SelectItem>
                    <SelectItem value="biology">Biology</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Value/Formula</Label>
                <Input
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="e.g., F = ma"
                />
              </div>
              <div>
                <Label className="text-xs">Unit (optional)</Label>
                <Input
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="e.g., N (Newtons)"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">Description (optional)</Label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief explanation of the theory or constant"
                className="h-16"
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleAdd} size="sm" className="flex-1">
                Add Theory
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

        {/* Theories List */}
        {theories.length > 0 ? (
          <div className="space-y-2">
            {theories.map((theory) => (
              <div
                key={theory.id}
                className="p-3 border rounded-lg bg-card hover:bg-muted/30 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-semibold">{theory.name}</p>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                        {theory.category}
                      </span>
                    </div>
                    <p className="text-sm font-mono mb-1">
                      {theory.value} {theory.unit && <span className="text-muted-foreground">({theory.unit})</span>}
                    </p>
                    {theory.description && (
                      <p className="text-xs text-muted-foreground">{theory.description}</p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-destructive hover:text-destructive"
                    onClick={() => removeTheory(theory.id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          !showForm && (
            <p className="text-sm text-muted-foreground text-center py-4">
              No theories or constants added yet
            </p>
          )
        )}
      </CardContent>
    </Card>
  );
}

