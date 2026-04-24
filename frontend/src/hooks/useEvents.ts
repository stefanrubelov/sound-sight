import { useEffect, useRef, useState } from "react";
import { wsUrl } from "../api/client";
import type { ClassifyResponse } from "../api/types";

export interface UseEventsResult {
  events: ClassifyResponse[];
  connected: boolean;
  error: string | null;
}

export function useEvents(maxEvents = 50): UseEventsResult {
  const [events, setEvents] = useState<ClassifyResponse[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let active = true;

    function connect() {
      if (!active) return;
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => {
        if (!active) return;
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (e: MessageEvent) => {
        if (!active) return;
        try {
          const payload = JSON.parse(e.data as string) as ClassifyResponse;
          setEvents((prev) => [payload, ...prev].slice(0, maxEvents));
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => {
        if (!active) return;
        setError("WebSocket error — retrying…");
        setConnected(false);
      };

      ws.onclose = () => {
        if (!active) return;
        setConnected(false);
        retryRef.current = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      active = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, [maxEvents]);

  return { events, connected, error };
}
