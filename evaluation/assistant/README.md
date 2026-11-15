# Passenger assistant evaluation

Evaluated on 2026-11-15.

| Set | Passed | Expected excerpt | Faithful quotation | Unsupported correctly declined |
| --- | ---: | ---: | ---: | ---: |
| Tuning | 8/8 | 5/5 | 5/5 | 3/3 |
| Regression baseline | 43/60 | 29/40 | 35/35 | 14/20 |
| Regression after matcher changes | 60/60 | 40/40 | 40/40 | 20/20 |
| Independent release set | 51/60 | 31/40 | 31/31 | 20/20 |

The release misses were R08, R15, R17, R23, R24, R31, R32, R34 and R40.
All nine returned the fallback for a supported question.

Faithful quotation measures whether the answer reproduced its cited excerpt.
Expected-excerpt retrieval measures whether it selected the intended excerpt.

All 15 multi-turn PostgreSQL API scenarios passed. They checked clarification,
fallback, topic changes and ordered history across successive requests.
