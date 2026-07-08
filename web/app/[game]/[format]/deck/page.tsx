import { Nav } from "@/components/Nav";
import { DeckImporter } from "@/components/DeckImporter";

export const dynamic = "force-dynamic";

export default function DeckPage({
  params,
}: {
  params: { game: string; format: string };
}) {
  const { game, format } = params;
  return (
    <main className="container">
      <Nav game={game} format={format} section="deck" />
      <p className="subhead">
        Paste your list — we&apos;ll name the archetype and pull its matchups.
      </p>
      <DeckImporter game={game} format={format} />
      <p className="foot">
        Card names resolve against the full catalogue; anything unrecognised is
        reported, never guessed. Classification uses the same rules as the data
        pipeline.
      </p>
    </main>
  );
}
