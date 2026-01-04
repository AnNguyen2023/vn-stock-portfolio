"use client";

export default function StatusBadge({ value, type = "percentage", showIcon = true }) {
  // Logic: Nếu giá trị >= 0 thì là màu xanh (Emerald), ngược lại là màu đỏ (Rose)
  const isPositive = parseFloat(value) >= 0;
  const colorClass = isPositive 
    ? "text-emerald-600 bg-emerald-50" 
    : "text-rose-500 bg-rose-50";

  // Format hiển thị: Thêm dấu + nếu là số dương
  const displayValue = isPositive ? `+${value}` : value;
  const icon = isPositive ? "↗" : "↘";

  return (
  <div className={`text-[15px] font-medium px-2.5 py-1 rounded-md inline-flex items-center gap-1 ${colorClass}`}>
    {showIcon && <span>{icon}</span>}
    <span>{displayValue}{type === "percentage" ? "%" : ""}</span>
  </div>
 );
}