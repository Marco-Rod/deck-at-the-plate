class SoundManager {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  init() {
    if (!this.ctx) {
      this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    // Reanudar contexto si fue suspendido (política autoplay de navegadores)
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  // ── Helpers internos ───────────────────────────────────────────────────────

  /**
   * Genera un buffer de ruido blanco de `duration` segundos.
   * Sirve como base para simular multitudes y aplausos.
   */
  _createNoiseBuffer(duration) {
    const sampleRate = this.ctx.sampleRate;
    const buffer = this.ctx.createBuffer(1, sampleRate * duration, sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    return buffer;
  }

  /**
   * Crea un nodo de ruido blanco con un filtro pasa-banda y un envelope de ganancia.
   * @param {number} freq        Frecuencia central del filtro (Hz)
   * @param {number} q           Factor Q del filtro (anchura de banda)
   * @param {number} peakGain    Ganancia máxima (0-1)
   * @param {number} attackTime  Tiempo de ataque en seg
   * @param {number} duration    Duración total del sonido en seg
   * @param {number} startTime   ctx.currentTime base
   */
  _playFilteredNoise(freq, q, peakGain, attackTime, duration, startTime) {
    const noise = this.ctx.createBufferSource();
    noise.buffer = this._createNoiseBuffer(duration + 0.1);

    const filter = this.ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = freq;
    filter.Q.value = q;

    const gain = this.ctx.createGain();
    gain.gain.setValueAtTime(0.001, startTime);
    gain.gain.linearRampToValueAtTime(peakGain, startTime + attackTime);
    gain.gain.linearRampToValueAtTime(0.001, startTime + duration);

    noise.connect(filter);
    filter.connect(gain);
    gain.connect(this.ctx.destination);

    noise.start(startTime);
    noise.stop(startTime + duration + 0.05);
  }

  /**
   * Crea un oscilador simple con envelope.
   */
  _playTone(type, freq, freqEnd, peakGain, startTime, duration) {
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = type;
    osc.frequency.setValueAtTime(freq, startTime);
    if (freqEnd !== freq) {
      osc.frequency.exponentialRampToValueAtTime(freqEnd, startTime + duration);
    }

    gain.gain.setValueAtTime(peakGain, startTime);
    gain.gain.exponentialRampToValueAtTime(0.001, startTime + duration);

    osc.connect(gain);
    gain.connect(this.ctx.destination);

    osc.start(startTime);
    osc.stop(startTime + duration + 0.05);
  }

  // ── Sonidos de UI ──────────────────────────────────────────────────────────

  playClick() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(700, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(350, this.ctx.currentTime + 0.04);
    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.04);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.04);
  }

  playCardSelect() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(250, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(500, this.ctx.currentTime + 0.08);
    gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.08);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.08);
  }

  playPackOpen() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Sonido de apertura dramático: barrido descendente + aplausos sutiles
    // Primero un sonido de tensión que sube
    this._playTone('sine', 200, 600, 0.2, now, 0.3);
    // Luego aplausos suaves que celebran la apertura
    this._playFilteredNoise(1200, 0.6, 0.15, 0.2, 0.8, now + 0.3);
    this._playFilteredNoise(800, 0.8, 0.12, 0.25, 0.7, now + 0.35);
  }

  playCardReveal() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Sonido corto y crisp de revelación: flip de carta
    // Sonido ascendente rápido
    this._playTone('triangle', 400, 800, 0.12, now, 0.15);
    // Pequeño click final
    this._playTone('sine', 600, 300, 0.08, now + 0.12, 0.05);
  }

  playGameStart() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(440, now);
    osc.frequency.setValueAtTime(554.37, now + 0.1);
    osc.frequency.setValueAtTime(659.25, now + 0.2);
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.35);
  }

  // ── Reacciones del público ─────────────────────────────────────────────────

  /**
   * Strike / Ball / Foul — murmullo breve y neutro del estadio.
   * El público apenas reacciona, solo un susurro colectivo.
   */
  playStrike() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Murmullo suave: ruido de baja frecuencia, corto
    this._playFilteredNoise(300, 0.8, 0.06, 0.08, 0.6, now);
  }

  playBall() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    this._playFilteredNoise(280, 0.7, 0.05, 0.1, 0.5, now);
  }

  playFoul() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Pequeño "ooh" colectivo — sube y baja rápido
    this._playFilteredNoise(400, 1.2, 0.09, 0.12, 0.7, now);
  }

  /**
   * Out (elevado o roletazo) — "oooh" decepcionado colectivo.
   * Frecuencia media que desciende suavemente.
   */
  playOut() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // "Ooh" colectivo: ruido filtrado en rango vocal con envelope que baja
    this._playFilteredNoise(500, 1.5, 0.12, 0.15, 1.2, now);
    // Tono de decepción descendente
    this._playTone('sine', 220, 140, 0.04, now + 0.1, 0.8);
  }

  /**
   * Ponche (Strikeout) — abucheo "BOOO" del equipo visitante.
   * Para el equipo local, sería aplausos — aquí usamos el contexto
   * de que el humano es HOME, así que un ponche del CPU es positivo
   * pero un ponche del humano es negativo. Se unifica en un sonido
   * dramático de tensión.
   */
  playStrikeout() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Abucheo: ruido de baja frecuencia + tono descendente dramático
    this._playFilteredNoise(250, 1.0, 0.18, 0.2, 1.8, now);
    this._playFilteredNoise(450, 0.8, 0.10, 0.3, 1.5, now + 0.1);
    // "Boo" descendente
    this._playTone('sawtooth', 180, 100, 0.05, now, 1.2);
  }

  /**
   * Base por bolas (Walk) — aplauso suave, el bateador toma la base con calma.
   */
  playWalk() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Aplauso suave y breve
    this._playFilteredNoise(1200, 0.6, 0.10, 0.2, 1.2, now);
    this._playFilteredNoise(800, 0.8, 0.08, 0.25, 1.0, now + 0.05);
  }

  /**
   * Hit sencillo — aplausos moderados, el público reacciona con alegría contenida.
   */
  playHit1B() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    // Crack del bat (tono percusivo corto)
    this._playTone('square', 800, 200, 0.15, now, 0.08);
    // Aplausos moderados: ruido de alta frecuencia con ataque medio
    this._playFilteredNoise(1500, 0.5, 0.18, 0.3, 1.8, now + 0.05);
    this._playFilteredNoise(900, 0.7, 0.12, 0.4, 1.5, now + 0.1);
  }

  /**
   * Doble — aplausos más fuertes y sostenidos, el público se pone de pie.
   */
  playHit2B() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    this._playTone('square', 900, 200, 0.18, now, 0.1);
    // Aplausos más intensos
    this._playFilteredNoise(1600, 0.5, 0.25, 0.25, 2.2, now + 0.05);
    this._playFilteredNoise(1000, 0.6, 0.18, 0.3, 2.0, now + 0.08);
    this._playFilteredNoise(600, 0.9, 0.10, 0.4, 1.8, now + 0.1);
  }

  /**
   * Triple — gritos del público + aplausos intensos. El bateador corre fuerte.
   */
  playHit3B() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;
    this._playTone('square', 1000, 180, 0.2, now, 0.1);
    // Grito colectivo: burst de ruido en frecuencias vocales altas
    this._playFilteredNoise(2000, 0.4, 0.30, 0.2, 2.8, now + 0.04);
    this._playFilteredNoise(1400, 0.5, 0.25, 0.25, 2.5, now + 0.06);
    this._playFilteredNoise(900, 0.6, 0.20, 0.3, 2.3, now + 0.08);
    this._playFilteredNoise(500, 1.0, 0.12, 0.5, 2.0, now + 0.1);
  }

  /**
   * Home Run — explosión de público completa: gritos, aplausos, euforia total.
   * El sonido más largo y emocionante.
   */
  playHomeRun() {
    if (!this.enabled) return;
    this.init();
    const now = this.ctx.currentTime;

    // Crack del bat épico
    this._playTone('square', 1200, 150, 0.25, now, 0.12);

    // Silencio de un instante antes de la explosión (la pelota sube)
    // Luego explosión completa del estadio en múltiples capas
    const boom = now + 0.3;

    // Capa grave: rugido del estadio
    this._playFilteredNoise(200, 1.2, 0.30, 0.4, 3.5, boom);
    // Capa media: aplausos masivos
    this._playFilteredNoise(800, 0.5, 0.35, 0.3, 3.8, boom + 0.05);
    this._playFilteredNoise(1400, 0.4, 0.30, 0.25, 3.5, boom + 0.08);
    // Capa alta: gritos agudos de euforia
    this._playFilteredNoise(2500, 0.3, 0.25, 0.2, 3.0, boom + 0.1);
    this._playFilteredNoise(3500, 0.25, 0.18, 0.2, 2.5, boom + 0.12);

    // Tono de triunfo: pequeño acorde ascendente
    this._playTone('sine', 440, 880, 0.08, boom, 0.6);
    this._playTone('sine', 554, 1108, 0.06, boom + 0.05, 0.5);
    this._playTone('sine', 660, 1320, 0.05, boom + 0.1, 0.4);
  }
}

export const soundFx = new SoundManager();