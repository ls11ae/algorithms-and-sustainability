---
title: "Chapter 2: Computational Movement Analysis"
subtitle: "Algorithms and Sustainability · Lecture Notes · Winter 2026/27"
author: Kevin Buchin
affiliation: TU Dortmund University
copyright: "CC BY 4.0 ·"
date: "version of 20 October 2026"
---

GPS tags show where animals move, when, and how their movement changes. This chapter develops algorithms for analyzing such tracking data. It accompanies Lectures 2 to 4 and grows with them: this version covers Lecture 2, on the similarity of trajectories. Sections on clustering (Lecture 3) and segmentation (Lecture 4) will follow.

After working through Sections 2.1 to 2.3, you should be able to

- explain how tracking data can inform the conservation of migratory animals, and which computational problems arise;
- define lock-step distances, the Hausdorff distance, the discrete and the continuous Fréchet distance, and dynamic time warping (DTW), and explain what each of them keeps and what it ignores;
- compute the discrete Fréchet distance and DTW by dynamic programming, prove the recurrence correct, and analyze running time and memory;
- explain what the conditional lower bound for the Fréchet distance says, and what it does not say;
- choose a similarity measure for a given question and justify the choice.

# 2.1 Migration and conservation

## Migratory animals under pressure

Many migratory species are in decline. A report for the UN Convention on the Conservation of Migratory Species of Wild Animals (CMS) covers the 1,189 species listed under the convention: 44% of them have declining populations, 22% are threatened with extinction, and 51% of the Key Biodiversity Areas that are important for them are not protected. Overexploitation and the loss of habitat through human activity are the greatest threats [UNEP 2024]. Migratory animals need protection in many places: where they breed, where they rest and feed on the way, where they spend the winter, and on the routes in between. This concerns [15]{.sdg .s15} Life on land, in particular target 15.5, to halt the loss of biodiversity and protect threatened species from extinction, as well as [14]{.sdg .s14} Life below water [United Nations 2015].

Protecting migratory animals can conflict with other goals. Gauld et al. (2022) combined the GPS tracks of 1,454 birds of 27 species that are susceptible to collisions into maps of the sensitivity of Europe and North Africa to collisions with wind turbines and power lines. Highly sensitive areas make up 13.6% of the mapped area for wind turbines and 9.4% for power lines, mostly along migration corridors and coasts. Hotspots where sensitive areas meet existing infrastructure lie near the Strait of Gibraltar, near the Bosporus, and in central Europe. Wind energy serves [7]{.sdg .s7} Affordable and clean energy; deciding where to build it requires knowing where birds fly.

## Animals change their routes

The white stork (*Ciconia ciconia*) is a well-studied example. Flack et al. (2016) equipped juvenile white storks from eight populations between Spain and Uzbekistan with solar-powered GPS tags in the nest and tracked them from then on (Figure 2.1). Four juveniles from south-western Germany spent their first winter at rubbish dumps in northern Morocco instead of crossing the Sahara, and some juveniles from Uzbekistan did not migrate at all. Storks that crossed the Sahara flew 3.4 times as far as those that wintered north of it, but spent only 1.3 times as much energy on movement, estimated from body acceleration. Human-associated food can thus make shorter migrations attractive. In a study of 169 GPS-tracked storks, juveniles that wintered closer to home survived more often [Cheng et al. 2019]. Among 151 juvenile storks at the European migratory divide, the timing of fledging and departure helps explain whether they take the western or the eastern flyway [Jorzik et al. 2026].

![Figure 2.1: First journeys of 71 juvenile white storks from eight populations, tracked from the nest in 2013/14 and colored by where they spent their first winter. Data: Flack et al. (2015), Movebank, CC0; map: Natural Earth.](../lectures/figures/storks-overview.svg){width="75%"}

If animals change their routes or wintering areas, **where and when is protection needed now?** Answering this question requires analyzing large amounts of tracking data. The online platform Movebank hosts such data, and on the platform MoveApps volunteer coders develop analysis apps for wildlife conservation [Kölzsch et al. 2025].

## From ecological questions to computational problems

Table 2.1 lists ecological questions and the algorithmic problems behind them. The last column gives the directions we take in this chapter, not the methods of the cited studies.

| Ecological question | Example study | Algorithmic problem |
|---------------------|---------------|---------------------|
| Does an animal fly the same route every year? | marsh harriers: timing is more repeatable than the route [Vardanis et al. 2011] | similarity of two trajectories (Section 2.3) |
| Which route does a juvenile take, and is this shifting? | white storks at the migratory divide [Jorzik et al. 2026] | classification and clustering of trajectories (Section 2.4) |
| Which corridors need protection, or should stay free of wind farms? | collision-risk maps from GPS data [Gauld et al. 2022] | common subtrajectories, representative routes (Section 2.4) |
| Where does an animal rest and feed? | rest days: less than 100 km per day [Flack et al. 2016] | segmentation into phases (Section 2.5) |

: Table 2.1: From ecological questions to computational problems.

# 2.2 Trajectories

::: definition
**Definition 2.1 (time series, trajectory).** A *time series* is a sequence $X = \langle (t_1, x_1), \ldots, (t_n, x_n) \rangle$ of observations with times $t_1 < \cdots < t_n$ and values $x_i \in \mathbb{R}^d$. If the values are positions, $X$ is a *trajectory*. We then often write $P = \langle p_1, \ldots, p_n \rangle$ for its sequence of positions, and view $P$ as the *polygonal curve* that connects successive positions by line segments.
:::

The values of a time series can be electricity demand, speed, acceleration, or positions. The tags of the juvenile storks from Lake Constance record a GPS position every five minutes for 18 hours a day, so 216 positions per day and about 32,000 in five months. Figure 2.2 shows one day of two of them: Karamell, wintering in northern Morocco, stays within 2 km, while Yolo, wintering in Senegal, flies 119 km. In December 2013, the two moved on average 4.9 km and 78 km per day.

![Figure 2.2: One day of GPS positions every five minutes (12 December 2013). Karamell in Morocco stays within 2 km; Yolo in Senegal flies 119 km. Data: Flack et al. (2015), CC0.](../lectures/figures/storks-one-day.svg){width="75%"}

We write $\lVert p - q \rVert$ for the Euclidean distance between two points $p, q \in \mathbb{R}^d$, for instance of positions in projected coordinates. Definitions 2.2 to 2.4 below only need *some* distance between positions; for the stork examples, we use the great-circle distance on Earth in km. Section 2.3.6 uses that $\lVert \cdot \rVert$ is a norm.

# 2.3 Similarity of trajectories

Karamell, Eamy, and Yolo all started from Lake Constance. Karamell and Eamy spent the winter in Morocco, Yolo in Senegal. Intuitively, Karamell's route is similar to Eamy's and different from Yolo's. Which distance measure captures this? The answer depends on what similarity should mean: being close *at the same time*, covering the same *area*, or visiting the same places *in the same order*. This section presents measures for each of these meanings, and the algorithms to compute them.

## 2.3.1 Lock-step comparison

If two time series $X$ and $Y$ are observed at the same times $t_1, \ldots, t_N$, a **lock-step** distance compares the values at the same times, for instance
$$d_{\mathrm{RMS}}(X, Y) = \sqrt{\frac{1}{N} \sum_{i=1}^{N} d(x_i, y_i)^2},$$
where $d(x, y) = |x - y|$ for scalar values and $d(x, y) = \lVert x - y \rVert$ for positions. Instead of the root mean square, we can also take the mean or the maximum of the distances. Lock-step comparison is the right choice when being close *at the same time* matters: two animals that meet, or electricity demand at the same time of day. It needs common observation times; otherwise we first have to assign observations to common times, for instance to the same day or the nearest full hour.

For comparing routes, lock-step comparison is a poor fit. Eamy left Lake Constance one day after Karamell, and the storks rested for different times along the way. On any given day, the two storks can be at quite different points of almost the same route, so the $k$-th positions of the two trajectories need not correspond. For routes, we keep the positions and their order, but allow different times to match.

## 2.3.2 Hausdorff distance

The simplest way to ignore time is to treat the positions of a trajectory as a set of points.

::: definition
**Definition 2.2 (Hausdorff distance).** For $P = \langle p_1, \ldots, p_n \rangle$ and $Q = \langle q_1, \ldots, q_m \rangle$,
$$d_H(P, Q) = \max\Big\{ \max_{i} \min_{j} \lVert p_i - q_j \rVert,\ \max_{j} \min_{i} \lVert p_i - q_j \rVert \Big\}.$$
:::

So $d_H(P, Q) \leq r$ means that every position of $P$ lies within distance $r$ of some position of $Q$, and vice versa. By brute force, $d_H$ takes $O(nm)$ time; nearest-neighbor data structures make it faster. With one position per day, the Hausdorff distance is 89 km for Karamell and Eamy and 2,442 km for Karamell and Yolo.

The Hausdorff distance ignores the order of the positions and how often a place is visited. This can be what we want, for instance when comparing the areas that two animals cover. But it cannot tell an outward journey from the return journey: reversing a trajectory does not change its set of positions. Figure 2.3 shows Karamell's first autumn migration, from Lake Constance to northern Morocco (10 August to 15 October 2013), and her spring migration back north to near Karlsruhe (5 April to 10 June 2014). The two routes use a similar corridor in opposite directions: their Hausdorff distance is only 193 km. The discrete Fréchet distance of the next section, which respects the order, is 1,996 km; with the spring route reversed, it is also 193 km. Whether direction should matter depends on the question: for a shared corridor it may not, for the same journey it does. Since it takes a maximum over nearest-point distances, the Hausdorff distance can also be dominated by a single outlier.

![Figure 2.3: Karamell's autumn migration and her spring migration back north, one position per day. Hausdorff distance 193 km (dotted), discrete Fréchet distance 1,996 km. Data: Flack et al. (2015), CC0.](../lectures/figures/storks-autumn-spring.svg){width="75%"}

## 2.3.3 The discrete Fréchet distance

The Fréchet distance, named after Maurice Fréchet [Fréchet 1906], respects the order in which places are visited. In the popular image, a person walks along one trajectory and a dog along the other. Both move forward only, but each may wait while the other moves on. The Fréchet distance is the length of the shortest leash that allows both to get from start to end. The walk need not reflect where the animals actually were at the same time: it is an *alignment* of the two trajectories, not a reconstruction of their simultaneous movement. In the **discrete** version, which we already met in Definition 1.1, both walk from position to position.

::: definition
**Definition 2.3 (coupling, discrete Fréchet distance).** A *coupling* of $P = \langle p_1, \ldots, p_n \rangle$ and $Q = \langle q_1, \ldots, q_m \rangle$ is a sequence of index pairs $(i_1, j_1), \ldots, (i_L, j_L)$ with $(i_1, j_1) = (1, 1)$ and $(i_L, j_L) = (n, m)$ such that
$$(i_{k+1}, j_{k+1}) \in \{(i_k + 1, j_k),\ (i_k, j_k + 1),\ (i_k + 1, j_k + 1)\} \quad \text{for } k = 1, \ldots, L - 1.$$
The *value* of the coupling is $\max_{k} \lVert p_{i_k} - q_{j_k} \rVert$, and the *discrete Fréchet distance* $\delta_{\mathrm{dF}}(P, Q)$ is the minimum value of a coupling of $P$ and $Q$.
:::

A coupling is a path through the $n \times m$ grid of index pairs from $(1, 1)$ to $(n, m)$, where each step advances one of the two indices or both. Every position of both trajectories is matched at least once, and neither sequence is reordered. If an index stays the same, the corresponding walker waits: one route waits while the other moves on. This makes the measure robust against stops and different speeds, up to effects of sampling (Section 2.3.6).

The number of couplings is a Delannoy number: the number of lattice paths from $(1, 1)$ to $(n, m)$ with steps $(1, 0)$, $(0, 1)$, and $(1, 1)$. It grows exponentially, so trying all couplings is out of the question.

## 2.3.4 Dynamic programming

We compute $\delta_{\mathrm{dF}}$ from the distances between prefixes. Let $P_i = \langle p_1, \ldots, p_i \rangle$ and $Q_j = \langle q_1, \ldots, q_j \rangle$, and define the table $C$ by $C[0, 0] = 0$, $C[i, 0] = C[0, j] = \infty$ for $i, j > 0$, and for $i, j \geq 1$
$$C[i, j] = \max\Big\{ \lVert p_i - q_j \rVert,\ \min\{ C[i-1, j],\ C[i, j-1],\ C[i-1, j-1] \} \Big\}.$$

::: theorem
**Lemma 2.1 [Eiter and Mannila 1994].** For all $1 \leq i \leq n$ and $1 \leq j \leq m$, $C[i, j] = \delta_{\mathrm{dF}}(P_i, Q_j)$. In particular, $\delta_{\mathrm{dF}}(P, Q) = C[n, m]$.

*Proof.* By induction on $i + j$. For $(i, j) = (1, 1)$, the only coupling of $P_1$ and $Q_1$ is $(1, 1)$, with value $\lVert p_1 - q_1 \rVert$; the recurrence gives $\max\{\lVert p_1 - q_1 \rVert, \min\{\infty, \infty, 0\}\} = \lVert p_1 - q_1 \rVert$.

Now let $i + j > 2$. Every coupling of $P_i$ and $Q_j$ ends with the pair $(i, j)$. Removing this pair leaves a coupling of $P_{i'}$ and $Q_{j'}$ for one of the predecessors $(i', j') \in \{(i-1, j), (i, j-1), (i-1, j-1)\}$ with $i', j' \geq 1$; conversely, appending $(i, j)$ to such a coupling gives a coupling of $P_i$ and $Q_j$. The value of a coupling is the maximum of $\lVert p_i - q_j \rVert$ and the value of the remaining coupling. Since $x \mapsto \max\{a, x\}$ is non-decreasing, the minimum value is attained by appending $(i, j)$ to an optimal coupling of the best predecessor:
$$\delta_{\mathrm{dF}}(P_i, Q_j) = \max\Big\{ \lVert p_i - q_j \rVert,\ \min_{(i', j')} \delta_{\mathrm{dF}}(P_{i'}, Q_{j'}) \Big\}.$$
By induction, $\delta_{\mathrm{dF}}(P_{i'}, Q_{j'}) = C[i', j']$ for the predecessors with $i', j' \geq 1$. The predecessors with a zero index have $C = \infty$ and do not affect the minimum, since at least one predecessor has both indices positive. So the right-hand side equals $C[i, j]$. [∎]{.qed}
:::

**Running time and memory.** The table has $(n + 1)(m + 1)$ entries, each computed in constant time from three earlier ones, row by row or column by column. So $\delta_{\mathrm{dF}}(P, Q)$ takes $O(nm)$ time. Each row only needs the previous one. To compute the distance alone, $O(\min(n, m))$ memory besides the input suffices: let the outer loop run over the longer sequence, so that each row has $\min(n, m) + 1$ entries. To output an optimal coupling, we store the whole table and **backtrack** from $(n, m)$: repeatedly move to a predecessor with the smallest $C$-value until we reach $(1, 1)$.

::: example
**Example 2.1.** Let $P = \langle (0, 0), (1, 0), (4, 0), (5, 0) \rangle$ and $Q = \langle (0, 1), (4, 1), (5, 1) \rangle$ in the plane (Figure 2.4). The distances $\lVert p_i - q_j \rVert$ and the table $C$ are:

| $\lVert p_i - q_j \rVert$ | $q_1$ | $q_2$ | $q_3$ |
|---|---:|---:|---:|
| $p_1$ | 1.00 | 4.12 | 5.10 |
| $p_2$ | 1.41 | 3.16 | 4.12 |
| $p_3$ | 4.12 | 1.00 | 1.41 |
| $p_4$ | 5.10 | 1.41 | 1.00 |

| $C[i, j]$ | $q_1$ | $q_2$ | $q_3$ |
|---|---:|---:|---:|
| $p_1$ | 1.00 | 4.12 | 5.10 |
| $p_2$ | 1.41 | 3.16 | 4.12 |
| $p_3$ | 4.12 | 1.41 | 1.41 |
| $p_4$ | 5.10 | 1.41 | **1.41** |

For instance, $C[2, 2] = \max\{3.16, \min\{4.12, 1.41, 1.00\}\} = 3.16$ and $C[3, 2] = \max\{1.00, \min\{3.16, 4.12, 1.41\}\} = 1.41$. Hence $\delta_{\mathrm{dF}}(P, Q) = C[4, 3] = \sqrt{2} \approx 1.41$. Backtracking, with ties broken in favor of the diagonal step, gives the optimal coupling $(1, 1), (2, 1), (3, 2), (4, 3)$: $q_1$ waits while $P$ moves from $p_1$ to $p_2$. At $(4, 3)$, all three predecessors have the value 1.41, so the other choices give two further optimal couplings. Pairing $p_2$ with $q_2$ instead would cost $\sqrt{10} \approx 3.16$.
:::

![Figure 2.4: An optimal coupling of Example 2.1; the longest pair, (p₂, q₁), has length √2 ≈ 1.41.](../lectures/figures/frechet-example-coupling.svg){width="55%"}

**Back to the storks.** With one position per day until 31 December 2013, the discrete Fréchet distance is 89 km for Karamell and Eamy and 2,445 km for Karamell and Yolo (Figure 2.5). Here, the Hausdorff distance gives almost the same values; the two measures differ markedly only in the example of Figure 2.3. Karamell and Yolo share the corridor to the Strait of Gibraltar and then part ways. A distance between *whole* routes is large in such a case, although the two storks share an important corridor. For protecting corridors, we should therefore also compare *parts* of trajectories; this leads to subtrajectory clustering in Section 2.4.

![Figure 2.5: Optimal couplings for two pairs of storks, one position per day. Grey: pairs of the coupling; black: the longest pair. Karamell and Eamy: 89 km; Karamell and Yolo: 2,445 km. Data: Flack et al. (2015), CC0.](../lectures/figures/storks-two-routes.svg){width="90%"}

## 2.3.5 Dynamic time warping

Dynamic time warping (DTW) comes from speech recognition [Sakoe and Chiba 1978] and is widely used for time series [Müller 2007]. It uses the same couplings as the discrete Fréchet distance, but minimizes the *sum* of the matched distances instead of the maximum.

::: definition
**Definition 2.4 (dynamic time warping).** For $P = \langle p_1, \ldots, p_n \rangle$ and $Q = \langle q_1, \ldots, q_m \rangle$,
$$\operatorname{DTW}(P, Q) = \min_{\text{couplings } \pi} \; \sum_{(i, j) \in \pi} \lVert p_i - q_j \rVert .$$
:::

The discrete Fréchet distance minimizes the *largest* discrepancy of an alignment, DTW the *accumulated* discrepancy. The same dynamic program works, with the maximum replaced by a sum: $D[0, 0] = 0$, $D[i, 0] = D[0, j] = \infty$ for $i, j > 0$, and for $i, j \geq 1$
$$D[i, j] = \lVert p_i - q_j \rVert + \min\{ D[i-1, j],\ D[i, j-1],\ D[i-1, j-1] \}.$$
The proof of Lemma 2.1 carries over, since $x \mapsto a + x$ is non-decreasing as well. Again, this takes $O(nm)$ time, and $O(\min(n, m))$ memory for the value alone.

In Example 2.1, the coupling $(1, 1), (2, 1), (3, 2), (4, 3)$ has costs $1, \sqrt{2}, 1, 1$. It is optimal for both measures, and for DTW it is the only optimal coupling: $\delta_{\mathrm{dF}}(P, Q) = \sqrt{2}$ and $\operatorname{DTW}(P, Q) = 3 + \sqrt{2} \approx 4.41$. In general, the optimal couplings of the two measures can differ, and the two measures can rank pairs of trajectories differently (Section 2.6, question 3). The DTW value is a sum, not an average distance between routes.

DTW is not restricted to positions. For scalar time series such as electricity demand or speed, we use $|x_i - y_j|$ as local cost, and the same dynamic program applies. Figure 2.6 shows two demand profiles with the same peak, one hour apart. Their DTW distance is 0, because a coupling can match equal values throughout, whereas the lock-step RMS distance at matching hours is $\sqrt{18/7} \approx 1.60$. Which is right depends on the question: for "same daily pattern?", DTW is suitable; for energy planning, where supply and demand must coincide, the shift matters and should stay visible.

![Figure 2.6: Two constructed hourly demand profiles from 9:00 to 15:00, day A = (1, 1, 4, 1, 1, 1, 1) and day B = (1, 1, 1, 4, 1, 1, 1), with the same peak one hour apart. DTW aligns the peaks at cost 0.](../lectures/figures/time-series-alignment.svg){width="60%"}

There are several conventions for DTW: squared local costs with a final square root, different weights for the three kinds of steps, normalization by the length of the coupling or by $\max(n, m)$, and restrictions on which pairs may be matched [Müller 2007; Tao et al. 2021]. Before comparing DTW values, state the convention. In these notes, DTW uses unsquared distances and no normalization. Unlike the Fréchet distances, DTW does not satisfy the triangle inequality, which matters for clustering (Section 2.4).

## 2.3.6 The continuous Fréchet distance

Sampled positions are only snapshots of a movement. If we connect successive positions by line segments, the walkers can also be matched *between* the positions.

::: definition
**Definition 2.5 (Fréchet distance).** For polygonal curves $P, Q : [0, 1] \to \mathbb{R}^d$,
$$\delta_F(P, Q) = \inf_{\alpha, \beta} \; \max_{t \in [0, 1]} \; \lVert P(\alpha(t)) - Q(\beta(t)) \rVert,$$
where $\lVert \cdot \rVert$ is the Euclidean norm and $\alpha$ and $\beta$ range over all continuous, non-decreasing, surjective functions $[0, 1] \to [0, 1]$. Here $P(s)$, $s \in [0, 1]$, parametrizes the polygonal curve through $p_1, \ldots, p_n$, for instance with $P\big(\frac{i-1}{n-1}\big) = p_i$ and linear in between; $\delta_F$ does not depend on this choice.
:::

In Example 2.1, $P$ and $Q$ are parallel segments from $x = 0$ to $x = 5$, one unit apart, so $\delta_F(P, Q) = 1$: both walkers move to the right at the same $x$-coordinate. The discrete Fréchet distance is $\sqrt{2}$, because $p_2$ must be matched with some $q_j$, and the nearest one, $q_1$, is $\sqrt{2}$ away.

::: theorem
**Lemma 2.2 [Eiter and Mannila 1994].** For polygonal curves $P$ and $Q$ with vertices $p_1, \ldots, p_n$ and $q_1, \ldots, q_m$, we have $\delta_F(P, Q) \leq \delta_{\mathrm{dF}}(P, Q)$.

*Proof.* Take an optimal coupling $(i_1, j_1), \ldots, (i_L, j_L)$ and let the two walkers perform its steps one after the other, each step in the same amount of time. In a step from $(i_k, j_k)$ to $(i_{k+1}, j_{k+1})$, each walker moves at constant speed along its segment, or stays put if its index does not change. At a fraction $s \in [0, 1]$ of the step, the two positions are $(1 - s)\, p_{i_k} + s\, p_{i_{k+1}}$ and $(1 - s)\, q_{j_k} + s\, q_{j_{k+1}}$, so their distance is
$$\big\lVert (1 - s)(p_{i_k} - q_{j_k}) + s\,(p_{i_{k+1}} - q_{j_{k+1}}) \big\rVert \leq (1 - s) \lVert p_{i_k} - q_{j_k} \rVert + s\, \lVert p_{i_{k+1}} - q_{j_{k+1}} \rVert,$$
which is at most the value of the coupling. This walk defines functions $\alpha$ and $\beta$ as in Definition 2.5, so $\delta_F(P, Q) \leq \delta_{\mathrm{dF}}(P, Q)$. [∎]{.qed}
:::

Conversely, $\delta_{\mathrm{dF}}(P, Q) \leq \delta_F(P, Q) + \max\{\ell_P, \ell_Q\}$, where $\ell_P$ and $\ell_Q$ are the lengths of the longest segments of $P$ and $Q$ [Eiter and Mannila 1994, Theorem 4]. If all segments are short, the discrete distance is therefore close to the continuous one; with sparse sampling, it can be considerably larger. For Karamell and Eamy, the discrete Fréchet distance is 89 km with one position per day and 71 km with all positions.

The continuous Fréchet distance of polygonal curves with $n$ and $m$ segments can be computed in $O(nm \log(nm))$ time [Alt and Godau 1995]. The algorithm decides for a given $r$ in $O(nm)$ time whether $\delta_F(P, Q) \leq r$, using the so-called free-space diagram, and then searches for the smallest such $r$. We do not derive it in this course.

A continuous measure is less sensitive to how the trajectories are sampled, which helps with different sampling rates and gaps in the data [Tao et al. 2021]. This assumes that interpolation is meaningful: a straight line between two GPS positions that are hours apart may cross areas that the animal never visited.

## 2.3.7 How fast can we compute the Fréchet distance?

Karamell's and Yolo's routes at full resolution, in the first 150 days after departure, have 32,491 and 32,398 positions. The table $C$ then has about $1.05 \cdot 10^9$ entries. Filling it took 4.3 s with a program in C on one core of a 2.8 GHz processor, and would take about 9 minutes in plain Python. All 91 pairs of the 14 storks with complete five-minute data took 6.5 minutes in C. With hundreds of tracked animals or many years of data, quadratic time becomes the bottleneck. Can we do better?

Algorithms that save logarithmic factors exist [Agarwal et al. 2014; Buchin et al. 2017]. Whether a polynomial factor can be saved depends on a hypothesis about Boolean satisfiability. The **Strong Exponential Time Hypothesis (SETH)** states that for every $\varepsilon > 0$ there is a $k$ such that $k$-SAT with $N$ variables cannot be solved in time $O((2 - \varepsilon)^N)$ [Impagliazzo and Paturi 2001].

::: theorem
**Theorem 2.1 [Bringmann 2014].** If there is an $\varepsilon > 0$ and an algorithm that computes the Fréchet distance of two polygonal curves with $n$ vertices each in time $O(n^{2 - \varepsilon})$, then SETH fails. This holds for the continuous and the discrete Fréchet distance, and even for approximating them within a factor of 1.001.
:::

This is a conditional bound on the *worst case* over all inputs. It does not rule out fast computations for realistic inputs. For instance, for $c$-packed curves, whose length inside any ball of radius $r$ is at most $c \cdot r$, the Fréchet distance can be approximated within a factor $1 + \varepsilon$ in near-linear time [Driemel et al. 2012]. In practice, we can also simplify trajectories, use approximations, or exploit structure in the data. Each of these choices is a modeling trade-off: fewer positions save computation, but can change the distance and hide a short detour or stopover.

## 2.3.8 Choosing a similarity measure

Table 2.2 summarizes the measures of this section by what the correspondence between the two trajectories should preserve.

| What should correspondence preserve? | Measure | What contributes? |
|---|---|---|
| matching observation times | lock-step, e.g., RMS | discrepancies at the same times |
| spatial coverage | Hausdorff on point sets | worst nearest-point distance |
| order of visits | discrete or continuous Fréchet | largest distance in an alignment |
| order of visits | DTW | sum of the distances in a coupling |

: Table 2.2: Similarity measures by what they preserve.

Two further measures use tolerance-based matching: the **longest common subsequence (LCSS)** counts positions that can be matched within a distance threshold [Vlachos et al. 2002], and the **edit distance on real sequences (EDR)** counts the edits needed to make two trajectories match within a threshold [Chen et al. 2005]. Both can skip positions, which makes them robust against outliers, but the results depend on the threshold.

Tao et al. (2021) compared DTW, LCSS, EDR, and the discrete and continuous Fréchet distance on bus trajectories and on trajectories of birds. Among their findings:

- The value and the ranking of similarities can change with the measure.
- In their data, spatial differences were easier to detect than temporal ones.
- Continuous measures cope better with different sampling rates and gaps.
- In principle, measures based on a maximum are more sensitive to outliers than measures based on a sum; in their experiments, the two kinds behaved similarly.
- LCSS and EDR need thresholds that depend on the data.

No measure fits every question. Before choosing one, decide whether to compare **routes**, **shared corridors**, or **activity patterns**, and check how sensitive your result is to the choice.

# 2.4 Clustering trajectories

This section follows after Lecture 3 (27 October). It covers how to find $k$ representative routes such that every trajectory in the data is close to one of them, which curves may serve as representatives, and how to find corridors that several trajectories share.

# 2.5 Segmentation

This section follows after Lecture 4 (3 November). It covers how to split a trajectory into phases of homogeneous movement, such as migrating, resting, and foraging.

# 2.6 Check your understanding

1. Let $P = \langle p_1, \ldots, p_n \rangle$ with $p_1 \neq p_n$, and let $Q = \langle p_n, \ldots, p_1 \rangle$ be $P$ reversed. What is $d_H(P, Q)$? Show that $\delta_{\mathrm{dF}}(P, Q) > 0$.

    <details>
    <summary>Answer</summary>
    $d_H(P, Q) = 0$, since $P$ and $Q$ have the same set of positions. Every coupling starts with the pair $(p_1, q_1) = (p_1, p_n)$, so $\delta_{\mathrm{dF}}(P, Q) \geq \lVert p_1 - p_n \rVert > 0$. The Fréchet distance distinguishes the outward from the return journey; the Hausdorff distance does not.
    </details>

2. Let $P = \langle (0, 0), (2, 0), (4, 0) \rangle$ and $Q = \langle (0, 0), (4, 0) \rangle$. Compute $\delta_{\mathrm{dF}}(P, Q)$ and $\delta_F(P, Q)$, and check the bound of Eiter and Mannila from Section 2.3.6.

    <details>
    <summary>Answer</summary>
    $p_2 = (2, 0)$ must be matched with $q_1$ or $q_2$, both at distance 2, and the coupling $(1, 1), (2, 1), (3, 2)$ has value 2, so $\delta_{\mathrm{dF}}(P, Q) = 2$. As polygonal curves, $P$ and $Q$ are the same segment, so $\delta_F(P, Q) = 0$. The bound gives $2 \leq 0 + \max\{2, 4\} = 4$. The discrete distance depends on where the curves are sampled. The continuous one is unchanged here, because the extra position lies on the segment; in general, other positions give a different polygonal curve.
    </details>

3. Consider the scalar time series $X = (0, 0, 0, 0, 0)$, $A = (0, 0, 3, 0, 0)$, and $B = (1, 1, 1, 1, 1)$ with local cost $|x - y|$. Which of $A$ and $B$ is closer to $X$ under the discrete Fréchet distance, and which under DTW?

    <details>
    <summary>Answer</summary>
    Discrete Fréchet: $A$ has distance 3, since the value 3 must be matched with some 0; $B$ has distance 1. So $B$ is closer. DTW: $A$ costs 3 (the diagonal coupling), $B$ costs 5, since every coupling has at least five pairs and each costs 1. So $A$ is closer. The maximum is determined by one large discrepancy, the sum accumulates many small ones.
    </details>

4. How much memory do you need to compute only the value $\delta_{\mathrm{dF}}(P, Q)$, and how much to output an optimal coupling with the method of Section 2.3.4?

    <details>
    <summary>Answer</summary>
    For the value, $O(\min(n, m))$ besides the input: let the outer loop run over the longer sequence and keep only the previous row, which has $\min(n, m) + 1$ entries. For backtracking, we store the whole table, so $O(nm)$. For the full-resolution routes of Section 2.3.7, this is the difference between a few hundred kilobytes and about 8 GB with 8-byte numbers.
    </details>

5. A colleague concludes from Theorem 2.1 that the Fréchet distance of GPS trajectories cannot be computed fast in practice. What is wrong with this conclusion?

    <details>
    <summary>Answer</summary>
    Theorem 2.1 is a worst-case bound over all inputs, and it is conditional on SETH. It does not say that typical trajectories are hard. Even the quadratic algorithm fills $10^9$ table entries in a few seconds in C, and for realistic curves, such as $c$-packed curves, there are fast approximation algorithms. What the theorem does say is that we should not expect an algorithm that is substantially faster than quadratic on *all* inputs.
    </details>

6. Two animals use a similar corridor but migrate on different days, and their daily activity patterns differ. What would you compare to study the similarity of their routes, and what for the similarity of their activity? Which differences should each comparison keep, and which ignore?

    <details>
    <summary>Answer</summary>
    For routes: the ordered positions, with a measure that allows different times to match, such as the Fréchet distance; the different migration days should be ignored. For activity: for instance speed or acceleration over the day, compared at the same time of day, or with limited time warping if small shifts should not count. Timing differences should be ignored only if they do not matter for the question; for a shared corridor, even the direction may not matter.
    </details>

7. For which question is a lock-step comparison the right choice, and what would DTW hide there?

    <details>
    <summary>Answer</summary>
    Whenever being close at the same time matters: whether two animals meet, or whether electricity demand and supply coincide at the same hour. DTW would align a shifted pattern and report a small distance, as for the demand profiles of Figure 2.6, where it gives 0 although the peaks are an hour apart.
    </details>

# References

::: refs
- Agarwal, P. K., Ben Avraham, R., Kaplan, H., Sharir, M. (2014). Computing the discrete Fréchet distance in subquadratic time. *SIAM Journal on Computing* 43(2), 429–449.
- Alt, H., Godau, M. (1995). Computing the Fréchet distance between two polygonal curves. *International Journal of Computational Geometry & Applications* 5(1–2), 75–91.
- Bringmann, K. (2014). Why walking the dog takes time: Fréchet distance has no strongly subquadratic algorithms unless SETH fails. *55th IEEE Symposium on Foundations of Computer Science (FOCS)*, 661–670.
- Buchin, K., Buchin, M., Meulemans, W., Mulzer, W. (2017). Four Soviets walk the dog: improved bounds for computing the Fréchet distance. *Discrete & Computational Geometry* 58(1), 180–216.
- Chen, L., Özsu, M. T., Oria, V. (2005). Robust and fast similarity search for moving object trajectories. *ACM SIGMOD International Conference on Management of Data*, 491–502.
- Cheng, Y., Fiedler, W., Wikelski, M., Flack, A. (2019). "Closer-to-home" strategy benefits juvenile survival in a long-distance migratory bird. *Ecology and Evolution* 9(16), 8945–8952. <https://doi.org/10.1002/ece3.5395>
- Driemel, A., Har-Peled, S., Wenk, C. (2012). Approximating the Fréchet distance for realistic curves in near linear time. *Discrete & Computational Geometry* 48(1), 94–127.
- Eiter, T., Mannila, H. (1994). Computing discrete Fréchet distance. Technical Report CD-TR 94/64, TU Wien.
- Flack, A., Fiedler, W., Blas, J., et al. (2015). Data from: Costs of migratory decisions: a comparison across eight white stork populations. Movebank Data Repository, CC0. <https://doi.org/10.5441/001/1.78152p3q>
- Flack, A., Fiedler, W., Blas, J., et al. (2016). Costs of migratory decisions: A comparison across eight white stork populations. *Science Advances* 2(1), e1500931. <https://doi.org/10.1126/sciadv.1500931>
- Fréchet, M. (1906). Sur quelques points du calcul fonctionnel. *Rendiconti del Circolo Matematico di Palermo* 22, 1–72.
- Gauld, J. G., Silva, J. P., Atkinson, P. W., et al. (2022). Hotspots in the grid: Avian sensitivity and vulnerability to collision risk from energy infrastructure interactions in Europe and North Africa. *Journal of Applied Ecology* 59(6), 1496–1512. <https://doi.org/10.1111/1365-2664.14160>
- Impagliazzo, R., Paturi, R. (2001). On the complexity of k-SAT. *Journal of Computer and System Sciences* 62(2), 367–375.
- Jorzik, I., Fiedler, W., Kaatz, M., Rotics, S., Nathan, R., Wikelski, M., Flack, A. (2026). Timing shapes flyway selection in juvenile white storks at the European migratory divide. *Journal of Ornithology* 167(1), 131–142. <https://doi.org/10.1007/s10336-025-02322-z>
- Kölzsch, A., et al. (2025). Citizen scientists for MoveApps: Innovations and insights from volunteer coders in wildlife conservation. *Methods in Ecology and Evolution* 16, 1550–1563. <https://doi.org/10.1111/2041-210X.70101>
- Müller, M. (2007). Dynamic time warping. Chapter 4 in *Information Retrieval for Music and Motion*, 69–84. Springer.
- Sakoe, H., Chiba, S. (1978). Dynamic programming algorithm optimization for spoken word recognition. *IEEE Transactions on Acoustics, Speech, and Signal Processing* 26(1), 43–49.
- Tao, Y., Both, A., Silveira, R. I., Buchin, K., Sijben, S., Purves, R. S., Laube, P., Peng, D., Toohey, K., Duckham, M. (2021). A comparative analysis of trajectory similarity measures. *GIScience & Remote Sensing* 58(5), 643–669. <https://doi.org/10.1080/15481603.2021.1908927>
- UNEP (2024). Landmark UN report reveals shocking state of wildlife: the world's migratory species. Press release, 12 February 2024. <https://www.unep.org/news-and-stories/press-release/landmark-un-report-reveals-shocking-state-wildlife-worlds-migratory>
- United Nations (2015). *Transforming our world: the 2030 Agenda for Sustainable Development*. Resolution A/RES/70/1.
- Vardanis, Y., Klaassen, R. H. G., Strandberg, R., Alerstam, T. (2011). Individuality in bird migration: routes and timing. *Biology Letters* 7, 502–505. <https://doi.org/10.1098/rsbl.2010.1180>
- Vlachos, M., Kollios, G., Gunopulos, D. (2002). Discovering similar multidimensional trajectories. *18th International Conference on Data Engineering (ICDE)*, 673–684.
:::

# License

These notes are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Suggested attribution: "Kevin Buchin, Algorithms and Sustainability, Lecture Notes, TU Dortmund University, CC BY 4.0". All figures are own work under the same license. The stork figures are based on data from Flack et al. (2015), Movebank Data Repository, CC0; the maps use Natural Earth (public domain). The demand profiles in Figure 2.6 are constructed examples, not measured data. The colors of the Sustainable Development Goals are used for orientation only; these notes are not endorsed by the United Nations. Not covered by the license: the TU Dortmund logo and the Decker software and its themes.
