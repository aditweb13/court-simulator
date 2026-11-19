import { ClientEvent, ServerEvent } from "./schemas";
import { useTrialStore } from "../store/trialStore";

export class TrialWebSocketClient {
  private ws: WebSocket | null = null;
  private trialId: string | null = null;
  private token: string | null = null;
  private isExplicitlyClosed = false;

  public get currentTrialId(): string | null {
    return this.trialId;
  }

  public connect(trialId: string, token: string, baseUrl?: string): void {
    this.trialId = trialId;
    this.token = token;
    this.isExplicitlyClosed = false;

    const store = useTrialStore.getState();
    store.setStatus("connecting");
    store.setTrialId(trialId);

    // Determine WebSocket URL
    let wsUrl: string;
    if (baseUrl) {
      wsUrl = `${baseUrl.replace(/^http/, "ws")}/ws/v1/trials/${trialId}`;
    } else if (typeof window !== "undefined") {
      const host = window.location.host || "localhost:8000";
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${proto}//${host}/ws/v1/trials/${trialId}`;
    } else {
      wsUrl = `ws://localhost:8000/ws/v1/trials/${trialId}`;
    }

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        // Send initial auth handshake
        this.send({
          type: "auth",
          token: this.token || "",
        });
        useTrialStore.getState().setStatus("running");
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const data: ServerEvent = JSON.parse(event.data);
          useTrialStore.getState().handleServerEvent(data, (seq: number) => {
            this.sendAck(seq);
          });
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err, event.data);
        }
      };

      this.ws.onerror = (err) => {
        console.error("WebSocket error:", err);
        useTrialStore.getState().setError("WebSocket connection failed");
      };

      this.ws.onclose = (event) => {
        if (!this.isExplicitlyClosed) {
          if (event.code !== 1000) {
            useTrialStore.getState().setError(
              event.reason || `Connection closed (code: ${event.code})`,
            );
          }
        }
      };
    } catch (err) {
      useTrialStore.getState().setError(
        err instanceof Error ? err.message : "Failed to open WebSocket",
      );
    }
  }

  public send(event: ClientEvent): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(event));
    }
  }

  public sendAck(seq: number): void {
    this.send({ type: "ack", seq });
  }

  public sendHumanAction(action: string, text?: string, target?: string): void {
    this.send({ type: "human_action", action, text, target });
  }

  public sendObjection(objectionType: string, reason?: string): void {
    this.send({ type: "object", objection_type: objectionType, reason });
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    useTrialStore.getState().reset();
  }
}

export const trialWs = new TrialWebSocketClient();
