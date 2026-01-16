import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="fixed inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
      />
      <div className="relative z-50 bg-background rounded-lg shadow-lg max-w-5xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {children}
      </div>
    </div>
  )
}

export function DialogContent({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="p-6">
      <button
        onClick={onClose}
        className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      >
        <X className="h-4 w-4" />
        <span className="sr-only">Close</span>
      </button>
      {children}
    </div>
  )
}

export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col space-y-1.5 text-center sm:text-left mb-4">{children}</div>
}

export function DialogTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn("text-lg font-semibold leading-none tracking-tight", className)}>{children}</h2>
}

