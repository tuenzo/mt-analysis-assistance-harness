'use client'

import {
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
  const hasMeasuredRef = useRef(false)
  const [scale, setScale] = useState(1)
  const [frameSize, setFrameSize] = useState({ width: designWidth, height: designHeight })

  useIsomorphicLayoutEffect(() => {
    if (hasMeasuredRef.current) return

    const frame = frameRef.current
    if (!frame) return
    hasMeasuredRef.current = true

    const rect = frame.getBoundingClientRect()
    const availableWidth = Math.max(rect.width, 1)
    const availableHeight = Math.max(rect.height, 1)
    const roundedFrame = {
      width: Math.round(availableWidth),
      height: Math.round(availableHeight),
    }

    const content = contentRef.current?.firstElementChild as HTMLElement | null
    const hasHorizontalOverflow = content ? content.scrollWidth > content.clientWidth + 1 : false
    const hasVerticalOverflow = content ? content.scrollHeight > content.clientHeight + 1 : false
    const fitWidth = hasHorizontalOverflow && content ? content.scrollWidth : designWidth
    const fitHeight = hasVerticalOverflow && content ? content.scrollHeight : designHeight
    const baseScale = Math.min(maxScale, Math.max(minScale, Math.min(availableWidth / designWidth, availableHeight / designHeight)))
    const overflowScale = Math.min(availableWidth / Math.max(fitWidth, 1), availableHeight / Math.max(fitHeight, 1))
    const nextScale = Math.min(baseScale, Math.max(minScale, overflowScale))
    const roundedScale = Number(nextScale.toFixed(3))

    setFrameSize(roundedFrame)
    setScale(roundedScale)
  }, [designHeight, designWidth, maxScale, minScale])

  const contentStyle: CSSProperties = {
    transform: `scale(${scale})`,
    transformOrigin: 'top left',
    width: `${frameSize.width / scale}px`,
    height: `${frameSize.height / scale}px`,
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
