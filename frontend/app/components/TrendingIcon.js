import React from 'react';
import { TrendingUp, TrendingDown, Minus, ArrowUp, ArrowDown } from 'lucide-react';

export default function TrendingIcon({ trend, changePct = 0, size = 24 }) {
    const iconProps = { size, strokeWidth: 2.5 };

    // Color themes matching stock price colors
    const getTheme = () => {
        switch (trend) {
            case 'strong_up':
                return {
                    icon: <TrendingUp {...iconProps} />,
                    color: 'text-emerald-600',
                    bg: 'bg-emerald-50'
                };
            case 'up':
                return {
                    icon: <ArrowUp {...iconProps} />,
                    color: 'text-emerald-500',
                    bg: 'bg-emerald-50'
                };
            case 'sideways':
                return {
                    icon: <Minus {...iconProps} />,
                    color: 'text-amber-500',
                    bg: 'bg-amber-50'
                };
            case 'down':
                return {
                    icon: <ArrowDown {...iconProps} />,
                    color: 'text-rose-500',
                    bg: 'bg-rose-50'
                };
            case 'strong_down':
                return {
                    icon: <TrendingDown {...iconProps} />,
                    color: 'text-rose-600',
                    bg: 'bg-rose-50'
                };
            default:
                return {
                    icon: <Minus {...iconProps} />,
                    color: 'text-slate-400',
                    bg: 'bg-slate-50'
                };
        }
    };

    const theme = getTheme();
    const displayPct = changePct > 0 ? `+${changePct.toFixed(2)}%` : `${changePct.toFixed(2)}%`;

    return (
        <div className={`inline-flex items-center gap-1.5 ${theme.bg} ${theme.color} px-2.5 py-1 rounded-lg font-bold text-base`}>
            {theme.icon}
            <span className="tabular-nums">{displayPct}</span>
        </div>
    );
}
