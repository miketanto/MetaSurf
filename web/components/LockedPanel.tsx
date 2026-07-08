// The plan's design principle (§8): every free screen showcases a locked
// premium widget *in context* — tease, don't hide. On S1 that tease is the
// trend/history layer the free snapshot doesn't include.

export function LockedPanel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="locked">
      <span className="lock-badge">🔒 Premium</span>
      <h3>{title}</h3>
      <p>{children}</p>
      <div className="blur" aria-hidden="true" />
    </div>
  );
}
