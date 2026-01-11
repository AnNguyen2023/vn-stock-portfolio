import { getTrending, parseTrendingResponse } from '../../lib/api';

export default function StockTrendingCell({ ticker }) {
    const [trending, setTrending] = useState({ trend: 'sideways', change_pct: 0 });

    useEffect(() => {
        getTrending(ticker)
            .then(res => setTrending(parseTrendingResponse(res)))
            .catch(() => setTrending({ trend: 'sideways', change_pct: 0 }));
    }, [ticker]);

    return <TrendingIcon trend={trending.trend} changePct={trending.change_pct} size={26} />;
}
