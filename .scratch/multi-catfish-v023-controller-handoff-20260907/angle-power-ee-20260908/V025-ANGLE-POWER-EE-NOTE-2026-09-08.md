# V0.25 angle → power → energy-efficiency KAT

This is a deterministic synthetic-link demonstration of the sealed primary
`a-r0` (`V025-ANGLE-RATE-TPC-TDM-ACM`) and fixed-RF reference `b0`.  It uses
one physical beam, no interference or fading, 2,000 km slant range, 10°
elevation, and sweeps transmit off-axis angle from boresight to the 1.66°
half-power pattern edge.  All users at occupancy \(n_b\) have the same link
and receive equal full-band TDM airtime.  Thus the table's beam bits are the
sum over \(n_b\) symmetric users; EE is beam bits divided by one beam's
partial-payload energy.

## Exact equations

With \(W=500\times10^6/3\) Hz, \(\Delta=47(0.640)=30.08\) s,
\(T_{sys}=150+290(10^{1.2/10}-1)\), and \(N=k_B T_{sys}W\),

\[
\begin{aligned}
\mu(\theta)&=2.07123\,\frac{\sin\theta}{\sin(3.32^\circ/2)},\\
G^T(\theta)&=2000\left[\frac{J_1(\mu)}{2\mu}
                 +36\frac{J_3(\mu)}{\mu^3}\right]^2,
\quad G^T(0)=2000,\\
L(10^\circ)&=\frac{0.25}{\sin 10^\circ}+1.08
             =2.5196926207859085\ \mathrm{dB},\\
\hat h(\theta)&=G^T(\theta)
 \left(\frac{c/f_c}{4\pi(2{,}000\times10^3)}\right)^2
 10^{-L/10}10^{35/10}\\
&=G^T(\theta)(6.296981727548675\times10^{-16}),\\
SE_m&=\frac{\eta_m}{1+0.20},\\
\gamma_m&=10^{[E_s/N_{0,m}+1.7-10\log_{10}(1+0.20)]/10},\\
m_r(n_b)&=\arg\min_m\{\gamma_m:W SE_m/n_b\ge50{,}000{,}000\},\\
\Gamma_r(n_b)&=\max(\gamma_{m_r(n_b)},\gamma_{PHY,min}),\\
p_{a-r0}(\theta,n_b)&=\min\left(1.65,
                  \frac{\Gamma_r(n_b)N}{\hat h(\theta)}\right),\\
p_{b0}(\theta)&=1.65,\\
B_u&=\Delta\,\frac{W}{n_b}SE_{m(\mathrm{SINR}_u)},
\qquad B=\sum_{u=1}^{n_b}B_u,\\
p_{sat}&=1.65\,10^{5/10}=5.217758139277826\ \mathrm W,\\
E&=\Delta\left(\frac{\sqrt{p\,p_{sat}}}{0.35}+0.338+0.200\right),\\
EE&=B/E.
\end{aligned}
\]

There is one numerical tie convention in the executable fixture: the
realised direct gain is the next representable float above the identical
nominal gain.  This is less than \(2.3\times10^{-16}\) relative and prevents
the last-bit direction of a divide/multiply round trip from deciding whether
an exactly targeted ACM threshold decodes.  It does not alter any number
shown below or any controller power.

The target modes are QPSK 1/4, QPSK 2/5, and QPSK 3/4 for
\(n_b=1,2,4\), with
\(\Gamma_r=(0.717494793565848,1.150320220502404,3.117588235600445)\).
For \(n_b=4\), the uncapped requirement reaches 1.65 W when
\(G^T=1672.930437138998\), giving the sealed cap-hit angle
**0.853069795148802°**.  Occupancies 1 and 2 remain below the cap through
1.66°.

## Numbers

Bits are achieved decodable ACM bits over one 30.08 s step.  `Mbit/J` is
numerically the same ordinate as \(10^6\) bit/J.

| Angle (°) | Model | \(n_b\) | \(G^T\) | RF (W) | Selected ACM | Mbit/user-step | Mbit/beam-step | Energy (J) | Mbit/J |
|---:|:---|---:|---:|---:|:---|---:|---:|---:|---:|
| 0.000000 | a-r0 | 1 | 2000.000000 | 0.317638 | QPSK 1/4 | 2048.126 | 2048.126 | 126.824 | 16.149 |
| 0.000000 | a-r0 | 2 | 2000.000000 | 0.509251 | QPSK 2/5 | 1648.994 | 3297.988 | 156.276 | 21.104 |
| 0.000000 | a-r0 | 4 | 2000.000000 | 1.380168 | QPSK 3/4 | 1553.583 | 6214.332 | 246.814 | 25.178 |
| 0.000000 | b0 | 1 | 2000.000000 | 1.650000 | QPSK 4/5 | 6630.952 | 6630.952 | 268.353 | 24.710 |
| 0.830000 | a-r0 | 1 | 1689.075704 | 0.376108 | QPSK 1/4 | 2048.126 | 2048.126 | 136.578 | 14.996 |
| 0.830000 | a-r0 | 2 | 1689.075704 | 0.602994 | QPSK 2/5 | 1648.994 | 3297.988 | 168.626 | 19.558 |
| 0.830000 | a-r0 | 4 | 1689.075704 | 1.634228 | QPSK 3/4 | 1553.583 | 6214.332 | 267.145 | 23.262 |
| 0.830000 | b0 | 1 | 1689.075704 | 1.650000 | QPSK 3/4 | 6214.332 | 6214.332 | 268.353 | 23.157 |
| 0.853070 | a-r0 | 1 | 1672.930437 | 0.379738 | QPSK 1/4 | 2048.126 | 2048.126 | 137.158 | 14.933 |
| 0.853070 | a-r0 | 2 | 1672.930437 | 0.608813 | QPSK 2/5 | 1648.994 | 3297.988 | 169.360 | 19.473 |
| 0.853070 | a-r0 | 4 | 1672.930437 | 1.650000 | QPSK 3/4 | 1553.583 | 6214.332 | 268.353 | 23.157 |
| 0.853070 | b0 | 1 | 1672.930437 | 1.650000 | QPSK 3/4 | 6214.332 | 6214.332 | 268.353 | 23.157 |
| 1.660000 | a-r0 | 1 | 1000.000817 | 0.635275 | QPSK 1/4 | 2048.126 | 2048.126 | 172.654 | 11.863 |
| 1.660000 | a-r0 | 2 | 1000.000817 | 1.018501 | QPSK 2/5 | 1648.994 | 3297.988 | 214.305 | 15.389 |
| 1.660000 | a-r0 | 4 | 1000.000817 | 1.650000 | QPSK 1/2 | 1032.807 | 4131.229 | 268.353 | 15.395 |
| 1.660000 | b0 | 1 | 1000.000817 | 1.650000 | QPSK 1/2 | 4131.229 | 4131.229 | 268.353 | 15.395 |

The result isolates the required mechanism.  Before saturation, decreasing
\(G^T(\theta)\) raises `a-r0` RF while the target mode holds delivered bits,
so PA energy rises and EE falls.  Once the four-user link reaches the cap,
RF and energy stay flat while achieved ACM bits fall in steps.  The `b0`
reference has 1.65 W RF and 268.353 J at every angle; only its selected ACM
mode, delivered bits, and therefore EE fall.
