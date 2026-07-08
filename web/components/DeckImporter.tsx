"use client";

import { useState } from "react";
import { parseDecklist } from "@/lib/decklist";
import type { ClassifyResponse } from "@/lib/types";

const SAMPLE = `4 Karn, the Great Creator
4 Expedition Map
4 Chromatic Star
2 Wurmcoil Engine
1 Ulamog, the Ceaseless Hunger
4 Urza's Tower
4 Urza's Mine
4 Urza's Power Plant
Sideboard
2 Boil
2 Karn Liberated`;

export function DeckImporter({ game, format }: { game: string; format: string }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ClassifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function analyze() {
    const cards = parseDecklist(text);
    if (cards.length === 0) {
      setError("Paste a decklist first.");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`/api/classify?game=${game}&format=${format}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cards }),
      });
      if (!res.ok) {
        setError(res.status === 422 ? "Couldn't read that list." : "Analysis failed.");
        return;
      }
      setResult((await res.json()) as ClassifyResponse);
    } catch {
      setError("Could not reach the analyzer.");
    } finally {
      setLoading(false);
    }
  }

  const methodLabel = (m: string) =>
    m === "rules" ? "exact rule match" : "closest archetype";

  return (
    <div>
      <textarea
        className="deckbox"
        placeholder={"Paste your decklist…\n\n4 Ragavan, Nimble Pilferer\n4 Lightning Bolt\n…\nSideboard\n2 Blood Moon"}
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={9}
      />
      <div className="deckbtns">
        <button className="btn primary" onClick={analyze} disabled={loading}>
          {loading ? "Analyzing…" : "Analyze deck"}
        </button>
        <button
          className="btn"
          onClick={() => {
            setText(SAMPLE);
            setResult(null);
            setError(null);
          }}
        >
          Try a sample
        </button>
      </div>

      {error && <div className="error" style={{ marginTop: 14 }}>{error}</div>}

      {result && (
        <div className="result">
          <div className="result-lead">Your deck is</div>
          <div className="result-arch">{result.name}</div>
          <div className="result-meta">
            {methodLabel(result.method)}
            {result.confidence != null && result.method !== "rules" && (
              <> · {Math.round(result.confidence * 100)}% match</>
            )}
          </div>

          {result.archetype_id != null && (
            <a
              className="btn primary wide"
              href={`/${game}/${format}/matchups/${result.archetype_id}`}
            >
              See {result.name}&apos;s matchups ›
            </a>
          )}

          {result.unresolved_cards.length > 0 && (
            <div className="unresolved">
              <b>{result.unresolved_cards.length} card(s) not recognised</b> — check
              the spelling; they were ignored, never guessed:
              <span> {result.unresolved_cards.join(", ")}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
