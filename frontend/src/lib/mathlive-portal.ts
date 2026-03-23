/**
 * MathLive renders the virtual keyboard (and related UI) as direct children of
 * `document.body`, outside Radix Dialog/Popover portals. Radix treats clicks on
 * those nodes as "outside" and closes the modal — use this to prevent that.
 */
export function isMathLivePortaledUI(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return Boolean(
    target.closest(
      [
        '.ML__keyboard',
        '.ML__virtual-keyboard',
        '.ML__popover',
        '.ML__tooltip',
        '.ML__menu',
      ].join(', ')
    )
  );
}
