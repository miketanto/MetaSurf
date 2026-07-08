import { redirect } from "next/navigation";

export default function Home() {
  // default landing: Modern meta snapshot
  redirect("/mtg/modern");
}
