import { useCallback, useEffect, useRef, useState } from 'react'
import { useInView } from '../lib/useInView'

/*
 * The hero's centrepiece: the whole mechanic in one moving picture.
 *
 *   [ roster of 40 ] --coins--> [ pool fills ] --payout--> [ auditor gate ]
 *
 * A table of transactions says nothing you could not read in a spreadsheet.
 * This shows the three things that actually make the product different:
 * members pay without accounts, the money pools in the open, and nothing
 * leaves until a second person signs it off.
 *
 * Two layouts share all the drawing code. Wide runs left to right; narrow
 * runs top to bottom, because a 720-unit viewBox squeezed into a 390px phone
 * renders its labels at about six pixels.
 */

const COUNT = 40
const DUE = 5000
const EXPENSE = 150000

interface Box { x: number; y: number; w: number; h: number }
interface Layout {
  vbW: number
  vbH: number
  cols: number
  cell: number
  gap: number
  gridX: number
  gridY: number
  jar: Box
  gate: Box
  labels: { class: [number, number]; pool: [number, number]; gate: [number, number] }
  vertical: boolean
}

const WIDE: Layout = {
  vbW: 720, vbH: 500,
  cols: 5, cell: 40, gap: 6, gridX: 12, gridY: 56,
  jar: { x: 300, y: 120, w: 170, h: 310 },
  gate: { x: 536, y: 186, w: 172, h: 108 },
  labels: { class: [12, 30], pool: [300, 30], gate: [536, 30] },
  vertical: false,
}

const NARROW: Layout = {
  vbW: 380, vbH: 650,
  cols: 8, cell: 34, gap: 5, gridX: 36, gridY: 66,
  jar: { x: 125, y: 312, w: 130, h: 148 },
  gate: { x: 36, y: 556, w: 308, h: 76 },
  labels: { class: [36, 28], pool: [36, 276], gate: [36, 528] },
  vertical: true,
}

const naira = (n: number) => `₦${n.toLocaleString('en-NG')}`

interface Coin { id: number; from: number; t: number }
type Phase = 'idle' | 'collecting' | 'pooled' | 'spending' | 'done'

export default function CollectionFlow() {
  const { ref, inView } = useInView<HTMLDivElement>(0.2)
  const [narrow, setNarrow] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const sync = () => setNarrow(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  const L = narrow ? NARROW : WIDE
  const mouth = { x: L.jar.x + L.jar.w / 2, y: L.jar.y + 16 }
  const gateC = { x: L.gate.x + L.gate.w / 2, y: L.gate.y + L.gate.h / 2 }

  const cellX = (i: number) => L.gridX + (i % L.cols) * (L.cell + L.gap)
  const cellY = (i: number) => L.gridY + Math.floor(i / L.cols) * (L.cell + L.gap)

  const [paid, setPaid] = useState<boolean[]>(() => Array(COUNT).fill(false))
  const [coins, setCoins] = useState<Coin[]>([])
  const [phase, setPhase] = useState<Phase>('idle')
  const [payout, setPayout] = useState(0)
  const [spent, setSpent] = useState(false)

  const paidCount = paid.filter(Boolean).length
  const balance = paidCount * DUE - (spent ? EXPENSE : 0)
  const level = paidCount / COUNT

  const rafRef = useRef(0)
  const lastRef = useRef(0)
  const coinId = useRef(0)
  const spawnAcc = useRef(0)
  const queue = useRef<number[]>([])
  const reduced = useRef(false)

  useEffect(() => {
    reduced.current = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  const sendCoin = useCallback((index: number) => {
    setCoins((cs) => (cs.some((c) => c.from === index) ? cs : [...cs, { id: coinId.current++, from: index, t: 0 }]))
  }, [])

  const reset = useCallback(() => {
    setPaid(Array(COUNT).fill(false))
    setCoins([])
    setPayout(0)
    setSpent(false)
    queue.current = Array.from({ length: COUNT }, (_, i) => i).sort(() => Math.random() - 0.5)
    spawnAcc.current = 0
    setPhase('collecting')
  }, [])

  useEffect(() => {
    if (!inView || phase !== 'idle') return
    if (reduced.current) {
      setPaid(Array(COUNT).fill(true))
      setSpent(true)
      setPayout(1)
      setPhase('done')
      return
    }
    reset()
  }, [inView, phase, reset])

  useEffect(() => {
    if (phase === 'idle' || phase === 'done' || reduced.current) return

    const tick = (now: number) => {
      const dt = lastRef.current ? Math.min(now - lastRef.current, 48) : 16
      lastRef.current = now

      if (phase === 'collecting') {
        spawnAcc.current += dt
        while (spawnAcc.current > 95 && queue.current.length) {
          spawnAcc.current -= 95
          sendCoin(queue.current.shift()!)
        }
      }

      setCoins((cs) => {
        if (!cs.length) return cs
        const landed: number[] = []
        const next: Coin[] = []
        for (const c of cs) {
          const t = c.t + dt / 620
          if (t >= 1) landed.push(c.from)
          else next.push({ ...c, t })
        }
        if (landed.length) {
          setPaid((p) => {
            const copy = [...p]
            for (const i of landed) copy[i] = true
            return copy
          })
        }
        return next
      })

      if (phase === 'spending') setPayout((p) => Math.min(1, p + dt / 1500))

      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(rafRef.current)
      lastRef.current = 0
    }
  }, [phase, sendCoin])

  useEffect(() => {
    if (phase === 'collecting' && paidCount === COUNT && coins.length === 0) {
      const id = setTimeout(() => setPhase('pooled'), 500)
      return () => clearTimeout(id)
    }
    if (phase === 'pooled') {
      const id = setTimeout(() => setPhase('spending'), 900)
      return () => clearTimeout(id)
    }
    if (phase === 'spending' && payout >= 1) {
      setSpent(true)
      setPhase('done')
    }
  }, [phase, paidCount, coins.length, payout])

  useEffect(() => {
    const onVis = () => { if (document.hidden) cancelAnimationFrame(rafRef.current) }
    document.addEventListener('visibilitychange', onVis)
    return () => document.removeEventListener('visibilitychange', onVis)
  }, [])

  const fillY = L.jar.y + L.jar.h - L.jar.h * level * 0.92
  const stamped = payout > 0.55

  // payout: pool -> gate, then out of frame
  const payFrom = L.vertical
    ? { x: L.jar.x + L.jar.w / 2, y: L.jar.y + L.jar.h }
    : { x: L.jar.x + L.jar.w, y: gateC.y }
  const legT = Math.min(payout / 0.55, 1)
  const payPos = {
    x: payFrom.x + (gateC.x - payFrom.x) * legT,
    y: payFrom.y + (gateC.y - payFrom.y) * legT,
  }
  const payOut = payout > 0.55 ? (payout - 0.55) / 0.45 : 0

  const label = (
    at: [number, number],
    head: string,
    sub: string,
  ) => (
    <>
      <text x={at[0]} y={at[1]} className="fill-ink-500 font-mono text-[13px] uppercase tracking-[0.14em]">
        {head}
      </text>
      <text x={at[0]} y={at[1] + 16} className="fill-ink-400 font-mono text-[11px]">
        {sub}
      </text>
    </>
  )

  return (
    <div ref={ref} className="border-2 border-ink-900 bg-paper-0 shadow-neo-lg">
      <div className="flex items-center justify-between gap-3 border-b-2 border-ink-900 bg-ink-900 px-3 py-2.5 sm:px-4">
        <p className="truncate font-mono text-[10px] uppercase tracking-[0.16em] text-paper-100 sm:text-[11px] sm:tracking-[0.18em]">
          Stats 200 · Semester dues
        </p>
        <p className="flex shrink-0 items-center gap-2 font-mono text-[10px] uppercase tracking-[0.16em] text-teal-400 sm:text-[11px]">
          <span className="h-1.5 w-1.5 rounded-full bg-teal-400 animate-pulse-dot" />
          {phase === 'done' ? 'Settled' : 'Live'}
        </p>
      </div>

      <svg
        viewBox={`0 0 ${L.vbW} ${L.vbH}`}
        className="block w-full"
        role="img"
        aria-label={`Collection simulation. ${paidCount} of ${COUNT} members have paid, ${naira(
          paidCount * DUE,
        )} collected. ${spent ? 'One approved expense of ₦150,000 has been paid out.' : 'No money has left the pool yet.'}`}
      >
        {label(L.labels.class, 'Your class', `${paidCount}/${COUNT} paid · no accounts`)}
        {label(L.labels.pool, 'The pool', 'Everyone can see it')}
        {label(L.labels.gate, 'To spend', 'Auditor must sign')}

        {/* roster */}
        {Array.from({ length: COUNT }).map((_, i) => (
          <g
            key={i}
            onClick={() => phase !== 'idle' && !paid[i] && sendCoin(i)}
            className={!paid[i] && phase !== 'done' ? 'cursor-pointer' : ''}
          >
            <rect
              x={cellX(i)}
              y={cellY(i)}
              width={L.cell}
              height={L.cell}
              className={paid[i] ? 'fill-teal-400' : 'fill-paper-100'}
              stroke="#241E1F"
              strokeWidth={2}
            />
            {paid[i] && (
              <path
                d={`M${cellX(i) + L.cell * 0.28} ${cellY(i) + L.cell * 0.5} l${L.cell * 0.15} ${L.cell * 0.15} l${L.cell * 0.3} -${L.cell * 0.3}`}
                fill="none"
                stroke="#241E1F"
                strokeWidth={3}
                strokeLinecap="square"
              />
            )}
          </g>
        ))}

        {/* pool */}
        <clipPath id="jarClip">
          <rect x={L.jar.x + 3} y={L.jar.y + 3} width={L.jar.w - 6} height={L.jar.h - 6} />
        </clipPath>

        <rect {...L.jar} className="fill-paper-100" stroke="#241E1F" strokeWidth={3} />
        <g clipPath="url(#jarClip)">
          <rect
            x={L.jar.x}
            y={fillY}
            width={L.jar.w}
            height={L.jar.h}
            className="fill-rose-600"
            style={{ transition: 'y 420ms cubic-bezier(0.22,1,0.36,1)' }}
          />
          <rect
            x={L.jar.x}
            y={fillY}
            width={L.jar.w}
            height={5}
            className="fill-gold-400"
            style={{ transition: 'y 420ms cubic-bezier(0.22,1,0.36,1)' }}
          />
        </g>
        <rect x={L.jar.x - 10} y={L.jar.y - 12} width={L.jar.w + 20} height={16} className="fill-ink-900" />

        <text
          x={L.jar.x + L.jar.w / 2}
          y={L.jar.y + L.jar.h + 32}
          textAnchor="middle"
          className="fill-ink-900 font-display text-[24px]"
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          {naira(balance)}
        </text>

        {/* coins in flight */}
        {coins.map((c) => {
          const fx = cellX(c.from) + L.cell / 2
          const fy = cellY(c.from) + L.cell / 2
          // control point arcs the path: sideways when the flow runs down the
          // page, lifted when it runs across
          const cpx = L.vertical ? (fx + mouth.x) / 2 + 70 : (fx + mouth.x) / 2
          const cpy = L.vertical ? (fy + mouth.y) / 2 : Math.min(fy, mouth.y) - 90
          const u = 1 - c.t
          const x = u * u * fx + 2 * u * c.t * cpx + c.t * c.t * mouth.x
          const y = u * u * fy + 2 * u * c.t * cpy + c.t * c.t * mouth.y
          return <circle key={c.id} cx={x} cy={y} r={7} className="fill-gold-400" stroke="#241E1F" strokeWidth={2} />
        })}

        {/* auditor gate */}
        <rect
          {...L.gate}
          className={stamped ? 'fill-teal-400' : 'fill-paper-100'}
          stroke="#241E1F"
          strokeWidth={3}
          style={{ transition: 'fill 260ms steps(1)' }}
        />
        <text
          x={gateC.x}
          y={L.gate.y + (L.vertical ? 30 : 42)}
          textAnchor="middle"
          className="fill-ink-900 font-mono text-[12px] uppercase tracking-[0.14em]"
        >
          Auditor
        </text>
        <text
          x={gateC.x}
          y={L.gate.y + (L.vertical ? 58 : 72)}
          textAnchor="middle"
          className="fill-ink-900 font-display text-[19px] uppercase"
        >
          {stamped ? 'Approved' : 'Waiting'}
        </text>

        {/* the payout in transit */}
        {phase !== 'idle' && payout > 0 && payout < 1 && (
          <g style={{ opacity: payOut > 0.85 ? 0 : 1 }}>
            <rect
              x={payPos.x - 46}
              y={payPos.y - 15}
              width={92}
              height={30}
              className="fill-rose-600"
              stroke="#241E1F"
              strokeWidth={2}
            />
            <text
              x={payPos.x}
              y={payPos.y + 5}
              textAnchor="middle"
              className="fill-white font-mono text-[12px] font-bold"
              style={{ fontVariantNumeric: 'tabular-nums' }}
            >
              {naira(EXPENSE)}
            </text>
          </g>
        )}
      </svg>

      <div className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-ink-900 bg-gold-400 px-3 py-2.5 sm:px-4 sm:py-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-ink-900 sm:text-[11px] sm:tracking-[0.14em]">
          {phase === 'collecting' && 'Members are paying'}
          {phase === 'pooled' && 'Collection closed'}
          {phase === 'spending' && 'Expense sent for approval'}
          {phase === 'done' && 'Approved and paid out'}
          {phase === 'idle' && 'Ready'}
        </p>

        <button
          onClick={reset}
          className="flex min-h-[44px] items-center border-2 border-ink-900 bg-paper-0 px-4 font-display text-[11px] uppercase text-ink-900 shadow-neo-sm transition-all duration-150 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-white active:translate-x-px active:translate-y-px active:shadow-none sm:text-[12px]"
        >
          Run it again
        </button>
      </div>
    </div>
  )
}
