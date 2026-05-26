import Link from "next/link";
import { Music4 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { LibraryView } from "@/components/library/library-view";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Track Library</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every track and reference clip stored under the audio prefix in B2 —
            cross-project, with inline playback, download, and delete.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/projects">
            <Music4 className="h-3.5 w-3.5" />
            Go to projects
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryView />
      </div>
    </div>
  );
}
