# LLM evaluation (synthesis prompt styles)

Exposures judged: **6** · judge & synthesizer: **llama3.1** · retrieval: **rerank**

| Prompt style | Faithfulness (1-5) | Actionability (1-5) | Overall |
|---|---|---|---|
| concise **(best)** | 5.00 | 4.17 | 4.58 |
| detailed | 4.83 | 4.17 | 4.50 |
| checklist | 4.83 | 4.17 | 4.50 |

**Winner: concise** — wired as the default synthesis prompt (`settings.synthesis_prompt`). Scores are LLM-as-judge (1-5): faithfulness (grounded in context) and actionability (concrete, correct steps).
