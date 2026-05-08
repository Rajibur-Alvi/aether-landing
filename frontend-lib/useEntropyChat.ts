import { useState, useCallback } from "react";
import {
  sendChatMessage,
  streamChatMessage,
  ChatMeta,
  mapEntropyToVisualIntensity,
  mapLatencyToGhostEffect,
  mapDensityToStormEffect,
} from "./api";

interface UseEntropyChatReturn {
  messages: Array<{ role: "user" | "assistant"; content: string; meta?: ChatMeta }>;
  isLoading: boolean;
  error: string | null;
  visualState: {
    entropy: ReturnType<typeof mapEntropyToVisualIntensity>;
    ghost: ReturnType<typeof mapLatencyToGhostEffect>;
    storm: ReturnType<typeof mapDensityToStormEffect>;
  };
  sendMessage: (message: string, conversationId?: string) => Promise<void>;
  sendStreamingMessage: (message: string, conversationId?: string) => Promise<void>;
  clearError: () => void;
  clearMessages: () => void;
}

const DEFAULT_VISUAL_STATE = {
  entropy: mapEntropyToVisualIntensity(0),
  ghost: mapLatencyToGhostEffect(0),
  storm: mapDensityToStormEffect(0),
};

export function useEntropyChat(): UseEntropyChatReturn {
  const [messages, setMessages] = useState<
    Array<{ role: "user" | "assistant"; content: string; meta?: ChatMeta }>
  >([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visualState, setVisualState] = useState(DEFAULT_VISUAL_STATE);

  const updateVisuals = useCallback((meta: ChatMeta) => {
    setVisualState({
      entropy: mapEntropyToVisualIntensity(meta.entropy_score),
      ghost: mapLatencyToGhostEffect(meta.latency_ms),
      storm: mapDensityToStormEffect(meta.data_density),
    });
  }, []);

  const sendMessage = useCallback(
    async (message: string, conversationId?: string) => {
      setIsLoading(true);
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: message }]);
      try {
        const response = await sendChatMessage({ message, conversation_id: conversationId });
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: response.content, meta: response.meta },
        ]);
        updateVisuals(response.meta);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    },
    [updateVisuals]
  );

  const sendStreamingMessage = useCallback(
    async (message: string, conversationId?: string) => {
      setIsLoading(true);
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: message }]);

      let assistantIndex: number;
      setMessages((prev) => {
        assistantIndex = prev.length;
        return [...prev, { role: "assistant", content: "" }];
      });

      let fullContent = "";

      try {
        await streamChatMessage(
          { message, conversation_id: conversationId },
          (token) => {
            fullContent += token;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { role: "assistant", content: fullContent };
              return updated;
            });
          },
          (meta) => {
            updateVisuals({
              entropy_score: (meta.entropy_score as number) || 0,
              latency_ms: 0,
              tokens_per_second: 0,
              data_density: (meta.data_density as number) || 0,
              sources: [],
            });
          },
          (data) => {
            updateVisuals({
              entropy_score: data.entropy_score || 0,
              latency_ms: 0,
              tokens_per_second: 0,
              data_density: 0,
              sources: [],
            });
          },
          (err) => setError(err.message)
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Stream failed");
      } finally {
        setIsLoading(false);
      }
    },
    [updateVisuals]
  );

  const clearError = useCallback(() => setError(null), []);
  const clearMessages = useCallback(() => {
    setMessages([]);
    setVisualState(DEFAULT_VISUAL_STATE);
  }, []);

  return { messages, isLoading, error, visualState, sendMessage, sendStreamingMessage, clearError, clearMessages };
}
