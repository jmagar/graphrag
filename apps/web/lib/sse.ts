type StreamController = ReadableStreamDefaultController<Uint8Array>;

export interface SSEStreamController {
  send: (payload: string) => void;
  close: () => void;
  isClosed: () => boolean;
}

/**
 * Wraps a ReadableStream controller to guard against writes or closes after the stream ends.
 */
export function createSSEStreamController(
  controller: StreamController,
  encoder: TextEncoder,
): SSEStreamController {
  let closed = false;

  const isClosed = () => closed;

  const close = () => {
    if (closed) {
      return;
    }
    closed = true;
    try {
      controller.close();
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("already closed")) {
        return;
      }
      throw error;
    }
  };

  const send = (payload: string) => {
    if (closed) {
      return;
    }

    try {
      controller.enqueue(encoder.encode(payload));
    } catch (error) {
      if (error instanceof TypeError && error.message.includes("already closed")) {
        closed = true;
        return;
      }
      closed = true;
      throw error;
    }
  };

  return { send, close, isClosed };
}
