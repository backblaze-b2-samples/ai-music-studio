import { FileBrowser } from "@/components/files/file-browser";

export default function FilesPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Files</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Full-bucket explorer — every object in your B2 bucket. For the
          project-scoped view, open a project and switch to the Project Files
          tab.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <FileBrowser />
      </div>
    </div>
  );
}
