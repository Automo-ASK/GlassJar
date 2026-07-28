export interface Box {
  x: number
  y: number
  w: number
  h: number
}

/**
 * The jar silhouette, shared by the hero simulation and the loading state so
 * both read as the same object: a narrow neck, sloped shoulders, straight
 * sides and a softly rounded base.
 *
 * `y` is the top of the neck, not the top of the lid. The lid is drawn
 * separately by the caller so it can sit above or be omitted.
 */
export function jarPath({ x, y, w, h }: Box): string {
  const neck = w * 0.15 // how far each side of the neck is inset
  const neckH = h * 0.09 // straight run before the shoulders flare
  const shoulderY = y + h * 0.2
  const r = Math.min(w, h) * 0.12 // base corner radius

  return [
    `M ${x + neck} ${y}`,
    `L ${x + w - neck} ${y}`,
    `L ${x + w - neck} ${y + neckH}`,
    // shoulder flaring out to the full body width
    `C ${x + w - neck} ${shoulderY}, ${x + w} ${shoulderY - h * 0.04}, ${x + w} ${shoulderY + h * 0.02}`,
    `L ${x + w} ${y + h - r}`,
    `Q ${x + w} ${y + h}, ${x + w - r} ${y + h}`,
    `L ${x + r} ${y + h}`,
    `Q ${x} ${y + h}, ${x} ${y + h - r}`,
    `L ${x} ${shoulderY + h * 0.02}`,
    `C ${x} ${shoulderY - h * 0.04}, ${x + neck} ${shoulderY}, ${x + neck} ${y + neckH}`,
    'Z',
  ].join(' ')
}

/** The lid: a squat rounded bar that overhangs the neck on both sides. */
export function lidBox({ x, y, w, h }: Box): Box & { r: number } {
  const overhang = w * 0.06
  const lidH = Math.max(10, h * 0.075)
  return {
    // overlap the neck by a couple of units so the lid reads as seated on the
    // jar rather than floating above it
    x: x + w * 0.15 - overhang,
    y: y - lidH + 2,
    w: w * 0.7 + overhang * 2,
    h: lidH,
    r: Math.min(4, lidH / 3),
  }
}

/** A glass highlight running down the inside of the left wall. */
export function shinePath({ x, y, w, h }: Box): string {
  const sx = x + w * 0.15
  const top = y + h * 0.26
  const bottom = y + h * 0.82
  return `M ${sx} ${top} L ${sx} ${bottom}`
}
