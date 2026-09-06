import './CardDesignsPage.css'

type Design = {
  rarity: string
  tone: string
  position: string
  number: string
  name: string
  team: string
  stats: Array<[string, number]>
}

const designs: Design[] = [
  { rarity: 'Normal', tone: 'normal', position: 'SP', number: '17', name: 'Adrian Vega', team: 'Riverdale', stats: [['VEL', 78], ['CTL', 72], ['STA', 75]] },
  { rarity: 'Bronce', tone: 'bronze', position: 'LF', number: '24', name: 'Marcus Rivera', team: 'Canyon City', stats: [['POW', 76], ['CON', 79], ['SPD', 82]] },
  { rarity: 'Plata', tone: 'silver', position: 'C', number: '8', name: 'Elias Torres', team: 'Northridge', stats: [['POW', 83], ['CON', 85], ['DEF', 80]] },
  { rarity: 'Oro', tone: 'gold', position: '2B', number: '11', name: 'Javier Cruz', team: 'Pinecrest', stats: [['POW', 87], ['CON', 84], ['SPD', 88]] },
  { rarity: 'Esmeralda', tone: 'emerald', position: 'RP', number: '35', name: 'Daniel Mora', team: 'Highland', stats: [['VEL', 91], ['CTL', 89], ['STA', 86]] },
  { rarity: 'Diamante', tone: 'diamond', position: 'CF', number: '3', name: 'Leo Santos', team: 'Bayview', stats: [['POW', 92], ['CON', 90], ['SPD', 94]] },
  { rarity: 'Especial', tone: 'special', position: 'SP', number: '27', name: 'Nico Ramirez', team: 'Redstone', stats: [['VEL', 88], ['CTL', 85], ['STA', 82]] },
]

function BaseballSeams() {
  return (
    <svg className="dc-card__seams" viewBox="0 0 100 310" aria-hidden="true">
      <path d="M88 -10 C28 65, 25 225, 91 320" />
      {Array.from({ length: 13 }, (_, index) => {
        const y = 20 + index * 22
        const x = 65 - Math.abs(155 - y) * 0.12
        return <path key={y} d={`M${x - 7} ${y - 5} L${x + 5} ${y + 5} M${x - 5} ${y + 6} L${x + 7} ${y - 4}`} />
      })}
    </svg>
  )
}

function DesignCard({ design, index }: { design: Design; index: number }) {
  return (
    <article className={`dc-card dc-card--${design.tone}`} style={{ '--delay': `${index * -0.65}s` } as React.CSSProperties}>
      <div className="dc-card__edge" />
      <div className="dc-card__face">
        <div className="dc-card__grain" />
        <div className="dc-card__geometry" />
        <BaseballSeams />
        <div className="dc-card__header">
          <span className="dc-card__position">{design.position}</span>
          <span className="dc-card__micro">D · P</span>
        </div>
        <div className="dc-card__number" data-number={design.number}>{design.number}</div>
        <div className="dc-card__identity">
          <h2>{design.name}</h2>
          <p>{design.team}</p>
        </div>
        <dl className="dc-card__stats">
          {design.stats.map(([label, value]) => (
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
          ))}
        </dl>
        <span className="dc-card__serial">DATP · {String(index + 1).padStart(3, '0')}</span>
      </div>
      <div className="dc-card__shine" />
    </article>
  )
}

export function CardDesignsPage() {
  return (
    <main className="dc-page">
      <div className="dc-page__atmosphere" aria-hidden="true" />
      <header className="dc-hero">
        <div className="dc-brand"><span>Deck</span> at the <strong>Plate</strong></div>
        <div className="dc-hero__rule" />
        <div>
          <p className="dc-eyebrow">Laboratorio de diseño · CSS + SVG</p>
          <h1>Mismos jugadores. <em>Otra liga.</em></h1>
          <p className="dc-intro">Exploración visual de marcos, materiales y personalidad por rareza.</p>
        </div>
      </header>

      <section className="dc-grid" aria-label="Diseños de cartas por rareza">
        {designs.map((design, index) => (
          <div className="dc-design" key={design.tone}>
            <DesignCard design={design} index={index} />
            <h3>{design.rarity}</h3>
            <span className="dc-design__swatches" aria-hidden="true"><i /><i /><i /></span>
          </div>
        ))}
      </section>

      <footer className="dc-footer"><span /> Más que cartas. Un juego más grande. <span /></footer>
    </main>
  )
}
