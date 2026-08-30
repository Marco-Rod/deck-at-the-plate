export interface RoutePlaceholderProps {
  title: string
  description?: string
}

export function RoutePlaceholder({ title, description }: RoutePlaceholderProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-koshien-dark px-4">
      <section className="w-full max-w-md rounded-lg border border-koshien-border bg-koshien-green p-8 text-center shadow-scoreboard">
        <h1 className="font-sports text-4xl uppercase tracking-wider text-koshien-gold">{title}</h1>
        {description ? (
          <p className="mt-3 font-vintage text-sm text-koshien-cream">{description}</p>
        ) : null}
      </section>
    </main>
  )
}
