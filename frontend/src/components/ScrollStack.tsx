import { useLayoutEffect, useRef, useCallback, type ReactNode } from 'react'
import Lenis from 'lenis'

/*
 * ScrollStack (React Bits) — cards pin at the top of the viewport and stack
 * behind one another as the page scrolls.
 *
 * Adapted from the reference JS implementation:
 *  - typed
 *  - defaults to window scroll (this page scrolls normally; an inner scroll
 *    container would trap the wheel)
 *  - honours prefers-reduced-motion by skipping Lenis and all transforms
 */

export const ScrollStackItem = ({
  children,
  itemClassName = '',
}: {
  children: ReactNode
  itemClassName?: string
}) => <div className={`scroll-stack-card ${itemClassName}`.trim()}>{children}</div>

interface Transform {
  translateY: number
  scale: number
  rotation: number
  blur: number
}

interface Props {
  children: ReactNode
  className?: string
  itemDistance?: number
  itemScale?: number
  itemStackDistance?: number
  stackPosition?: string
  scaleEndPosition?: string
  baseScale?: number
  scaleDuration?: number
  rotationAmount?: number
  blurAmount?: number
  useWindowScroll?: boolean
  onStackComplete?: () => void
}

const ScrollStack = ({
  children,
  className = '',
  itemDistance = 100,
  itemScale = 0.03,
  itemStackDistance = 30,
  stackPosition = '20%',
  scaleEndPosition = '10%',
  baseScale = 0.85,
  scaleDuration = 0.5,
  rotationAmount = 0,
  blurAmount = 0,
  useWindowScroll = true,
  onStackComplete,
}: Props) => {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const innerRef = useRef<HTMLDivElement>(null)
  const stackCompletedRef = useRef(false)
  const animationFrameRef = useRef<number | null>(null)
  const lenisRef = useRef<Lenis | null>(null)
  const cardsRef = useRef<HTMLElement[]>([])
  const lastTransformsRef = useRef(new Map<number, Transform>())
  const isUpdatingRef = useRef(false)

  const calculateProgress = useCallback((scrollTop: number, start: number, end: number) => {
    if (scrollTop < start) return 0
    if (scrollTop > end) return 1
    if (end === start) return 1
    return (scrollTop - start) / (end - start)
  }, [])

  const parsePercentage = useCallback((value: string | number, containerHeight: number) => {
    if (typeof value === 'string' && value.includes('%')) {
      return (parseFloat(value) / 100) * containerHeight
    }
    return parseFloat(String(value))
  }, [])

  const getScrollData = useCallback(() => {
    if (useWindowScroll) {
      return { scrollTop: window.scrollY, containerHeight: window.innerHeight }
    }
    const scroller = scrollerRef.current
    return {
      scrollTop: scroller?.scrollTop ?? 0,
      containerHeight: scroller?.clientHeight ?? 0,
    }
  }, [useWindowScroll])

  const getElementOffset = useCallback(
    (element: HTMLElement) => {
      // Must be a *layout* offset. getBoundingClientRect() reflects the
      // transform this component applies to the card, so measuring with it
      // feeds each frame's translateY back into the next frame's input and
      // the pin never settles. offsetTop is unaffected by transforms.
      if (useWindowScroll) {
        let top = 0
        let node: HTMLElement | null = element
        while (node) {
          top += node.offsetTop
          node = node.offsetParent as HTMLElement | null
        }
        return top
      }
      return element.offsetTop
    },
    [useWindowScroll],
  )

  const updateCardTransforms = useCallback(() => {
    if (!cardsRef.current.length || isUpdatingRef.current) return
    isUpdatingRef.current = true

    const { scrollTop, containerHeight } = getScrollData()
    const stackPositionPx = parsePercentage(stackPosition, containerHeight)
    const scaleEndPositionPx = parsePercentage(scaleEndPosition, containerHeight)

    const endElement = useWindowScroll
      ? document.querySelector<HTMLElement>('.scroll-stack-end')
      : scrollerRef.current?.querySelector<HTMLElement>('.scroll-stack-end')
    const endElementTop = endElement ? getElementOffset(endElement) : 0

    cardsRef.current.forEach((card, i) => {
      if (!card) return

      const cardTop = getElementOffset(card)
      const triggerStart = cardTop - stackPositionPx - itemStackDistance * i
      const triggerEnd = cardTop - scaleEndPositionPx
      const pinStart = triggerStart
      const pinEnd = endElementTop - containerHeight / 2

      const scaleProgress = calculateProgress(scrollTop, triggerStart, triggerEnd)
      const targetScale = baseScale + i * itemScale
      const scale = 1 - scaleProgress * (1 - targetScale)
      const rotation = rotationAmount ? i * rotationAmount * scaleProgress : 0

      let blur = 0
      if (blurAmount) {
        let topCardIndex = 0
        for (let j = 0; j < cardsRef.current.length; j++) {
          const jCardTop = getElementOffset(cardsRef.current[j])
          const jTriggerStart = jCardTop - stackPositionPx - itemStackDistance * j
          if (scrollTop >= jTriggerStart) topCardIndex = j
        }
        if (i < topCardIndex) blur = Math.max(0, (topCardIndex - i) * blurAmount)
      }

      let translateY = 0
      const isPinned = scrollTop >= pinStart && scrollTop <= pinEnd
      if (isPinned) {
        translateY = scrollTop - cardTop + stackPositionPx + itemStackDistance * i
      } else if (scrollTop > pinEnd) {
        translateY = pinEnd - cardTop + stackPositionPx + itemStackDistance * i
      }

      const next: Transform = {
        translateY: Math.round(translateY * 100) / 100,
        scale: Math.round(scale * 1000) / 1000,
        rotation: Math.round(rotation * 100) / 100,
        blur: Math.round(blur * 100) / 100,
      }

      const last = lastTransformsRef.current.get(i)
      const changed =
        !last ||
        Math.abs(last.translateY - next.translateY) > 0.1 ||
        Math.abs(last.scale - next.scale) > 0.001 ||
        Math.abs(last.rotation - next.rotation) > 0.1 ||
        Math.abs(last.blur - next.blur) > 0.1

      if (changed) {
        card.style.transform = `translate3d(0, ${next.translateY}px, 0) scale(${next.scale}) rotate(${next.rotation}deg)`
        card.style.filter = next.blur > 0 ? `blur(${next.blur}px)` : ''
        lastTransformsRef.current.set(i, next)
      }

      if (i === cardsRef.current.length - 1) {
        const isInView = scrollTop >= pinStart && scrollTop <= pinEnd
        if (isInView && !stackCompletedRef.current) {
          stackCompletedRef.current = true
          onStackComplete?.()
        } else if (!isInView && stackCompletedRef.current) {
          stackCompletedRef.current = false
        }
      }
    })

    isUpdatingRef.current = false
  }, [
    itemScale, itemStackDistance, stackPosition, scaleEndPosition, baseScale,
    rotationAmount, blurAmount, useWindowScroll, onStackComplete,
    calculateProgress, parsePercentage, getScrollData, getElementOffset,
  ])

  const handleScroll = useCallback(() => { updateCardTransforms() }, [updateCardTransforms])

  /*
   * A pinned card keeps its layout box where it started while its transform
   * carries it down the page, so the section's own height does not cover
   * where the last card actually ends up and it overlaps whatever follows.
   *
   * The last card comes to rest at:
   *   pinEnd + stackPosition + itemStackDistance * (n - 1)
   * where pinEnd = endElementTop - containerHeight / 2. Reserving that
   * distance below the end marker makes the overlap impossible. A fixed rem
   * value cannot work here because card height varies with viewport: the
   * same five cards are ~400px tall on desktop and ~700px on a phone.
   */
  const applySpacer = useCallback(() => {
    const inner = innerRef.current
    if (!inner) return

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      inner.style.paddingBottom = ''
      return
    }

    const cards = cardsRef.current
    if (!cards.length) return

    const containerHeight = useWindowScroll
      ? window.innerHeight
      : scrollerRef.current?.clientHeight ?? 0
    const stackPositionPx = parsePercentage(stackPosition, containerHeight)
    const tallest = Math.max(...cards.map((c) => c.offsetHeight))

    const needed =
      stackPositionPx + itemStackDistance * (cards.length - 1) + tallest - containerHeight / 2 + 48

    inner.style.paddingBottom = `${Math.max(64, Math.round(needed))}px`
  }, [itemStackDistance, stackPosition, useWindowScroll, parsePercentage])

  useLayoutEffect(() => {
    const scroller = scrollerRef.current
    if (!scroller) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const cards = Array.from(
      useWindowScroll
        ? document.querySelectorAll<HTMLElement>('.scroll-stack-card')
        : scroller.querySelectorAll<HTMLElement>('.scroll-stack-card'),
    )
    cardsRef.current = cards
    const transformsCache = lastTransformsRef.current

    if (reduced) {
      // Plain stacked list; CSS already neutralises the transforms.
      return () => { cardsRef.current = [] }
    }

    cards.forEach((card, i) => {
      if (i < cards.length - 1) card.style.marginBottom = `${itemDistance}px`
      card.style.willChange = 'transform, filter'
      card.style.transformOrigin = 'top center'
      card.style.backfaceVisibility = 'hidden'
    })

    const lenis = useWindowScroll
      ? new Lenis({
          duration: 1.2,
          easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
          touchMultiplier: 2,
          wheelMultiplier: 1,
          lerp: 0.1,
          syncTouch: true,
          syncTouchLerp: 0.075,
        })
      : new Lenis({
          wrapper: scroller,
          content: scroller.querySelector('.scroll-stack-inner') as HTMLElement,
          duration: 1.2,
          easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
          touchMultiplier: 2,
          wheelMultiplier: 1,
          lerp: 0.1,
          syncTouch: true,
          syncTouchLerp: 0.075,
        })

    lenis.on('scroll', handleScroll)
    const raf = (time: number) => {
      lenis.raf(time)
      animationFrameRef.current = requestAnimationFrame(raf)
    }
    animationFrameRef.current = requestAnimationFrame(raf)
    lenisRef.current = lenis

    applySpacer()
    updateCardTransforms()

    const onResize = () => {
      applySpacer()
      updateCardTransforms()
    }
    window.addEventListener('resize', onResize)

    // Card height changes as images and webfonts land, which changes how far
    // the last card travels.
    const ro = new ResizeObserver(() => {
      applySpacer()
      updateCardTransforms()
    })
    cards.forEach((c) => ro.observe(c))

    return () => {
      window.removeEventListener('resize', onResize)
      ro.disconnect()
      if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current)
      lenisRef.current?.destroy()
      lenisRef.current = null
      stackCompletedRef.current = false
      cardsRef.current = []
      transformsCache.clear()
      isUpdatingRef.current = false
    }
  }, [
    itemDistance, itemScale, itemStackDistance, stackPosition, scaleEndPosition,
    baseScale, scaleDuration, rotationAmount, blurAmount, useWindowScroll,
    onStackComplete, handleScroll, updateCardTransforms, applySpacer,
  ])

  return (
    <div
      className={`scroll-stack-scroller ${useWindowScroll ? 'is-window' : ''} ${className}`.trim()}
      ref={scrollerRef}
    >
      <div className="scroll-stack-inner" ref={innerRef}>
        {children}
        {/* spacer so the last pin can release cleanly */}
        <div className="scroll-stack-end" />
      </div>
    </div>
  )
}

export default ScrollStack
