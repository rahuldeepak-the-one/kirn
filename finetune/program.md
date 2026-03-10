# Kirn Fine-tuning Agent Instructions

## Objective
Iteratively improve the `finetune/train.py` configuration to produce the best
possible Kirn model within a 5-minute time budget per experiment.

## Metric
Evaluation is done via `finetune/eval.py`. The metric is **pass rate** — how
many of the 8 test scenarios the model handles correctly. Target: 7/8+.

## Rules
1. You may ONLY modify `finetune/train.py` (hyperparameters, LoRA config).
2. You may ONLY modify `finetune/generate_dataset.py` (add more examples).
3. Do NOT modify `finetune/eval.py` — that is the fixed evaluation.
4. Do NOT modify any files outside `finetune/`.

## Workflow
1. **Setup** (one-time):
   ```bash
   uv run finetune/generate_dataset.py
   ```

2. **Train** (each iteration):
   ```bash
   uv run finetune/train.py
   ```

3. **Evaluate**:
   ```bash
   uv run finetune/eval.py
   ```

4. **Analyze**: Read the pass/fail results. Decide which hyperparameters
   or dataset changes could improve failed cases.

5. **Iterate**: Modify `train.py` or `generate_dataset.py` and repeat.

## Hyperparameters to Tune
- `LORA_R`: LoRA rank (try 8, 16, 32, 64)
- `LORA_ALPHA`: scaling factor (usually 2x LORA_R)
- `LR`: learning rate (try 1e-4, 2e-4, 5e-4)
- `EPOCHS`: number of passes (try 2, 3, 5)
- `MAX_SEQ_LEN`: context length (try 512, 1024, 2048)
- `target_modules`: which layers to adapt (add/remove projections)

## Dataset Improvements
- Add more error correction scenarios
- Add more diverse tool call examples
- Ensure tool call format is consistent: `<tool_call>\n{json}\n</tool_call>`
- Make sure the personality stays sharp and concise
