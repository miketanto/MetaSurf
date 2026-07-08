export function ArchetypeTabs({
  game,
  format,
  id,
  active,
}: {
  game: string;
  format: string;
  id: number;
  active: "overview" | "decks" | "matchups";
}) {
  const base = `/${game}/${format}/archetypes/${id}`;
  const cls = (k: string) => (active === k ? "section active" : "section");
  return (
    <nav className="sections">
      <a className={cls("overview")} href={base}>
        Overview
      </a>
      <a className={cls("decks")} href={`${base}/decks`}>
        Decks
      </a>
      <a className={cls("matchups")} href={`${base}/matchups`}>
        Matchups
      </a>
    </nav>
  );
}
