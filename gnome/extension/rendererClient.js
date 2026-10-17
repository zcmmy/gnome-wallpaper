import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
// Short-lived asynchronous commands; no status polling when preferences close.
export function command(path, cmd, args = {}) {
    return new Promise((resolve, reject) => {
        const cancel = new Gio.Cancellable();
        const timeout = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2500, () => {cancel.cancel(); return GLib.SOURCE_REMOVE;});
        let connection = null, finished = false;
        const finish = (value, error) => {
            if (finished) return; finished = true;
            if (!cancel.is_cancelled()) GLib.source_remove(timeout);
            try {connection?.close(null);} catch (_) {}
            if (error) reject(error); else resolve(value);
        };
        new Gio.SocketClient({timeout:2}).connect_async(new Gio.UnixSocketAddress({path}), cancel, (client, result) => {
            try {
                connection = client.connect_finish(result);
                const bytes = new TextEncoder().encode(JSON.stringify({id:1, cmd, args}) + '\n');
                connection.get_output_stream().write_all_async(bytes, GLib.PRIORITY_DEFAULT, cancel, (stream, written) => {
                    try {
                        stream.write_all_finish(written);
                        const input = new Gio.DataInputStream({base_stream:connection.get_input_stream()});
                        input.read_line_async(GLib.PRIORITY_DEFAULT, cancel, (reader, response) => {
                            try {const [line] = reader.read_line_finish_utf8(response); const data = JSON.parse(line);
                                if (!data?.ok) throw new Error(data?.error?.message ?? 'Renderer rejected command');
                                finish(data.result, null);
                            } catch (e) {finish(null,e);}
                        });
                    } catch (e) {finish(null,e);}
                });
            } catch (e) {finish(null,e);}
        });
    });
}
