---
title: "Chapter 3: Route Planning for Sustainable Mobility"
subtitle: "Algorithms and Sustainability · Lecture Notes · Winter 2026/27"
author: Kevin Buchin
affiliation: TU Dortmund University
copyright: "CC BY 4.0 ·"
date: "version of 17 November 2026"
---

Route planners decide which options people see: the fastest way by car, a quiet route for a cautious cyclist, a step-free route for a wheelchair user, a connection by bike and train. This chapter develops the algorithms behind them. It accompanies the route planning block of the course and grows with it: this version covers Lecture 5 (10 November) on shortest paths in road networks and Lecture 6 (24 November) on several criteria and on timetables, with running examples in Dortmund. Lecture 7 on public transport will follow.

After working through Sections 3.1 to 3.9, you should be able to

- explain why route planning matters for sustainable mobility and inclusion, and why the fastest route is often not the one people want;
- model a street network as a weighted graph and choose an edge weight for a given question;
- run Dijkstra's algorithm, prove it correct, and analyze its running time with binary and Fibonacci heaps;
- run bidirectional search and prove its stopping criterion correct;
- decide whether a heuristic for A\* is a lower bound and whether it is consistent, explain A\* as Dijkstra's algorithm on reduced costs, and derive landmark bounds from the triangle inequality;
- contract nodes, decide which shortcuts are needed, run a contraction hierarchy query, and prove that two upward searches suffice;
- explain how customizable contraction hierarchies make personal profiles practical;
- decide which routes are Pareto-optimal and which of them a weighted sum finds;
- run multi-criteria Dijkstra, prove it correct, and explain why the Pareto front can be exponentially large;
- explain how contraction hierarchies handle all weighted sums of two criteria at once;
- model timetables as graphs, run the Connection Scan Algorithm, and prove it correct.

# 3.1 Route planning and sustainable mobility

## Transport, climate, and inclusion

The Sustainable Development Goals ask for mobility that is sustainable *and* open to everyone. Target 11.2 reads: "By 2030, provide access to safe, affordable, accessible and sustainable transport systems for all, improving road safety, notably by expanding public transport, with special attention to the needs of those in vulnerable situations, women, children, persons with disabilities and older persons" [United Nations 2015]. Three numbers for Germany show what is at stake.

- [13]{.sdg .s13} **Climate.** In 2025, transport caused 146.3 of 648.9 Mt CO₂e, 23% of Germany's greenhouse gas emissions. Its emissions rose by 2.1 Mt compared with 2024, while the total fell slightly [Umweltbundesamt 2026a].
- [11]{.sdg .s11} **Short trips.** In large German cities, more than 40% of car trips are shorter than five kilometres [Umweltbundesamt 2026b, based on the survey *Mobilität in Deutschland 2023*], a distance that is easy by bike.
- [10]{.sdg .s10} **Inclusion.** At the end of 2025, just over 7.8 million people in Germany had a severe disability, 9.4% of the population [Destatis 2026]. Accessible routes matter for them, and also for older people, parents with prams, and anyone with a temporary injury.

Route planning does not build cycle tracks or bus lines. But it decides which routes people see and choose, and it is a building block of planning tools, for instance to estimate which streets cyclists would use or which places can be reached without a car.

## Travel time is not everything

Table 3.1 collects research on what matters besides travel time. All these questions lead to the same computational problem, with another edge weight or with several weights at once.

| Who | What matters besides travel time | Source | SDG |
|-----|----------------------------------|--------|-----|
| cyclists | suitability: safety, traffic volume and speed, cycle lanes, terrain; every cyclist weighs it differently | Ehrgott et al. 2012 | [3]{.sdg .s3} |
| potential cyclists | 60% of the adults in Portland (56% in the region) are "interested but concerned": they would like to cycle more, but worry about safety | Dill and McNeil 2013 | [11]{.sdg .s11} |
| blind pedestrians | length, number of turns, landmarks for orientation, type of way | Cohen and Dalyot 2021 | [10]{.sdg .s10} |
| drivers | fuel and emissions: in a field test in the Netherlands, a route of 15.6 minutes used 1.34 l of fuel, one of 15.7 minutes only 0.76 l | Minett et al. 2011 | [13]{.sdg .s13} |
| wheelchair users | steps, kerbs, slopes, surfaces such as cobbles | guest lecture on 17 November | [10]{.sdg .s10} |
| public transport users | timetables, transfers, combined trips with bike and train | Lectures 6 and 7 | [11]{.sdg .s11} |

: Table 3.1: What matters besides travel time.

The SDG chips link each row to a goal: [3]{.sdg .s3} good health, including road safety (target 3.6), [10]{.sdg .s10} reduced inequalities, [11]{.sdg .s11} sustainable cities, [13]{.sdg .s13} climate action. The choice of the weight is the sustainability question; the algorithms of this chapter work for any non-negative weight.

## A first example: two bike routes in Dortmund

::: example
**Example 3.1.** From Dortmund Hbf, the main station, to the Phoenix-See by bike, on OpenStreetMap data and the bicycle model of Section 3.2: the fastest route takes 19.2 minutes, and 5.2 of its 5.6 km run on busy main roads (along the Wall, Heiliger Weg, and Märkische Straße). A quieter route takes 21.1 minutes and uses busy roads for only 0.2 of its 5.7 km; it runs through residential streets east of the centre (Kaiserstraße, Kronprinzenstraße) and on paths such as the Hundeweg (Figure 3.1). Two minutes more buy five kilometres less on busy roads. Both routes are computed by the same algorithm, with different edge weights.
:::

![Figure 3.1: Fastest route (blue) and quieter route (green) by bike from Dortmund Hbf to the Phoenix-See. Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-fast-quiet.png){width="70%"}

The [interactive demo](../static/routing-demo/index.html) shows this example and all algorithms of this chapter on the street network of Dortmund: a click sets the start, a second click the target.

# 3.2 Street networks as graphs

::: definition
**Definition 3.1 (shortest path problem).** A *street network* is a directed graph $G = (V, E)$ with non-negative edge weights $c\colon E \to \mathbb{R}_{\geq 0}$; we write $n = |V|$ and $m = |E|$. A *path* $P = \langle v_0, \ldots, v_k \rangle$ uses the edges $(v_{i-1}, v_i) \in E$ and has the *length* $c(P) = \sum_{i=1}^{k} c(v_{i-1}, v_i)$. The *distance* $d(s, t)$ is the length of a shortest $s$–$t$ path, or $\infty$ if there is none. The *shortest path problem* asks, for given nodes $s$ and $t$, for an $s$–$t$ path of length $d(s, t)$.
:::

Nodes are junctions. Each piece of street between two junctions gives one edge for each direction in which it may be used; a one-way street gives a single edge, unless cyclists may ride both ways. The weight decides what "shortest" means: travel time, length, fuel, stress, or the effort for a wheelchair user. Impassable pieces, such as steps for a wheelchair, are left out.

::: example
**Example 3.2 (Dortmund by bike).** Our running example contains all streets and paths of Dortmund from OpenStreetMap (51.42–51.56° N, 7.30–7.55° E, downloaded on 9 November 2026). With one node per junction, the largest strongly connected part has 112,743 nodes and 264,203 directed edges, with 5,068 km of streets and paths. Two edge weights model cyclists:

- **fast**: the travel time at 18 km/h on roads and cycleways; 16 km/h on designated paths, 14 on good tracks and shared footways, 12 on other paths and service lanes, 10 on living streets; times 0.8 on unpaved and times 0.75 on cobbled surfaces; 5 km/h for pushing on footways; motorways, steps, and roads closed to bicycles are left out;
- **quiet**: the travel time times a stress factor of the road: 3 on primary roads, 2.2 on secondary, 1.6 on tertiary, 1.2 on unclassified roads, otherwise 1; with a cycle track only 20% of the extra stress counts, with a cycle lane or a speed limit of 30 km/h 50%.

This is a simple model for teaching: it ignores hills, traffic lights, turns, and the time of day. Real route planners for cyclists use similar ingredients, such as the road class, the cycle infrastructure, and the speed limit.
:::

Road networks are *sparse*: Dortmund has about 2.3 edges per node, and in general $m \leq c \cdot n$ for a small constant $c$, since only few streets meet at a junction. They can also be large: the road network of Western Europe that is used in the route planning literature has 18,010,173 nodes and 42,188,664 edges [Bast et al. 2016], about 160 times our city.

# 3.3 Dijkstra's algorithm

Dijkstra's algorithm [Dijkstra 1959] computes the distances from $s$ in increasing order. Every node $v$ has a *tentative distance* $d(v)$, the length of the best $s$–$v$ path found so far, and a *parent*, its predecessor on that path.

1. Set $d(s) = 0$ and $d(v) = \infty$ for all $v \neq s$. No node is settled.
2. Repeat: *settle* the unsettled node $u$ with the smallest $d(u)$. For each edge $(u, v)$, *relax* it: if $d(u) + c(u, v) < d(v)$, set $d(v) = d(u) + c(u, v)$ and make $u$ the parent of $v$.
3. Stop when $t$ is settled, or when no unsettled node has a finite tentative distance.

The parents of the settled nodes form a shortest-path tree; following the parents back from $t$ gives a shortest path.

::: example
**Example 3.3.** In the undirected graph of Figure 3.2, Dijkstra's algorithm settles $s$ (0), $b$ (1), $a$ (2), $c$ (4), $d$ (5), $e$ (7), and $t$ (8). Two tentative distances improve on the way: $c$ first gets 5 via $b$, then 4 via $a$; $d$ first gets 7 via $a$, then 5 via $c$. The shortest path is $s, a, c, d, t$ with length 8.
:::

![Figure 3.2: The end of Example 3.3: all nodes settled, the shortest-path tree, and the shortest path from s to t.](../lectures/figures/dijkstra-step-7.svg){width="55%"}

## Correctness

::: theorem
**Theorem 3.1 [Dijkstra 1959].** If all edge weights are non-negative, then $d(u) = d(s, u)$ whenever Dijkstra's algorithm settles a node $u$.

*Proof.* Tentative distances are lengths of paths, so $d(u) \geq d(s, u)$ at all times. We show by induction over the settled nodes that, when $u$ is settled, every $s$–$u$ path $P$ has length $c(P) \geq d(u)$; then $d(u) \leq d(s, u)$ as well. For $u = s$, $d(s) = 0$. Otherwise let $S$ be the set of nodes settled before $u$, with $s \in S$. The path $P$ starts in $S$ and ends outside, so it has a first edge $(x, y)$ with $x \in S$ and $y \notin S$ (Figure 3.3).

- By induction, $d(x) = d(s, x)$ is at most the length of $P$ up to $x$. When $x$ was settled, the edge $(x, y)$ was relaxed, so $d(y) \leq d(x) + c(x, y)$, which is at most the length of $P$ up to $y$.
- The algorithm settles $u$ because it has the smallest tentative distance among the unsettled nodes, so $d(y) \geq d(u)$.
- The rest of $P$, from $y$ to $u$, has non-negative length.

Together, $c(P) \geq$ (length of $P$ up to $y$) $\geq d(y) \geq d(u)$. [∎]{.qed}
:::

![Figure 3.3: The proof of Theorem 3.1: S is the set of settled nodes and u the next node to settle; another path P leaves S over the edge (x, y).](../lectures/figures/dijkstra-invariant.svg){width="62%"}

The proof uses non-negative weights only in the last step: the rest of $P$ must not be negative. With a negative edge, both the proof and the algorithm fail. In the graph with the edges $s \to a$ (1), $s \to b$ (2), and $b \to a$ ($-2$), Dijkstra's algorithm settles $a$ with $d(a) = 1$, but $d(s, a) = 0$. The Bellman–Ford algorithm handles negative weights, as long as there is no cycle of negative length, in $O(nm)$ time. Travel times and lengths are never negative.

## Running time

**Adjacency lists.** The algorithm needs the outgoing edges of each settled node. In practice, all edges are stored in one array, sorted by their tail, together with an array of offsets: the edges of node $u$ are those at the positions off$[u]$ to off$[u+1] - 1$. Such an *adjacency array* (also known as the compressed sparse row format) uses $O(n + m)$ memory, and the edges of a node lie next to each other in memory, which is good for the cache. Our demo stores the Dortmund graph this way.

**Priority queue.** The unsettled nodes with finite tentative distance are kept in a priority queue, with the tentative distance as key. Over the whole run, there are at most $n$ insertions, at most $n$ delete-min operations, and at most $m$ decrease-key operations, one per relaxed edge.

- With a **binary heap**, every operation takes $O(\log n)$ time, in total $O((n + m) \log n)$.
- With a **Fibonacci heap** [Fredman and Tarjan 1987], insertions and decrease-key take $O(1)$ amortized time and delete-min $O(\log n)$, in total $O(m + n \log n)$.

For road networks, $m = O(n)$, so both bounds are $O(n \log n)$; the Fibonacci heap pays off on dense graphs. In practice, a binary heap is faster, often with *lazy deletion*: instead of decreasing a key, the node is inserted again with the new key, and outdated entries are skipped when they come out of the heap. Our demo does this.

Can we do better than $O(m + n \log n)$? Dijkstra's algorithm settles the nodes in the order of their distances, so it sorts them, and sorting $n$ numbers needs $\Omega(n \log n)$ comparisons. In this sense, $O(m + n \log n)$ is optimal for Dijkstra's algorithm. Haeupler, Hladík, Rozhoň, Tarjan, and Tětek (2024) show even more: with a suitable heap, Dijkstra's algorithm is *universally optimal* for ordering the nodes by distance; for every graph, its running time in the worst case over all edge weights is optimal up to a constant factor. Algorithms that do not sort can be faster: for directed graphs with non-negative real weights, Duan, Mao, Mao, Shu, and Yin (2025) compute all distances from $s$ in $O(m \log^{2/3} n)$ time, which beats $O(m + n \log n)$ on sparse graphs.

**In Dortmund.** From TU Dortmund to the Phoenix-See (27.4 minutes and 7.6 km by bike), Dijkstra's algorithm settles 62,880 of the 112,743 nodes, in about 15 ms in JavaScript (Figure 3.4). For a single city, this is fast enough. Faster methods are needed for continents (on the road network of Western Europe, a query takes 1.56 s [Dibbelt et al. 2014]), for route planning services with many queries per second, and for the harder problems of the following lectures, which run many such searches.

![Figure 3.4: Dijkstra's algorithm from TU Dortmund to the Phoenix-See: the searched streets (blue) form a disk around the start. Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-dijkstra.png){width="60%"}

# 3.4 Bidirectional search

Dijkstra's algorithm explores a disk around $s$ until it reaches $t$. *Bidirectional search* runs a *forward* search from $s$ and a *backward* search from $t$ on the reversed edges, for instance alternately, so that two smaller disks meet in the middle. If the search space grows with the area, two disks of radius $r/2$ together have half the area of one disk of radius $r$: a factor of 2.

Let $d_F$ and $d_B$ be the tentative distances of the two searches. Whenever a search relaxes an edge $(x, y)$, in its own direction, and the other endpoint already has a tentative distance from the other search, it updates
$$\mu \gets \min\{\mu,\ d_F(x) + c(x, y) + d_B(y)\},$$
the length of the best $s$–$t$ path seen so far; at the start, $\mu = \infty$.

::: theorem
**Lemma 3.2.** Let the edge weights be non-negative. If the searches stop as soon as the smallest keys $\min_F$ and $\min_B$ of their priority queues satisfy $\min_F + \min_B \geq \mu$, then $\mu = d(s, t)$.

*Proof.* $\mu$ is the length of a path, so $\mu \geq d(s, t)$. Let $P$ be a shortest $s$–$t$ path; we show $c(P) \geq \mu$.

If $P$ contains a node $v$ that neither search has settled, then $d(s, v) \geq \min_F$, because Dijkstra's algorithm settles all nodes closer than its smallest key, and likewise $d(v, t) \geq \min_B$. Hence $c(P) \geq d(s, v) + d(v, t) \geq \min_F + \min_B \geq \mu$.

Otherwise every node of $P$ is settled by at least one search. Walk along $P$ from $s$, which the forward search has settled. Let $(x, y)$ be the first edge of $P$ whose end $y$ is not settled by the forward search, so that $y$ is settled by the backward search; if there is no such edge, let $(x, y)$ be the last edge of $P$, with $y = t$. Whichever search settled its endpoint of $(x, y)$ later relaxed this edge, and at that time the other endpoint already had its final distance from the other search. Hence
$\mu \leq d_F(x) + c(x, y) + d_B(y) = d(s, x) + c(x, y) + d(y, t) \leq c(P)$. [∎]{.qed}
:::

The stopping criterion is easy to get wrong. It is tempting to stop as soon as a node is settled by both searches and to return the path through this node. Stopping at that moment is in fact correct, because then $\min_F + \min_B \geq \mu$ holds already, but the path through the node need not be a shortest one: the shortest path may cross from one search to the other over an edge. The answer is $\mu$.

::: example
**Example 3.4.** The undirected graph has the edges $s$–$x$ (5), $x$–$t$ (5), $s$–$u$ (3), $u$–$v$ (3), and $v$–$t$ (3), so $d(s, t) = 9$ via $u$ and $v$. The searches alternate. The forward search settles $s$; the backward search settles $t$ and reaches $x$, which the forward search has reached: $\mu = 5 + 5 = 10$. The forward search settles $u$ (3) and reaches $v$, which the backward search has reached: $\mu = 3 + 3 + 3 = 9$. The backward search settles $v$ (3). Now $\min_F = \min_B = 5$, both at $x$, and $5 + 5 \geq 9$: the search stops with $\mu = 9$, before any node has been settled by both searches. Continuing until the first node is settled by both would settle $x$ in both directions, and the path through $x$ has length 10.
:::

**In Dortmund.** From TU Dortmund to the Phoenix-See, bidirectional search settles 33,547 nodes instead of 62,880, a factor of 1.9 (Figure 3.5). Over 300 random pairs, it settles 34,990 instead of 54,587 nodes on average, a factor of only 1.6: for many random pairs near the border of the map, Dijkstra's disk is cut off by the border.

![Figure 3.5: Bidirectional search from TU Dortmund (blue) and from the Phoenix-See (orange). Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-bidirectional.png){width="60%"}

# 3.5 Goal-directed search: A\* and landmarks

Dijkstra's algorithm and bidirectional search explore all directions alike. *Goal-directed* search prefers nodes that seem to lie towards the target.

::: definition
**Definition 3.2 (heuristic).** A *heuristic* for the target $t$ is a function $h\colon V \to \mathbb{R}$. It is a *lower bound* if $h(v) \leq d(v, t)$ for all $v \in V$, and *consistent* if $h(u) \leq c(u, v) + h(v)$ for every edge $(u, v)$.
:::

A\* [Hart et al. 1968] is Dijkstra's algorithm with a different key: it settles the unsettled node $v$ with the smallest $d(v) + h(v)$, the length of the best known path to $v$ plus an estimate of the rest. With $h = 0$, A\* is Dijkstra's algorithm. A lower bound is also called *admissible*. A consistent heuristic with $h(t) = 0$ is a lower bound: add up the condition along a shortest $v$–$t$ path.

**Terminology.** In artificial intelligence, $h$ is the *heuristic* of A\*. In route planning, the same function is usually called a *potential*, often written $\pi$ [Goldberg and Harrelson 2005]. The name comes from the reduced costs of Lemma 3.3, as for node potentials in network flows; a consistent heuristic is a *feasible potential*.

::: theorem
**Lemma 3.3.** Let $h$ be consistent, and define the *reduced costs* $c_h(u, v) = c(u, v) - h(u) + h(v)$. Then $c_h \geq 0$, A\* with $h$ settles the nodes in the same order as Dijkstra's algorithm with the weights $c_h$, and $d(v) = d(s, v)$ whenever A\* settles a node $v$.

*Proof.* Consistency says exactly that $c_h \geq 0$. For every $s$–$v$ path $P$, the sum telescopes: $c_h(P) = c(P) - h(s) + h(v)$. For a fixed $v$, all $s$–$v$ paths are shifted by the same amount $h(v) - h(s)$, so they keep their order: shortest paths stay shortest, and a tentative distance $d(v)$ with respect to $c$ corresponds to the tentative distance $d(v) - h(s) + h(v)$ with respect to $c_h$. These are the keys of Dijkstra's algorithm with $c_h$; they differ from the keys $d(v) + h(v)$ of A\* by the constant $h(s)$, so both algorithms make the same choices. Dijkstra's algorithm with $c_h \geq 0$ is correct by Theorem 3.1. [∎]{.qed}
:::

So A\* with a consistent heuristic settles every node at most once, and if $h(t) = 0$, it settles only nodes $v$ with $d(s, v) + h(v) \leq d(s, t)$ before it settles $t$. The better the lower bound, the fewer nodes. With the exact distance $h(v) = d(v, t)$, every node on a shortest $s$–$t$ path has the key $d(s, t)$, and every other node a larger key, so A\* settles only nodes on shortest paths. Computing exact distances to $t$, however, is a shortest path problem itself.

::: example
**Example 3.5.** In Figure 3.6 (undirected), the shortest $s$–$t$ path $s, u_1, u_2, t$ has length 6. The edge from $s$ to $\ell_1$ is cheap (1), but leads away from $t$. Dijkstra's algorithm settles $s$ (0), $\ell_1$ (1), $u_1$ (2), $\ell_2$ (3), $u_2$ (4), and $t$ (6): all six nodes. With the consistent lower bound $h(s) = 5$, $h(u_1) = 3$, $h(u_2) = 1$, $h(t) = 0$, $h(\ell_1) = 6$, $h(\ell_2) = 4$, A\* settles $s$, $u_1$, $u_2$ (key 5 each) and $t$ (key 6), and never $\ell_1$: its key is $1 + 6 = 7 > 6$.
:::

![Figure 3.6: A\* on the graph of Example 3.5 with the heuristic h (orange): it settles only s, u₁, u₂, and t.](../lectures/figures/astar.svg){width="55%"}

## The straight-line heuristic

For travel times, a natural lower bound is the straight-line distance divided by the highest speed: $h(v) = \lVert v - t \rVert / v_{\max}$, where $\lVert v - t \rVert$ is the straight-line distance between the positions of $v$ and $t$. No route from $v$ to $t$ is shorter than the straight line, and no edge is faster than $v_{\max}$. If every edge $(u, v)$ takes at least the time $\lVert u - v \rVert / v_{\max}$, the heuristic is also consistent, by the triangle inequality $\lVert u - t \rVert \leq \lVert u - v \rVert + \lVert v - t \rVert$. In the Dortmund demo, $v_{\max} = 18$ km/h, and the travel times are rounded up and never below the straight-line time, so that the heuristic is consistent on every edge.

The straight line is a weak bound for travel times, because few routes run straight at top speed: rivers, railway lines, motorways, and parks force detours, and slow paths cost time. From TU Dortmund to the Phoenix-See, the bound at the start is 21.0 minutes, against a true travel time of 27.4 minutes. A\* settles 8,725 nodes instead of 62,880 (Figure 3.7).

## Landmarks: A\*, landmarks, triangle inequality (ALT)

Better bounds come from the network itself. Goldberg and Harrelson (2005) precompute, for a few *landmarks* $L$, the distances $d(L, v)$ and $d(v, L)$ from and to all nodes $v$.

::: theorem
**Lemma 3.4.** For every landmark $L$ and every node $v$,
$$d(v, t) \geq d(v, L) - d(t, L) \qquad\text{and}\qquad d(v, t) \geq d(L, t) - d(L, v).$$
The maximum of 0 and of these bounds over all landmarks is a consistent lower bound.

*Proof.* The bounds follow from the triangle inequalities $d(v, L) \leq d(v, t) + d(t, L)$ and $d(L, t) \leq d(L, v) + d(v, t)$. For consistency, consider an edge $(u, v)$. For the first bound, $\big(d(u, L) - d(t, L)\big) - \big(d(v, L) - d(t, L)\big) = d(u, L) - d(v, L) \leq c(u, v)$, since $d(u, L) \leq c(u, v) + d(v, L)$. For the second, $d(L, v) - d(L, u) \leq c(u, v)$ in the same way. So every bound is consistent, and so is the constant 0. A maximum of consistent functions is consistent: if $h_i(u) \leq c(u, v) + h_i(v)$ for all $i$, then $\max_i h_i(u) \leq c(u, v) + \max_i h_i(v)$. All of them are lower bounds, so their maximum is one as well. [∎]{.qed}
:::

The first bound is exact if $t$ lies on a shortest path from $v$ to $L$, that is, if $L$ lies "behind" $t$ as seen from $v$. The second bound is exact if $v$ lies on a shortest path from $L$ to $t$, so if $L$ lies behind $v$, for instance behind the start. Good landmarks therefore lie spread out, often at the border of the network. A simple way to choose them is farthest-first selection, which is Gonzalez's algorithm from Section 2.4.3, here with the distance $d(L, v) + d(v, L)$ there and back.

::: example
**Example 3.6 (landmarks in Dortmund).** The demo chooses 8 landmarks by farthest-first selection, starting from TU Dortmund. The first four lie at the border of the network, near the corners of the map. The fifth lies in the middle, just north-east of the campus: once the corners are taken, the middle is farthest from all landmarks chosen so far, as for $k$-center clustering. The last three lie near the middles of the sides. From TU Dortmund to the Phoenix-See, the landmark in the middle gives the best bound for 56% of the nodes that ALT settles, and the one at the western border for 43%: both lie behind the start as seen from the target. The bound at the start is 23.7 minutes, against 21.0 for the straight line and 27.4 for the true travel time. ALT settles 6,123 nodes, A\* with the straight line 8,725 (Figure 3.7); over 300 random pairs, 4,896 against 13,775 on average. The landmark distances take 16 runs of Dijkstra's algorithm over the whole graph, from and to each landmark, about a quarter of a second in the browser.
:::

![Figure 3.7: A\* with the straight line (left) and ALT with 8 landmarks (right; red diamonds, the north-western one is hidden under the legend), from TU Dortmund to the Phoenix-See. Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-astar-alt.png){width="100%"}

# 3.6 Contraction hierarchies

Long routes use few important roads: a trip across Dortmund leaves the residential streets soon and returns to them only near the target. *Contraction hierarchies* [Geisberger et al. 2008] exploit this without being told which roads are important. They order the nodes by importance and *contract* them one by one, from the least important to the most important; a query then searches only *upwards* in this order, from $s$ and from $t$. Contraction hierarchies are, among other techniques, the basis of open-source route planners such as OSRM and GraphHopper, of the customizable variant in Section 3.7, and of the multi-criteria variant in Section 3.8.

## Contracting a node

::: definition
**Definition 3.3 (contraction, shortcut, witness).** To *contract* a node $v$, remove $v$ and its edges from the graph. For every remaining node $u$ with an edge $(u, v)$ and every remaining node $w \neq u$ with an edge $(v, w)$, add a *shortcut* $(u, w)$ of length $c(u, v) + c(v, w)$, unless there is a *witness*: a $u$–$w$ path that avoids $v$ and is at most as long as $c(u, v) + c(v, w)$. Of parallel edges, only the shortest is kept.
:::

Contracting a node keeps all distances between the remaining nodes: a shortcut is exactly as long as the path it replaces, so no distance gets shorter, and a shortest path through $v$ can use the shortcut or the witness instead, so no distance gets longer. Witnesses are found by a small Dijkstra search from $u$ that avoids $v$. This search may stop early, for instance after a fixed number of settled nodes: a missed witness only adds an unnecessary shortcut, never a wrong distance. Every shortcut remembers the node it skips, so that it can later be *unpacked* into the two edges it replaces.

::: example
**Example 3.7.** Figure 3.8 shows a small undirected network: a road $s, a, m, b, t$ with four edges of length 2, and the detours $s, x, m$ with edges of length 3 and 3 and $m, y, t$ with edges of length 2 and 3. We contract in the order $a, x, b, y, s, t, m$.

- Contracting $a$: the path $s, a, m$ has length 4, the only other path from $s$ to $m$ has length 6. Shortcut $s$–$m$ (4).
- Contracting $x$: the path $s, x, m$ has length 6, but the shortcut $s$–$m$ (4) is a witness. Witnesses may use shortcuts.
- Contracting $b$: the path $m, b, t$ has length 4, the detour via $y$ has length 5. Shortcut $m$–$t$ (4).
- Contracting $y$: the path $m, y, t$ has length 5, and the shortcut $m$–$t$ (4) is a witness.
- Then $s$ and $t$ have only $m$ as a neighbour, and contracting them adds nothing.

The hierarchy has two shortcuts. Contracting the important node $m$ first would instead add five shortcuts, between $a$ and $b$, $a$ and $y$, $b$ and $x$, $b$ and $y$, and $x$ and $y$; only the pair $a$, $x$ has a witness, the path $a, s, x$ of length 5.
:::

![Figure 3.8: The network of Example 3.7.](../lectures/figures/ch-contract-0.svg){width="55%"}

The *edge difference* of a node is the number of shortcuts that its contraction adds minus the number of edges it removes. In the exercise of Lecture 5, a node $v$ has the neighbours $a$, $b$, $c$ with edges of length 2, 3, 4, and the graph also has the edges $a$–$b$ (4) and $b$–$c$ (8). Contracting $v$ adds the shortcuts $a$–$c$ (6) and $b$–$c$ (7), which replaces the longer edge $b$–$c$, but none for $a$ and $b$, which have the witness $a$–$b$ of length $4 < 5$. The graph has five edges before and three after: the edge difference is $2 - 3 = -1$, so $v$ is a good node to contract early.

## The order

Any order gives correct distances; the order only decides how many shortcuts are added and how fast the queries are. Good orders contract unimportant nodes first. Implementations keep the nodes in a priority queue whose priority combines, for instance, the edge difference and the number of neighbours already contracted, which spreads the contractions over the map [Geisberger et al. 2008]. After each contraction, the priorities of the neighbours change and are recomputed. The priorities of other nodes can change as well, because witness searches may now use the new shortcuts. Instead of recomputing all of them, the node at the top of the queue is evaluated again before it is contracted, and it goes back into the queue if its priority has become larger than the next key (*lazy updates*).

In Dortmund, with the priority 2 × edge difference + number of contracted neighbours and witness searches that stop after 100 settled nodes, the hierarchy has 185,295 shortcuts for 264,203 edges; contracting all nodes takes about 9 seconds in JavaScript (Node.js). Optimized implementations preprocess continental networks within minutes.

## The query

The *rank* of a node is its position in the contraction order. The query runs a bidirectional Dijkstra search on the original edges and all shortcuts, in which the forward search from $s$ only uses edges to nodes of higher rank, and the backward search from $t$ only uses edges from nodes of higher rank, read backwards. The answer is the best meeting value $\mu = \min_x \big(d_F(x) + d_B(x)\big)$ over the nodes $x$ reached by both searches. Each search may stop as soon as its smallest key is at least $\mu$, since it cannot improve on $\mu$ any more. Unpacking the shortcuts recursively gives the path in the original graph. In Example 3.7, the forward search from $s$ settles $s$ and $m$ (via the shortcut, 4), the backward search from $t$ settles $t$ and $m$ (4), so $\mu = 8$, and unpacking gives $s, a, m, b, t$ (Figure 3.9).

![Figure 3.9: The contraction hierarchy of Example 3.7, with the nodes drawn by rank: the upward searches from s and from t meet at m (4 + 4 = 8).](../lectures/figures/ch-query.svg){width="55%"}

::: theorem
**Theorem 3.5.** For all nodes $s$ and $t$ with $d(s, t) < \infty$, the original edges and the shortcuts contain a shortest $s$–$t$ path that first visits nodes of increasing rank and then nodes of decreasing rank. Hence the query returns $d(s, t)$.

*Proof.* With the shortcuts, the distances are the same as in the original graph, since every shortcut is as long as a path. Start with any shortest $s$–$t$ path $P$ that uses original edges and shortcuts. Call an inner node of $P$ a *valley* if both its neighbours on $P$ have a higher rank. If $P$ has no valley, it first goes up and then down. Otherwise, let $v$ be the valley of lowest rank, with the neighbours $u$ and $w$ on $P$ (Figure 3.10). When $v$ was contracted, $u$ and $w$ were not contracted yet, since their ranks are higher, and edges from $u$ to $v$ and from $v$ to $w$ at most as long as those on $P$ were present. So the contraction of $v$ either added a shortcut $(u, w)$ of length at most $c(u, v) + c(v, w)$, or it found a witness of at most this length that consists of nodes not yet contracted, of higher rank than $v$. Replacing $u, v, w$ in $P$ by the shortcut or the witness gives a path that is no longer, hence again a shortest path. It no longer contains $v$, and every node whose neighbours change, $u$, $w$, and the nodes of a witness, has a higher rank than $v$. So all valleys of the new path have a higher rank than $v$: the rank of the lowest valley increases with every step, and after at most $n$ steps no valley is left.

For the query, let $P$ be such a path and $m$ its highest node. The part of $P$ from $s$ to $m$ only goes up, so the forward search can use it; the part from $m$ to $t$, read backwards, only goes up as well. If neither search stops before settling $m$, then $d_F(m) + d_B(m) \leq c(P) = d(s, t)$. If a search stops earlier, then its smallest key was at least $\mu$, and the part of $P$ on its side is at least that long, so again $\mu \leq c(P)$. Conversely, every value $d_F(x) + d_B(x)$ is the length of an $s$–$t$ path, so $\mu = d(s, t)$. [∎]{.qed}
:::

![Figure 3.10: Why upward searches suffice: a shortest path drawn with the rank as height. The valley v is replaced by the shortcut u–w, or by a witness through higher nodes. In the end, the path goes up from s to its highest node m and down to t, and the upward searches from s and from t meet at m.](../lectures/figures/ch-up-down.svg){width="55%"}

In Dortmund, the query from TU Dortmund to the Phoenix-See settles 239 nodes, against 62,880 for Dijkstra's algorithm; over 300 random pairs, it settles 249 nodes on average (Figure 3.11). The two search trees reach important junctions all over the city, often by shortcuts: the searches only go up, to more important nodes wherever they are, and they do not know where the target lies.

![Figure 3.11: Contraction hierarchy query from TU Dortmund (blue) and from the Phoenix-See (orange); dashed lines are shortcuts. Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-ch.png){width="60%"}

## Comparison and other techniques

| Dortmund by bike | preprocessing | settled nodes, TU → Phoenix-See | mean over 300 random pairs |
|------------------|---------------|--------------------------------:|---------------------------:|
| Dijkstra | none | 62,880 | 54,587 |
| bidirectional | none | 33,547 | 34,990 |
| A\*, straight line | none | 8,725 | 13,775 |
| ALT, 8 landmarks | 16 Dijkstra runs | 6,123 | 4,896 |
| contraction hierarchy | 185,295 shortcuts, about 9 s | 239 | 249 |

: Table 3.2: Settled nodes in Dortmund. All methods give the same distances; the demo was checked against Dijkstra's algorithm on 300 random pairs.

Settled nodes measure the work independently of the computer. On the road network of Western Europe, a query takes 1.56 s with Dijkstra's algorithm and 0.41 ms with a customizable contraction hierarchy [Dibbelt et al. 2014]. The survey of Bast et al. (2016) describes many more techniques, among them:

- *Arc flags* partition the map into regions; every edge stores for which target regions it lies on a shortest path.
- *Transit node routing* [Bast et al. 2007] uses that long routes leave the neighbourhood of the start through a few *access nodes*; distances between all such transit nodes, and from every node to its access nodes, are precomputed.
- *Hub labels* store for every node a list of hubs with their distances, such that every pair of nodes has a common hub on a shortest path; a query intersects two lists. Hub labels are the fastest exact method in practice, at about a microsecond per query, at the price of a lot of memory; they are often computed from a contraction hierarchy.

# 3.7 Personal profiles

Inclusive route planning needs a weight per group or even per person: for a wheelchair user, a parent with a pram, a cautious cyclist, an e-bike. Weights also change with building sites and traffic. A contraction hierarchy is built for one weight, since its shortcuts and witnesses depend on it; the hierarchy of the Dortmund demo is built for travel time and cannot answer queries for the quiet weight. *Customizable contraction hierarchies* [Dibbelt et al. 2014, 2016] split the preprocessing into three phases:

1. **Metric-independent preprocessing**, once: an order computed from the graph alone, by nested dissection, so that small separators of the road network are contracted last; then all shortcuts for this order, without witness searches, since a witness for one weight need not be one for another.
2. **Customization**, for every new weight: the lengths of all shortcuts, in 0.74 seconds for Western Europe on 16 threads.
3. **Queries** as in a contraction hierarchy: 0.41 ms for Western Europe.

This makes personal profiles practical. Accessibility-aware route planning was the topic of the guest lecture by Sabine Storandt on 17 November.

# 3.8 Several criteria

Faster is often louder, steeper, or dirtier. In Example 3.1, the fastest bike route from Dortmund Hbf to the Phoenix-See takes 19.2 minutes, 5.2 km of it on busy roads; a quieter one takes 21.1 minutes, with only 0.2 km on busy roads. There is no single best route. Let every edge $e$ have two costs $c(e) = (c_1(e), c_2(e))$, for instance travel time and quiet weight, both to be minimized. There are three common ways to combine them:

| model | question | difficulty |
|---|---|---|
| weighted sum | minimize $\lambda c_1 + (1 - \lambda) c_2$ for a given $\lambda \in [0, 1]$ | one Dijkstra run |
| constraint | minimize $c_1$ subject to $c_2 \leq B$ | NP-hard |
| Pareto set | all routes that no other route beats in every criterion | can be exponentially large |

A weighted sum is just a new edge weight, $\lambda c_1(e) + (1 - \lambda) c_2(e)$, so everything from Sections 3.3 to 3.7 applies. The constrained problem is known as the shortest weight-constrained path problem and is NP-hard [Garey and Johnson 1979]; Storandt (2012) solves it exactly for bicycle routes with a bound on the height difference, using contraction hierarchies. The Pareto set is the most complete answer: it shows all sensible trade-offs and leaves the choice to the person.

::: definition
**Definition 3.4 (Pareto-optimal).** Let every path have several costs that are all to be minimized, such as travel time and quiet weight. A path $P$ *dominates* a path $Q$ if $P$ is at least as good as $Q$ in every criterion and better in at least one. An $s$–$t$ path is *Pareto-optimal* if no $s$–$t$ path dominates it. The costs of the Pareto-optimal $s$–$t$ paths form the *Pareto front*.
:::

## Weighted sums find only part of the Pareto front

For two criteria, the costs of the $s$–$t$ paths are points in the plane. For $\lambda \in (0, 1)$, every path that minimizes the weighted sum $f_\lambda(x) = \lambda x_1 + (1 - \lambda) x_2$ is Pareto-optimal, since a path that dominates it would have a smaller weighted sum. The converse is false.

::: theorem
**Lemma 3.6.** Let $p$, $q$, $r$ be costs of $s$–$t$ paths, and let $p$ lie above the segment from $q$ to $r$: $p \geq \mu q + (1 - \mu) r$ in both components for some $\mu \in [0, 1]$, and $p \neq \mu q + (1 - \mu) r$. Then $f_\lambda(p) > \min\{f_\lambda(q), f_\lambda(r)\}$ for every $\lambda \in (0, 1)$.

*Proof.* The function $f_\lambda$ is linear with positive coefficients, so $f_\lambda(p) > f_\lambda(\mu q + (1 - \mu) r) = \mu f_\lambda(q) + (1 - \mu) f_\lambda(r) \geq \min\{f_\lambda(q), f_\lambda(r)\}$. [∎]{.qed}
:::

So only routes on the *lower convex hull* of the Pareto front can be optimal for a weighted sum, and apart from ties only its corners; a Pareto-optimal route in a dent between two corners is optimal for no $\lambda \in (0, 1)$. Conversely, every corner of the lower convex hull is the unique optimum for all $\lambda$ in an open interval: a line through the corner can be tilted between the directions of the two hull edges at the corner without meeting the rest of the front.

::: definition
**Definition 3.5 (supported).** A Pareto-optimal route is *supported* if it minimizes a weighted sum $f_\lambda$ for some $\lambda \in [0, 1]$, and *unsupported* otherwise.
:::

::: example
**Example 3.8.** From Dortmund Hbf to the Phoenix-See, there are 115 Pareto-optimal routes for travel time and quiet weight, between the fastest route (19.2 minutes) and the quietest one (21.1 minutes). Minimizing the weighted sum $\lambda \cdot \text{time} + (1 - \lambda) \cdot \text{quiet}$ for $\lambda = 0, 0.01, \ldots, 1$ finds only 13 of them, the corners of the lower convex hull (Figure 3.12); the other 102 routes are unsupported. Each $\lambda$ is one run of Dijkstra's algorithm, about 15 ms.
:::

![Figure 3.12: The 115 Pareto-optimal routes from Dortmund Hbf to the Phoenix-See (grey); the 13 routes found by weighted sums (blue circles) lie on the lower convex hull.](../lectures/figures/dortmund-pareto.svg){width="60%"}

## Multi-criteria Dijkstra (MC-Dijkstra)

To compute the whole Pareto front, *multi-criteria Dijkstra* (MC-Dijkstra) [Martins 1984] keeps *labels* instead of distances: a label $\ell = (\ell_1, \ell_2)$ at a node $v$ is the cost of one $s$–$v$ path. Every node $v$ has a *bag* $B_v$ of labels of which none dominates another, and a priority queue holds the labels that are not settled yet, ordered *lexicographically*: by the first component, ties by the second.

1. Put the label $(0, 0)$ into $B_s$ and into the queue.
2. Repeat until the queue is empty: extract the lexicographically smallest label $\ell$, at node $u$, and *settle* it. For each edge $(u, v)$, let $\ell' = \ell + c(u, v)$. If no label in $B_v$ dominates or equals $\ell'$, insert $\ell'$ into $B_v$ and into the queue, and remove all labels that $\ell'$ dominates from $B_v$ and from the queue.
3. At the end, $B_t$ contains the costs of the Pareto-optimal $s$–$t$ paths. Following the labels back, as with the parents in Dijkstra's algorithm, gives one path for each cost.

With a single criterion, every bag holds at most one label, and MC-Dijkstra is Dijkstra's algorithm.

::: example
**Example 3.9.** Consider the graph of Figure 3.13 with the costs (time, stress) $s \to a$ (1, 3), $s \to b$ (3, 1), $a \leftrightarrow b$ (1, 1), $a \to t$ (2, 4), and $b \to t$ (2, 2). MC-Dijkstra settles the labels $s$ (0, 0), $a$ (1, 3), $b$ (2, 4), $b$ (3, 1), $t$ (3, 7), $a$ (4, 2), $t$ (4, 6), $t$ (5, 3), in this order. Settling $b$ (2, 4) creates $(3, 5)$ at $a$, which $(1, 3)$ dominates. Settling $a$ (4, 2) creates $(5, 3)$ at $b$, dominated by $(3, 1)$, and $(6, 6)$ at $t$, dominated by $(4, 6)$. The node $b$ keeps two labels, $(2, 4)$ via $a$ and $(3, 1)$ directly, since neither dominates the other. At the end, $B_t$ holds three labels: $(3, 7)$ for the path $s, a, t$, $(4, 6)$ for $s, a, b, t$, and $(5, 3)$ for $s, b, t$.
:::

![Figure 3.13: The end of Example 3.9: the final labels at every node (blue) and the rejected ones (red, struck through); three Pareto-optimal labels at t.](../lectures/figures/martins-step-6.svg){width="60%"}

::: theorem
**Theorem 3.7.** If all edge costs are non-negative, then MC-Dijkstra never removes a settled label, and at the end, $B_t$ consists of the costs of the Pareto-optimal $s$–$t$ paths.

*Proof.* A new label is a settled label plus a non-negative cost, so it is lexicographically at least as large as the label just settled. Hence labels are settled in lexicographically non-decreasing order, and every label created after the settling of $\ell$ is lexicographically at least $\ell$. A label that dominates $\ell$ is lexicographically smaller than $\ell$, so no later label dominates a settled label: settled labels are never removed.

Every label is the cost of an $s$–$v$ walk. A walk that returns to a node $x$ cannot create a new label there: when it first reached $x$, the label it had then was settled, and the label after the cycle is at least as large in both components. So all labels belong to paths, there are finitely many of them, and MC-Dijkstra terminates.

Let $P = (s = v_0, v_1, \ldots, v_k = t)$ be a Pareto-optimal path and $P_i$ its part up to $v_i$. No $s$–$v_i$ path dominates $P_i$: followed by the rest of $P$, it would give an $s$–$t$ walk, and after removing cycles an $s$–$t$ path, that dominates $P$. So no label at $v_i$ dominates $c(P_i)$. By induction over $i$, a label with the cost $c(P_i)$ is settled at $v_i$: for $i = 0$, this is $(0, 0)$, and extending it over the edge $(v_i, v_{i+1})$ gives $c(P_{i+1})$, which is inserted unless a label with the same cost is already in $B_{v_{i+1}}$, and is never removed. So $c(P) \in B_t$ at the end. Conversely, if an $s$–$t$ path dominated a label $\ell \in B_t$, then so would a Pareto-optimal path, whose cost is in $B_t$ as well; but no label in a bag dominates another. [∎]{.qed}
:::

**When to stop.** Unlike Dijkstra's algorithm, MC-Dijkstra must not stop at the first label at $t$: further Pareto-optimal labels at $t$ may still be in the queue, as in Example 3.9. It may, however, discard every label that a label at $t$ already dominates (*target pruning*): extending it only gives labels that are dominated at $t$. Lower bounds on the remaining costs to $t$, as in A\*, make the pruning stronger [Mandow and Pérez de la Cruz 2010].

**Implementation.** The Dortmund demo compares a new label only with the settled labels at its node and checks it again when it comes out of the queue. Then one number per node suffices for the test. Every settled label at $v$ is lexicographically at most the new label $\ell'$, so it is at most as large in the first component, and it dominates or equals $\ell'$ if and only if its second component is at most $\ell'_2$. So $\ell'$ is rejected if and only if $\ell'_2 \geq \min\{\ell_2 : \ell \text{ settled at } v\}$ [Hernández et al. 2023].

::: example
**Example 3.10 (MC-Dijkstra in Dortmund).** From Dortmund Hbf to the Phoenix-See, MC-Dijkstra with target pruning settles 1,364,095 labels at 43,797 nodes, 31 per node on average and at most 291 (Figure 3.14); Dijkstra's algorithm settles 39,856 nodes for travel time. It finds the 115 Pareto-optimal routes of Example 3.8 in about 0.4 seconds in JavaScript, against 15 ms for one Dijkstra run; comparing each new label with the whole bag, the same search took 7 seconds. There are so many labels because every node has its own Pareto front of partial routes from $s$, fast but busy against slow but quiet, and each of them may be the beginning of a Pareto-optimal route to another node.
:::

![Figure 3.14: MC-Dijkstra from Dortmund Hbf to the Phoenix-See: settled labels (blue), the 115 Pareto-optimal routes (grey), the fastest (blue) and the quietest (green); right, the Pareto front with 13 routes on the convex hull. Map data © OpenStreetMap contributors, ODbL.](../lectures/figures/dortmund-martins.png){width="100%"}

## How many Pareto-optimal routes?

::: theorem
**Lemma 3.8.** For every $k \geq 1$, there is a graph with $2^k$ Pareto-optimal $s$–$t$ paths, all with different costs.

*Proof.* Take a chain of $k$ sections, where section $i = 0, \ldots, k - 1$ offers an upper edge with the cost $(2^i, 0)$ and a lower edge with the cost $(0, 2^i)$ (Figure 3.15; to avoid parallel edges, subdivide each upper edge by a node). A path chooses one edge per section. If $x$ is the sum of $2^i$ over the sections where it takes the upper edge, its cost is $(x, 2^k - 1 - x)$. By the binary representation, the $2^k$ paths have the $2^k$ different values $x = 0, \ldots, 2^k - 1$. Of two of them, the one with the smaller first component has the larger second component, so none dominates another. [∎]{.qed}
:::

![Figure 3.15: The chain of Lemma 3.8 with four sections: all 16 paths have costs $(x, y)$ with $x + y = 15$.](../lectures/figures/pareto-chain.svg){width="70%"}

So no algorithm that outputs the whole Pareto front runs in polynomial time in the worst case. In practice, the fronts are smaller, but still large. For bicycle routes in Prague with three criteria (travel time, comfort, and elevation gain), Hrnčíř et al. (2017) find 1,647 Pareto-optimal routes per query on average on neighbourhood graphs of about 10 km², and 2,984 on the whole city with 69,544 nodes, where NAMOA\*, a multi-criteria A\*, takes 106 seconds on average. Heuristics, which prune by an ellipse around $s$ and $t$, by ratios of the criteria, and by $\varepsilon$-dominance, bring this down to about 81 ms on the neighbourhood graphs, and 56 % of the routes they find are optimal ones. Nobody wants to look at 3,000 routes; a route planner shows a few diverse ones.

## Contraction hierarchies for several criteria

For weighted sums, contraction hierarchies extend to all $\lambda$ at once. Funke and Storandt (2013) compute one hierarchy for all weighted sums of two criteria, with $\lambda$ chosen at query time. When $v$ is contracted, the shortcut $(u, w)$ is needed if and only if the path $\pi = u, v, w$ is a best $u$–$w$ path for some $\lambda \in [0, 1]$. For a path $p$, the weighted cost $\lambda c_1(p) + (1 - \lambda) c_2(p)$ is a linear function of $\lambda$. So every $u$–$w$ path is a line over $[0, 1]$, and $\pi$ needs a shortcut if and only if its line touches the lower envelope of all these lines (Figure 3.16). This is the dual view of Lemma 3.6: the corners of the lower convex hull of the costs correspond to the segments of the lower envelope of the lines.

The witness search becomes a binary search over $\lambda$. It starts with the interval $[0, 1]$ of weights for which $\pi$ might be best, and runs Dijkstra's algorithm for the weight $\lambda$ in the middle of the interval. If it finds $\pi$, the shortcut is added. Otherwise it finds a path $p$ that is at least as good as $\pi$ at $\lambda$. The lines of $p$ and $\pi$ cross at most once, so $\pi$ can only be better than $p$ on one side of the crossing, and the interval shrinks to the part on this side. If the interval becomes empty, no shortcut is needed.

::: example
**Example 3.11.** Let $\pi = u, v, w$ cost $(5, 7)$, and let there be two other $u$–$w$ paths, via $x$ with the cost $(8, 2)$ and via $y$ with $(2, 10)$ (Figure 3.16). For $\lambda = 0.5$, the path via $x$ is best, with the weighted cost 5 against 6 for $\pi$. Their lines, $2 + 6\lambda$ and $7 - 2\lambda$, cross at $\lambda = 0.625$, and $\pi$ is below only for larger $\lambda$; the interval becomes $[0.625, 1]$. For its middle, $\lambda = 0.8125$, the path via $y$ is best, with 3.5 against 5.375 for $\pi$. Their lines cross at $\lambda = 0.5$, and $\pi$ would need $\lambda < 0.5$. The interval is empty, and no shortcut is needed, although neither path alone is a witness for all $\lambda$. Both together are: $\pi$ is Pareto-optimal, but unsupported.
:::

![Figure 3.16: The three u–w paths of Example 3.11 as lines over λ: via y (2, 10), via x (8, 2), and π via v (5, 7, orange and dashed), which lies above the lower envelope.](../lectures/figures/mcch-envelope.svg){width="50%"}

In every round, $\lambda$ is the middle of the interval and $p$ is at least as good as $\pi$ there, so the interval at least halves. With integer edge costs of at most $M$ in a graph with $n$ nodes, all crossings are fractions with denominators of at most $2nM$, and two different crossings differ by at least $1/(4n^2M^2)$. So $O(\log(nM))$ runs of Dijkstra's algorithm suffice for one witness search, and the preprocessing takes polynomial time [Funke and Storandt 2013]; in their experiments, a witness search needed at most 8 rounds. On OpenStreetMap graphs with travel time and fuel cost as criteria and a random $\lambda$ per query, they report queries of 0.42 ms for Baden-Württemberg (2.5 million nodes) and 1.98 ms for California (11.3 million nodes), against 410 ms and 2,100 ms for Dijkstra's algorithm, a speed-up of about 1,000. The preprocessing took 2 and 18 minutes on one core; the hierarchy has about twice as many edges as the graph, and about 0.05 % of the nodes stay uncontracted, as a core at the top.

**Other techniques.** Goal direction carries over: NAMOA\* uses one potential per criterion [Mandow and Pérez de la Cruz 2010], and BOA\* tests dominance in constant time for two criteria [Hernández et al. 2023]. Arc flags carry over if a flag marks the edges on some Pareto-optimal route into a region [Delling and Wagner 2009], which works when the Pareto fronts are small. Techniques that store one distance per pair of nodes, such as transit node routing, suffer most: with several criteria, a distance becomes a set.

# 3.9 Public transport

Public transport is the backbone of SDG target 11.2, access to safe, affordable, accessible, and sustainable transport systems for all. Why not run Dijkstra's algorithm on the network of lines? Because the cost of an edge depends on when one gets there: one waits for the next train.

## Timetables

A timetable consists of *stops* and *trips*. A trip is one run of a vehicle; trips with the same sequence of stops form a *route*. We split every trip into *connections*, its hops from one stop to the next.

::: definition
**Definition 3.6 (connection, journey).** A *connection* $c$ goes from the stop $\text{from}(c)$, departing at $\text{dep}(c)$, to the stop $\text{to}(c)$, arriving at $\text{arr}(c) > \text{dep}(c)$, with the trip $\text{trip}(c)$. Changing trips at a stop $v$ takes at least the *change time* $\text{ch}(v) \geq 0$. A *journey* from $s$ to $t$, departing not before $\tau$, is a sequence of connections $c_1, \ldots, c_k$ with $\text{from}(c_1) = s$, $\text{dep}(c_1) \geq \tau$, $\text{to}(c_k) = t$, and $\text{to}(c_i) = \text{from}(c_{i+1})$ for all $i$, such that $c_{i+1}$ is the next connection of the same trip as $c_i$, or $\text{arr}(c_i) + \text{ch}(\text{to}(c_i)) \leq \text{dep}(c_{i+1})$. Its arrival time is $\text{arr}(c_k)$.
:::

::: example
**Example 3.12.** Figure 3.17 shows a small example around TU Dortmund, with real stop names, a simplified network, and invented times: the H-Bahn from Campus Süd to Dortmund Universität, the S1 between Dortmund Hbf and Essen Hbf via Dortmund Universität and Bochum Hbf, and the RE from Dortmund Hbf via Bochum Hbf to Essen Hbf. Changing takes 2 minutes at Dortmund Universität, 5 at Dortmund Hbf, and 4 at Bochum Hbf and Essen Hbf. Six trips give 13 connections. Leaving Campus Süd at 7:50, one arrives in Essen at 8:39 with three trips (H-Bahn 7:56–8:00, S1 8:04–8:12 to Dortmund Hbf, RE 8:17–8:39), or at 9:01 with two trips (H-Bahn, then the S1 from Dortmund Universität at 8:21).
:::

![Figure 3.17: The network of Example 3.12, with real stop names, a simplified network, and invented times; minimum change times of 2, 5, 4, and 4 minutes.](../lectures/figures/transit-terms.svg){width="75%"}

**Data.** Timetables are published in the General Transit Feed Specification (GTFS), a set of CSV files: `stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt` with one line per stop of a trip, `calendar.txt`, and `transfers.txt` with minimum change times. Consecutive lines of a trip in `stop_times.txt` give its connections. Timetables for all of Germany are open data, for instance from DELFI and gtfs.de, and the VRR publishes its timetable for the Rhine-Ruhr area.

**Queries.** An *earliest arrival query* asks, for $s$, $t$, and $\tau$, for a journey that arrives as early as possible. A *profile query* asks for the best journeys for all departure times in an interval, and a *multi-criteria query* for the Pareto set with respect to arrival time and number of trips. In Example 3.12, the two journeys form this Pareto set; an earliest arrival query finds only the first.

## Timetables as graphs

In the *time-expanded graph*, every departure and every arrival is a node, the connections are edges, and waiting edges link the events at each stop in the order of time (Figure 3.18, left); changes need additional nodes. Dijkstra's algorithm works without any change, but the graph is huge: for one day of a country-wide timetable, it has tens of millions of nodes. In the *time-dependent graph*, every stop is a node, and the cost of an edge depends on the time at which one is at its tail: $f_{uv}(\tau)$ is the earliest arrival at $v$ for someone at $u$ at time $\tau$, a step function (Figure 3.18, right). Dijkstra's algorithm, with earliest arrival times as labels, remains correct if every edge is *FIFO*: $f_{uv}$ is non-decreasing, so being somewhere later never gets one anywhere earlier. Timetables are FIFO, since one can always wait for a later trip.

![Figure 3.18: Left, the time-expanded graph with one node per departure and arrival and waiting edges at every stop; right, the time-dependent edge from Dortmund Hbf to Bochum Hbf: the arrival time as a step function of the departure time.](../lectures/figures/transit-graphs.svg){width="90%"}

## The Connection Scan Algorithm

The Connection Scan Algorithm (CSA) [Dibbelt et al. 2018] needs neither a graph nor a priority queue. The connections are sorted by departure time once, in a preprocessing step. A query keeps an arrival time $d[v]$ for every stop and a flag for every trip.

1. Set $d[s] = \tau$ and $d[v] = \infty$ for all other stops $v$; no trip is reached.
2. Scan the connections $c$ with $\text{dep}(c) \geq \tau$ in the order of departure. The connection $c$ is *usable* if its trip is reached, or if $d[\text{from}(c)] + \text{ch}(\text{from}(c)) \leq \text{dep}(c)$, where no change time is needed at $s$. If $c$ is usable, mark its trip as reached and set $d[\text{to}(c)] = \min\{d[\text{to}(c)], \text{arr}(c)\}$.
3. Stop as soon as $\text{dep}(c) \geq d[t]$.

To output the journey, store for every trip the connection where it was entered, and for every stop the connection that last improved it. Footpaths between stops can be added by updating, after an improvement of $d[v]$, the stops within walking distance of $v$.

::: example
**Example 3.13.** We run CSA from Campus Süd at 7:50 in Example 3.12 (Figure 3.19). The S1 from Bochum Hbf at 7:45 departs too early and is not scanned; the S1 from Dortmund Hbf at 7:52 is not usable, since Dortmund Hbf is not reached yet. The H-Bahn at 7:56 is usable and sets Dortmund Universität to 8:00. The S1 from there at 8:01 is not usable, since changing takes until 8:02, but the S1 at 8:04 is, and it sets Dortmund Hbf to 8:12. The RE at 8:09 and the S1 at 8:12 leave Dortmund Hbf before 8:17; the RE at 8:17 is usable and sets Bochum Hbf to 8:27. There, the RE at 8:19 and the S1 at 8:20 leave before 8:31. The S1 from Dortmund Universität at 8:21 is usable, but its arrival at Bochum Hbf at 8:40 does not improve 8:27. The RE from Bochum Hbf at 8:27 belongs to a reached trip and sets Essen Hbf to 8:39. The next connection departs at 8:40, so the scan stops. The earliest arrival is 8:39, with the journey of Example 3.12.
:::

![Figure 3.19: Example 3.13: the 13 connections sorted by departure time; usable connections in green, the others in grey; the scan stops at the last row.](../lectures/figures/csa-step-5.svg){width="70%"}

::: theorem
**Theorem 3.9.** If every connection takes positive time and all change times are non-negative, CSA computes the earliest arrival time at $t$.

*Proof.* By induction over the scan, every value $d[v]$ that CSA sets is the arrival time of a journey, so $d[t]$ is never too small. Conversely, let $c_1, \ldots, c_k$ be a journey with the earliest arrival time at $t$. Its connections depart in increasing order: $\text{dep}(c_{i+1}) \geq \text{arr}(c_i) > \text{dep}(c_i)$. We show by induction that every $c_i$ that is scanned is usable. The connection $c_1$ departs from $s$ at or after $\tau = d[s]$. If $c_{i+1}$ is the next connection of the trip of $c_i$, this trip was marked when $c_i$ was scanned. Otherwise the journey changes at $v = \text{to}(c_i)$, and $d[v] + \text{ch}(v) \leq \text{arr}(c_i) + \text{ch}(v) \leq \text{dep}(c_{i+1})$. If the scan reaches $c_k$, then $d[t] \leq \text{arr}(c_k)$ afterwards. If it stops before, at a connection $c$ with $\text{dep}(c) \geq d[t]$, then $d[t] \leq \text{dep}(c) \leq \text{dep}(c_k) < \text{arr}(c_k)$ already. In both cases, $d[t] \leq \text{arr}(c_k)$. [∎]{.qed}
:::

The order of departure is a topological order of the time-expanded graph: every connection that can come before $c$ in a journey departs earlier and is scanned before $c$. So CSA is a dynamic program over an acyclic graph, like the segmentation algorithms of Lecture 4, and needs no priority queue. A query is one pass over an array, which suits the cache. On the timetable of London with 4.85 million connections, a query takes 41 ms, and 2.7 ms when it starts the scan at $\tau$ by binary search and uses the stopping criterion; on the timetable of Germany with 46 million connections, 329 ms and 68 ms [Dibbelt et al. 2018]. Scanning the connections in decreasing order of departure, with a list of Pareto-optimal pairs of departure and arrival time per stop, answers profile queries in one pass. Lecture 7 (8 December) treats journeys with few changes (RAPTOR [Delling et al. 2015]), several criteria, and bikes on the first and last mile.

# 3.10 Check your understanding

1. Give a directed graph with a negative edge for which Dijkstra's algorithm computes a wrong distance. Which step of the proof of Theorem 3.1 fails?

    <details>
    <summary>Answer</summary>
    The edges $s \to a$ (1), $s \to b$ (2), $b \to a$ ($-2$): $a$ is settled with $d(a) = 1$, but $d(s, a) = 0$ via $b$. The last step fails. The path $P = s, b, a$ leaves $S = \{s\}$ over the edge $(s, b)$, and $d(b) = 2 \geq d(a) = 1$ holds, but the rest of $P$, from $b$ to $a$, has the negative length $-2$.
    </details>

2. In Example 3.4, why is it not enough to stop when a node is settled by both searches and to return the path through this node? Is it wrong to stop at that moment?

    <details>
    <summary>Answer</summary>
    The first node settled by both searches is $x$, and the path through $x$ has length 10, but $d(s, t) = 9$: the shortest path crosses from the forward to the backward search over the edge $u$–$v$. Stopping at that moment is not wrong, since then $\min_F + \min_B \geq \mu$ holds already, but the answer must be $\mu$, the best path seen so far.
    </details>

3. For which graphs does the Fibonacci heap give an asymptotically better running time for Dijkstra's algorithm than the binary heap? What do both bounds give for road networks?

    <details>
    <summary>Answer</summary>
    $O(m + n \log n)$ is better than $O((n + m) \log n)$ if $m$ grows faster than $n$, for instance on dense graphs with $m = \Theta(n^2)$: $O(n^2)$ against $O(n^2 \log n)$. For road networks, $m = O(n)$, and both bounds are $O(n \log n)$.
    </details>

4. A heuristic may be a lower bound without being consistent. Give a small example in which A\* then settles a node before its distance is known.

    <details>
    <summary>Answer</summary>
    Take the edges $s \to a$ (4), $s \to b$ (1), $b \to a$ (1), $a \to t$ (5), so $d(s, t) = 7$ via $b$ and $a$, and the heuristic $h(s) = h(a) = h(t) = 0$, $h(b) = 6$. It is a lower bound, since $d(b, t) = 6$, but not consistent: $h(b) = 6 > c(b, a) + h(a) = 1$. A\* settles $s$, then $a$ with key $4 + 0 = 4$, although $d(s, a) = 2$; $b$ has key $1 + 6 = 7$. Only after settling $b$ does A\* find the shorter path to $a$, and it has to process $a$ again. A\* with reopening still finds a shortest path for every lower bound [Hart et al. 1968], but it may process nodes several times; with a consistent heuristic, Lemma 3.3 rules this out.
    </details>

5. Why is the straight-line distance divided by $v_{\max}$ a lower bound on the travel time? Why does the Dortmund demo round travel times up?

    <details>
    <summary>Answer</summary>
    No route is shorter than the straight line, and no edge is faster than $v_{\max}$. The demo stores travel times as whole numbers (tenths of seconds). Rounding down could make an edge slightly faster than $v_{\max}$ allows, and then the heuristic would no longer be consistent on that edge.
    </details>

6. Why is the maximum of landmark bounds a lower bound, but not the sum of two of them?

    <details>
    <summary>Answer</summary>
    Each bound is at most $d(v, t)$, so their maximum is as well. Two bounds can both be exact: if $t$ lies on shortest paths from $v$ to $L_1$ and from $v$ to $L_2$, both first bounds equal $d(v, t)$, and their sum is $2\,d(v, t)$.
    </details>

7. In Example 3.7, why does contracting $m$ first add so many shortcuts? Are the distances still correct?

    <details>
    <summary>Answer</summary>
    $m$ is a hub: the shortest connections between most pairs of its neighbours pass through $m$, so there are few witnesses, and five shortcuts are needed. The distances stay correct for every order, but the hierarchy gets more edges, and the queries search more. This is why the priority prefers nodes with a small edge difference.
    </details>

8. Why do the search trees of a contraction hierarchy query reach junctions all over the city instead of staying near the route?

    <details>
    <summary>Answer</summary>
    The searches only go up, to more important nodes, in every direction; they do not know where the target is. Important nodes are spread over the city, because the order prefers to contract nodes all over the map. The trees are tiny all the same: 239 nodes from TU Dortmund to the Phoenix-See.
    </details>

9. Give three routes with travel time and quiet weight such that one of them is Pareto-optimal, but not optimal for any weighted sum.

    <details>
    <summary>Answer</summary>
    $A = (0, 10)$, $B = (6, 6)$, $C = (10, 0)$. No route dominates $B$. For every $\lambda$, $B$ has the weighted sum $6$, while the better of $A$ and $C$ has $\min\{10 - 10\lambda, 10\lambda\} \leq 5$. $B$ lies above the line from $A$ to $C$.
    </details>

10. Why can the metric-independent phase of customizable contraction hierarchies not use witness searches?

    <details>
    <summary>Answer</summary>
    A witness depends on the weights: a path that is at most as long as $u, v, w$ for one weight can be longer for another. The shortcuts of the first phase must be correct for every weight, so they are added for all pairs; only the customization uses the weights, to compute the lengths of the shortcuts.
    </details>

11. Why must MC-Dijkstra continue after it has settled the first label at $t$, while Dijkstra's algorithm may stop when it settles $t$?

    <details>
    <summary>Answer</summary>
    The first label at $t$ is only best in the first criterion. Other Pareto-optimal labels at $t$, larger in the first criterion but smaller in the second, may still be in the queue: in Example 3.9, $(3, 7)$ is settled first, and $(4, 6)$ and $(5, 3)$ come later. With target pruning, the search still ends early in practice, since it discards all labels that a label at $t$ dominates.
    </details>

12. In Example 3.9, the label $(3, 5)$ at $a$ is rejected. Which path does it belong to, and why can no Pareto-optimal $s$–$t$ path begin with it?

    <details>
    <summary>Answer</summary>
    It belongs to $s, a, b, a$, a walk with a cycle. The label $(1, 3)$ of $s, a$ dominates it, so every continuation of $s, a, b, a$ is dominated by the same continuation of $s, a$. This is the argument of Theorem 3.7: prefixes of Pareto-optimal paths are Pareto-optimal.
    </details>

13. The chain of Lemma 3.8 uses costs that double from section to section. What changes if every section offers the costs $(1, 0)$ and $(0, 1)$?

    <details>
    <summary>Answer</summary>
    All $2^k$ paths are still Pareto-optimal, but they have only $k + 1$ different costs $(j, k - j)$. MC-Dijkstra keeps one label per cost, since it rejects labels that equal one in the bag, so it settles at most $i + 1$ labels at the node after $i$ sections and runs in polynomial time. With doubling costs, all $2^k$ costs are different.
    </details>

14. In the witness search for contraction hierarchies with several criteria, why does the interval at least halve in every round?

    <details>
    <summary>Answer</summary>
    The search runs Dijkstra's algorithm for the middle $\lambda$ of the interval and finds a path $p$ that is at least as good as $\pi$ at $\lambda$. The lines of $p$ and $\pi$ cross at most once, and $\pi$ can only be better on one side of the crossing, which does not contain $\lambda$. So the new interval lies on one side of the middle.
    </details>

15. Why does the Connection Scan Algorithm need no priority queue?

    <details>
    <summary>Answer</summary>
    Every connection that can come before $c$ in a journey departs earlier than $c$. So the order of departure, computed once in the preprocessing, is a topological order of the time-expanded graph, and scanning in this order is a dynamic program over an acyclic graph. The order does not depend on the query, unlike the order in which Dijkstra's algorithm settles nodes.
    </details>

16. In Example 3.13, which arrival time does CSA compute for Essen Hbf if the H-Bahn leaves Campus Süd at 8:06 instead of 7:56 (arriving at 8:10)? Which step of the scan changes?

    <details>
    <summary>Answer</summary>
    9:01. Dortmund Universität is now reached at 8:10, too late for the S1 at 8:04 to Dortmund Hbf, so the RE at 8:17 cannot be reached. The S1 from Dortmund Universität at 8:21 is usable, since $8{:}10 + 2 \leq 8{:}21$, and arrives in Essen at 9:01, with one change.
    </details>

# References

::: refs
- Bast, H., Delling, D., Goldberg, A., Müller-Hannemann, M., Pajor, T., Sanders, P., Wagner, D., Werneck, R. F. (2016). Route planning in transportation networks. In *Algorithm Engineering*, LNCS 9220, 19–80. <https://doi.org/10.1007/978-3-319-49487-6_2>
- Bast, H., Funke, S., Matijevic, D., Sanders, P., Schultes, D. (2007). In transit to constant time shortest-path queries in road networks. *9th Workshop on Algorithm Engineering and Experiments (ALENEX)*, 46–59.
- Cohen, A., Dalyot, S. (2021). Route planning for blind pedestrians using OpenStreetMap. *Environment and Planning B* 48(6), 1511–1526.
- Delling, D., Pajor, T., Werneck, R. F. (2015). Round-based public transit routing. *Transportation Science* 49(3), 591–604.
- Delling, D., Wagner, D. (2009). Pareto paths with SHARC. *8th International Symposium on Experimental Algorithms (SEA)*, LNCS 5526, 125–136.
- Destatis (2026). 7,8 Millionen schwerbehinderte Menschen leben in Deutschland. Press release 246, 13 July 2026.
- Dibbelt, J., Pajor, T., Strasser, B., Wagner, D. (2018). Connection scan algorithm. *ACM Journal of Experimental Algorithmics* 23, 1.7. <https://doi.org/10.1145/3274661>
- Dibbelt, J., Strasser, B., Wagner, D. (2014). Customizable contraction hierarchies. *13th International Symposium on Experimental Algorithms (SEA)*, LNCS 8504; journal version: *ACM Journal of Experimental Algorithmics* 21 (2016).
- Dijkstra, E. W. (1959). A note on two problems in connexion with graphs. *Numerische Mathematik* 1, 269–271.
- Dill, J., McNeil, N. (2013). Four types of cyclists? Examination of typology for better understanding of bicycling behavior and potential. *Transportation Research Record* 2387, 129–138.
- Duan, R., Mao, J., Mao, X., Shu, X., Yin, L. (2025). Breaking the sorting barrier for directed single-source shortest paths. *57th ACM Symposium on Theory of Computing (STOC)*. <https://arxiv.org/abs/2504.17033>
- Ehrgott, M., Wang, J. Y. T., Raith, A., van Houtte, C. (2012). A bi-objective cyclist route choice model. *Transportation Research Part A* 46(4), 652–663.
- Fredman, M. L., Tarjan, R. E. (1987). Fibonacci heaps and their uses in improved network optimization algorithms. *Journal of the ACM* 34(3), 596–615.
- Funke, S., Storandt, S. (2013). Polynomial-time construction of contraction hierarchies for multi-criteria objectives. *15th Workshop on Algorithm Engineering and Experiments (ALENEX)*.
- Garey, M. R., Johnson, D. S. (1979). *Computers and Intractability: A Guide to the Theory of NP-Completeness*. W. H. Freeman.
- Geisberger, R., Sanders, P., Schultes, D., Delling, D. (2008). Contraction hierarchies: faster and simpler hierarchical routing in road networks. *7th Workshop on Experimental Algorithms (WEA)*, LNCS 5038, 319–333.
- Goldberg, A. V., Harrelson, C. (2005). Computing the shortest path: A\* search meets graph theory. *16th ACM-SIAM Symposium on Discrete Algorithms (SODA)*, 156–165.
- Haeupler, B., Hladík, R., Rozhoň, V., Tarjan, R. E., Tětek, J. (2024). Universal optimality of Dijkstra via beyond-worst-case heaps. *65th IEEE Symposium on Foundations of Computer Science (FOCS)*. <https://arxiv.org/abs/2311.11793>
- Hart, P. E., Nilsson, N. J., Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics* 4(2), 100–107.
- Hernández, C., Yeoh, W., Baier, J. A., Zhang, H., Suazo, L., Koenig, S., Salzman, O. (2023). Simple and efficient bi-objective search algorithms via fast dominance checks. *Artificial Intelligence* 314, 103807.
- Hrnčíř, J., Žilecký, P., Song, Q., Jakob, M. (2017). Practical multicriteria urban bicycle routing. *IEEE Transactions on Intelligent Transportation Systems* 18(3), 493–504.
- Mandow, L., Pérez de la Cruz, J. L. (2010). Multiobjective A\* search with consistent heuristics. *Journal of the ACM* 57(5), 27.
- Martins, E. Q. V. (1984). On a multicriteria shortest path problem. *European Journal of Operational Research* 16(2), 236–245.
- Minett, C. F., Salomons, A. M., Daamen, W., van Arem, B., Kuijpers, S. (2011). Eco-routing: comparing the fuel consumption of different routes between an origin and destination using field test speed profiles and synthetic speed profiles. *IEEE Forum on Integrated and Sustainable Transportation Systems*, 32–39.
- OpenStreetMap contributors (2026). Street network of Dortmund, downloaded on 9 November 2026 via the Overpass API. Open Database License. <https://www.openstreetmap.org/copyright>
- Storandt, S. (2012). Route planning for bicycles – exact constrained shortest paths made practical via contraction hierarchy. *22nd International Conference on Automated Planning and Scheduling (ICAPS)*, 234–242.
- Umweltbundesamt (2026a). Treibhausgasdaten 2025. Press release 08/2026, 14 March 2026.
- Umweltbundesamt (2026b). Radverkehr. Web page, citing *Mobilität in Deutschland 2023*.
- United Nations (2015). *Transforming our world: the 2030 Agenda for Sustainable Development*. Resolution A/RES/70/1.
:::

# License

These notes are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Suggested attribution: "Kevin Buchin, Algorithms and Sustainability, Lecture Notes, TU Dortmund University, CC BY 4.0". The maps and the Dortmund graph are based on data © OpenStreetMap contributors, available under the Open Database License (ODbL); the graph of the demo is a derived database and also available under the ODbL. The map images, the demo code, and all other figures are own work under CC BY 4.0. The small example graphs are constructed, not measured, and the bicycle profile is a model for teaching. The colors of the Sustainable Development Goals are used for orientation only; these notes are not endorsed by the United Nations. Not covered by the license: the TU Dortmund logo and the Decker software and its themes.
