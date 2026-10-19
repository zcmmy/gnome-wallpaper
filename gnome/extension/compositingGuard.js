// A full-monitor wallpaper surface must be composited with Shell chrome.
// Mutter's native scanout candidate selection can bypass the actor hierarchy.
// The inhibitor is refcounted; own exactly one reference and balance our release.
import Meta from 'gi://Meta';

export function holdCompositing(extension) {
    if (extension._compositingRelease) return;
    const compositor = global.compositor;
    if (typeof compositor?.disable_unredirect === 'function' &&
        typeof compositor?.enable_unredirect === 'function') {
        compositor.disable_unredirect();
        extension._compositingRelease = () => compositor.enable_unredirect();
    } else if (typeof Meta.disable_unredirect_for_display === 'function' &&
               typeof Meta.enable_unredirect_for_display === 'function') {
        const display = global.display;
        Meta.disable_unredirect_for_display(display);
        extension._compositingRelease = () => Meta.enable_unredirect_for_display(display);
    } else {
        throw new Error('This Mutter version cannot inhibit wallpaper direct scanout');
    }
}

export function releaseCompositing(extension) {
    const release = extension._compositingRelease;
    extension._compositingRelease = null;
    release?.();
}
