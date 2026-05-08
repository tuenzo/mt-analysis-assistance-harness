'use client'

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react'

type ScaledPageFrameProps = {
  children: ReactNode
  designWidth: number
  designHeight: number
  minScale?: number
  maxScale?: number
  className?: string
  contentClassName?: string
}

const useIsomorphicLayoutEffect =
  typeof window === 'undefined' ? useEffect : useLayoutEffect

export function ScaledPageFrame({
  children,
  designWidth,
  designHeight,
  minScale = 0.25,
  maxScale = 1,
  className = '',
  contentClassName = '',
}: ScaledPageFrameProps) {
  const frameRef = useRef<HTMLDivElement>(null)
  const contentRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  const updateScale = useCallback(() => {
    const frame = frameRef.current
    if (!frame) return

    const rect = frame.getBoundingClientRect()
    const availableWidth = Math.max(rect.width, 1)
    const availableHeight = Math.max(rect.height, 1)

    const content = contentRef.current?.firstElementChild as HTMLElement | null
    const measuredWidth = content?.scrollWidth || designWidth
    const measuredHeight = content?.scrollHeight || designHeight
    const fitWidth = Math.max(designWidth, measuredWidth)
    const fitHeight = Math.max(designHeight, measuredHeight)

    const widthScale = availableWidth / fitWidth
    const heightScale = availableHeight / fitHeight
    const viewportRatio = availableWidth / availableHeight
    const contentRatio = fitWidth / fitHeight
    const ratioScale = viewportRatio < contentRatio ? widthScale : heightScale

    // Keep desktop dashboard-like pages fitted to the current page ratio.
    const nextScale = Math.min(maxScale, Math.max(minScale, ratioScale))
    setScale((current) => {
      const rounded = Number(nextScale.toFixed(3))
      return Math.abs(current - rounded) > 0.005 ? rounded : current
    })
  }, [designHeight, designWidth, maxScale, minScale])

  useIsomorphicLayoutEffect(() => {
    const frame = frameRef.current
    if (!frame) return

    updateScale()
    const observer = new ResizeObserver(updateScale)
    observer.observe(frame)
    window.addEventListener('resize', updateScale)

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', updateScale)
    }
  }, [updateScale])

  useEffect(() => {
    const frame = window.requestAnimationFrame(updateScale)
    return () => window.cancelAnimationFrame(frame)
  }, [scale, updateScale])

  const contentStyle: CSSProperties = {
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    width: `${designWidth}px`,
    height: `${designHeight}px`,
  }

  return (
    <div
      ref={frameRef}
      data-scaled-page-frame
      className={`h-full min-h-0 overflow-hidden ${className}`}
    >
      <div
        ref={contentRef}
        data-scaled-page-content
        data-scale={scale}
        className={`min-h-0 ${contentClassName}`}
        style={contentStyle}
      >
        {children}
      </div>
    </div>
  )
}
