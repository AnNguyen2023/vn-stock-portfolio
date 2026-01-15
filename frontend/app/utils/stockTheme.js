import { TrendingUp, TrendingDown, Minus } from "lucide-react";

/**
 * Determines the color theme and icon for a stock based on its price relative to reference, ceiling, and floor prices.
 * @param {number} price - The current price of the stock.
 * @param {number} refPrice - The reference price (yesterday's close).
 * @param {number} ceilingPrice - The ceiling price.
 * @param {number} floorPrice - The floor price.
 * @returns {object} An object containing Tailwind CSS classes and icon component.
 *                   Structure: { text, bg, priceColor, badgeClass, icon }
 */
export function getStockTheme(price, refPrice, ceilingPrice, floorPrice) {
    // Default theme (Reference/No Change - Amber)
    let theme = {
        text: "text-amber-500",
        bg: "bg-amber-500",
        priceColor: "text-amber-500",
        badgeClass: "bg-amber-100 text-amber-700",
        icon: <Minus size={14} />
    };

    if (price >= ceilingPrice && ceilingPrice > 0) {
        // Ceiling (Purple)
        theme = {
            text: "text-purple-500",
            bg: "bg-purple-500",
            priceColor: "text-purple-500",
            badgeClass: "bg-purple-100 text-purple-700",
            icon: <TrendingUp size={14} />
        };
    } else if (price <= floorPrice && floorPrice > 0) {
        // Floor (Cyan)
        theme = {
            text: "text-cyan-500",
            bg: "bg-cyan-500",
            priceColor: "text-cyan-500",
            badgeClass: "bg-cyan-100 text-cyan-700",
            icon: <TrendingDown size={14} />
        };
    } else if (price > refPrice) {
        // Increase (Green)
        theme = {
            text: "text-emerald-500",
            bg: "bg-emerald-500",
            priceColor: "text-emerald-500",
            badgeClass: "bg-emerald-100 text-emerald-700",
            icon: <TrendingUp size={14} />
        };
    } else if (price < refPrice) {
        // Decrease (Red)
        theme = {
            text: "text-rose-500",
            bg: "bg-rose-500",
            priceColor: "text-rose-500",
            badgeClass: "bg-rose-100 text-rose-700",
            icon: <TrendingDown size={14} />
        };
    }

    return theme;
}
