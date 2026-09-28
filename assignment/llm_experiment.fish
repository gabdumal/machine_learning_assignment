#!/usr/bin/env fish

# python -m pipeline.llm \
#     --dataset genis \
#     --method zero_shot \
#     --test-sample-size 2000 \
#     --api-backend lm_studio

# python -m pipeline.llm \
#     --dataset genis \
#     --method few_shot \
#     --test-sample-size 2000 \
#     --api-backend lm_studio

# python -m pipeline.llm \
#     --dataset rosids \
#     --method zero_shot \
#     --test-sample-size 2000 \
#     --api-backend lm_studio

python -m pipeline.llm \
    --dataset rosids \
    --method few_shot \
    --test-sample-size 2000 \
    --api-backend lm_studio
