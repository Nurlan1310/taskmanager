interface PieChartData {
  label: string
  value: number
  color: string
}

interface PieChartProps {
  data: PieChartData[]
  total: number
  size?: number
}

export default function PieChart({ data, total, size = 200 }: PieChartProps) {
  const radius = size / 2
  const centerX = radius
  const centerY = radius
  
  // Фильтруем данные с нулевыми значениями
  const validData = data.filter(item => item.value > 0)
  
  if (validData.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-muted-foreground">Нет данных</span>
      </div>
    )
  }
  
  // Вычисляем углы для каждой секции
  let currentAngle = -90 // Начинаем сверху
  const paths: Array<{ path: string; color: string; label: string; value: number; percentage: number }> = []
  
  validData.forEach((item) => {
    const percentage = total > 0 ? (item.value / total) * 100 : 0
    const angle = (percentage / 100) * 360
    
    const startAngle = currentAngle
    const endAngle = currentAngle + angle
    
    let path: string
    
    // Если угол равен 360 градусам или больше, рисуем полный круг через две дуги
    if (angle >= 360) {
      const topY = centerY - radius
      const bottomY = centerY + radius
      path = `M ${centerX} ${topY} A ${radius} ${radius} 0 1 1 ${centerX} ${bottomY} A ${radius} ${radius} 0 1 1 ${centerX} ${topY} Z`
    } else {
      const startAngleRad = (startAngle * Math.PI) / 180
      const endAngleRad = (endAngle * Math.PI) / 180
      
      const x1 = centerX + radius * Math.cos(startAngleRad)
      const y1 = centerY + radius * Math.sin(startAngleRad)
      const x2 = centerX + radius * Math.cos(endAngleRad)
      const y2 = centerY + radius * Math.sin(endAngleRad)
      
      const largeArcFlag = angle > 180 ? 1 : 0
      
      path = `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`
    }
    
    paths.push({
      path,
      color: item.color,
      label: item.label,
      value: item.value,
      percentage: Math.round(percentage * 10) / 10
    })
    
    currentAngle += angle
  })
  
  return (
    <div className="flex flex-col items-center gap-6">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="transform -rotate-90">
          {paths.map((item, index) => (
            <path
              key={index}
              d={item.path}
              fill={item.color}
              className="transition-all hover:opacity-80"
            />
          ))}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-muted-foreground">
            {paths.reduce((sum, item) => sum + item.percentage, 0).toFixed(0)}%
          </div>
        </div>
      </div>
      
      {/* Легенда */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
        {paths.map((item, index) => (
          <div key={index} className="flex items-center gap-3">
            <div
              className="w-4 h-4 rounded-full flex-shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium">{item.label}</div>
              <div className="text-xs text-muted-foreground">
                {item.value} ({item.percentage}%)
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
