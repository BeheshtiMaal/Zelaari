"use client";
import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { dictionary } from "../../i18n";
import { useSession } from "../../lib/use-session";
import { WorkspaceScreen } from "../../components/workspace/workspace-screen";

function WorkspaceRoute() {
  // The workspace is a query parameter so the static export keeps working: every
  // workspace renders the same document.
  const path = useSearchParams().get("path") ?? "";
  const session = useSession();
  return <WorkspaceScreen t={dictionary(session.locale)} session={session} root={path} />;
}

export default function WorkspacePage() {
  return <Suspense fallback={null}><WorkspaceRoute /></Suspense>;
}
