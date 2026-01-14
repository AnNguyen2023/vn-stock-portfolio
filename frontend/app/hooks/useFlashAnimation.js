import { useState, useEffect } from 'react';

/**
 * Custom hook for flash animation when values change
 * @param {any} value - The value to track for changes
 * @param {number} duration - Flash duration in milliseconds (default: 600)
 * @returns {boolean} flash - Whether the flash animation is active
 */
export function useFlashAnimation(value, duration = 600) {
    const [flash, setFlash] = useState(false);
    const [prevValue, setPrevValue] = useState(value);

    useEffect(() => {
        let timeoutId;
        if (value !== prevValue) {
            setFlash(true);
            setPrevValue(value);
            timeoutId = setTimeout(() => setFlash(false), duration);
        }
        return () => clearTimeout(timeoutId);
    }, [value, prevValue, duration]);

    return flash;
}
