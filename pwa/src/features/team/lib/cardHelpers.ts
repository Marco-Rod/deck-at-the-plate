/**
 * Utilidades para selección y búsqueda de cartas de jugador
 */

/**
 * Encuentra la mejor carta según un predicado, ordenada por OVR descendente
 * @generic T - Tipo de carta (PlayerCard, etc)
 * @param items - Lista de items con propiedad `card` tipada
 * @param predicate - Función que retorna true para cartas válidas
 * @returns La mejor carta que cumple el predicado, o undefined
 */
export function bestCardFor<T extends { overall: number }>(
  items: { card: T }[],
  predicate: (c: T) => boolean,
): T | undefined {
  return items
    .map((i) => i.card)
    .filter(predicate)
    .sort((a, b) => b.overall - a.overall)[0]
}

/**
 * Encuentra una carta por ID
 * @param list - Lista de items con propiedad `card`
 * @param id - ID de la carta a buscar
 * @returns La carta encontrada, o undefined
 */
export function findCard<T extends { id: string }>(
  list: { card: T }[],
  id?: string,
): T | undefined {
  if (!id) return undefined
  return list.find((i) => i.card.id === id)?.card
}

/**
 * Encuentra el primer spot libre en el lineup
 * @param lineup - Objeto con posiciones asignadas (ej: { "1": "card_123", "2": "card_456" })
 * @param spots - Array de spots disponibles (ej: ["1", "2", "3", ..., "9"])
 * @returns El primer spot sin asignar, o undefined si todos están ocupados
 */
export function findFreeSpot(
  lineup: Record<string, string>,
  spots: string[],
): string | undefined {
  return spots.find((s) => !lineup[s])
}
