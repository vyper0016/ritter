import { useRef, useState } from 'react'

interface Props {
  src: string
  onClick?: () => void
}

const LENS = 90
const PANEL = 320
const SCALE = PANEL / LENS

export default function ReceiptImageZoom({ src, onClick }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const [rect, setRect] = useState<DOMRect | null>(null)

  function handleMove(e: React.MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect()
    setRect(r)
    setPos({ x: e.clientX - r.left, y: e.clientY - r.top })
  }

  const cw = rect?.width ?? 1
  const ch = rect?.height ?? 1
  const lensX = pos ? Math.max(0, Math.min(pos.x - LENS / 2, cw - LENS)) : 0
  const lensY = pos ? Math.max(0, Math.min(pos.y - LENS / 2, ch - LENS)) : 0

  // Place zoom panel to right of image, or left if not enough room.
  const panelLeft = rect
    ? rect.right + 12 + PANEL <= window.innerWidth
      ? rect.right + 12
      : Math.max(8, rect.left - PANEL - 12)
    : 0
  const panelTop = rect ? Math.max(8, Math.min(rect.top, window.innerHeight - PANEL - 8)) : 0

  return (
    <div className="relative inline-block">
      <div
        ref={containerRef}
        className="relative cursor-crosshair"
        onMouseMove={handleMove}
        onMouseLeave={() => setPos(null)}
        onClick={onClick}
      >
        <img
          src={src}
          alt="Receipt"
          className="max-h-72 w-auto rounded-lg border border-gray-200 object-contain block"
        />
        {pos && (
          <div
            className="absolute border-2 border-blue-400 bg-blue-100/20 pointer-events-none"
            style={{ left: lensX, top: lensY, width: LENS, height: LENS }}
          />
        )}
      </div>

      {pos && rect && (
        <div
          className="fixed z-[1000] rounded-lg border border-gray-300 shadow-xl overflow-hidden pointer-events-none bg-white"
          style={{ left: panelLeft, top: panelTop, width: PANEL, height: PANEL }}
        >
          <div
            style={{
              width: '100%',
              height: '100%',
              backgroundImage: `url(${src})`,
              backgroundRepeat: 'no-repeat',
              backgroundSize: `${cw * SCALE}px ${ch * SCALE}px`,
              backgroundPosition: `-${lensX * SCALE}px -${lensY * SCALE}px`,
            }}
          />
        </div>
      )}
    </div>
  )
}
