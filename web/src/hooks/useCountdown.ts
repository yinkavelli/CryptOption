'use client';

import { useState, useEffect } from 'react';

export function useCountdown(from: number) {
  const [remaining, setRemaining] = useState(from);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => (prev <= 1 ? from : prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [from]);

  return remaining;
}
