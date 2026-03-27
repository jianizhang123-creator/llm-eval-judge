/**
 * SSE streaming and fetch utilities.
 */

async function streamSSE(url, body, handlers) {
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '', eventType = '';
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('event: ')) eventType = line.slice(7).trim();
                else if (line.startsWith('data: ') && eventType) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (handlers[eventType]) handlers[eventType](data);
                    } catch(e) { console.error('SSE parse:', e); }
                    eventType = '';
                }
            }
        }
    } catch(e) {
        console.error('SSE error:', e);
        if (handlers.error) handlers.error({ message: e.message });
    }
}
