import { useState, useRef, useEffect } from 'react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'
import { ChevronDown, X } from 'lucide-react'

interface SearchableSelectOption {
  value: string
  label: string
}

interface SearchableSelectProps {
  options: SearchableSelectOption[]
  value: string
  onChange: (value: string) => void
  placeholder?: string
  disabled?: boolean
  emptyText?: string
}

export default function SearchableSelect({
  options,
  value,
  onChange,
  placeholder = 'Выберите...',
  disabled = false,
  emptyText = 'Нет вариантов',
}: SearchableSelectProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const selectedOption = options.find(opt => opt.value === value)

  // Фильтрация опций по поисковому запросу
  const filteredOptions = options.filter(opt =>
    opt.label.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Закрытие при клике вне компонента
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSearchQuery('')
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Фокус на input при открытии
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const handleSelect = (optionValue: string) => {
    onChange(optionValue)
    setIsOpen(false)
    setSearchQuery('')
  }

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setSearchQuery('')
  }

  return (
    <div ref={containerRef} className="relative">
      {/* Основной input (отображает выбранное значение или placeholder) */}
      <div
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          "placeholder:text-muted-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "cursor-pointer",
          disabled && "cursor-not-allowed opacity-50"
        )}
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        <div className="flex-1 flex items-center">
          {selectedOption ? (
            <span className="truncate">{selectedOption.label}</span>
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </div>
        <div className="flex items-center gap-1 ml-2">
          {value && !disabled && (
            <X
              className="h-4 w-4 text-muted-foreground hover:text-foreground"
              onClick={handleClear}
            />
          )}
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform",
              isOpen && "transform rotate-180"
            )}
          />
        </div>
      </div>

      {/* Выпадающий список */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full mt-1 bg-popover border border-border rounded-md shadow-md max-h-60 overflow-auto">
          {/* Поле поиска */}
          <div className="p-2 border-b border-border">
            <Input
              ref={inputRef}
              type="text"
              placeholder="Поиск..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8"
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          {/* Список опций */}
          <div className="py-1">
            {filteredOptions.length > 0 ? (
              filteredOptions.map((option) => (
                <div
                  key={option.value}
                  className={cn(
                    "px-3 py-2 cursor-pointer hover:bg-accent hover:text-accent-foreground",
                    value === option.value && "bg-accent text-accent-foreground"
                  )}
                  onClick={() => handleSelect(option.value)}
                >
                  {option.label}
                </div>
              ))
            ) : (
              <div className="px-3 py-2 text-sm text-muted-foreground text-center">
                {emptyText}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
