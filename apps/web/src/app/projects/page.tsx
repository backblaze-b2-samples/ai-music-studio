import { ProjectsView } from "@/components/projects/projects-view";

export default function ProjectsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Projects</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Each project holds a prompt thread plus its full revision tree —
          stored as <code className="font-mono text-xs">projects/&lt;id&gt;/</code>{" "}
          in B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <ProjectsView />
      </div>
    </div>
  );
}
