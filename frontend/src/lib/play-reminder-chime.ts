/** Short two-tone chime for due reminders (Web Audio; no asset file). */
export function playReminderChime(): void {
  type Win = Window & { webkitAudioContext?: typeof AudioContext };
  const Ctor = window.AudioContext || (window as Win).webkitAudioContext;
  if (!Ctor) return;

  const ctx = new Ctor();
  const start = ctx.currentTime;
  const freqs = [784, 988];

  freqs.forEach((freq, i) => {
    const t0 = start + i * 0.2;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(0.11, t0 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.16);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + 0.18);
  });

  void ctx.resume().catch(() => {});
  window.setTimeout(() => {
    void ctx.close().catch(() => {});
  }, 900);
}
