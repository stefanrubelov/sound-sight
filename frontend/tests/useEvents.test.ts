import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useEvents } from "../src/hooks/useEvents";

vi.mock("../src/api/client", () => ({
  wsUrl: () => "ws://localhost:8000/ws/events",
}));

// Minimal WebSocket mock wired up the same way the hook wires it
class MockWS {
  static instances: MockWS[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(_url: string) {
    MockWS.instances.push(this);
  }

  close() {
    this.onclose?.();
  }

  // Helpers called by tests to simulate server events
  open() {
    this.onopen?.();
  }
  send(payload: object) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
  fail() {
    this.onerror?.();
  }
  drop() {
    this.onclose?.();
  }
}

const fakeEvent = (id: number) => ({
  event_id: id,
  class_name: "doorbell",
  confidence: 0.9,
  severity: "info",
  led_color: "#0078ff",
  vibration_pattern: "short",
  device_id: 1,
  timestamp: "2026-04-26T10:00:00Z",
});

beforeEach(() => {
  MockWS.instances = [];
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", MockWS);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("useEvents", () => {
  it("starts disconnected with empty events", () => {
    const { result } = renderHook(() => useEvents());
    expect(result.current.events).toEqual([]);
    expect(result.current.connected).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sets connected on socket open", () => {
    const { result } = renderHook(() => useEvents());
    act(() => {
      MockWS.instances[0].open();
    });
    expect(result.current.connected).toBe(true);
    expect(result.current.error).toBeNull();
  });

  it("prepends incoming event to the list", () => {
    const { result } = renderHook(() => useEvents());
    act(() => {
      MockWS.instances[0].open();
      MockWS.instances[0].send(fakeEvent(1));
    });
    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0].class_name).toBe("doorbell");
    expect(result.current.events[0].event_id).toBe(1);
  });

  it("newest event appears first", () => {
    const { result } = renderHook(() => useEvents());
    act(() => {
      MockWS.instances[0].open();
      MockWS.instances[0].send(fakeEvent(1));
      MockWS.instances[0].send(fakeEvent(2));
    });
    expect(result.current.events[0].event_id).toBe(2);
  });

  it("caps list at maxEvents", () => {
    const { result } = renderHook(() => useEvents(3));
    act(() => {
      MockWS.instances[0].open();
      for (let i = 0; i < 5; i++) MockWS.instances[0].send(fakeEvent(i));
    });
    expect(result.current.events).toHaveLength(3);
  });

  it("sets error and disconnects on socket error", () => {
    const { result } = renderHook(() => useEvents());
    act(() => {
      MockWS.instances[0].open();
      MockWS.instances[0].fail();
    });
    expect(result.current.connected).toBe(false);
    expect(result.current.error).toMatch(/retrying/i);
  });

  it("reconnects after 3 s on socket close", () => {
    renderHook(() => useEvents());
    expect(MockWS.instances).toHaveLength(1);
    act(() => {
      MockWS.instances[0].drop();
      vi.advanceTimersByTime(3000);
    });
    expect(MockWS.instances).toHaveLength(2);
  });

  it("ignores malformed JSON without crashing", () => {
    const { result } = renderHook(() => useEvents());
    act(() => {
      MockWS.instances[0].open();
      MockWS.instances[0].onmessage?.({ data: "not-json{{" });
    });
    expect(result.current.events).toHaveLength(0);
  });
});
