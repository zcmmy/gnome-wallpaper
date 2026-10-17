import Gio from 'gi://Gio';
import GLib from 'gi://GLib';

// One async request in flight, one reply consumed per request. A stalled renderer
// never blocks Shell or builds an unbounded pointer queue.
export class PointerBridge {
    constructor(path, sample) {
        this._path = path;
        this._sample = sample;
        this._cancel = new Gio.Cancellable();
        this._connection = null;
        this._busy = false;
        this._id = 0;
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
            this._tick();
            return GLib.SOURCE_CONTINUE;
        });
    }

    _tick() {
        if (this._busy || this._cancel.is_cancelled())
            return;
        this._busy = true;
        if (!this._connection) {
            const client = new Gio.SocketClient({timeout: 1});
            client.connect_async(new Gio.UnixSocketAddress({path: this._path}), this._cancel, (c, result) => {
                try {
                    const connection = c.connect_finish(result);
                    if (this._cancel.is_cancelled()) {
                        connection.close(null);
                        return;
                    }
                    this._connection = connection;
                    this._input = new Gio.DataInputStream({base_stream: connection.get_input_stream()});
                } catch (_) { /* The renderer may still be loading or restarting. */ }
                this._busy = false;
            });
            return;
        }
        const bytes = new TextEncoder().encode(JSON.stringify({id: ++this._id, cmd: 'pointer', args: this._sample()}) + '\n');
        this._connection.get_output_stream().write_all_async(bytes, GLib.PRIORITY_DEFAULT, this._cancel, (stream, result) => {
            try {
                stream.write_all_finish(result);
                this._input.read_line_async(GLib.PRIORITY_DEFAULT, this._cancel, (input, readResult) => {
                    try {
                        const [line] = input.read_line_finish_utf8(readResult);
                        if (line === null || !JSON.parse(line).ok)
                            this._disconnect();
                    } catch (_) { this._disconnect(); }
                    this._busy = false;
                });
            } catch (_) {
                this._disconnect();
                this._busy = false;
            }
        });
    }

    _disconnect() {
        try { this._connection?.close(null); } catch (_) { /* Already closed. */ }
        this._connection = null;
        this._input = null;
    }

    stop() {
        GLib.source_remove(this._timer);
        this._cancel.cancel();
        this._disconnect();
    }
}
