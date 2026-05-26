import { ProjectDetail } from "@/components/projects/project-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProjectDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <ProjectDetail projectId={id} />;
}
