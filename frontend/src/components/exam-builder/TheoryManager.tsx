import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Plus, X, BookOpen, Search, Database } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import type { Theory } from './QuestionBuilder';
import { toast } from 'sonner';
import { formulasDataset, type DatasetEntry } from '@/data/formulasDataset';

interface TheoryManagerProps {
  theories: Theory[];
  onUpdate: (theories: Theory[]) => void;
}

const SUBJECTS = ['All', 'Physics', 'Mathematics', 'Chemistry', 'Biology'];
const CATEGORIES = ['All', 'Law', 'Principle', 'Formula', 'Theorem', 'Equation', 'Constant', 'Identity', 'Rule', 'Theory', 'Method', 'Property'];

export function TheoryManager({ theories, onUpdate }: TheoryManagerProps) {
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [unit, setUnit] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('physics');

  // Dataset browser state
  const [search, setSearch] = useState('');
  const [filterSubject, setFilterSubject] = useState('All');
  const [filterCategory, setFilterCategory] = useState('All');

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

  const addFromDataset = (entry: DatasetEntry) => {
    const alreadyAdded = theories.some((t) => t.name === entry.name);
    if (alreadyAdded) {
      toast.info(`"${entry.name}" is already added`);
      return;
    }
    const newTheory: Theory = {
      id: crypto.randomUUID(),
      name: entry.name,
      value: entry.formula,
      unit: '',
      description: entry.description,
      category: entry.subject.toLowerCase(),
    };
    onUpdate([...theories, newTheory]);
    toast.success(`Added: ${entry.name}`);
  };

  const filteredDataset = useMemo(() => {
    return formulasDataset.filter((entry) => {
      const matchSubject = filterSubject === 'All' || entry.subject === filterSubject;
      const matchCategory = filterCategory === 'All' || entry.category === filterCategory;
      const matchSearch =
        !search ||
        entry.name.toLowerCase().includes(search.toLowerCase()) ||
        entry.formula.toLowerCase().includes(search.toLowerCase()) ||
        entry.description.toLowerCase().includes(search.toLowerCase());
      return matchSubject && matchCategory && matchSearch;
    });
  }, [search, filterSubject, filterCategory]);

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
            Add Custom
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="library">
          <TabsList className="w-full grid grid-cols-2">
            <TabsTrigger value="library" className="flex items-center gap-1">
              <Database className="h-3.5 w-3.5" />
              Dataset Library
            </TabsTrigger>
            <TabsTrigger value="added" className="flex items-center gap-1">
              <BookOpen className="h-3.5 w-3.5" />
              Added ({theories.length})
            </TabsTrigger>
          </TabsList>

          {/* Dataset Library Tab */}
          <TabsContent value="library" className="space-y-3 mt-3">
            {/* Search & Filters */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search formulas, laws, theorems..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-8 h-8 text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Select value={filterSubject} onValueChange={setFilterSubject}>
                <SelectTrigger className="h-8 text-xs flex-1">
                  <SelectValue placeholder="Subject" />
                </SelectTrigger>
                <SelectContent>
                  {SUBJECTS.map((s) => (
                    <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="h-8 text-xs flex-1">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c} value={c} className="text-xs">{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <p className="text-xs text-muted-foreground">{filteredDataset.length} results</p>

            {/* Results */}
            <div className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
              {filteredDataset.map((entry) => {
                const isAdded = theories.some((t) => t.name === entry.name);
                return (
                  <div
                    key={entry.id}
                    className="flex items-start gap-2 p-2.5 border rounded-lg hover:bg-muted/40 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 flex-wrap mb-0.5">
                        <span className="text-sm font-medium">{entry.name}</span>
                        <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{entry.subject}</Badge>
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0">{entry.category}</Badge>
                      </div>
                      <p className="text-xs font-mono text-primary">{entry.formula}</p>
                      <p className="text-xs text-muted-foreground line-clamp-1 mt-0.5">{entry.description}</p>
                    </div>
                    <Button
                      size="sm"
                      variant={isAdded ? 'secondary' : 'default'}
                      className="h-7 px-2 text-xs shrink-0"
                      onClick={() => addFromDataset(entry)}
                      disabled={isAdded}
                    >
                      {isAdded ? 'Added' : '+ Add'}
                    </Button>
                  </div>
                );
              })}
              {filteredDataset.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-6">No results found</p>
              )}
            </div>
          </TabsContent>

          {/* Added Theories Tab */}
          <TabsContent value="added" className="space-y-3 mt-3">
            {/* Custom Add Form */}
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
                    placeholder="Explanation"
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
              <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
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
                          <p className="text-xs text-muted-foreground line-clamp-2">{theory.description}</p>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-destructive hover:text-destructive shrink-0"
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
                <p className="text-sm text-muted-foreground text-center py-6">
                  No theories or constants added yet.<br />
                  <span className="text-xs">Browse the Dataset Library or click "Add Custom".</span>
                </p>
              )
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
