import { redirect } from "next/navigation";

// The per-deck drilldown is now the archetype page — keep this path working.
export default function LegacyDrilldown({
  params,
}: {
  params: { game: string; format: string; arch: string };
}) {
  redirect(`/${params.game}/${params.format}/archetypes/${params.arch}`);
}
