# Estrategia base

## Motores

### M1 — Global bloqueado
Solo existe un candidato pendiente. Hasta confirmar/invalidad no nace otro.

### M3 — Global reemplazable
Un candidato posterior válido puede sustituir el pendiente.

## Rangos

### R4 — cuerpo actual
Cuerpo de la primera vela contraria.

### R7 — mecha previa + cuerpo actual
Bajista: `High[1] → parte inferior cuerpo actual`.
Alcista: `parte superior cuerpo actual → Low[1]`.

### R8 — cuerpo previo + mecha actual
Bajista: `parte superior cuerpo previo → Low actual`.
Alcista: `High actual → parte inferior cuerpo previo`.

## Confirmación
Las mechas posteriores no resuelven el candidato.
- bajista: `close < bottom`;
- alcista: `close > top`.

La ruptura por el extremo opuesto invalida.

## Benchmark de trading
- alcista confirmado → LONG;
- bajista confirmado → SHORT;
- señal contraria cierra y revierte;
- retorno medido desde precio de confirmación.
