import { useEffect, useRef, useState } from 'react'

/**
 * True once the element has entered the viewport. Used to hold card visuals
 * (bars, counters, stamps) until they are actually on screen, so the motion
 * lands when someone is looking at it rather than firing on mount.
 */
export function useInView<T extends HTMLElement = HTMLDivElement>(threshold = 0.35) {
  const ref = useRef<T>(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true)
          observer.disconnect()
        }
      },
      { threshold },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [threshold])

  return { ref, inView }
}
