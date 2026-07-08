"use client";

import { useState } from "react";
import type { CardLine } from "@/lib/decklist";
import { toArena, toMtgo, toPlain, tcgplayerUrl } from "@/lib/export";

export function ExportBar({ cards }: { cards: CardLine[] }) {
  const [copied, setCopied] = useState<string | null>(null);

  async function copy(fmt: string, text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(fmt);
      setTimeout(() => setCopied((c) => (c === fmt ? null : c)), 1500);
    } catch {
      setCopied("err");
    }
  }

  return (
    <div className="export">
      <div className="export-lbl">Export</div>
      <div className="export-btns">
        <button
          className="btn sm primary"
          onClick={() => copy("LIST", toPlain(cards))}
        >
          {copied === "LIST" ? "Copied ✓" : "Copy list"}
        </button>
        <button className="btn sm" onClick={() => copy("MTGA", toArena(cards))}>
          {copied === "MTGA" ? "Copied ✓" : "MTGA"}
        </button>
        <button className="btn sm" onClick={() => copy("MTGO", toMtgo(cards))}>
          {copied === "MTGO" ? "Copied ✓" : "MTGO"}
        </button>
        <a
          className="btn sm"
          href={tcgplayerUrl(cards)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Buy on TCGplayer ↗
        </a>
      </div>
    </div>
  );
}
