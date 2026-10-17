// Pure deterministic scheduling order, independent of Shell and the renderer.
export function makeOrder(ids, mode, seed, previous = null) {
    const order = [...new Set(ids)];
    let state = seed >>> 0 || 0x6d2b79f5;
    if (mode === 'shuffle') {
        for (let i = order.length - 1; i > 0; i--) {
            state ^= state << 13; state ^= state >>> 17; state ^= state << 5; state >>>= 0;
            const j = Math.floor(state / 4294967296 * (i + 1));
            [order[i],order[j]] = [order[j],order[i]];
        }
        if (order.length > 1 && order[0] === previous) [order[0],order[1]] = [order[1],order[0]];
    }
    return {order, seed:state >>> 0};
}
export function advance(ids, mode, saved, current, direction = 1) {
    const signature = JSON.stringify([ids, mode]);
    let state = saved?.signature === signature && Array.isArray(saved.order) ? {...saved, order:[...saved.order]} : null;
    if (!state || state.order.length !== ids.length || new Set(state.order).size !== ids.length || state.order.some(id => !ids.includes(id))) {
        state = {...makeOrder(ids, mode, saved?.seed ?? 0x6d2b79f5), signature};
    }
    if (!state.order.length) return {...state, cursor:-1, id:null};
    let cursor = state.order.indexOf(current);
    if (direction < 0) cursor = (cursor < 0 ? 0 : cursor) - 1;
    else cursor++;
    if (cursor >= state.order.length) {
        state = {...makeOrder(ids, mode, state.seed, current), signature};
        cursor = 0;
    }
    if (cursor < 0) cursor = state.order.length - 1;
    return {...state, cursor, id:state.order[cursor]};
}
