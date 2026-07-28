import { jarPath, lidBox, shinePath, type Box } from './jar'

/*
 * Loading state: the brand mark filling up.
 *
 * The liquid is a full-height rect clipped to the jar silhouette and moved by
 * transform rather than by animating `y`, so it composites on the GPU and the
 * surface line stays welded to it.
 */

const BOX: Box = { x: 14, y: 20, w: 44, h: 58 }
const LID = lidBox(BOX)

export default function JarLoader({
  size = 72,
  label = 'Loading',
}: {
  size?: number
  label?: string
}) {
  return (
    <svg
      width={size}
      height={size * 1.15}
      viewBox="0 0 72 86"
      fill="none"
      role="img"
      aria-label={label}
    >
      <clipPath id="jarFillClip">
        <path d={jarPath(BOX)} />
      </clipPath>

      {/* glass body */}
      <path d={jarPath(BOX)} className="fill-paper-0" />

      {/* contents */}
      <g clipPath="url(#jarFillClip)">
        <g className="jar-liquid">
          <rect x={BOX.x} y={BOX.y} width={BOX.w} height={BOX.h} className="fill-rose-600" />
          <rect x={BOX.x} y={BOX.y} width={BOX.w} height={3} className="fill-gold-400" />
        </g>
      </g>

      {/* glass outline over the liquid */}
      <path d={jarPath(BOX)} fill="none" stroke="#241E1F" strokeWidth={3} strokeLinejoin="round" />

      {/* highlight */}
      <path
        d={shinePath(BOX)}
        stroke="#FFFFFF"
        strokeWidth={2.5}
        strokeLinecap="round"
        opacity={0.5}
      />

      {/* lid */}
      <rect
        x={LID.x}
        y={LID.y}
        width={LID.w}
        height={LID.h}
        rx={LID.r}
        className="fill-teal-400"
        stroke="#241E1F"
        strokeWidth={3}
      />

      {/* coins dropping in, timed to the fill */}
      <circle cx={36} cy={10} r={4} className="fill-gold-400 jar-coin" stroke="#241E1F" strokeWidth={2} />
      <circle
        cx={36}
        cy={10}
        r={4}
        className="fill-gold-400 jar-coin"
        stroke="#241E1F"
        strokeWidth={2}
        style={{ animationDelay: '-1.1s' }}
      />
    </svg>
  )
}
