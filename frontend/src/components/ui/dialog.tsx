import * as React from "react"
import { cn } from "@/lib/utils"
import { X } from "lucide-react"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
  centered?: boolean
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
}

export function Dialog({ open, onOpenChange, children, centered = false, maxWidth = 'md' }: DialogProps) {
  if (!open) return null

  const maxWidthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  }

  if (centered) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="fixed inset-0 bg-black/50"
          onClick={() => onOpenChange(false)}
        />
        <div 
          className={cn(
            "relative z-50 bg-background rounded-lg shadow-lg w-full overflow-hidden flex flex-col border",
            maxWidthClasses[maxWidth],
            "max-h-[90vh]"
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {React.Children.map(children, (child) => {
            if (React.isValidElement(child)) {
              return React.cloneElement(child, { onClose: () => onOpenChange(false) } as any)
            }
            return child
          })}
        </div>
      </div>
    )
  }

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={() => onOpenChange(false)}
      />
      <div className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-4 pointer-events-none">
        <div 
          className={cn(
            "relative bg-background rounded-lg shadow-lg w-full max-h-[calc(100vh-5rem)] overflow-hidden flex flex-col border pointer-events-auto",
            maxWidthClasses[maxWidth]
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {React.Children.map(children, (child) => {
            if (React.isValidElement(child)) {
              return React.cloneElement(child, { onClose: () => onOpenChange(false) } as any)
            }
            return child
          })}
        </div>
      </div>
    </>
  )
}

export function DialogContent({ children, onClose, className }: { children: React.ReactNode; onClose?: () => void; className?: string }) {
  return (
    <div className={cn("p-6 flex-1 flex flex-col relative", className)}>
      {onClose && (
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 z-10"
        >
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </button>
      )}
      <div className="flex-1 overflow-y-auto">
        {children}
      </div>
    </div>
  )
}

export function DialogHeader({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-col space-y-1.5 text-center sm:text-left mb-4">{children}</div>
}

export function DialogTitle({ children, className }: { children: React.ReactNode; className?: string }) {
  return <h2 className={cn("text-lg font-semibold leading-none tracking-tight", className)}>{children}</h2>
}

