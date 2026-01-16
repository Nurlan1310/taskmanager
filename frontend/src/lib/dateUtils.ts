import { format } from 'date-fns'

// Часовой пояс Астаны (UTC+6)
const ASTANA_TIMEZONE = 'Asia/Almaty'

/**
 * Конвертирует дату в часовой пояс Астаны
 * @param date - Дата в формате ISO string или Date object
 * @returns Date object в часовом поясе Астаны
 */
function toAstanaTime(date: string | Date | null | undefined): Date | null {
  if (!date) return null
  
  try {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    
    // Если дата невалидна, возвращаем null
    if (isNaN(dateObj.getTime())) {
      return null
    }
    
    // Используем Intl API для конвертации в часовой пояс Астаны
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: ASTANA_TIMEZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
    
    const parts = formatter.formatToParts(dateObj)
    const year = parseInt(parts.find(p => p.type === 'year')?.value || '0')
    const month = parseInt(parts.find(p => p.type === 'month')?.value || '0') - 1
    const day = parseInt(parts.find(p => p.type === 'day')?.value || '0')
    const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0')
    const minute = parseInt(parts.find(p => p.type === 'minute')?.value || '0')
    const second = parseInt(parts.find(p => p.type === 'second')?.value || '0')
    
    return new Date(year, month, day, hour, minute, second)
  } catch (error) {
    console.error('Error converting date to Astana time:', error)
    return null
  }
}

/**
 * Форматирует дату в часовом поясе Астаны
 * @param date - Дата в формате ISO string или Date object
 * @param formatStr - Строка формата для date-fns (по умолчанию 'dd.MM.yyyy HH:mm')
 * @returns Отформатированная строка даты в часовом поясе Астаны
 */
export function formatInAstanaTime(
  date: string | Date | null | undefined,
  formatStr: string = 'dd.MM.yyyy HH:mm'
): string {
  const astanaDate = toAstanaTime(date)
  if (!astanaDate) return ''
  
  return format(astanaDate, formatStr)
}

/**
 * Форматирует только дату (без времени) в часовом поясе Астаны
 */
export function formatDateInAstanaTime(
  date: string | Date | null | undefined
): string {
  return formatInAstanaTime(date, 'dd.MM.yyyy')
}

/**
 * Форматирует дату и время в часовом поясе Астаны
 */
export function formatDateTimeInAstanaTime(
  date: string | Date | null | undefined
): string {
  return formatInAstanaTime(date, 'dd.MM.yyyy HH:mm')
}
