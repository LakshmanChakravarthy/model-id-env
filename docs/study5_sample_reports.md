# Study 5: sample reports for review

Three simulated experiments, one per true account. The account is named in each heading here for your review only; Claude never sees it. All three are shown at the full evidence level (4); at lower levels the later sections are omitted. Under each report is the ideal reader's posterior: what a reader shown only levels 1, 2, 3, or 4 should believe.

**Please check:** does this read like a C-PRO results section? Are the numbers plausible? Is anything missing that a reviewer would expect, or present that would never be reported? Is the wording of the three accounts (shown to Claude above the report) fair to the field?

## The three accounts, as Claude will see them

**(A) Compositional.** Participants perform novel tasks by reusing the practiced rules as separable parts: they reconfigure the practiced task set that shares the most rules with the novel task, changing the rules that differ. They do not rely on practiced conjunctive (whole-task) representations for novel tasks. Repeating a novel task only adds general practice; no new whole-task representation is formed.

**(B) Conjunctive.** Performance relies mainly on conjunctive (whole-task) representations formed during practice. A novel task tends to retrieve the practiced conjunction that shares the most rules with it: this is fast, but the retrieved task's responses intrude where the two tasks differ. Composing a novel task from its rules is possible but slow. Once a novel task has been performed, it is stored as a new conjunction that persists across the session.

**(C) Dual-route with compilation.** Participants mostly compose novel tasks from rules, but practiced conjunctions are sometimes retrieved and compete (with occasional intrusions). A novel task that has been performed is compiled into a new conjunction, but this new representation decays over intervening mini-blocks.

---

# Sample report: true account = compositional

## Method (summary)

32 participants performed the Concrete Permuted Rule Operations (C-PRO) paradigm. Each task combines one logic rule (BOTH, NOT BOTH, EITHER, NEITHER), one sensory rule (RED, VERTICAL, HIGH PITCH, CONSTANT TONE), and one motor rule (LEFT INDEX, LEFT MIDDLE, RIGHT INDEX, RIGHT MIDDLE); 64 tasks in total. On each trial two audiovisual stimuli are presented; the logic rule is applied to whether each stimulus has the sensory feature, and the motor rule maps the result to a button (for example, LEFT INDEX: true -> left index finger, false -> left middle finger). Tasks are presented in mini-blocks: an instruction screen, then 3 trials, with speeded responses.

**Practice phase.** Four tasks covering all 12 rules (each rule in exactly one practiced task), practiced over 6 blocks:
- NEITHER / VERTICAL / RIGHT INDEX
- NOT BOTH / CONSTANT TONE / LEFT MIDDLE
- BOTH / RED / LEFT INDEX
- EITHER / HIGH PITCH / RIGHT MIDDLE

**Test phase.** The 4 practiced tasks (2 mini-blocks each) and 18 novel tasks. Every novel task combines practiced rules. Each novel task was presented in 3 mini-blocks: the second occurrence followed the first after either a short lag (1-2 intervening mini-blocks; half of the novel tasks) or a long lag (8-12; the other half), and the third occurrence followed after 8-12 intervening mini-blocks. Unless noted, novel-task results refer to the first occurrence.

RT is the mean of correct trials. SE is the standard error across participants.

## Results

**Practice.** RT and accuracy for the practiced tasks over the practice blocks:

| Block | RT | Accuracy |
|---|---|---|
| 1 | 1280 ms (SE 34) | 80.4% (SE 0.9) |
| 2 | 884 ms (SE 26) | 90.4% (SE 0.7) |
| 3 | 799 ms (SE 20) | 92.6% (SE 0.6) |
| 4 | 750 ms (SE 21) | 94.1% (SE 0.5) |
| 5 | 726 ms (SE 22) | 95.3% (SE 0.6) |
| 6 | 719 ms (SE 22) | 95.0% (SE 0.5) |

**Test: practiced vs. novel tasks.**

| Condition | RT | Accuracy |
|---|---|---|
| Practiced tasks | 662 ms (SE 20) | 97.9% (SE 0.5) |
| Novel tasks | 1404 ms (SE 35) | 84.7% (SE 1.3) |

Novel vs. practiced tasks, paired t-tests: RT t(31) = 16.10, p < .001; accuracy t(31) = -9.44, p < .001.

**Novel tasks by overlap with the practice set.** Each novel task shares either 2 rules or 1 rule with its most similar practiced task (9 and 9 novel tasks). For tasks sharing 2 rules, the table also splits by which rule type differs from that practiced task.

| Novel tasks | RT | Accuracy |
|---|---|---|
| Share 2 rules | 1341 ms (SE 33) | 85.9% (SE 1.4) |
| Share 1 rule | 1475 ms (SE 36) | 84.3% (SE 1.5) |
| Share 2, logic rule differs | 1504 ms (SE 44) | 87.5% (SE 2.3) |
| Share 2, sensory rule differs | 1340 ms (SE 31) | 85.1% (SE 2.1) |
| Share 2, motor rule differs | 1241 ms (SE 36) | 83.3% (SE 2.1) |

Share 2 vs. share 1 rule, paired t-tests: RT t(31) = -7.06, p < .001; accuracy t(31) = 1.02, p = .317.

**Intrusion errors.** For novel tasks sharing 2 rules with a practiced task, we classified each error by whether the response given is the one that practiced task would require on that trial (an intrusion). If errors were unrelated to the practiced task, about 33% would match by chance.

| Rule that differs | Intrusions (% of errors) |
|---|---|
| logic | 39.2% (SE 7.0) |
| sensory | 34.0% (SE 7.8) |
| motor | 28.5% (SE 8.7) |

**Repetition of novel tasks.**

| Novel tasks | RT | Accuracy |
|---|---|---|
| 1st occurrence | 1404 ms (SE 35) | 84.7% (SE 1.3) |
| 2nd occurrence, short lag | 1392 ms (SE 33) | 85.3% (SE 1.4) |
| 2nd occurrence, long lag | 1351 ms (SE 33) | 83.7% (SE 1.6) |
| 3rd occurrence | 1343 ms (SE 32) | 86.1% (SE 1.2) |

Paired t-tests on RT: 2nd occurrence (short lag) vs. 1st occurrence t(31) = -0.87, p = .393; 2nd occurrence, long vs. short lag t(31) = -2.29, p = .029.

*Ideal reader's posterior by evidence level:* L1: compositional 0.52, conjunctive 0.14, dual-route 0.34; L2: compositional 0.90, conjunctive 0.00, dual-route 0.10; L3: compositional 1.00, conjunctive 0.00, dual-route 0.00; L4: compositional 1.00, conjunctive 0.00, dual-route 0.00

---

# Sample report: true account = conjunctive

## Method (summary)

32 participants performed the Concrete Permuted Rule Operations (C-PRO) paradigm. Each task combines one logic rule (BOTH, NOT BOTH, EITHER, NEITHER), one sensory rule (RED, VERTICAL, HIGH PITCH, CONSTANT TONE), and one motor rule (LEFT INDEX, LEFT MIDDLE, RIGHT INDEX, RIGHT MIDDLE); 64 tasks in total. On each trial two audiovisual stimuli are presented; the logic rule is applied to whether each stimulus has the sensory feature, and the motor rule maps the result to a button (for example, LEFT INDEX: true -> left index finger, false -> left middle finger). Tasks are presented in mini-blocks: an instruction screen, then 3 trials, with speeded responses.

**Practice phase.** Four tasks covering all 12 rules (each rule in exactly one practiced task), practiced over 6 blocks:
- NOT BOTH / VERTICAL / LEFT INDEX
- NEITHER / HIGH PITCH / RIGHT MIDDLE
- BOTH / CONSTANT TONE / LEFT MIDDLE
- EITHER / RED / RIGHT INDEX

**Test phase.** The 4 practiced tasks (2 mini-blocks each) and 18 novel tasks. Every novel task combines practiced rules. Each novel task was presented in 3 mini-blocks: the second occurrence followed the first after either a short lag (1-2 intervening mini-blocks; half of the novel tasks) or a long lag (8-12; the other half), and the third occurrence followed after 8-12 intervening mini-blocks. Unless noted, novel-task results refer to the first occurrence.

RT is the mean of correct trials. SE is the standard error across participants.

## Results

**Practice.** RT and accuracy for the practiced tasks over the practice blocks:

| Block | RT | Accuracy |
|---|---|---|
| 1 | 1592 ms (SE 56) | 76.7% (SE 0.8) |
| 2 | 1096 ms (SE 38) | 89.0% (SE 0.5) |
| 3 | 976 ms (SE 33) | 91.1% (SE 0.7) |
| 4 | 919 ms (SE 28) | 92.9% (SE 0.5) |
| 5 | 887 ms (SE 29) | 94.9% (SE 0.5) |
| 6 | 874 ms (SE 30) | 94.4% (SE 0.6) |

**Test: practiced vs. novel tasks.**

| Condition | RT | Accuracy |
|---|---|---|
| Practiced tasks | 751 ms (SE 16) | 96.6% (SE 0.6) |
| Novel tasks | 1654 ms (SE 40) | 70.8% (SE 1.6) |

Novel vs. practiced tasks, paired t-tests: RT t(31) = 20.62, p < .001; accuracy t(31) = -15.00, p < .001.

**Novel tasks by overlap with the practice set.** Each novel task shares either 2 rules or 1 rule with its most similar practiced task (9 and 9 novel tasks). For tasks sharing 2 rules, the table also splits by which rule type differs from that practiced task.

| Novel tasks | RT | Accuracy |
|---|---|---|
| Share 2 rules | 1503 ms (SE 45) | 63.0% (SE 2.0) |
| Share 1 rule | 1758 ms (SE 43) | 76.6% (SE 2.0) |
| Share 2, logic rule differs | 1658 ms (SE 46) | 65.3% (SE 3.5) |
| Share 2, sensory rule differs | 1322 ms (SE 39) | 77.8% (SE 2.7) |
| Share 2, motor rule differs | 1669 ms (SE 53) | 50.3% (SE 3.5) |

Share 2 vs. share 1 rule, paired t-tests: RT t(31) = -10.46, p < .001; accuracy t(31) = -5.38, p < .001.

**Intrusion errors.** For novel tasks sharing 2 rules with a practiced task, we classified each error by whether the response given is the one that practiced task would require on that trial (an intrusion). If errors were unrelated to the practiced task, about 33% would match by chance.

| Rule that differs | Intrusions (% of errors) |
|---|---|
| logic | 89.9% (SE 3.6) |
| sensory | 89.4% (SE 5.6) |
| motor | 88.7% (SE 4.7) |

**Repetition of novel tasks.**

| Novel tasks | RT | Accuracy |
|---|---|---|
| 1st occurrence | 1654 ms (SE 40) | 70.8% (SE 1.6) |
| 2nd occurrence, short lag | 890 ms (SE 26) | 91.1% (SE 1.5) |
| 2nd occurrence, long lag | 896 ms (SE 24) | 92.6% (SE 1.0) |
| 3rd occurrence | 782 ms (SE 19) | 95.9% (SE 0.7) |

Paired t-tests on RT: 2nd occurrence (short lag) vs. 1st occurrence t(31) = -19.37, p < .001; 2nd occurrence, long vs. short lag t(31) = 0.69, p = .496.

*Ideal reader's posterior by evidence level:* L1: compositional 0.24, conjunctive 0.37, dual-route 0.39; L2: compositional 0.00, conjunctive 0.85, dual-route 0.15; L3: compositional 0.00, conjunctive 0.99, dual-route 0.01; L4: compositional 0.00, conjunctive 1.00, dual-route 0.00

---

# Sample report: true account = dual-route

## Method (summary)

32 participants performed the Concrete Permuted Rule Operations (C-PRO) paradigm. Each task combines one logic rule (BOTH, NOT BOTH, EITHER, NEITHER), one sensory rule (RED, VERTICAL, HIGH PITCH, CONSTANT TONE), and one motor rule (LEFT INDEX, LEFT MIDDLE, RIGHT INDEX, RIGHT MIDDLE); 64 tasks in total. On each trial two audiovisual stimuli are presented; the logic rule is applied to whether each stimulus has the sensory feature, and the motor rule maps the result to a button (for example, LEFT INDEX: true -> left index finger, false -> left middle finger). Tasks are presented in mini-blocks: an instruction screen, then 3 trials, with speeded responses.

**Practice phase.** Four tasks covering all 12 rules (each rule in exactly one practiced task), practiced over 6 blocks:
- EITHER / CONSTANT TONE / RIGHT INDEX
- NEITHER / VERTICAL / LEFT INDEX
- NOT BOTH / RED / LEFT MIDDLE
- BOTH / HIGH PITCH / RIGHT MIDDLE

**Test phase.** The 4 practiced tasks (2 mini-blocks each) and 18 novel tasks. Every novel task combines practiced rules. Each novel task was presented in 3 mini-blocks: the second occurrence followed the first after either a short lag (1-2 intervening mini-blocks; half of the novel tasks) or a long lag (8-12; the other half), and the third occurrence followed after 8-12 intervening mini-blocks. Unless noted, novel-task results refer to the first occurrence.

RT is the mean of correct trials. SE is the standard error across participants.

## Results

**Practice.** RT and accuracy for the practiced tasks over the practice blocks:

| Block | RT | Accuracy |
|---|---|---|
| 1 | 1663 ms (SE 42) | 75.8% (SE 1.1) |
| 2 | 1137 ms (SE 31) | 85.8% (SE 0.8) |
| 3 | 1027 ms (SE 28) | 89.4% (SE 0.7) |
| 4 | 981 ms (SE 23) | 90.8% (SE 0.7) |
| 5 | 939 ms (SE 27) | 90.8% (SE 0.8) |
| 6 | 905 ms (SE 24) | 90.4% (SE 0.8) |

**Test: practiced vs. novel tasks.**

| Condition | RT | Accuracy |
|---|---|---|
| Practiced tasks | 867 ms (SE 25) | 93.1% (SE 0.9) |
| Novel tasks | 1217 ms (SE 25) | 80.0% (SE 1.4) |

Novel vs. practiced tasks, paired t-tests: RT t(31) = 10.33, p < .001; accuracy t(31) = -7.89, p < .001.

**Novel tasks by overlap with the practice set.** Each novel task shares either 2 rules or 1 rule with its most similar practiced task (9 and 9 novel tasks). For tasks sharing 2 rules, the table also splits by which rule type differs from that practiced task.

| Novel tasks | RT | Accuracy |
|---|---|---|
| Share 2 rules | 1150 ms (SE 24) | 77.3% (SE 1.5) |
| Share 1 rule | 1278 ms (SE 26) | 82.2% (SE 1.3) |
| Share 2, logic rule differs | 1167 ms (SE 29) | 75.0% (SE 3.3) |
| Share 2, sensory rule differs | 1114 ms (SE 28) | 81.2% (SE 2.8) |
| Share 2, motor rule differs | 1146 ms (SE 31) | 70.1% (SE 2.8) |

Share 2 vs. share 1 rule, paired t-tests: RT t(31) = -8.14, p < .001; accuracy t(31) = -2.52, p = .017.

**Intrusion errors.** For novel tasks sharing 2 rules with a practiced task, we classified each error by whether the response given is the one that practiced task would require on that trial (an intrusion). If errors were unrelated to the practiced task, about 33% would match by chance.

| Rule that differs | Intrusions (% of errors) |
|---|---|
| logic | 69.8% (SE 7.5) |
| sensory | 43.6% (SE 8.5) |
| motor | 78.3% (SE 5.4) |

**Repetition of novel tasks.**

| Novel tasks | RT | Accuracy |
|---|---|---|
| 1st occurrence | 1217 ms (SE 25) | 80.0% (SE 1.4) |
| 2nd occurrence, short lag | 1057 ms (SE 21) | 84.3% (SE 1.1) |
| 2nd occurrence, long lag | 1153 ms (SE 23) | 81.8% (SE 1.5) |
| 3rd occurrence | 1073 ms (SE 20) | 81.4% (SE 1.3) |

Paired t-tests on RT: 2nd occurrence (short lag) vs. 1st occurrence t(31) = -13.46, p < .001; 2nd occurrence, long vs. short lag t(31) = 6.98, p < .001.

*Ideal reader's posterior by evidence level:* L1: compositional 0.34, conjunctive 0.26, dual-route 0.40; L2: compositional 0.04, conjunctive 0.50, dual-route 0.47; L3: compositional 0.00, conjunctive 0.29, dual-route 0.71; L4: compositional 0.00, conjunctive 0.00, dual-route 1.00
