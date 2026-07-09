import { Nav } from "@/components/Nav";
import { ArchetypeTabs } from "@/components/ArchetypeTabs";
import { DecksBrowser } from "@/components/DecksBrowser";
import { ColorPips } from "@/components/ColorPips";
import { getArchetypeDecks, ApiError } from "@/lib/api";
import type { DecksResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function ArchetypeDecksPage({
  params,
}: {
  params: { game: string; format: string; id: string };
}) {
  const { game, format } = params;
  const id = Number(params.id);

  let res: DecksResponse | null = null;
  let error: string | null = null;
  try {
    res = await getArchetypeDecks(game, format, id, 100);
  } catch (e) {
    error = e instanceof ApiError && e.status === 404 ? "Unknown archetype." : "Could not reach the API.";
  }

  return (
    <main className="container">
      <Nav game={game} format={format} section="meta" />
      <a className="back" href={`/${game}/${format}`}>
        ‹ Meta
      </a>
      {error || !res ? (
        <div className="error">
          <strong>{error ?? "Not found."}</strong>
        </div>
      ) : (
        <>
          <div className="titlerow">
            <h1 className="deck-title">{res.name}</h1>
            <ColorPips colors={res.colors} />
          </div>
          <ArchetypeTabs game={game} format={format} id={id} active="decks" />
          <DecksBrowser decks={res.decks} game={game} format={format} />
        </>
      )}
    </main>
  );
}
