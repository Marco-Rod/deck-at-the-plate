# GAMEPLAY-ENGINE-001B · Fatiga — seguimiento

Estado: **001C (threshold calibration) CERRADA** y **Fatigue Policy v2
implementada en producción** (001C-6). Curva **SMOOTH-0.55-F35** + threshold
escalado `round(100 × innings / 9)` → 3/6/9 = 33/67/100. Deuda abierta:
**GAMEPLAY-FATIGUE-CPU-001** (semántica de `fatigue_level` en UI/CPU). `001D-1`
la caracterizó: la CPU actual dispara el cambio a w≈1.05–1.11 (factor
≈0.97–0.99), es decir con el pitcher **casi sano** según el engine real.

```
001A    Fatigue propagation             CLOSED ✓
001B-1  Current curve characterization  CLOSED ✓
001B-2  Candidate curves                CLOSED ✓
001B-3  Pitch Monte Carlo               CLOSED ✓
001B-4  Full PA Monte Carlo             CLOSED ✓
001B-5  Curve selection                 CLOSED ✓ (SMOOTH-0.55-F35 selected;
                                                   LINEAR valid alt; CURRENT rejected)

001C    Threshold calibration           CLOSED ✓
001C-1  Natural workload distribution   CLOSED ✓ (≈150 pit / 9 inn; 25 = inning 2)
001C-2  Threshold candidates            CLOSED ✓ (EARLY 75 / BALANCED 100 / LATE 125)
001C-3  Threshold × outing simulation   CLOSED ✓ (BALANCED-100 seleccionada)
001C-4  Matchup robustness              CLOSED ✓ (SMOOTH-100 robusta STRONG/MID/WEAK)
001C-5  3/6/9 inning scaling            CLOSED ✓ ({33,67,100} ≈ 2/3 natural, validado)
001C-6  Production implementation       CLOSED ✓ (Fatigue Policy v2 en producción)

GAMEPLAY-FATIGUE-CPU-001 — UI / CPU STRATEGY SEMANTICS
001D-1  Characterize current CPU change  CLOSED ✓ (dispara a w≈1.05–1.11, factor ≈0.97–0.99)
001D-2  Define fatigue signal semantics  CLOSED ✓ (workload canónico; bandas HEALTHY..SEVERE)
001D-3  Simulate CPU change strategies   CLOSED ✓ (AGGRESSIVE/BALANCED/TOLERANT × STRONG/MID/WEAK)
001D-4  Select EASY/MEDIUM/HARD policies  CLOSED ✓ (recomendado HARD 1.20 / MEDIUM 1.35 / EASY 1.50)
001D-5  UI fatigue representation        OPEN
001D-6  Production implementation        OPEN

GAMEPLAY-ENGINE-002 — DISCIPLINE / COUNT MODEL
002A    PA/count characterization       CLOSED / PASS
002B    CTL×VIS original                CLOSED / PASS
002C-B  TAKE baseline                   CLOSED / PASS
002C-C  Foul continuation               CLOSED / PASS
002C-BC TAKE×Foul                       CLOSED / PASS
002D    Batter policy                   CLOSED / PASS
002C-CV CTL×VIS calibrated              CLOSED / PASS

Finding:
GAMEPLAY-ENGINE-002-CLAMP-001
  TAKE strike chance floor=0.25 causes saturation for
  low-Control / high-Vision matchups.
Severity:
  LOW / calibration debt
Action:
  Documented; DO NOT change during current balance pass.
```

> Nota de producción: `B3-C1 + 65/50/30` NO se promueve directo al motor. Los
> dos primeros (`take_bias=0.30`, `foul=45%`) son posibles cambios del engine;
> `65/50/30` es **política de agente LAB** (cómo decide batear) y en producción
> debe originarse en estrategia/dificultad/atributos/count, no como regla
> universal.

## 001B-5 · Full PA Monte Carlo sobre el PA calibrado 002

Re-ejecución del MC full-PA de 001B-4 con la configuración calibrada de 002:
**B3-C1** (TAKE baseline 0.30, foul 45%) + política LAB **65/50/30**. Fatiga
dinámica intra-PA. 750,000 PA (3 curvas × 5 workloads × 50k). MID vs MID,
threshold=25, fatiga determinista por curve (`effective_attrs`).

### Resultados de PA

| Curve | Start | K% | BB% | BIP% | OUT% | 1B% | 2B% | 3B% | HR% | Reach% | Pit/PA | FinalWk |
| :---- | ----: | -: | --: | ---: | ---: | --: | --: | --: | --: | -----: | -----: | ------: |
| CURRENT | 75% | 35.82 | 8.80 | 55.38 | 30.35 | 12.27 | 4.30 | 1.77 | 6.69 | 33.82 | 3.69 | 82.8 |
| CURRENT | 100% | 24.38 | 10.57 | 65.05 | 35.58 | 14.28 | 5.39 | 2.02 | 7.77 | 40.04 | 3.70 | 110.8 |
| CURRENT | 110% | 16.44 | 12.17 | 71.39 | 39.45 | 15.70 | 5.71 | 2.08 | 8.45 | 44.11 | 3.67 | 118.7 |
| CURRENT | 125% | 7.78 | 12.24 | 79.98 | 44.40 | 17.36 | 6.31 | 2.36 | 9.55 | 47.82 | 3.48 | 133.9 |
| CURRENT | 150% | 7.07 | 12.09 | 80.83 | 44.52 | 18.01 | 6.40 | 2.28 | 9.62 | 48.41 | 3.38 | 157.5 |
| LINEAR | 75% | 35.83 | 8.79 | 55.37 | 30.35 | 12.27 | 4.30 | 1.77 | 6.69 | 33.82 | 3.69 | 82.8 |
| LINEAR | 100% | 32.10 | 9.26 | 58.65 | 32.01 | 12.93 | 4.88 | 1.81 | 7.01 | 35.89 | 3.69 | 110.7 |
| LINEAR | 110% | 29.17 | 10.19 | 60.64 | 33.60 | 13.30 | 4.81 | 1.76 | 7.17 | 37.23 | 3.69 | 118.8 |
| LINEAR | 125% | 23.83 | 11.20 | 64.97 | 36.01 | 14.12 | 5.24 | 1.87 | 7.74 | 40.16 | 3.65 | 134.6 |
| LINEAR | 150% | 16.83 | 12.77 | 70.40 | 38.77 | 15.66 | 5.64 | 2.07 | 8.26 | 44.40 | 3.58 | 158.3 |
| SMOOTH | 75% | 35.83 | 8.79 | 55.37 | 30.35 | 12.27 | 4.30 | 1.77 | 6.69 | 33.82 | 3.69 | 82.8 |
| SMOOTH | 100% | 34.40 | 8.86 | 56.74 | 30.92 | 12.54 | 4.71 | 1.77 | 6.80 | 34.68 | 3.68 | 110.7 |
| SMOOTH | 110% | 32.31 | 9.58 | 58.11 | 32.18 | 12.73 | 4.62 | 1.68 | 6.90 | 35.51 | 3.70 | 118.8 |
| SMOOTH | 125% | 26.65 | 10.53 | 62.83 | 34.76 | 13.58 | 5.12 | 1.81 | 7.57 | 38.60 | 3.67 | 134.7 |
| SMOOTH | 150% | 17.54 | 12.68 | 69.78 | 38.48 | 15.53 | 5.60 | 2.03 | 8.13 | 43.98 | 3.59 | 158.4 |

### Las dos vías de coste de la fatiga

| Curve | Start | P(full) | P(≥4) | P(≥6) | CalledS/take | Whiff/swing |
| :---- | ----: | ------: | ----: | ----: | -----------: | ----------: |
| CURRENT | 75% | 9.13 | 54.82 | 12.89 | 34.31 | 42.90 |
| CURRENT | 100% | 9.13 | 53.59 | 13.74 | 31.48 | 33.84 |
| CURRENT | 110% | 8.61 | 53.38 | 13.48 | 27.22 | 25.14 |
| CURRENT | 125% | 7.91 | 48.64 | 12.57 | 24.85 | 9.54 |
| CURRENT | 150% | 7.61 | 46.36 | 11.82 | 25.10 | 5.06 |
| LINEAR | 75% | 9.13 | 54.82 | 12.89 | 34.31 | 42.90 |
| LINEAR | 100% | 9.11 | 53.93 | 13.19 | 33.55 | 40.03 |
| LINEAR | 110% | 9.04 | 54.41 | 13.31 | 31.71 | 37.36 |
| LINEAR | 125% | 9.23 | 53.70 | 13.55 | 28.98 | 31.66 |
| LINEAR | 150% | 8.92 | 51.92 | 13.15 | 25.35 | 23.53 |
| SMOOTH | 100% | 9.13 | 54.03 | 13.04 | 34.26 | 41.92 |
| SMOOTH | 110% | 8.91 | 54.69 | 13.09 | 33.15 | 40.32 |
| SMOOTH | 125% | 9.17 | 54.13 | 13.45 | 30.61 | 34.67 |
| SMOOTH | 150% | 9.04 | 52.24 | 13.26 | 25.80 | 24.71 |

### Veredicto 001B-5

- **Los dos canales ahora existen**: el canal **comando** (CalledS/take ↓ →
  BB ↑) y el canal **dominio** (Whiff/swing ↓ → contacto/BIP ↑) son ambos
  observables. Ese era el requisito que el PA pre-002 no podía cumplir.
- **CURRENT reproducido como "muerto a 110"**: K% 24.4→16.4 y Whiff/swing
  33.8→25.1 ya entre 100→110%; a 125% colapsa (K 7.8, Whiff 9.5, BIP 80%).
  Confirma el patrón malo.
- **Gradiente de decisión** (lo que queremos: 110 señales cómodas / 125 riesgo
  perceptible / 150 deteriorado pero usable):
  - **SMOOTH** 110: K 32.31 (−3.5 vs fresco), Whiff 40.32 (−2.6) → cómodo con
    primeras señales. 125: K 26.65 (−9.2), Whiff 34.67 (−8.2) → riesgo claro.
    150: K 17.54 (−18.3), BIP 69.8 → deteriorado, utilizable. **Encaja mejor.**
  - **LINEAR** comunica antes: 110 K 29.17 (−6.7), Whiff 37.36 (−5.5); 125 K
    23.83 (−12.0), Whiff 31.66. Válida si se quiere señal temprana para bullpen.
- **Separación LINEAR vs SMOOTH en 110–125%** (sospecha confirmada): ~2.8–3.1pp
  de K% y ~3.0–3.3pp de Whiff/swing. Es exactamente la zona decisiva.
- **Pit/PA y counts profundos estables** en ambas candidatas (Pit/PA 3.58–3.70,
  P(full) 8.9–9.2, P(≥6) 13–13.6); CURRENT los erosiona. Las candidatas
  preservan la estructura de count al fatigarse.
- **Recomendación**: **SMOOTH-0.55-F35** como candidata de fatiga para pasar a
  thresholds, con LINEAR-0.8-F50 como alternativa de "señal temprana". Decisión
  final de diseño pendiente del usuario; ambas superan a CURRENT en gradiente.

## 001C-1 · Natural workload distribution (fatiga neutralizada)

Simula outings de **9 innings headless** con el PA calibrado 002 y **sin
deterioro por fatiga** (factor 1.0), para encontrar la escala natural de pitch
counts del motor. Modelo de inning: 3 outs; K y OUT cuentan como out, BB/hits
no (sin dobles matanzas ni avance de corredores). 5,000 outings por matchup
(~600k PA). Matchups: WEAK 78/58/70, MID 90/80/85, STRONG 96/94/95 (vel/ctl/mov),
bateador MID 70/70/70.

### MID: pitches por inning

| Inn | Mean | p50 | p75 | p90 | p95 |
| --: | ---: | --: | --: | --: | --: |
| 1 | 16.57 | 15 | 20 | 25 | 28 |
| 2 | 16.70 | 16 | 20 | 25 | 28 |
| 3 | 16.65 | 15 | 20 | 25 | 29 |
| 4 | 16.74 | 16 | 20 | 25 | 29 |
| 5 | 16.71 | 15 | 20 | 25 | 29 |
| 6 | 16.70 | 16 | 20 | 25 | 29 |
| 7 | 16.80 | 16 | 20 | 26 | 29 |
| 8 | 16.65 | 16 | 20 | 25 | 28 |
| 9 | 16.72 | 16 | 20 | 25 | 29 |

### MID: pitch count acumulado tras inning k

| k | Mean | p50 | p75 | p90 | p95 |
| -: | ---: | --: | --: | --: | --: |
| 1 | 16.6 | 15 | 20 | 25 | 28 |
| 2 | 33.3 | 32 | 38 | 45 | 49 |
| 3 | 49.9 | 49 | 56 | 64 | 70 |
| 4 | 66.7 | 66 | 74 | 83 | 89 |
| 5 | 83.4 | 82 | 92 | 102 | 108 |
| 6 | 100.1 | 99 | 110 | 121 | 127 |
| 7 | 116.9 | 116 | 127 | 139 | 146 |
| 8 | 133.5 | 132 | 144 | 157 | 165 |
| 9 | 150.2 | 149 | 162 | 176 | 184 |

### Comparativa por matchup (outing de 9 innings, sin fatiga)

| Matchup | Pit/PA | PA/Inn | Total p50 | Total p90 | Inn p50 | Inn p90 |
| :------ | -----: | -----: | --------: | --------: | ------: | ------: |
| WEAK | 3.68 | 4.92 | 162 | 192 | 17 | 28 |
| MID | 3.69 | 4.53 | 149 | 176 | 16 | 25 |
| STRONG | 3.67 | 4.32 | 142 | 165 | 15 | 24 |

### Cruce de thresholds (inning mediano en que se cruza el acumulado)

| Threshold | WEAK p50 | MID p50 | STRONG p50 | MID @3inn |
| --------: | -------: | ------: | ---------: | --------: |
| 25 | 2 | 2 | 2 | 99.9% |
| 40 | 3 | 3 | 3 | 82.9% |
| 50 | 3 | 4 | 4 | 47.3% |
| 60 | 4 | 4 | 4 | 18.1% |
| 75 | 5 | 5 | 5 | 2.5% |
| 90 | 6 | 6 | 6 | 0.2% |

### Veredicto 001C-1

- **La escala natural es ~150 pitches por outing de 9 innings** (MID p50 149;
  p90 176). Pitches/inning prácticamente plano (~16.7) e independiente del
  inning. ~3.68 Pit/PA y ~4.5 PA/inning.
- **El threshold de producción (25) se cruza en el inning 2 en ~100% de los
  outings.** Traducido: con CURRENT/SMOOTH, la fatiga empezaría en el segundo
  inning de un juego de 9, es decir al ~11–17% del outing. Ese es el defecto de
  escala, no de la curva.
- Puntos de referencia con la carga natural: 40 → inning 3; 50 → inning 3–4;
  60 → inning 4; 75 → inning 5; 90 → inning 6. Un "100%" que quiera caer cerca
  del inning 5–6 exigiría un threshold del orden de **80–100**.
- **El matchup mueve poco la carga** (WEAK 162 vs STRONG 142 en total p50,
  ~14%): el out-rate y el Pit/PA compensan. La forma de la distribución no
  depende mucho del pitcher; el threshold vive en la misma zona para todos.
- **CURRENT y las candidatas comparten el threshold**, así que esta escala
  afecta a las tres; 001C-2 debe elegir candidatos relativos a ~150, no a 25.
- Recordatorio: aquí la fatiga está neutralizada a propósito; esto mide carga,
  no deterioro.

### Constantes de producción relevantes (histórico, pre-v2)

> Superseded por **001C-6**. La política vigente es SMOOTH-0.55-F35 con
> `get_pitch_threshold = round(100 × innings / 9)` (3/6/9 → 33/67/100).

- `FATIGUE_THRESHOLDS = {3: 6, 6: 15, 9: 25}`; `get_pitch_threshold(9) = 25`.
- `apply_pitcher_fatigue` (CURRENT): `penalty = 1.0 − 0.10·extra`, **sin cap** →
  factor 0 al +10 pitches tras el umbral. De ahí el precipicio de CURRENT.
- **Docstring obsoleto** (ya corregido en 001C-6): decía "9 innings: 60 pitches"
  pero el diccionario devolvía 25.
- Con 3 innings el patrón se repetía: umbral 6 vs ~50 pitches naturales (~16.7 × 3).

## 001C-2 · Threshold candidates (propuesta)

Con ~16.7 pitches/inning y p50≈149/9 inn, el "100%" de SMOOTH (w=1) cae donde
`threshold` se elija. Candidatos relativos a la carga natural (fatiga dinámica,
curva fija SMOOTH-0.55-F35):

| Candidato | Threshold | w=1 (onset) | w=1.25 | w=1.50 | Intención |
| :-------- | --------: | ----------: | -----: | -----: | :-------- |
| EARLY | 75 | inn ~4.5 | inn ~5.6 | inn ~6.7 | castigo temprano, bullpen protagonista |
| BALANCED | 100 | inn ~6.0 | inn ~7.5 | inn ~9.0 | una salida larga empieza a doler al final |
| LATE | 125 | inn ~7.5 | inn ~9.0 | no se alcanza | fatiga solo si se estira mucho |

Validar en 001C-3 cruzando `threshold × outing` y midiendo en qué inning la
caída de K/whiff se vuelve perceptible (objetivo: que ~110% sea cómodo, ~125%
riesgoso, ~150% deteriorado-usable). No tocar `fatigue_manager.py` hasta 001C-4.

## 001C-3 · Threshold × outing (SMOOTH-0.55-F35)

Outings completos de 9 innings, **pitch_count continuo entre innings**, fatiga
dinámica, PA calibrado 002. MID/MID. 10,000 outings por escenario (40,000 en
total, ~1.6M PA). `NO_FATIGUE` es el control (factor 1.0). Sin cambio de pitcher
(se deja al abridor los 9 innings a propósito).

### Snapshot por inning · EARLY (threshold=75)

| Inn | cumPitch p50/p90 | w p50/p90 | factor | K% | BB% | BIP% | Reach% | Pit/PA |
| --: | :--------------- | :-------- | -----: | -: | --: | ---: | -----: | -----: |
| 1 | 16 / 25 | 0.21 / 0.33 | 1.000 | 36.13 | 8.98 | 54.89 | 33.90 | 3.68 |
| 2 | 32 / 45 | 0.43 / 0.60 | 1.000 | 36.03 | 8.75 | 55.21 | 33.56 | 3.69 |
| 3 | 49 / 64 | 0.65 / 0.85 | 0.999 | 36.12 | 8.53 | 55.35 | 33.29 | 3.66 |
| 4 | 65 / 83 | 0.87 / 1.11 | 0.988 | 35.85 | 8.92 | 55.23 | 33.47 | 3.69 |
| 5 | 82 / 103 | 1.09 / 1.37 | 0.927 | 33.72 | 9.17 | 57.11 | 34.55 | 3.67 |
| 6 | 99 / 123 | 1.32 / 1.64 | 0.780 | 28.57 | 10.17 | 61.26 | 37.64 | 3.65 |
| 7 | 117 / 145 | 1.56 / 1.93 | 0.599 | 21.48 | 11.48 | 67.04 | 41.66 | 3.60 |
| 8 | 137 / 167 | 1.83 / 2.23 | 0.462 | 16.47 | 12.48 | 71.05 | 44.16 | 3.56 |
| 9 | 156 / 189 | 2.08 / 2.52 | 0.389 | 13.58 | 12.46 | 73.97 | 45.86 | 3.51 |

### Snapshot por inning · BALANCED (threshold=100)

| Inn | cumPitch p50/p90 | w p50/p90 | factor | K% | BB% | BIP% | Reach% | Pit/PA |
| --: | :--------------- | :-------- | -----: | -: | --: | ---: | -----: | -----: |
| 1 | 16 / 25 | 0.16 / 0.25 | 1.000 | 36.13 | 8.98 | 54.89 | 33.90 | 3.68 |
| 2 | 32 / 45 | 0.32 / 0.45 | 1.000 | 36.03 | 8.75 | 55.21 | 33.56 | 3.69 |
| 3 | 49 / 64 | 0.49 / 0.64 | 1.000 | 36.13 | 8.53 | 55.34 | 33.28 | 3.66 |
| 4 | 65 / 83 | 0.65 / 0.83 | 1.000 | 36.12 | 8.87 | 55.02 | 33.33 | 3.69 |
| 5 | 82 / 102 | 0.82 / 1.02 | 0.997 | 35.74 | 8.74 | 55.53 | 33.40 | 3.68 |
| 6 | 98 / 120 | 0.98 / 1.20 | 0.975 | 35.27 | 8.80 | 55.93 | 33.89 | 3.68 |
| 7 | 115 / 140 | 1.15 / 1.40 | 0.906 | 32.49 | 9.28 | 58.22 | 35.68 | 3.66 |
| 8 | 132 / 160 | 1.32 / 1.60 | 0.782 | 28.43 | 10.44 | 61.13 | 37.82 | 3.65 |
| 9 | 151 / 181 | 1.51 / 1.81 | 0.636 | 22.58 | 11.50 | 65.92 | 41.18 | 3.62 |

### Snapshot por inning · LATE (threshold=125)

| Inn | cumPitch p50/p90 | w p50/p90 | factor | K% | BB% | BIP% | Reach% | Pit/PA |
| --: | :--------------- | :-------- | -----: | -: | --: | ---: | -----: | -----: |
| 1 | 16 / 25 | 0.13 / 0.20 | 1.000 | 36.13 | 8.98 | 54.89 | 33.90 | 3.68 |
| 2 | 32 / 45 | 0.26 / 0.36 | 1.000 | 36.03 | 8.75 | 55.21 | 33.56 | 3.69 |
| 3 | 49 / 64 | 0.39 / 0.51 | 1.000 | 36.13 | 8.53 | 55.34 | 33.28 | 3.66 |
| 4 | 65 / 83 | 0.52 / 0.66 | 1.000 | 36.12 | 8.86 | 55.01 | 33.33 | 3.69 |
| 5 | 82 / 102 | 0.66 / 0.82 | 1.000 | 35.83 | 8.71 | 55.46 | 33.34 | 3.68 |
| 6 | 98 / 120 | 0.78 / 0.96 | 0.999 | 35.96 | 8.64 | 55.40 | 33.52 | 3.68 |
| 7 | 115 / 138 | 0.92 / 1.10 | 0.991 | 35.46 | 8.72 | 55.81 | 34.09 | 3.67 |
| 8 | 132 / 157 | 1.06 / 1.26 | 0.961 | 34.92 | 9.00 | 56.08 | 34.20 | 3.68 |
| 9 | 149 / 176 | 1.19 / 1.41 | 0.890 | 32.01 | 9.58 | 58.41 | 36.06 | 3.67 |

### Acumulado, bandas y cruces

| Scenario | TotPit p50/p90 | PA | K% | BB% | BIP% | Reach% | Pit/PA |
| :------- | :------------- | -: | -: | --: | ---: | -----: | -----: |
| NO_FATIGUE | 149 / 175 | 40.7 | 36.00 | 8.75 | 55.25 | 33.60 | 3.68 |
| EARLY (75) | 156 / 189 | 43.5 | 27.97 | 10.23 | 61.81 | 37.95 | 3.63 |
| BALANCED (100) | 151 / 181 | 41.7 | 33.02 | 9.36 | 57.62 | 35.22 | 3.67 |
| LATE (125) | 149 / 176 | 40.9 | 35.39 | 8.87 | 55.75 | 33.93 | 3.68 |

| Scenario | w≤1.00 | 1–1.10 | 1.10–1.25 | 1.25–1.50 | >1.50 |
| :------- | -----: | -----: | --------: | --------: | ----: |
| EARLY | 48.52% | 4.39% | 6.89% | 11.99% | 28.21% |
| BALANCED | 66.93% | 6.52% | 9.31% | 11.38% | 5.86% |
| LATE | 84.37% | 6.32% | 6.24% | 2.77% | 0.30% |

| Scenario | w>1.00 | w≥1.10 | w≥1.25 | w≥1.50 |
| :------- | -----: | -----: | -----: | -----: |
| EARLY | 5 / 6 | 6 / 7 | 6 / 7 | 7 / 9 |
| BALANCED | 7 / 8 | 7 / 8 | 8 / 9 | 9 / 10 |
| LATE | 8 / 9 | 9 / 10 | 10 / 10 | 10 / 10 |

(valores = inning p50 / p90 de cruce; 10 = no cruza en 9 innings. NO_FATIGUE = control, sin w.)

### Veredicto 001C-3

- **Las predicciones de 001C-1 se cumplieron.** EARLY: w=1 en inning 5, >1.5 en
  7. BALANCED: w=1 en 7, >1.5 recién en 9. LATE: w=1 en 8, casi nunca >1.25.
- **EARLY=75** hace del bullpen el centro: 48.5% de PAs sanos, 28.2% en >1.50,
  K% cae 36→14 y Reach sube a 45.9%. Informativo, pero probablemente demasiado
  punitivo (el abridor queda destruido por 3 innings).
- **BALANCED=100** da la ventana de decisión buscada: sano hasta inning 6
  (67% de PAs en w≤1), primeras señales inning 7 (factor 0.906, K 32.5), riesgo
  inning 8 (0.782, K 28.4, BB 10.4), deterioro claro inning 9 (0.636, K 22.6,
  BB 11.5, Reach 41.2). Castigo **progresivo**, no precipicio.
- **LATE=125** deja al abridor prácticamente fresco: 84% de PAs en w≤1, solo
  0.30% >1.50, K total 35.4 (≈ NO_FATIGUE 36.0). El bullpen se vuelve casi
  opcional salvo outing malo.
- **Control NO_FATIGUE** útil: la merma agregada es K −8.0 (EARLY), −3.0
  (BALANCED), −1.4 (LATE); Reach +4.4 / +1.6 / +0.3. Confirma que la diferencia
  es del threshold y no ruido.
- **Recomendación**: **BALANCED = 100** (SMOOTH-0.55-F35) para 001C-4. Cumple
  mejor el criterio de ventana útil: fresco → señales → decisión → castigo
  progresivo. EARLY queda como perfil "bullpen-heavy" y LATE como "starter
  friendly" si luego se quiere variar por dificultad.
- **Doc obsoleto** (`FATIGUE-DOC-001`): `get_pitch_threshold` decía "9 inn: 60"
  pero devolvía 25. Corregido en 001C-6 junto con la política.

## 001C-4 · Matchup robustness (SMOOTH-0.55-F35, threshold=100)

Fija `Curve = SMOOTH-0.55-F35` y `threshold = 100` (selección de 001C-3) y
comprueba que `100` no sea accidentalmente perfecto sólo para MID/MID. Tres
perfiles de abridor contra el bateador MID, outings completos de 9 innings con
fatiga dinámica, 10,000 outings por matchup.

Perfiles (mismos que 001C-1): WEAK 78/58/70, MID 90/80/85, STRONG 96/94/95.
Batería MID 70/70/70; take 0.30 / foul 45% / política 65/50/30.

### Innings 6-9 por matchup (w p50/p90 · factor · K%/BB%/BIP%)

| Matchup | Inn | w p50/p90 | factor | K% | BB% | BIP% | PA |
| :------ | --: | :-------- | -----: | -: | --: | ---: | -: |
| STRONG | 6 | 0.94 / 1.14 | 0.987 | 41.12 | 7.16 | 51.72 | 43,265 |
| STRONG | 7 | 1.10 / 1.32 | 0.939 | 39.14 | 7.70 | 53.16 | 43,779 |
| STRONG | 8 | 1.26 / 1.51 | 0.836 | 34.44 | 8.38 | 57.17 | 45,368 |
| STRONG | 9 | 1.43 / 1.72 | 0.695 | 28.21 | 9.94 | 61.85 | 48,165 |
| MID | 6 | 0.99 / 1.20 | 0.975 | 35.69 | 8.88 | 55.43 | 45,315 |
| MID | 7 | 1.16 / 1.40 | 0.904 | 32.75 | 9.44 | 57.81 | 46,349 |
| MID | 8 | 1.33 / 1.61 | 0.780 | 28.09 | 10.17 | 61.74 | 48,199 |
| MID | 9 | 1.51 / 1.82 | 0.633 | 22.49 | 11.50 | 66.00 | 51,116 |
| WEAK | 6 | 1.08 / 1.33 | 0.940 | 26.29 | 11.83 | 61.88 | 49,740 |
| WEAK | 7 | 1.26 / 1.54 | 0.833 | 23.49 | 12.12 | 64.39 | 50,867 |
| WEAK | 8 | 1.45 / 1.76 | 0.687 | 19.60 | 12.53 | 67.87 | 52,786 |
| WEAK | 9 | 1.64 / 1.97 | 0.548 | 16.11 | 12.87 | 71.02 | 54,729 |

### Acumulado, bandas y cruces

| Matchup | TotPit p50/p90 | PA | K% | BB% | BIP% | Reach% | Pit/PA |
| :------ | :------------- | -: | -: | --: | ---: | -----: | -----: |
| STRONG | 143 / 172 | 39.6 | 38.60 | 7.69 | 53.71 | 31.82 | 3.67 |
| MID | 151 / 182 | 41.7 | 33.00 | 9.37 | 57.63 | 35.25 | 3.67 |
| WEAK | 164 / 197 | 45.4 | 24.73 | 11.94 | 63.33 | 40.49 | 3.65 |

| Matchup | w≤1.00 | 1–1.10 | 1.10–1.25 | 1.25–1.50 | >1.50 |
| :------ | -----: | -----: | --------: | --------: | ----: |
| STRONG | 70.51% | 6.79% | 9.40% | 9.80% | 3.50% |
| MID | 66.76% | 6.46% | 9.32% | 11.51% | 5.95% |
| WEAK | 61.44% | 5.99% | 8.89% | 12.98% | 10.69% |

| Matchup | w>1.00 | w≥1.25 | w≥1.50 |
| :------ | -----: | -----: | -----: |
| STRONG | 7 / 8 | 8 / 10 | 10 / 10 |
| MID | 7 / 8 | 8 / 9 | 9 / 10 |
| WEAK | 6 / 7 | 7 / 9 | 9 / 10 |

### Veredicto 001C-4

- **Ordenamiento correcto y gradual.** STRONG carga 143 pit (K 38.6, 3.5% de PAs
  en >1.50) → MID 151 (33.0, 5.95%) → WEAK 164 (24.7, 10.69%). El spread
  STRONG→WEAK es **+14.7%**, consistente con el ~14% natural de 001C-1.
- **La fatiga emerge del trabajo acumulado, no del inning.** El cruce de w=1 se
  corre un inning entero por tier: WEAK en 6, MID/STRONG en 7. Con w≥1.25 WEAK
  en 7, MID en 8, STRONG en 8 (p90 no llega hasta 10).
- **Ningún extremo se rompe.** STRONG no queda fresco (inn 9 factor 0.695, K
  41→28); WEAK no está destruido desde el quinto (inn 6 factor 0.940, K 26;
  el colapso real es inn 9, factor 0.548). `100` no es demasiado sensible al
  matchup: los tres conservan ventana de decisión de ~3 innings.
- **PASS.** Se cierra la calibración de 9 innings. Política candidata firme:
  **threshold 100 + SMOOTH-0.55-F35**. No se requieren más sweeps de 9 innings.
- **Bug de harness corregido (001C-4).** `_apply_factor` dividía por
  `pitcher_raw` en vez de `PITCHER_RAW`, colapsando el perfil del abridor
  (los tres matchups daban idénticos). Alineado con `neutral_attrs`/
  `effective_attrs`. No afecta 001C-3 (siempre MID=PITCHER_RAW).

## 001C-5 · Escala del threshold para 3/6/9 innings

Hipótesis a validar: **threshold ≈ 2/3 del workload natural esperado** →
`{3: 33, 6: 67, 9: 100}`. Principio rector: la fatiga depende del trabajo
acumulado respecto al outing, no del número de inning; por eso el cruce de w=1
debe ser una *consecuencia* del workload relativo. MID/MID, SMOOTH-0.55-F35,
10,000 outings por duración. No se conserva `{3: 6, 6: 15, 9: 100}`.

### 001C-5A · Workload natural (fatiga neutralizada)

| Dur | Thr | Nat p50 | Nat p90 | Mean | Pit/PA | PA | Thr/p50 | Thr/Mean |
| --: | --: | ------: | ------: | ---: | -----: | -: | ------: | -------: |
| 3 | 33 | 49 | 65 | 50.2 | 3.68 | 13.6 | 1.48 | 1.52 |
| 6 | 67 | 99 | 121 | 100.3 | 3.69 | 27.2 | 1.48 | 1.50 |
| 9 | 100 | 149 | 176 | 150.3 | 3.69 | 40.8 | 1.49 | 1.50 |

`Thr/p50 ≈ 1.48` en las tres duraciones → threshold = **67.5% / 67.5% / 67.1%**
del workload natural p50. La hipótesis 2/3 queda verificada, no extrapolada.

### 001C-5B · Snapshot por inning (SMOOTH dinámico)

| Dur | Inn | w p50/p90 | factor | K% | BB% | BIP% | Pit/PA |
| --: | --: | :-------- | -----: | -: | --: | ---: | -----: |
| 3 | 1 | 0.45 / 0.76 | 0.999 | 36.04 | 8.77 | 55.18 | 3.68 |
| 3 | 2 | 0.97 / 1.36 | 0.935 | 34.64 | 9.08 | 56.28 | 3.69 |
| 3 | 3 | 1.48 / 2.09 | 0.652 | 26.09 | 10.43 | 63.48 | 3.63 |
| 6 | 1-2 | 0.22–0.48 | 1.000/1.000 | 36.0 | 8.8 | 55.2 | 3.68 |
| 6 | 3 | 0.73 / 0.96 | 0.997 | 35.87 | 8.31 | 55.82 | 3.67 |
| 6 | 4 | 0.97 / 1.24 | 0.966 | 35.30 | 9.02 | 55.68 | 3.68 |
| 6 | 5 | 1.22 / 1.55 | 0.846 | 31.40 | 9.45 | 59.15 | 3.66 |
| 6 | 6 | 1.49 / 1.88 | 0.652 | 24.36 | 10.98 | 64.66 | 3.62 |
| 9 | 1-6 | 0.15–0.98 | 1.000→0.976 | 35.5–36.1 | 8.6–8.9 | 55.0–55.8 | 3.67 |
| 9 | 7 | 1.15 / 1.40 | 0.907 | 33.12 | 9.42 | 57.45 | 3.67 |
| 9 | 8 | 1.32 / 1.60 | 0.783 | 28.42 | 10.31 | 61.27 | 3.65 |
| 9 | 9 | 1.51 / 1.82 | 0.636 | 22.69 | 11.53 | 65.78 | 3.62 |

### 001C-5C · Comparación normalizada por duración

| Dur | Thr | TotPit p50/p90 | PA | K% | BB% | BIP% | Reach% | Pit/PA |
| --: | --: | :------------- | -: | -: | --: | ---: | -----: | -----: |
| 3 | 33 | 49 / 69 | 14.0 | 32.08 | 9.46 | 58.46 | 35.75 | 3.66 |
| 6 | 67 | 100 / 126 | 27.8 | 33.00 | 9.26 | 57.74 | 35.17 | 3.67 |
| 9 | 100 | 151 / 182 | 41.7 | 33.14 | 9.29 | 57.57 | 35.20 | 3.67 |

| Dur | w≤1.00 | 1–1.10 | 1.10–1.25 | 1.25–1.50 | >1.50 |
| --: | -----: | -----: | --------: | --------: | ----: |
| 3 | 68.75% | 5.21% | 7.56% | 8.86% | 9.62% |
| 6 | 68.18% | 5.74% | 8.79% | 10.59% | 6.70% |
| 9 | 66.96% | 6.53% | 9.31% | 11.42% | 5.79% |

| Dur | w>1.00 | w≥1.25 | w≥1.50 |
| --: | -----: | -----: | -----: |
| 3 | 3 (1.00) | 3 (1.00) | 4 (1.00) |
| 6 | 5 (0.83) | 6 (1.00) | 7 (1.00) |
| 9 | 7 (0.78) | 8 (0.89) | 9 (1.00) |

(valores = inning p50 de cruce con fracción del outing entre paréntesis;
coincide con "entrar al último tercio": 1.00 / 0.83 / 0.78.)

| Dur | Primer 1/3 | Segundo 1/3 | Último 1/3 |
| --: | ---------: | ----------: | ---------: |
| 3 | 0.999 | 0.935 | 0.652 |
| 6 | 1.000 | 0.982 | 0.749 |
| 9 | 1.000 | 0.991 | 0.776 |

### Dentro del último inning (decisión PA-a-PA)

Factor p50 por posición de PA en el inning final (SMOOTH):

| Dur | PA1 | PA2 | PA3 | PA4 | PA5 | PA6 | PA7 | PA8 | PA9 | piso |
| --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | ---: |
| 3 | 1.000 | 0.982 | 0.910 | 0.800 | 0.678 | 0.543 | 0.463 | 0.410 | 0.379 | 0.350 |
| 6 | 0.901 | 0.848 | 0.805 | 0.730 | 0.670 | 0.600 | 0.538 | 0.487 | 0.453 | 0.355 |
| 9 | 0.813 | 0.773 | 0.733 | 0.693 | 0.644 | 0.607 | 0.564 | 0.518 | 0.491 | 0.368 |

### Veredicto 001C-5

- **`{33, 67, 100}` valida como hipótesis.** Estructuralmente las tres
  duraciones cuentan la misma historia: ~68% del trabajo en w≤1, cruce de w=1
  entrando al último tercio (1.00/0.83/0.78), deterioro progresivo en el último
  tercio y **w≥1.50 sólo aparece en el inning final** en las tres.
- **Resultado ofensivo normalizado casi idéntico**: K% 32.1/33.0/33.1,
  BB% 9.5/9.3/9.3, BIP% 58.5/57.7/57.6, Pit/PA 3.66/3.67/3.67.
- **El juego de 3 innings es el más duro en el último tercio** (factor 0.652,
  9.6% de PAs en >1.50) por granularidad gruesa. Es esperado y aceptable: no se
  deforma el threshold para forzar los cuatro estados narrativos donde no caben.
  Aun así, dentro del inning 3 el factor recorre 1.000→0.350, así que existe
  decisión real de aguantar/llamar bullpen incluso en un juego corto.
- **No se fatiga por inning sino por pitch count**: verificado por diseño y por
  que las fracciones de cruce dependen del workload relativo, no del inning.
- **PASS.** Evidencia suficiente para `001C-6`. Fórmula de producción
  (`threshold = round(100 * total_innings / 9)`), con tratamiento explícito de
  las duraciones soportadas; reemplaza `FATIGUE_THRESHOLDS = {3:6, 6:15, 9:25}`
  y el docstring obsoleto `FATIGUE-DOC-001`. Implementado en `001C-6` ↓.

## 001C-6 · Implementación de producción (Fatigue Policy v2)

Implementado y verificado. Commit aislado (sin CPU bullpen, Stuff ni
telemetría). Cambio pequeño: sustituir la política, no rediseñar el sistema.

### Contrato v2 (`backend/app/engine/fatigue_manager.py`)

```text
STANDARD_GAME_INNINGS      = 9
STANDARD_PITCH_THRESHOLD   = 100
FATIGUE_FLOOR              = 0.35
FATIGUE_SIGMA              = 0.55

get_pitch_threshold(innings) = max(1, round(100 * innings / 9))
    3 → 33   6 → 67   9 → 100   (1→11, 2→22, 4→44, 5→56, 7→78, 8→89, 12→133, 18→200)

w = pitch_count / threshold
factor = 1.0                                       si w <= 1
factor = 0.35 + 0.65 * exp(-((w - 1) / 0.55)**2)   si w > 1
attr   = max(1, int(attr * factor))
```

`get_fatigue_factor(pitch_count, threshold)` se extrajo como función testeable;
`apply_pitcher_fatigue` es ahora sólo su consumidor (pipeline
`count → threshold → workload → factor → attrs`). Se eliminó
`FATIGUE_THRESHOLDS = {3: 6, 6: 15, 9: 25}` y `FATIGUE_PENALTY_STEP`.

### Archivos

- `app/engine/fatigue_manager.py` — política v2 + docstrings (corrige
  `FATIGUE-DOC-001`).
- `tests/test_fatigue_curve.py` — contratos v2 + puntos SMOOTH congelados
  (w=1.10 → 0.9788636821; 1.25 → 0.8786680830; 1.50 → 0.6344410658;
  2.00 → 0.3738357663; alto → 0.35). Incluye escala relativa entre 33/67/100.
- `tests/test_fatigue_manager.py` — onset v2 (9 inn: 100→0, 101→10, 104→40,
  107→70, 110→100).
- `tests/test_game_actions_fatigue.py` — fixture del test de propagación
  actualizada al onset v2 (130→131 pitches en vez de 30→31).
- `scripts/simulate_fatigue_impact.py` — **política legacy CONGELADA**
  (`LEGACY_THRESHOLDS {3:6,6:15,9:25}`, `LEGACY_PENALTY_STEP 0.10`,
  `legacy_apply_pitcher_fatigue`) para reproducir los experimentos 001B sin
  depender de producción. Ya no importa los helpers de `fatigue_manager`.

`game_actions.py` no requirió cambios funcionales (001A ya lo consume bien).

### Gate de regresión

```text
test_fatigue_curve.py + test_fatigue_manager.py + test_game_actions_fatigue.py
+ test_card_presenter.py + test_phase1_consumer_inventory.py
+ test_game_actions_persistence.py   → 60 passed
suite completa                       → passed (sin fallos)
```

El contrato de 001A se mantiene: el factor SMOOTH se propaga a los atributos
**pitch-specific** (el test de `resolve_swing` lo verifica).

### Deuda registrada

```text
GAMEPLAY-FATIGUE-CPU-001 — OPEN

Fatigue Policy v2 alinea el ONSET de UI/CPU con el engine, pero no la magnitud:
compute_fatigue_level conserva la fórmula legacy (+10%/extra, cap 100).

- onset compartido: get_pitch_threshold()
- severidad NO equivalente al factor SMOOTH
- CPU thresholds 40/65/95 NO calibrados para v2
- fatigue_level de UI NO es representación exacta del factor SMOOTH

Follow-up: recalibrar/reemplazar la semántica de fatigue_level (UI/CPU)
después de 001C-6. No mezclar con el commit de política física.
```

## 001D-1 · Characterize current CPU behavior under Policy v2

Primer paso de **GAMEPLAY-FATIGUE-CPU-001** (deuda registrada en 001C-6). **Sin
tocar código productivo**: sólo se leen `compute_fatigue_level` y
`get_cpu_pitcher_change_decision` tal como están hoy, sobre outings SMOOTH v2
(`threshold=100`, 9 innings). `--mode d1`.

Método (10,000 outings por matchup; MID/WEAK/STRONG): se camina PA a PA y se
registra, por salida, el **primer PA en que la CPU es elegible** para cambiar
(`compute_fatigue_level() >= umbral de dificultad`, que es cuando el engine
evalúa la decisión — `game_actions.py:586-601`), más el primer cambio
**efectivo** (con `_CPU_CHANGE_PROBABILITY`). En ese instante se guardan inning,
`pitch_count`, workload (`pc/100`) y el **factor SMOOTH real** del engine
(`get_fatigue_factor`). Es la evidencia que justifica con qué reemplazar
`fatigue_level`.

### Trigger nominal analítico

`level = 10·(pc − 100)`; primer entero con `level >= umbral`:

```text
   Dif  level umbral |   pc      w   factor SMOOTH
  HARD         40.0 |  104   1.04          0.9966
MEDIUM         65.0 |  107   1.07          0.9896
  EASY         95.0 |  110   1.10          0.9789
```

### Elegibilidad determinística (primer PA elegible)

```text
MID        inn p50/p90   pc p50/p90   w p50/p90    factor p50/p90   %outings
  HARD          7 / 8     105 / 108   1.05 / 1.08  0.9947 / 0.9966     99.6%
MEDIUM          7 / 8     108 / 111   1.08 / 1.11  0.9864 / 0.9896     99.1%
  EASY          7 / 9     111 / 114   1.11 / 1.14  0.9745 / 0.9789     98.5%

WEAK
  HARD          7 / 8     105 / 108   1.05 / 1.08  0.9947 / 0.9966     99.9%
MEDIUM          7 / 8     108 / 111   1.08 / 1.11  0.9864 / 0.9896     99.7%
  EASY          7 / 8     111 / 114   1.11 / 1.14  0.9745 / 0.9789     99.5%

STRONG
  HARD          7 / 9     105 / 108   1.05 / 1.08  0.9947 / 0.9966     99.1%
MEDIUM          8 / 9     108 / 111   1.08 / 1.11  0.9864 / 0.9896     98.3%
  EASY          8 / 9     111 / 114   1.11 / 1.14  0.9745 / 0.9789     97.0%
```

Cambio efectivo (con probabilidad) en MID: HARD inn 7/8 · MEDIUM inn 7/8 ·
EASY inn 8/9; el `%outings` baja a 96–99%.

### Veredicto 001D-1

- **Confirma la hipótesis.** Las tres dificultades disparan el cambio en la
  franja `w ≈ 1.05–1.11`, donde el factor SMOOTH está en **0.97–0.99**: el
  pitcher está **casi completamente sano según el engine real**.
- **Las dificultades apenas se diferencian**: sólo ~5–6 lanzamientos y ~2
  centésimas de factor separan HARD de EASY; las tres cambian prácticamente en
  el mismo inning (7–8).
- Consecuencia de diseño: `fatigue_level` legacy **no debe seguir siendo el
  input estratégico de la CPU**. Hay que reconstruir la decisión sobre el
  gradiente real ya validado (`w≈1.00` sano → `1.10` primera señal → `1.25`
  riesgo → `1.50` deterioro), para que HARD sea anticipatoria, MEDIUM
  equilibrada y EASY tolere más deterioro.

Reproducibilidad: `scripts/compare_fatigue_curves.py` ahora **congela la misma
política legacy** que `simulate_fatigue_impact.py` (definición duplicada y
documentada) y ya no importa helpers de producción; de lo contrario su
etiqueta `CURRENT` habría pasado a mostrar v2 tras 001C-6.

## 001D-2 · Fatigue signal semantics (contrato)

Decisión: **la señal estratégica canónica de la CPU es `workload`**, no
`fatigue_level` (legacy) ni `fatigue_factor`.

```text
workload       = pitch_count / get_pitch_threshold(total_innings)   → señal estratégica CPU
fatigue_factor = get_fatigue_factor(pitch_count, threshold)          → degradación física del outcome engine
fatigue_level  = compute_fatigue_level(...)                          → abstracción legacy; YA NO autoritativa para CPU
```

`workload` describe **en qué zona de utilización está el pitcher** y es
independiente de la duración (3 inn → 33, 6 → 67, 9 → 100; la CPU no necesita
saber si son 40, 80 o 120 pitches). `fatigue_factor` describe cuánto han caído
los atributos.

Bandas (derivadas de los puntos ya usados en 001B/001C, **no** constantes
nuevas). Implementadas como `WORKLOAD_BANDS` / `workload_band()` en el harness:

```text
HEALTHY        w <= 1.00            factor 1.000   sano
EARLY_FATIGUE  1.00 < w <= 1.10     factor ~0.98   primeras señales
MANAGEABLE     1.10 < w <= 1.25     factor ~0.88   riesgo manejable
HIGH_RISK      1.25 < w <= 1.50     factor ~0.63   deterioro importante
SEVERE         w > 1.50             factor → 0.35  piso
```

**No** se fijan aquí los thresholds de dificultad (eso es 001D-3/001D-4).

## 001D-3 · CPU change strategies (workload-based) × matchup

Comparación de tres políticas LAB (`--mode d3`, 10,000 outings/matchup). No son
todavía EASY/MEDIUM/HARD: primero se caracteriza su comportamiento. La CPU
considera el cambio al alcanzar el workload, respetando `MIN_PITCHES_TO_CHANGE`
y el requisito de cambio legal. Outing completo de 9 innings como stream
compartido; cada política corta en su primer PA elegible.

```text
AGGRESSIVE → w >= 1.10     (≈110 pitches a 9 inn)
BALANCED   → w >= 1.25     (≈125 pitches)
TOLERANT   → w >= 1.50     (≈150 pitches)
```

### Resultados (mediana)

```text
AGGRESSIVE   removed 96.8–99.5%  factor@removal ~0.975  (<6 inn: STRONG 9.6% / MID 18.1% / WEAK 35.9%)
             PA: HEALTHY 92%  EARLY 8%   (nunca MANAGEABLE+)
BALANCED     removed 79.7–95.3%  factor@removal ~0.87   (<6 inn: STRONG 1.7% / MID 4.5% / WEAK 13.8%)
             PA: HEALTHY 82%  EARLY 8%  MANAGEABLE 11%   (nunca HIGH_RISK+)
TOLERANT     removed 30.5–67.6%  factor@removal ~0.63   never: STRONG 69.5% / MID 54.6% / WEAK 32.4%
             PA: HEALTHY 69–74%  EARLY 7%  MANAGEABLE 10%  HIGH_RISK 10–14%
```

### Veredicto 001D-3

- **Las tres políticas producen regímenes físicos claramente distintos**, no
  comprimidos como el legacy (001D-1): AGGRESSIVE retira casi sano (factor ~0.97),
  BALANCED roza el riesgo manejable (~0.87), TOLERANT atraviesa deterioro
  importante (~0.63).
- **Preservan la diferenciación por matchup** (propiedad de 001C-4): STRONG
  trabaja menos → se retira más tarde / completa más; WEAK trabaja más → se
  retira antes. Orden `STRONG > MID > WEAK` en "nunca removido" y en inning de
  retiro. El threshold de decisión **no** destruye la diferenciación.
- El `pitch@removal` es casi idéntico entre matchups (~112/126/152) por
  construcción (workload relativo): la diferenciación vive en **cuándo** dentro
  del juego, no en el count absoluto.
- Ninguna política llega a SEVERE (>1.50) en el percentil mediano; TOLERANT es
  la única con exposición material a HIGH_RISK.

Siguiente (001D-4): mapear estas políticas (o combinaciones contextuales) a
EASY/MEDIUM/HARD. No asumir automáticamente `HARD=AGGRESSIVE`; una dificultad
mayor no implica sacar antes al pitcher. v1 = heurística por workload; futuro =
workload + marcador/leverage + inning + calidad del bullpen + matchup +
rendimiento reciente. UI (001D-5) queda aparte.

## 001D-4 · Precio estratégico de esperar + mapeo a dificultad

`--mode d4`, 10,000 outings/matchup. **4A** amplía el barrido a
`1.10/1.20/1.25/1.35/1.50`; **4B** mide el coste marginal de esperar (outcomes
por ventana de workload sobre el stream completo, sin retiro); **4C** propone el
mapeo a EASY/MEDIUM/HARD. Sigue **sin tocar `cpu_ai.py`**.

### 4A · Retiro por política (mediana; % outings)

```text
thr    STRONG removed/never inn factor | MID removed/never inn factor | WEAK removed/never inn factor
1.10    97.0 / 3.0  8  0.9745  |  98.6 / 1.4   7  0.9745  |  99.7 / 0.3   7  0.9745
1.20    87.1 / 12.9 8  0.9118  |  93.2 / 6.8   8  0.9118  |  97.8 / 2.2   7  0.9118
1.25    79.7 / 20.3 8  0.8698  |  88.0 / 12.0  8  0.8698  |  95.9 / 4.1   8  0.8698
1.35    60.6 / 39.4 9  0.7735  |  73.5 / 26.5  8  0.7735  |  88.2 / 11.8  8  0.7735
1.50    31.1 / 68.9 9  0.6251  |  46.3 / 53.7  9  0.6251  |  68.0 / 32.0  8  0.6251
```

### 4B · Coste marginal de esperar (Δ vs banda sana w<=1.00; MID)

```text
ventana     PA/out    K%     BB%    Reach%   ΔReach    ΔK
sano        27.88   36.07   8.68   33.65    +0.00   +0.00
1.00-1.10    2.70   34.84   9.11   34.32    +0.66   -1.23   prácticamente gratis
1.10-1.20    2.63   32.91   9.24   34.71    +1.06   -3.16   casi gratis
1.20-1.25    1.24   30.51  10.17   37.17    +3.52   -5.56   coste empieza
1.25-1.35    2.25   27.27  10.48   38.94    +5.28   -8.80   coste claro
1.35-1.50    2.53   21.82  11.88   41.56    +7.91  -14.25   coste fuerte
>1.50        2.51   15.32  12.86   44.98   +11.32  -20.75   severo
```

El mismo patrón (convexo) en STRONG y WEAK; WEAK es más plano (ya arranca
tocado). Dato clave: **hasta ~1.20 esperar no cuesta nada** (`ΔReach +1.06`,
`ΔK −3.16`); el coste se acelera a partir de 1.20–1.25 y es fuerte en 1.35–1.50.

### 4C · Mapeo recomendado (data-driven)

Cada dificultad corta **al inicio del siguiente régimen de coste**, no en un
número arbitrario. Esto evita el problema del legacy `40/65/95`: no se cambia un
pitcher casi sano sólo por cruzar una regla.

```text
HARD   → w >= 1.20   (factor ~0.91)  evita el régimen de coste moderado; a 1.10 no gana nada
MEDIUM → w >= 1.35   (factor ~0.77)  tolera la ventana moderada; corta antes del coste fuerte
EASY   → w >= 1.50   (factor ~0.63)  tolera claramente más deterioro; corta antes del severo
```

Propiedades: `% removed / never` monótono HARD > MEDIUM > EASY; STRONG trabaja
menos y llega más tarde. `HARD = AGGRESSIVE (1.10)` se descarta por artificial.

**v1 = heurística por workload.** No es diseño permanente: el futuro añade
marcador/leverage, inning, calidad del bullpen, matchup y rendimiento reciente.
Un HARD no debe implicar "sacar siempre antes", sino "evitar exposición costosa".

### Cierre 001D-4

```text
GAMEPLAY-FATIGUE-CPU-001D-4 — CLOSED / PASS

CPU bullpen heuristic v1 candidates:

HARD   → workload >= 1.20
MEDIUM → workload >= 1.35
EASY   → workload >= 1.50

Rationale:
HARD
  acts when waiting begins to have measurable cost
  factor ≈ 0.91

MEDIUM
  tolerates clear but moderate deterioration
  factor ≈ 0.77

EASY
  tolerates substantial deterioration
  factor ≈ 0.63

Not a permanent strategic model.
Future CPU strategy may additionally consider:
score leverage, inning, matchup, bullpen quality,
recent performance and game context.
```

No se afinan decimales (`1.25/1.30/1.40`): el sweep entregó **regímenes de
coste**, no un óptimo. Lo que valida el mapeo es la frontera
`≤1.10 gratis · 1.10–1.20 barato · 1.20–1.25 empieza · 1.25–1.35 claro ·
1.35–1.50 fuerte · >1.50 severo`; HARD=1.20 = "empezar a protegerse justo
cuando esperar deja de ser barato".

## 002A · Plate discipline / count diagnostics

Cerrado con 300,000 PA (100k × 3 políticas LAB), MID vs MID, **fatiga congelada**
en 75% (factor 1.0) para aislar la dinámica del count.

### Resultados (100k PA/política)

| Política | K% | BB% | BIP% | P(3bolas) | P(2str) | P(full) | P(BB\|3bol) | P(K\|2str) | Pit/PA | ≥3 | ≥6 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT_LAB (35/25/10) | 29.30 | 0.03 | 70.67 | 0.31 | 39.07 | 0.18 | **9.42** | 75.01 | 2.55 | 55.0 | 1.0 |
| PATIENT (50/35/15) | 33.92 | 0.15 | 65.93 | 0.88 | 45.58 | 0.53 | 17.14 | 74.41 | 2.78 | 62.6 | 1.7 |
| VERY_PATIENT (65/50/25) | 41.56 | 0.52 | 57.92 | 2.30 | 55.41 | 1.49 | 22.75 | 75.01 | 3.07 | 72.1 | 3.1 |

| Política | Take/PA | TBall/PA | TCall/PA | Swing/PA | Whiff/PA | BIP/PA |
|---|---:|---:|---:|---:|---:|---:|
| CURRENT_LAB | 0.652 | 0.199 | 0.453 | 1.900 | 0.814 | 0.707 |
| PATIENT | 1.002 | 0.306 | 0.696 | 1.773 | 0.761 | 0.659 |
| VERY_PATIENT | 1.514 | 0.463 | 1.051 | 1.559 | 0.669 | 0.579 |

### Veredicto de hipótesis

- **A (TAKE demasiado poco): descartada como causa principal.** Incluso con
  VERY_PATIENT (TAKE 65/50/25) el BB% llega sólo a 0.52%. La disciplina sube el
  BB ~17× (0.03→0.52) pero en términos absolutos sigue siendo inexistente.
- **B (TAKE → demasiados called strikes): CONFIRMADA.** Called strike por take
  ≈ **69.5%** constante en las tres políticas. Con Control=80 / Vision=70 la
  fórmula da `strike_chance = 0.65 + (80−50)·0.003 − (70−50)·0.002 = 0.70`.
  En MLB real la frecuencia de called strike en toma es ~15–20% y la de bola
  ~38–42%. El take está brutalmente pitcher-favorable.
- **C (SWING → BIP prematuro): CONFIRMADA.** Pit/PA 2.55, P(≥3) 55%, P(≥6) 1%.
  Un PA fresco muere antes de desarrollar count; P(BB|3bolas)=9.4% en
  CURRENT_LAB: incluso con 3 bolas acumuladas, el engine casi nunca entrega la
  4ª bola (la siguiente toma es called strike ~70% o el swing → BIP/K).

### Conclusión 002A

`BB≈0` NO es un artefacto del agente experimental: es un problema estructural
del calculator. La cadena se rompe en B y C. La política (A) es un lever lineal
pero insuficiente. Siguiente paso: 002B (Control × Vision) para comprobar que
los atributos ordenan la superficie en la dirección correcta antes de tocar
fórmulas.

## 002B · Control × Vision sensitivity (3×3 factorial)

Cerrado con 450,000 PA (50k × 9 celdas). Fatiga congelada al 75% (factor 1.0),
velocity 90, movement 85, power/contact 70 (todo MID), política CURRENT_LAB
35/25/10. Mismas seeds por rep entre celdas (la única variable son los ratings).

Escala ratings-2.0 real: `40..99` (`percentile_rating`, percentiles.py) →
terciles LAB documentados: **LOW=45, MID=70, HIGH=95**.

### Called strike por TAKE (MC) vs fórmula analítica

`take_strike_probability = 0.65 + (CTL−50)·0.003 − (VIS−50)·0.002` (clamp 25–85%)

| CTL\VIS | LOW 45 | MID 70 | HIGH 95 |
|---|---:|---:|---:|
| LOW 45  | 64.20 / 64.50 | 59.16 / 59.50 | 53.94 / 54.50 |
| MID 70  | 71.47 / 72.00 | 66.55 / 67.00 | 61.62 / 62.00 |
| HIGH 95 | 78.96 / 79.50 | 73.91 / 74.50 | 69.03 / 69.50 |

(MC vs fórmula en porcentaje.) El MC sigue la fórmula analítica a
~0.5pp: el engine replica la superficie esperada, no la distorsiona.

### Matrices pedidas

| CTL\VIS | BB% LOW | BB% MID | BB% HIGH | P(3 bolas) LOW | P(3) MID | P(3) HIGH | Pit/PA LOW | Pit/PA MID | Pit/PA HIGH |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LOW 45  | 0.07 | 0.11 | 0.15 | 0.46 | 0.66 | 0.92 | 2.57 | 2.59 | 2.62 |
| MID 70  | 0.03 | 0.05 | 0.09 | 0.26 | 0.40 | 0.57 | 2.54 | 2.56 | 2.58 |
| HIGH 95 | 0.01 | 0.02 | 0.03 | 0.08 | 0.21 | 0.31 | 2.51 | 2.53 | 2.55 |

### Veredicto

- **Control y Vision ordenan la superficie correctamente y con sensibilidad
  limpia**: CTL↑ ⇒ llamadas furiosas (llamado strikes↑, bolas↓, BB↓) y VIS↑ ⇒
  count profundo↑. Sin fallos de dirección en ninguna celda. Los atributos de
  ratings-2.0 están bien conectados al calculator en el plano del strike zone.
- **Pero el efecto absoluto es residual**: mover CTL 45→95 o VIS 45→95 cambia
  BB% en ~0.1pp. El problema estructural de 002A (called strike ~70% + SWING→BIP
  en pitch 2–3) domina por completo; la sensibilidad de ratings es un ajuste
  fino, no un lever.
- **P(BB|3bolas) impuro**: la fila HIGH es ruido/anti-monótona (10–12%) porque
  llegar a 3 bolas con CTL HIGH es rarísimo (0.08–0.31%) → pequeños n.

### Conclusión 002B

No es necesario rediseñar el conector de atributos: solo recalibrar los
**niveles** del strike zone (B de 002A) y de la terminación de count (C). Pasar a
002C.

## 002C-B · TAKE baseline sweep (intercepto de strike_chance)

Cerrado con 400,000 PA (100k × 4 baselines). MID/MID, fatiga congelada 75%,
política CURRENT_LAB 35/25/10. **Production intacta**: `calculate_play_outcome`
gana `take_bias: float = None` (None → 0.65); la variante CURRENT reproduce el
comportamiento actual. Coefs CTL/VIS SIN tocar (0.003 / −0.002).

| Variante | Base | CalledS/take | Ball/take | K% | BB% | BIP% | P(3bolas) | P(full) | P(BB\|3bol) | Pit/PA | ≥3 | ≥4 | ≥6 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CURRENT | 0.65 | 69.52 | 30.48 | 29.30 | 0.03 | 70.67 | 0.31 | 0.18 | 9.42 | 2.55 | 55.0 | 18.4 | 1.0 |
| TAKE-B1 | 0.50 | 54.54 | 45.46 | 27.75 | 0.15 | 72.10 | 0.95 | 0.53 | 15.81 | 2.62 | 55.2 | 21.9 | 1.7 |
| TAKE-B2 | 0.40 | 44.37 | 55.63 | 26.55 | 0.35 | 73.10 | 1.64 | 0.85 | 21.42 | 2.66 | 55.4 | 24.2 | 2.2 |
| TAKE-B3 | 0.30 | 34.36 | 65.64 | 25.32 | 0.66 | 74.02 | 2.62 | 1.29 | 25.24 | 2.71 | 55.5 | 26.3 | 2.8 |

(CalledS/take teórico por fórmula CTL80/VIS70: 0.70 / 0.55 / 0.45 / 0.35; el MC
lo sigue a ~0.5pp.)

### Veredicto 002C-B

- **El intercepto funciona como lever**: baja called strike/take 69.5→34.4%, sube
  BB% 0.03→0.66 (~22×), P(3bolas) 0.31→2.62%, P(full) 0.18→1.29%. Dirección y
  magnitud sanas, y no rompe K (29.3→25.3 K%) ni BIP (sigue siendo la terminación
  dominante, 70.7→74.0%).
- **PERO el efecto absoluto sigue siendo residual**: aun con base 0.30 (called
  strike al 34%, radicalmente bateador-favorable) el BB% es 0.66% y Pit/PA solo
  sube a 2.71. La cadena sigue rompiéndose en C: el SWING termina el PA en
  pitch 2–3 antes de que el count profundo (3+ bolas) tenga oportunidad de
  existir.
- **La estructura de TAKE no necesita cambio de forma**: su superficie
  CTL/VIS es sana y responde a calibración de nivel. El lever B es *necesario*
  pero *insuficiente* en soledad.
- **Candidatas para el factorial B×C**: TAKE-B2 (0.40) y TAKE-B3 (0.30) —
  preservan K mientras hacen P(3bolas) y P(BB|3bol) significativamente mayores.

## 002C-C · Swing termination sweep (foul/contact)

Cerrado con 400,000 PA (100k × 4 foules). TAKE vuelve a CURRENT (0.65) para
aislar C. **Production intacta**: `foul_chance: float = None` en
`calculate_play_outcome` (None → 35.0). NO se tocó el whiff model ni la regla
zona+tipo. MID/MID, fatiga congelada 75%, política CURRENT_LAB 35/25/10.

| Foul% | Foul/Cnt | BIP/Cnt | CalledS/tk | K% | BB% | BIP% | P(3bolas) | P(full) | P(BB\|3bol) | Pit/PA | p95 | max | ≥3 | ≥4 | ≥6 | ≥8 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 35 (prod) | 34.91 | 65.09 | 69.52 | 29.30 | 0.03 | 70.67 | 0.31 | 0.18 | 9.42 | 2.55 | 4 | 10 | 55.0 | 18.4 | 1.0 | 0.0 |
| 45 | 44.82 | 55.18 | 69.55 | 35.33 | 0.03 | 64.64 | 0.33 | 0.20 | 9.20 | 2.73 | 5 | 11 | 61.1 | 23.0 | 1.7 | 0.1 |
| 55 | 54.93 | 45.07 | 69.53 | 42.66 | 0.03 | 57.31 | 0.34 | 0.25 | 10.00 | 2.93 | 5 | 12 | 67.5 | 28.4 | 3.0 | 0.3 |
| 65 | 64.85 | 35.15 | 69.54 | 51.23 | 0.04 | 48.73 | 0.36 | 0.29 | 10.74 | 3.17 | 5 | 15 | 74.1 | 34.4 | 4.9 | 0.6 |

### Veredicto 002C-C

- **El parámetro LAB llega exactamente al sitio correcto**: Foul/Cnt reproduce
  la config (34.9/44.8/54.9/64.9 vs 35/45/55/65) y BIP/Cnt su complemento; BIP%
  global baja hasta 48.7%. CalledS/tk y whiff quedan invariantes (69.5,
  K% de whiff intacto): el sweep NO contaminó ni el TAKE ni el whiff model.
- **C en solitario NO produce BB**: BB% queda congelado en ~0.03–0.04 con
  TAKE sin cambios. Sorprendente pero coherente: el foul extiende el PA por
  el lado de los STRIKES (foul→strike), así que la supervivencia compra
  oportunidades de K, no de bolas. P(3bolas) solo va 0.31→0.36. **BB no viene
  de C solo**; viene de más oportunidades de TAKE, que C no crea.
- **El coste en K es alto**: K% 29.3→51.2 al subir foul a 65 (más foul = más
  strikes acumulados = más duelos a 2 strikes que terminan en K). Pit/PA sube
  hasta 3.17 y ≥6 a 4.9%, pero a costa de destruir BIP (70.7→48.7%).
- **Pit/PA gana sensibilidad sana (2.55→3.17 con p95 4→5, max 10→15)**, pero
  la causante es la acumulación de strikes, no bolas: la profundidad es una
  profundidad de strike, no de count.
- **Conclusión: C NO debe solucionarse aumentando fouls en soledad.** La
  abstracción `contact → foul|BIP` necesita profundidad mixta. La hipótesis de
  que "más supervivencia ⇒ más BB" es FALSA bajo la política actual porque la
  supervivencia compra strikes; SOLO se convierte en bolas cuando el TAKE puede
  aprovecharla (B). Esto predice que el factorial B×C será la interacción que
  revele el count real.
- **Candidatos C**: C1 (45%) como C-low y C2 (55%) como C-high — profundización
  moderada sin destruir K completamente; C3 (65%) genera K 51%, descartada
  como mayoritariamente strike-side.

## 002C-BC · Factorial TAKE×foul (B×C, interacción)

Cerrado con 500,000 PA (100k × 5 = PROD + 2×2). MID/MID, fatiga congelada 75%,
política CURRENT_LAB 35/25/10, whiff + zona/tipo intactos, shared seeds.

| Cell | K% | BB% | BIP% | OUT% | 1B% | HR% | Reach% | P(3bol) | P(full) | P(BB\|3bol) | Pit/PA | p95 | max | ≥3 | ≥4 | ≥6 | ≥8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| PROD | 29.30 | 0.03 | 70.67 | 38.90 | 15.44 | 8.49 | 31.80 | 0.31 | 0.18 | 9.42 | 2.55 | 4 | 10 | 55.0 | 18.4 | 1.0 | 0.0 |
| B2-C1 | 32.52 | 0.37 | 67.10 | 36.97 | 14.64 | 8.04 | 30.51 | 1.72 | 0.98 | 21.64 | 2.85 | 5 | 13 | 61.4 | 29.1 | 3.3 | 0.2 |
| B2-C2 | 39.85 | 0.41 | 59.74 | 32.96 | 13.01 | 7.18 | 27.20 | 1.85 | 1.16 | 22.13 | 3.08 | 6 | 13 | 67.8 | 34.9 | 5.1 | 0.5 |
| B3-C1 | 31.27 | 0.70 | 68.03 | 37.49 | 14.85 | 8.15 | 31.24 | 2.76 | 1.50 | 25.44 | 2.91 | 5 | 13 | 61.5 | 31.3 | 4.1 | 0.3 |
| B3-C2 | 38.58 | 0.75 | 60.67 | 33.47 | 13.21 | 7.29 | 27.96 | 2.95 | 1.78 | 25.46 | 3.14 | 6 | 14 | 67.9 | 37.1 | 6.2 | 0.6 |

| Cell | CalledS/tk | Foul/Cnt | BIP/Cnt | Whiff% | P(K\|≥4) | P(BB\|≥4) | P(BIP\|≥4) |
|---|---:|---:|---:|---:|---:|---:|---:|
| PROD | 69.52 | 34.91 | 65.09 | 42.86 | 55.83 | 0.16 | 44.01 |
| B2-C1 | 44.41 | 44.84 | 55.16 | 42.94 | 56.32 | 1.28 | 42.39 |
| B2-C2 | 44.39 | 54.93 | 45.07 | 42.98 | 61.79 | 1.17 | 37.04 |
| B3-C1 | 34.39 | 44.85 | 55.15 | 42.97 | 54.36 | 2.25 | 43.39 |
| B3-C2 | 34.39 | 54.93 | 45.07 | 43.01 | 59.99 | 2.02 | 37.98 |

### Veredicto 002C-BC

- **Sanidad del harness intacta**: CalledS/tk sigue la fórmula por B (0.70→0.44→0.34),
  Foul/Cnt sigue la config por C (35→45→55), Whiff% invariante por ambos (42.9). Los
  dos parámetros llegan al sitio correcto y no se contaminan.
- **B y C son unidireccionales y no se compensan**: B (bajar take) monetiza bolas
  (BB 0.03→0.70) y baja K ligeramente; C (subir foul) monetiza strikes (K 32→40,
  BIP 67→60). La interacción B3×C1/C2 no produce una región mixta: C solo sube K y
  B solo sube BB; prácticamente aditiva, no interactiva.
- **BB sigue < 1% en las 4 celdas (0.37–0.75)** → criterio de corte 002C
  cumplido: B×C NO basta. El count profundo puro ya existe (P(3bol) 2.76,
  P(full) 1.50, ≥3 61, ≥4 37, Pit/PA 2.91) pero la SUPERVIVENCIA va a strikes:
  P(K|≥4) ≈ 54–62% vs P(BB|≥4) ≈ 1–2%. Y la BIP total se hunde a ~60 (C)
  porque el contacto se convierte en foul→strike.
- **La abstracción `contact → foul | BIP` empuja todo a counts de strike.** El
  problema interesante: a 2 strikes la política LAB toma solo 10% → la bola se
  monetiza pero el PA muere por call/whiff en pitch de strike. La cadena B+C
  entrega "deep counts" pero casi todos terminan en K.
- **Decisión**: NO seguir bajando interceptos Ni subiendo fouls a fuerza (criterio
  del usuario). El freno ya no está en las dos constantes: está en la distribución
  de terminaciones del PA con count profundo. Cuestionar estructura: (a) qué
  compone la terminación a ≥4 pitches (P(K|≥4)=54-62% es la huella), (b) la
  política de TAKE a 2 strikes, (c) si `foul|BIP` debe tener una tercera vía.

## 002D · Two-strike discipline sensitivity

Cerrado con 500,000 PA (100k × 5 TAKE a 2 strikes). Config fija **B3-C1**
(TAKE baseline 0.30, foul 45%) con política 0/1 strikes = **65/50**
(VERY_PATIENT) deliberadamente, para aislar la decisión a 2 strikes. Mismas
seeds por PA.

| TAKE 2s | K% | BB% | BIP% | Pit/PA | p95 | max | P(3bol) | P(full) | P(K\|≥4) | P(BB\|≥4) | P(K\|2s) | P(BB\|2s) | P(TAKE\|2s) | Ball\|TAKE2s | Cs\|TAKE2s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% | 34.10 | 7.13 | 58.77 | 3.61 | 6 | 13 | 15.37 | 6.32 | 45.64 | 13.50 | 59.50 | 0.95 | 10.09 | 65.62 | 34.38 |
| 20% | 34.93 | 7.82 | 57.24 | 3.65 | 6 | 12 | 16.64 | 7.59 | 46.76 | 14.56 | 60.97 | 2.14 | 19.97 | 65.43 | 34.57 |
| 30% | 35.83 | 8.71 | 55.46 | 3.69 | 6 | 12 | 18.12 | 9.08 | 47.89 | 15.90 | 62.48 | 3.71 | 30.05 | 65.23 | 34.77 |
| 40% | 36.70 | 9.88 | 53.41 | 3.73 | 6 | 12 | 19.93 | 10.88 | 48.95 | 17.75 | 63.87 | 5.73 | 40.09 | 65.23 | 34.77 |
| 50% | 37.55 | 11.37 | 51.09 | 3.77 | 6 | 12 | 22.03 | 12.98 | 49.95 | 20.06 | 65.35 | 8.32 | 50.17 | 65.39 | 34.61 |

### Veredicto 002D

- **La cadena se abre**: con disciplina early (VERY_PATIENT 65/50) el BB% salta
  de 0.70 a **7.1–11.4%** incluso con TAKE a 2s bajo. Los counts profundos se
  construyen (P(3bol) 15–22%, P(full) 6–13%) y P(BB|≥4) llega a 13.5–20%.
- **Subir TAKE a 2 strikes monetiza más BB** (7.1→11.4 con 10→50%) y no quiebra
  la terminalidad: K sube solo 34→37.5 (costo leve, por more called-strikes en
  2s), BIP se mantiene dominante (59→51%), colas controladas (p95=6, max 12–13).
- **La trampa no apareció**: TAKE con dos strikes NO produce estallido de K; el
  duelo 34% called-strike / 66% ball de B3 hace que pet-take a 2s sobreviva más
  veces de las que mata. El candidato por-2s deja P(K|2s) ≈ 62 (con una vía real
  de BB ~4–8%).
- **El cuello de botella era DE AGENTE, no del calculator.** El `P(K|≥4)≈55-62%`
  de los bloques anteriores provenía en gran parte de la política CURRENT_LAB
  (tomas 35/25/10), no de una terminalidad estructural. No hace falta deformar
  el motor ni inventar la tercera vía (c).
- **No es el resultado extremo**: TAKE 2s al 50% da BB 11.4% (arriba de cualquier
  referencia), y el sweep 10–50 todas pasan el criterio 002C (BB expresable, K
  significativo, BIP dominante, Pit/PA>3, colas controladas). Candidata razonable:
  **B3-C1 + 65/50/30** (BB 8.71, K 35.83, BIP 55.5, Pit/PA 3.69, P(BB|≥4) 15.9).
- **Siguiente paso**: 002C-CV — volver a correr Control × Vision (45/70/95) sobre
  el candidato para verificar que CTL/VIS siguen ordenando con el baseline nuevo.

## 002C-CV · Control × Vision sobre el candidato 002D

Factorial 3×3 (CTL/VIS = 45/70/95) sobre el candidato 002D: **B3-C1** (TAKE
baseline 0.30, foul 45%) + política **65/50/30**. 450,000 PA (50k × 9 celdas).
Objetivo: confirmar que CTL/VIS no solo mueven CalledS/take sino el resultado
del PA (K%/BB%/BIP%/P(full)/Pit/PA), con magnitud material.

### CTL × VIS → resultado de PA

| CTL | VIS | CalledS/tk | K% | BB% | BIP% | P(3bol) | P(full) | Pit/PA |
| --: | --: | ---------: | -: | --: | ---: | ------: | ------: | -----: |
| 45 | 45 | 29.06 | 33.13 | 11.32 | 55.56 | 21.76 | 10.09 | 3.74 |
| 45 | 70 | 24.66 | 30.81 | 13.61 | 55.58 | 24.79 | 10.72 | 3.78 |
| 45 | 95 | 24.66 | 30.81 | 13.61 | 55.58 | 24.79 | 10.72 | 3.78 |
| 70 | 45 | 36.27 | 36.71 | 7.97 | 55.32 | 16.89 | 8.69 | 3.67 |
| 70 | 70 | 31.38 | 34.35 | 10.14 | 55.51 | 20.18 | 9.71 | 3.72 |
| 70 | 95 | 26.58 | 31.84 | 12.58 | 55.58 | 23.49 | 10.47 | 3.76 |
| 95 | 45 | 43.84 | 40.23 | 5.24 | 54.53 | 12.40 | 6.92 | 3.58 |
| 95 | 70 | 38.80 | 37.91 | 6.92 | 55.17 | 15.31 | 8.13 | 3.64 |
| 95 | 95 | 33.82 | 35.59 | 9.01 | 55.41 | 18.55 | 9.22 | 3.69 |

### Diagnóstico deep-count / 2-strike

| Cell | P(BB\|≥4) | P(K\|≥4) | P(BIP\|≥4) | P(BB\|2s) | P(K\|2s) | P(BIP\|2s) | P(TAKE\|2s) |
| :--- | --------: | -------: | ---------: | --------: | -------: | ---------: | ----------: |
| 45-45 | 19.93 | 44.09 | 35.98 | 4.96 | 60.87 | 34.17 | 30.16 |
| 45-70 | 23.35 | 40.92 | 35.74 | 5.80 | 59.67 | 34.53 | 30.08 |
| 45-95 | 23.35 | 40.92 | 35.74 | 5.80 | 59.67 | 34.53 | 30.08 |
| 70-45 | 14.71 | 49.04 | 36.25 | 3.56 | 62.84 | 33.60 | 30.03 |
| 70-70 | 18.15 | 45.76 | 36.09 | 4.47 | 61.57 | 33.96 | 30.11 |
| 70-95 | 21.80 | 42.34 | 35.85 | 5.40 | 60.31 | 34.29 | 30.13 |
| 95-45 | 10.29 | 54.04 | 35.68 | 2.41 | 64.86 | 32.74 | 30.28 |
| 95-70 | 13.02 | 50.78 | 36.20 | 3.12 | 63.46 | 33.42 | 30.08 |
| 95-95 | 16.38 | 47.44 | 36.19 | 3.96 | 62.30 | 33.75 | 29.92 |

### Veredicto 002C-CV

- **Contrato CTL (Vision fija), LOW→MID→HIGH**: CalledS ↑, BB ↓, K ↑ en las tres
  columnas de Vision. ✓ Cumplido y **material a nivel PA** (p.ej. a VIS MID:
  BB 13.61→10.14→6.92 ≈ 2×; K 30.81→34.35→37.91).
- **Contrato VIS (Control fijo), LOW→MID→HIGH**: CalledS ↓, BB ↑, K ↓ en CTL MID
  y CTL HIGH. ✓ En **CTL LOW se satura**: V70 y V95 idénticos (escalón MID→HIGH
  plano). No es ruido: es el clamp de producción `max(0.25, min(0.85,
  strike_chance))` en `calculator.py:118`.
- **Origen de la saturación**: con baseline 0.30, en el rincón CTL45/VIS≥70,
  `strike_chance = 0.30 − 0.015 − (vis−50)·0.002` cae a 0.245/0.195 y ambos
  pisan el piso 0.25. En 002B (base 0.65) ese rincón no tocaba el clamp, por eso
  no se veía. El clamp es pre-existente (producción), no introducido por LAB.
- **Integración**: CTL70/VIS70 reproduce el candidato 002D en BIP (55.51 vs 55.5)
  y Pit/PA (3.72 vs 3.69); K 34.35 vs 35.8 y BB 10.14 vs 8.7 difieren ~1.4pp en la
  dirección esperada (Control 70 es más débil que el 80 del bloque 002D → menos
  called-strikes, algo más de BB y algo menos de K). Consistente, no sospechoso.
- **P(BIP|2s) invariante** (32.7–34.5) en todo el factorial: el canal CTL/VIS solo
  toca la rama TAKE (llamado/bola), como se diseñó. Whiff no depende de CTL/VIS. ✓
- **Conclusión**: por primera vez un pitcher Control 95 se siente distinto de uno
  Control 45 (BB 5.2–13.6% según celda) y Vision 95 da ventaja observable frente
  a Vision 45, salvo el plateau en el rincón CTL45/VIS≥70 por el clamp.

**Pendiente de decisión (002C selección)**: el clamp 0.25 es una constante de
producción que en el régimen calibrado se vuelve binding. Opciones: (i) aceptarlo
como comportamiento de diseño (piso anti-absurdo), (ii) estrechar el rango del
factorial o (iii) revisar si el piso 0.25 debe bajar/acompañar el baseline. No se
toca producción sin decisión explícita.

## Tratamientos experimentales (LAB)

```python
CURRENT   → apply_pitcher_fatigue() real (pitch_count absoluto, sin clamps nuevos)
LINEAR    →  factor = max(0.50, 1.0 - 0.80 * (w - 1.0))           # LINEAR-0.8-F50
SMOOTH    →  factor = 0.35 + 0.65 * exp(-((w - 1.0) / 0.55) ** 2) # SMOOTH-0.55-F35
```

`w = workload normalizado = pitch_count / threshold`. Ambas con `factor = 1.0` explícito cuando `w <= 1.0`.

## Cierre 001B-3 · Pitch-level Monte Carlo (750k pitches)

1. CURRENT queda descartada como candidata de balance. No necesariamente eliminada de producción todavía: sigue siendo nuestro control experimental.
2. LINEAR y SMOOTH pasan a 001B-4. Ambas preservan una zona "fatigado pero competitivo".
3. SMOOTH retrasa mucho más el castigo inicial: 110% todavía se parece bastante al pitcher fresco.
4. LINEAR empieza a comunicar fatiga antes: produce una degradación más visible entre 100–125%.
5. A 150%, LINEAR y SMOOTH convergen suficientemente como para mantener al pitcher funcional pero deteriorado.
6. El calculator convierte la fatiga principalmente en:
   - ↓ Velocity/Movement → ↓ Whiff
   - ↓ Control → ↓ Called Strike
   - Ambos → ↑ BIP / Ball
7. La calidad condicional del contacto no empeora. Aumentan hits/XBH/HR principalmente porque aumenta el volumen de BIP.

El punto 7 es un **hallazgo del modelo**, no necesariamente un bug. Decidir si Movement/Stuff/fatiga deben influir en calidad de contacto queda fuera del alcance de 001B.

## 001B-4 · Full PA Monte Carlo

Cerrado con 750,000 PA (50k × 5 starting workloads × 3 curvas). MID vs MID, política LAB.

### Resultados clave (resumen)

| Curva  | Start | K% | BB% | BIP% | OUT% | 1B% | HR% | Reach% | Pit/PA |
| ------ | ----- | --- | ---- | ---- | ---- | --- | --- | ------ | ------ |
| CURRENT| 100% | 22.81 | 0.05 | 77.13 | 42.15 | 17.01 | 9.41 | 35.04 | 2.56 |
| CURRENT| 110% | 15.24 | 0.09 | 84.67 | 46.52 | 18.89 | 10.19 | 38.24 | 2.47 |
| CURRENT| 125% | 4.71 | 0.19 | 95.10 | 52.33 | 21.00 | 11.40 | 42.95 | 2.28 |
| CURRENT| 150% | 3.29 | 0.26 | 96.45 | 53.27 | 21.30 | 11.33 | 43.44 | 2.17 |
| LINEAR | 110% | 24.57 | 0.05 | 75.39 | 41.51 | 16.81 | 9.02 | 33.92 | 2.53 |
| LINEAR | 150% | 13.59 | 0.11 | 86.31 | 47.43 | 19.02 | 10.34 | 38.99 | 2.39 |
| SMOOTH | 110% | 27.32 | 0.04 | 72.64 | 40.07 | 16.11 | 8.68 | 32.61 | 2.55 |
| SMOOTH | 150% | 14.52 | 0.11 | 85.37 | 46.90 | 18.81 | 10.24 | 38.58 | 2.41 |

### Hallazgos

1. **BB ≈ 0 (0.03–0.26%)**: la política TAKE 35/25/10 + calculator produce
   prácticamente cero bases por bolas. Con ~2.5 pitches/PA nunca se juntan 4
   bolas. La política LAB no es usable si queremos expresión de BB; es un
   hallazgo de calibración (ball-rate del TAKE), no un bug.
2. **Aun arrancando en 100%, la fatiga intra-PA importa**: CURRENT pierde K%
   22.8→15.2 ya entre 100→110% start y SMOOTH solo 28.8→27.3. El precipicio de
   CURRENT muerde dentro del mismo turno (pitch 26+ del PA).
3. **LINEAR/SMOOTH mantienen K% en banda estrecha (resp. 13.6 y 14.5 K% a 150%);
   CURRENT colapsa a 3.3**. La "zona fatigado pero competitivo" es real en las
   dos candidatas.
4. **El hallazgo del modelo (punto 7 de 001B-3) se confirma a nivel PA**: la
   fatiga no degrada la calidad condicional del contacto; suben BIP/OUT/1B/HR
   por VOLUMEN de bolas en juego (todas suben proporcionalmente).
5. **Pit/PA cortos y estables (~2.2–2.6), max observado 17, 0 CAP**: sin bug de
   transición; los PA terminan rápido (50%+ por BIP en pitch temprano).

## 001B-4 detalles de diseño

- Transiciones de count reales sobre el dominio actual de `calculate_play_outcome()`:
  SWING_MISS/CALLED_STRIKE→strike (3er strike=K), BALL→ball (4ª bola=BB),
  FOUL→strike si <2 (se queda en 2 si ya hay 2), BIP→terminal OUT/1B/2B/3B/HR.
- Fatiga dinámica DENTRO de cada PA: pitch_count se incrementa por lanzamiento
  (31→32→33→…) y se recalcula; etiqueta = **starting workload**.
- Mismas seeds por PA entre CURRENT/LINEAR/SMOOTH (seed = int(w*1000)*10^6 + rep).
- CURRENT se reproduce fielmente sin estabilizarla ni clamps nuevos (floor = 1 real).
- Red de seguridad: `MAX_PA_PITCHES = 100` (0 PA alcanzado en esta corrida).

## 001B-1 · CURRENT characterization · CLOSED

- Thresholds 3/6/9 → 6/15/25; `get_pitch_threshold` interpola `max(6, int(60/9*inn))`.
- `apply_pitcher_fatigue`: factor = 1 − 0.10·extra sin clamp, `attr = max(1, int(attr·factor))`
  (único clamp: floor 1). +10 extra → 1/1/1 (precipicio).
- `compute_fatigue_level`: nivel lineal 10%/extra, cap 100 — es la función que
  informa UI/CPU; semánticamente distinta de `apply_pitcher_fatigue` aunque
  derivan ambas del mismo factor. (Ver la decisión pendiente de 001B-6: si ambas
  representan la misma función o tienen semánticas deliberadamente distintas.)