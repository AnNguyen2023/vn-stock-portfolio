import { useState, useEffect } from 'react';
import { getTrending, parseTrendingResponse } from '../../lib/api';
import TrendingIcon from './TrendingIcon';

export default function StockTrendingCell({ ticker, trending: preFetchedTrending }) {
    const [trending, setTrending] = useState(preFetchedTrending || { trend: 'sideways', change_pct: 0 });

    useEffect(() => {
        // Only fetch if not pre-fetched
        if (!preFetchedTrending) {
            getTrending(ticker)
                .then(res => setTrending(parseTrendingResponse(res)))
                .catch(() => setTrending({ trend: 'sideways', change_pct: 0 }));
        } else {
            setTrending(preFetchedTrending);
        }
    }, [ticker, preFetchedTrending]);

    return <TrendingIcon trend={trending.trend} changePct={trending.change_pct} size={26} />;
}
