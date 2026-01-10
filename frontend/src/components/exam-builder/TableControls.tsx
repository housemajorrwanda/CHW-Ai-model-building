import { Button } from '@/components/ui/button';
import { Plus, Trash2, Columns, Rows } from 'lucide-react';
import type { Editor } from '@tiptap/react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface TableControlsProps {
  editor: Editor;
}

export function TableControls({ editor }: TableControlsProps) {
  if (!editor.can().addRowBefore()) return null;

  return (
    <div className="flex items-center gap-1 border rounded p-1 bg-background">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-7 px-2">
            <Rows className="h-3 w-3 mr-1" />
            Row
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().addRowBefore().run()}
          >
            <Plus className="h-3 w-3 mr-2" />
            Add Row Above
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().addRowAfter().run()}
          >
            <Plus className="h-3 w-3 mr-2" />
            Add Row Below
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().deleteRow().run()}
            className="text-destructive"
          >
            <Trash2 className="h-3 w-3 mr-2" />
            Delete Row
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm" className="h-7 px-2">
            <Columns className="h-3 w-3 mr-1" />
            Column
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().addColumnBefore().run()}
          >
            <Plus className="h-3 w-3 mr-2" />
            Add Column Left
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().addColumnAfter().run()}
          >
            <Plus className="h-3 w-3 mr-2" />
            Add Column Right
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => editor.chain().focus().deleteColumn().run()}
            className="text-destructive"
          >
            <Trash2 className="h-3 w-3 mr-2" />
            Delete Column
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-destructive"
        onClick={() => editor.chain().focus().deleteTable().run()}
      >
        <Trash2 className="h-3 w-3 mr-1" />
        Delete Table
      </Button>
    </div>
  );
}

