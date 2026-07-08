import { KNOWN_FORMATS } from "@/lib/api";

export function Nav({
  game,
  format,
  section,
  asOf,
}: {
  game: string;
  format: string;
  section: "meta" | "matchups" | "deck";
  asOf?: string;
}) {
  const suffix =
    section === "matchups" ? "/matchups" : section === "deck" ? "/deck" : "";
  return (
    <>
      <header className="app">
        <div className="brand">
          Meta<span>Surf</span>
        </div>
        {asOf && <div className="subhead">as of {asOf}</div>}
      </header>

      <nav className="tabs">
        {KNOWN_FORMATS.map((f) => {
          const active = f.game === game && f.format === format;
          return (
            <a
              key={`${f.game}/${f.format}`}
              className={active ? "tab active" : "tab"}
              href={`/${f.game}/${f.format}${suffix}`}
            >
              {f.label}
            </a>
          );
        })}
      </nav>

      <nav className="sections">
        <a
          className={section === "meta" ? "section active" : "section"}
          href={`/${game}/${format}`}
        >
          Meta
        </a>
        <a
          className={section === "matchups" ? "section active" : "section"}
          href={`/${game}/${format}/matchups`}
        >
          Matchups
        </a>
        <a
          className={section === "deck" ? "section active" : "section"}
          href={`/${game}/${format}/deck`}
        >
          Your deck
        </a>
      </nav>
    </>
  );
}
