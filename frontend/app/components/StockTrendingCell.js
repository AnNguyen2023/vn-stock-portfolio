// Helper component to fetch and display trending icon for each stock
import { useState, useEffect } from 'react';
import TrendingIcon from '../components/TrendingIcon';

export default function StockTrendingCell({ ticker }) {
    const [trending, setTrending] = useState({ trend: 'sideways', change_pct: 0 });

    useEffect(() => {
        fetch(`http://localhost:8000/trending/${ticker}`)
            .then(res => res.json())
            .then(data => setTrending(data))
            .catch(() => setTrending({ trend: 'sideways', change_pct: 0 }));
    }, [ticker]);

    return <TrendingIcon trend={trending.trend} changePct={trending.change_pct} size={26} />;
}
