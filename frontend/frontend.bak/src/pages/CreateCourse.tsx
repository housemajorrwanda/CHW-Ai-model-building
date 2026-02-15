import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { coursesAPI } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Plus, Trash2, Loader2, ArrowLeft } from 'lucide-react';
import { toast } from 'sonner';

interface Topic {
  name: string;
  description: string;
  order: number;
  subtopics: Subtopic[];
}

interface Subtopic {
  name: string;
  description: string;
  order: number;
}

export default function CreateCourse() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);
  const [courseName, setCourseName] = useState('');
  const [courseCode, setCourseCode] = useState('');
  const [description, setDescription] = useState('');
  const [level, setLevel] = useState('all_levels');
  const [topics, setTopics] = useState<Topic[]>([]);

  const handleAddTopic = () => {
    setTopics([
      ...topics,
      {
        name: '',
        description: '',
        order: topics.length,
        subtopics: []
      }
    ]);
  };

  const handleRemoveTopic = (index: number) => {
    setTopics(topics.filter((_, i) => i !== index));
  };

  const handleTopicChange = (index: number, field: keyof Topic, value: any) => {
    const newTopics = [...topics];
    newTopics[index] = { ...newTopics[index], [field]: value };
    setTopics(newTopics);
  };

  const handleAddSubtopic = (topicIndex: number) => {
    const newTopics = [...topics];
    newTopics[topicIndex].subtopics.push({
      name: '',
      description: '',
      order: newTopics[topicIndex].subtopics.length
    });
    setTopics(newTopics);
  };

  const handleRemoveSubtopic = (topicIndex: number, subtopicIndex: number) => {
    const newTopics = [...topics];
    newTopics[topicIndex].subtopics = newTopics[topicIndex].subtopics.filter((_, i) => i !== subtopicIndex);
    setTopics(newTopics);
  };

  const handleSubtopicChange = (topicIndex: number, subtopicIndex: number, field: keyof Subtopic, value: any) => {
    const newTopics = [...topics];
    newTopics[topicIndex].subtopics[subtopicIndex] = {
      ...newTopics[topicIndex].subtopics[subtopicIndex],
      [field]: value
    };
    setTopics(newTopics);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!courseName || !courseCode) {
      toast.error('Please fill in required fields');
      return;
    }

    try {
      setIsLoading(true);
      await coursesAPI.create({
        name: courseName,
        code: courseCode,
        description,
        level,
        topics: topics.map((topic, i) => ({
          ...topic,
          order: i,
          subtopics: topic.subtopics.map((sub, j) => ({
            ...sub,
            order: j
          }))
        }))
      });
      
      toast.success('Course created successfully!');
      navigate('/courses');
    } catch (error: any) {
      toast.error('Failed to create course: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/courses')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold">Create New Course</h1>
          <p className="text-muted-foreground mt-1">
            Set up a new course with topics and subtopics
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Basic Information</CardTitle>
            <CardDescription>
              Essential details about your course
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="courseName">
                  Course Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="courseName"
                  placeholder="e.g., Calculus I"
                  value={courseName}
                  onChange={(e) => setCourseName(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="courseCode">
                  Course Code <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="courseCode"
                  placeholder="e.g., MATH-101"
                  value={courseCode}
                  onChange={(e) => setCourseCode(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="level">Level</Label>
              <Select value={level} onValueChange={setLevel}>
                <SelectTrigger id="level">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all_levels">All Levels</SelectItem>
                  <SelectItem value="beginner">Beginner</SelectItem>
                  <SelectItem value="intermediate">Intermediate</SelectItem>
                  <SelectItem value="advanced">Advanced</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Course description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
              />
            </div>
          </CardContent>
        </Card>

        {/* Topics */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Course Topics</CardTitle>
                <CardDescription>
                  Organize your course content into topics and subtopics
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleAddTopic}
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Topic
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {topics.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No topics added yet</p>
                <p className="text-sm mt-1">Click "Add Topic" to get started</p>
              </div>
            ) : (
              topics.map((topic, topicIndex) => (
                <Card key={topicIndex}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">Topic {topicIndex + 1}</CardTitle>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => handleRemoveTopic(topicIndex)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <Label>Topic Name</Label>
                      <Input
                        placeholder="e.g., Limits and Continuity"
                        value={topic.name}
                        onChange={(e) => handleTopicChange(topicIndex, 'name', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Topic Description</Label>
                      <Textarea
                        placeholder="Topic description"
                        value={topic.description}
                        onChange={(e) => handleTopicChange(topicIndex, 'description', e.target.value)}
                        rows={2}
                      />
                    </div>

                    {/* Subtopics */}
                    <div className="space-y-3 mt-4">
                      <div className="flex items-center justify-between">
                        <Label className="text-sm font-medium">Subtopics</Label>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => handleAddSubtopic(topicIndex)}
                        >
                          <Plus className="h-3 w-3 mr-2" />
                          Add Subtopic
                        </Button>
                      </div>
                      
                      {topic.subtopics.map((subtopic, subtopicIndex) => (
                        <div key={subtopicIndex} className="flex gap-2 items-start p-3 bg-muted rounded-lg">
                          <div className="flex-1 space-y-2">
                            <Input
                              placeholder="Subtopic name"
                              value={subtopic.name}
                              onChange={(e) => handleSubtopicChange(topicIndex, subtopicIndex, 'name', e.target.value)}
                              className="bg-background"
                            />
                            <Input
                              placeholder="Subtopic description (optional)"
                              value={subtopic.description}
                              onChange={(e) => handleSubtopicChange(topicIndex, subtopicIndex, 'description', e.target.value)}
                              className="bg-background"
                            />
                          </div>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            onClick={() => handleRemoveSubtopic(topicIndex, subtopicIndex)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </CardContent>
        </Card>

        {/* Submit */}
        <div className="flex justify-end gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate('/courses')}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Course'
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}

