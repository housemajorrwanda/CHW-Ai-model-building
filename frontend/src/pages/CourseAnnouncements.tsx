import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { useAuth } from '@/contexts/AuthContext';
import { api, type AnnouncementReactionKind, type CourseAnnouncement } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import {
  ArrowLeft,
  Heart,
  MessageCircle,
  Lightbulb,
  CircleCheck,
  Megaphone,
  Loader2,
  MoreHorizontal,
  Pencil,
  Trash2,
  Pin,
  Send,
} from 'lucide-react';

function ReactionChip({
  active,
  count,
  icon: Icon,
  label,
  onClick,
  disabled,
}: {
  active: boolean;
  count: number;
  icon: typeof Heart;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          disabled={disabled}
          onClick={onClick}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-all',
            active
              ? 'border-primary/40 bg-primary/12 text-primary shadow-sm'
              : 'border-transparent bg-muted/50 text-muted-foreground hover:bg-muted hover:text-foreground',
            disabled && 'pointer-events-none opacity-50'
          )}
        >
          <Icon className={cn('h-3.5 w-3.5', active && 'scale-105')} aria-hidden />
          <span className="tabular-nums">{count}</span>
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-[220px] text-center">
        {label}
      </TooltipContent>
    </Tooltip>
  );
}

export default function CourseAnnouncements() {
  const { courseId } = useParams<{ courseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();

  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newPinned, setNewPinned] = useState(false);
  const [commentText, setCommentText] = useState<Record<string, string>>({});
  const [editOpen, setEditOpen] = useState(false);
  const [editAnn, setEditAnn] = useState<CourseAnnouncement | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editPinned, setEditPinned] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data: course, isLoading: courseLoading } = useQuery({
    queryKey: ['course', courseId],
    queryFn: () => api.courses.getById(courseId!) as Promise<{
      id: string;
      name: string;
      code: string;
      professorId: string;
      professorName?: string;
    }>,
    enabled: !!courseId,
  });

  const {
    data: announcements = [],
    isLoading: annLoading,
    isError: annError,
    error: annErr,
  } = useQuery({
    queryKey: ['announcements', courseId],
    queryFn: () => api.announcements.list(courseId!),
    enabled: !!courseId,
    retry: false,
  });

  const canPost = useMemo(() => {
    if (!user || !course) return false;
    if (user.role === 'admin') return true;
    if (user.role === 'professor' && course.professorId === user.id) return true;
    return false;
  }, [user, course]);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['announcements', courseId] });
  };

  const createMut = useMutation({
    mutationFn: () =>
      api.announcements.create(courseId!, {
        title: newTitle.trim(),
        body: newBody.trim(),
        pinned: newPinned,
      }),
    onSuccess: () => {
      setNewTitle('');
      setNewBody('');
      setNewPinned(false);
      invalidate();
      toast.success('Announcement posted');
    },
    onError: (e: Error) => toast.error(e.message || 'Could not post'),
  });

  const updateMut = useMutation({
    mutationFn: () =>
      api.announcements.update(courseId!, editAnn!.id, {
        title: editTitle.trim(),
        body: editBody.trim(),
        pinned: editPinned,
      }),
    onSuccess: () => {
      setEditOpen(false);
      setEditAnn(null);
      invalidate();
      toast.success('Saved');
    },
    onError: (e: Error) => toast.error(e.message || 'Could not save'),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => api.announcements.remove(courseId!, id),
    onSuccess: () => {
      setDeleteId(null);
      invalidate();
      toast.success('Removed');
    },
    onError: (e: Error) => toast.error(e.message || 'Could not delete'),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, kind }: { id: string; kind: AnnouncementReactionKind }) =>
      api.announcements.toggleReaction(courseId!, id, kind),
    onSuccess: () => invalidate(),
    onError: (e: Error) => toast.error(e.message || 'Could not update reaction'),
  });

  const commentMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      api.announcements.addComment(courseId!, id, body),
    onSuccess: (_, v) => {
      setCommentText((prev) => ({ ...prev, [v.id]: '' }));
      invalidate();
      toast.success('Comment added');
    },
    onError: (e: Error) => toast.error(e.message || 'Could not comment'),
  });

  const delCommentMut = useMutation({
    mutationFn: ({ annId, commentId }: { annId: string; commentId: string }) =>
      api.announcements.deleteComment(courseId!, annId, commentId),
    onSuccess: () => {
      invalidate();
      toast.success('Comment removed');
    },
    onError: (e: Error) => toast.error(e.message || 'Could not remove'),
  });

  const openEdit = (a: CourseAnnouncement) => {
    setEditAnn(a);
    setEditTitle(a.title);
    setEditBody(a.body);
    setEditPinned(a.pinned);
    setEditOpen(true);
  };

  if (!courseId) {
    return null;
  }

  if (courseLoading) {
    return (
      <div className="flex min-h-[320px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center">
        <p className="text-muted-foreground">Course not found.</p>
        <Button className="mt-4" variant="outline" onClick={() => navigate(-1)}>
          Go back
        </Button>
      </div>
    );
  }

  const backHref =
    user?.role === 'student' ? '/announcements' : `/courses/${courseId}`;

  return (
    <div className="mx-auto max-w-3xl space-y-8 pb-12">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" className="mt-0.5 shrink-0" asChild>
            <Link to={backHref} aria-label="Back">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Announcements</h1>
              <Badge variant="secondary" className="rounded-full font-mono text-[10px] uppercase">
                {course.code}
              </Badge>
            </div>
            <p className="mt-1 text-muted-foreground">{course.name}</p>
            {course.professorName && (
              <p className="text-sm text-muted-foreground/90">Instructor · {course.professorName}</p>
            )}
          </div>
        </div>
        <Button variant="outline" size="sm" className="shrink-0 rounded-full" asChild>
          <Link to="/announcements">All courses</Link>
        </Button>
      </div>

      {/* Composer */}
      {canPost && (
        <Card className="overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-b from-primary/[0.06] to-card shadow-sm">
          <CardContent className="space-y-4 p-5 sm:p-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <Megaphone className="h-4 w-4 text-primary" aria-hidden />
              New announcement
            </div>
            <Input
              placeholder="Title — keep it short and clear"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="h-11 rounded-xl border-border/80 bg-background/80"
            />
            <Textarea
              placeholder="What should students know? Dates, resources, expectations…"
              value={newBody}
              onChange={(e) => setNewBody(e.target.value)}
              rows={5}
              className="min-h-[120px] resize-y rounded-xl border-border/80 bg-background/80"
            />
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <Switch id="pin-new" checked={newPinned} onCheckedChange={setNewPinned} />
                <Label htmlFor="pin-new" className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
                  <Pin className="h-3.5 w-3.5" aria-hidden />
                  Pin to top of the feed
                </Label>
              </div>
              <Button
                className="rounded-xl"
                disabled={!newTitle.trim() || !newBody.trim() || createMut.isPending}
                onClick={() => createMut.mutate()}
              >
                {createMut.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Publish
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Feed */}
      {annError && (
        <Card className="rounded-2xl border-destructive/30 bg-destructive/5">
          <CardContent className="p-6 text-center">
            <p className="font-medium text-destructive">
              {(annErr as Error)?.message || 'You cannot view this board.'}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              Students need an approved enrollment. Instructors must own the course.
            </p>
            <Button asChild className="mt-4 rounded-xl" variant="outline">
              <Link to="/announcements">Back to hub</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {!annError && annLoading && (
        <div className="flex justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {!annError && !annLoading && announcements.length === 0 && (
        <Card className="rounded-2xl border-dashed">
          <CardContent className="flex flex-col items-center py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-muted">
              <MessageCircle className="h-7 w-7 text-muted-foreground" aria-hidden />
            </div>
            <p className="text-lg font-semibold">Quiet for now</p>
            <p className="mt-2 max-w-sm text-sm text-muted-foreground">
              {canPost
                ? 'Post your first update above — students will get an in-app notification.'
                : 'Your instructor has not posted anything yet. Check back later.'}
            </p>
          </CardContent>
        </Card>
      )}

      {!annError && !annLoading && announcements.length > 0 && (
        <div className="space-y-5">
          {announcements.map((a) => (
            <article
              key={a.id}
              className={cn(
                'overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:shadow-md',
                a.pinned && 'border-amber-300/60 ring-1 ring-amber-400/20 dark:border-amber-800/50'
              )}
            >
              <div className="border-b border-border/50 bg-muted/15 px-5 py-4 sm:px-6">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      {a.pinned && (
                        <Badge className="rounded-full bg-amber-500/90 text-[10px] font-semibold uppercase tracking-wide text-white hover:bg-amber-500">
                          <Pin className="mr-1 h-3 w-3" aria-hidden />
                          Pinned
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(a.createdAt), { addSuffix: true })}
                      </span>
                    </div>
                    <h2 className="text-lg font-semibold leading-snug sm:text-xl">{a.title}</h2>
                    <p className="text-sm text-muted-foreground">{a.authorName}</p>
                  </div>
                  {canPost && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 rounded-full">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">Announcement actions</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-44">
                        <DropdownMenuItem onClick={() => openEdit(a)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeleteId(a.id)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </div>

              <div className="space-y-5 px-5 py-5 sm:px-6">
                <div className="whitespace-pre-wrap text-[0.95rem] leading-relaxed text-foreground/95">
                  {a.body}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <ReactionChip
                    active={a.myLiked}
                    count={a.likeCount}
                    icon={Heart}
                    label="Like — thanks, this helped"
                    disabled={toggleMut.isPending}
                    onClick={() => toggleMut.mutate({ id: a.id, kind: 'like' })}
                  />
                  <ReactionChip
                    active={a.myImprove}
                    count={a.improveCount}
                    icon={Lightbulb}
                    label="Improve — I would like a bit more detail or clarification"
                    disabled={toggleMut.isPending}
                    onClick={() => toggleMut.mutate({ id: a.id, kind: 'improve' })}
                  />
                  <ReactionChip
                    active={a.myImplement}
                    count={a.implementCount}
                    icon={CircleCheck}
                    label="Implemented — I have applied or completed this"
                    disabled={toggleMut.isPending}
                    onClick={() => toggleMut.mutate({ id: a.id, kind: 'implement' })}
                  />
                </div>

                <Separator />

                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    <MessageCircle className="h-4 w-4" aria-hidden />
                    Comments ({a.commentCount})
                  </div>
                  <ul className="max-h-64 space-y-3 overflow-y-auto pr-1">
                    {a.comments.map((c) => (
                      <li
                        key={c.id}
                        className="rounded-xl border border-border/40 bg-muted/20 px-3 py-2.5 text-sm"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-medium text-foreground">{c.authorName}</span>
                            <span className="ml-2 text-xs text-muted-foreground">
                              {formatDistanceToNow(new Date(c.createdAt), { addSuffix: true })}
                            </span>
                          </div>
                          {(user?.id === c.authorId || canPost) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 shrink-0 px-2 text-xs text-muted-foreground hover:text-destructive"
                              disabled={delCommentMut.isPending}
                              onClick={() =>
                                delCommentMut.mutate({ annId: a.id, commentId: c.id })
                              }
                            >
                              Remove
                            </Button>
                          )}
                        </div>
                        <p className="mt-1.5 whitespace-pre-wrap leading-relaxed text-foreground/90">
                          {c.body}
                        </p>
                      </li>
                    ))}
                  </ul>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Textarea
                      placeholder="Write a reply…"
                      rows={2}
                      value={commentText[a.id] ?? ''}
                      onChange={(e) =>
                        setCommentText((prev) => ({ ...prev, [a.id]: e.target.value }))
                      }
                      className="min-h-[72px] flex-1 resize-none rounded-xl sm:min-h-0"
                    />
                    <Button
                      className="h-auto shrink-0 rounded-xl sm:self-end"
                      disabled={!(commentText[a.id] || '').trim() || commentMut.isPending}
                      onClick={() => {
                        const t = (commentText[a.id] || '').trim();
                        if (t) commentMut.mutate({ id: a.id, body: t });
                      }}
                    >
                      {commentMut.isPending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <>
                          <Send className="mr-2 h-4 w-4" />
                          Send
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <Dialog open={editOpen} onOpenChange={(o) => !o && setEditOpen(false)}>
        <DialogContent className="max-w-lg rounded-2xl">
          <DialogHeader>
            <DialogTitle>Edit announcement</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <Input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="rounded-xl"
            />
            <Textarea
              value={editBody}
              onChange={(e) => setEditBody(e.target.value)}
              rows={6}
              className="rounded-xl"
            />
            <div className="flex items-center gap-3">
              <Switch id="pin-edit" checked={editPinned} onCheckedChange={setEditPinned} />
              <Label htmlFor="pin-edit" className="text-sm text-muted-foreground">
                Pinned
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={!editTitle.trim() || !editBody.trim() || updateMut.isPending}
              onClick={() => updateMut.mutate()}
            >
              {updateMut.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteId} onOpenChange={(o) => !o && setDeleteId(null)}>
        <AlertDialogContent className="rounded-2xl">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this announcement?</AlertDialogTitle>
            <AlertDialogDescription>
              Students will no longer see it. Comments and reactions are removed as well.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-xl">Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="rounded-xl bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => deleteId && deleteMut.mutate(deleteId)}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
