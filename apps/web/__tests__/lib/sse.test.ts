import { TextEncoder as NodeTextEncoder } from "util";
import { createSSEStreamController } from "@/lib/sse";

const Encoder = (globalThis as unknown as { TextEncoder?: typeof NodeTextEncoder }).TextEncoder ?? NodeTextEncoder;

describe("createSSEStreamController", () => {
  it("ignores enqueue errors once the stream is closed", () => {
    let closed = false;
    const encoder = new Encoder();

    const controller = {
      enqueue: jest.fn().mockImplementation(() => {
        if (closed) {
          throw new TypeError("Invalid state: Controller is already closed");
        }
      }),
      close: jest.fn().mockImplementation(() => {
        closed = true;
      }),
    } as unknown as ReadableStreamDefaultController<Uint8Array>;

    const { send, close } = createSSEStreamController(controller, encoder);

    send("event: start");
    close();

    expect(() => send("event: after-close")).not.toThrow();
    expect(controller.enqueue).toHaveBeenCalledTimes(1);
  });

  it("closes the underlying controller at most once", () => {
    const encoder = new Encoder();
    const closeSpy = jest.fn();
    const controller = {
      enqueue: jest.fn(),
      close: closeSpy,
    } as unknown as ReadableStreamDefaultController<Uint8Array>;

    const { close } = createSSEStreamController(controller, encoder);

    close();
    close();

    expect(closeSpy).toHaveBeenCalledTimes(1);
  });
});
