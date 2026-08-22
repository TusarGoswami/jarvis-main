/**
 * Centralized API & WebSocket Configuration for Vocalis AI Frontend.
 * Supports:
 * - Local Development: http://127.0.0.1:8005 & ws://127.0.0.1:8005/ws/stream
 * - Vercel Production Deployment: Connects to AWS Backend via NEXT_PUBLIC_BACKEND_URL and NEXT_PUBLIC_WS_URL
 */

export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1"
    ? "" // Vercel rewrite or proxy
    : "http://127.0.0.1:8005");

export const getApiUrl = (endpoint: string): string => {
  const cleanEndpoint = endpoint.startsWith("/") ? endpoint : `/${endpoint}`;
  if (!BACKEND_URL) return cleanEndpoint;
  return `${BACKEND_URL.replace(/\/+$/, "")}${cleanEndpoint}`;
};

export const getWsUrl = (path: string = "/ws/stream"): string => {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return `${process.env.NEXT_PUBLIC_WS_URL.replace(/\/+$/, "")}${cleanPath}`;
  }
  
  if (typeof window !== "undefined") {
    // If backend URL is specified via HTTPS/HTTP, convert to WSS/WS
    if (process.env.NEXT_PUBLIC_BACKEND_URL) {
      const url = new URL(process.env.NEXT_PUBLIC_BACKEND_URL);
      const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:";
      return `${wsProtocol}//${url.host}${cleanPath}`;
    }
    
    // In local browser mode
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return `ws://127.0.0.1:8005${cleanPath}`;
    }
    
    // In production hosted mode
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${wsProtocol}//${window.location.host}${cleanPath}`;
  }

  return `ws://127.0.0.1:8005${cleanPath}`;
};
