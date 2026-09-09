# The two-arrival activation window, checked against the engine's own quantile

`DIAGNOSTIC_NOT_CLAIM`. Round 11A gives an exact condition for the mechanism where a beam
holding one or two users selects no transmitted mode, while three users activate one.
It is `q*Gamma(n) < gamma_min` for n = 1 and 2, and `>= gamma_min` for n = 3.

modes in the engine table: 28
lowest threshold gamma_min: 0.7174947935 linear, -1.441812 dB

| n | required SE | target mode | Gamma(n) dB | gamma_min/Gamma(n) |
|---:|---:|---|---:|---:|
| 1 | 0.3000 | QPSK 1/4 | -1.441812 | 1.0000000000 |
| 2 | 0.6000 | QPSK 2/5 | 0.608188 | 0.6237348355 |
| 3 | 0.9000 | QPSK 3/5 | 3.138188 | 0.3483373150 |
| 4 | 1.2000 | QPSK 3/4 | 4.938188 | 0.2301441817 |
| 5 | 1.5000 | 8PSK 2/3 | 7.528188 | 0.1267651866 |
| 6 | 1.8000 | 8PSK 3/4 | 8.818188 | 0.0941889597 |
| 7 | 2.1000 | 16APSK 2/3 | 9.878188 | 0.0737904230 |

**Two-arrival window from the engine's own table:** 0.3483373150 <= q < 0.6237348355
equivalently 2.0500 dB < M <= 4.5800 dB, with M = -10 log10 q

Round 11A computed 0.3483373150 <= q < 0.6237348355, that is 2.05 < M <= 4.58 dB.

## The engine's actual quantile
found `channel.fading_product_quantile`

| elevation deg | q10 | M dB | inside the two-arrival window? |
|---:|---:|---:|---|
| 10.0 | 0.42923539 | 3.6730 | YES |
| 20.0 | 0.53431848 | 2.7220 | YES |
| 30.0 | 0.51210438 | 2.9064 | YES |
| 40.0 | 0.46632501 | 3.3131 | YES |
| 50.0 | 0.42017210 | 3.7657 | YES |
| 60.0 | 0.37823375 | 4.2224 | YES |
| 90.0 | 0.77494862 | 1.1073 | no |
