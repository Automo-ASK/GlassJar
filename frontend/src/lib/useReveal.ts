import { useEffect, useRef } from 'react'

/**
 * Reveals `[data-reveal]` descendants as they scroll into view, staggering
 * siblings by their document order. Returns a ref to attach to the container.
 *
 * Elements are styled to start hidden in index.css and get `.is-revealed`
 * added here. If IntersectionObserver is unavailable everything is revealed
 * immediately so content is never trapped behind the animation.
 */
export function useReveal<T extends HTMLElement = HTMLDivElement>(options?: {
  stagger?: number
  threshold?: number
  once?: boolean
}) {
  const { stagger = 90, threshold = 0.12, once = true } = options ?? {}
  const ref = useRef<T>(null)

  useEffect(() => {
    const root = ref.current
    if (!root) return

    const targets = Array.from(root.querySelectorAll<HTMLElement>('[data-reveal]'))
    if (targets.length === 0) return

    if (typeof IntersectionObserver === 'undefined') {
      targets.forEach((el) => el.classList.add('is-revealed'))
      return
    }

    // Stagger is per-group: elements sharing a data-reveal-group animate as a
    // sequence, everything else is indexed within the container.
    const indexOf = new Map<HTMLElement, number>()
    const groupCounts = new Map<string, number>()
    targets.forEach((el) => {
      const group = el.dataset.revealGroup ?? '__default'
      const next = groupCounts.get(group) ?? 0
      indexOf.set(el, next)
      groupCounts.set(group, next + 1)
    })

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return
          const el = entry.target as HTMLElement
          const i = indexOf.get(el) ?? 0
          el.style.setProperty('--reveal-delay', `${i * stagger}ms`)
          el.classList.add('is-revealed')
          if (once) observer.unobserve(el)
        })
      },
      { threshold, rootMargin: '0px 0px -8% 0px' },
    )

    targets.forEach((el) => observer.observe(el))
    return () => observer.disconnect()
  }, [stagger, threshold, once])

  return ref
}
