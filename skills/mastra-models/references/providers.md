# Providers, gateways, and environment variables

Built from `https://mastra.ai/models/environment-variables.md` and `https://mastra.ai/models/gateways.md`. The model router reads these variables automatically. The registry changes often: confirm a prefix and its variables with `scripts/provider-registry.mjs` or the provider page before relying on a row.

## Contents

- Using this table
- Gateways
- Major providers
- All providers (A to Z)

---

## Using this table

- The model string is `<prefix><model-id>`, for example prefix `openai/` plus `gpt-6.1-sol` gives `'openai/gpt-6.1-sol'`.
- Gateway strings add the upstream provider: `openrouter/<provider>/<model>`, `vercel/<provider>/<model>`, `mastra/<provider>/<model>`.
- `azure-openai/<deployment-name>` uses your Azure deployment name instead of a model ID.
- When two variables are listed, set all of them unless the provider page says one is a fallback (Google reads `GOOGLE_API_KEY`, then falls back to `GOOGLE_GENERATIVE_AI_API_KEY`).
- Per-provider pages live at `https://mastra.ai/models/providers/<prefix>` and `https://mastra.ai/models/gateways/<prefix>`.

---

## Gateways

| Gateway | Prefix | Environment variables |
|---|---|---|
| Azure OpenAI | `azure-openai/` | `AZURE_API_KEY`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID` |
| Mastra | `mastra/` | `MASTRA_GATEWAY_API_KEY` |
| Merge Gateway | `merge-gateway/` | `MERGE_GATEWAY_API_KEY` |
| Neon | `neon/` | `NEON_AI_GATEWAY_BASE_URL`, `NEON_AI_GATEWAY_TOKEN` |
| Netlify | `netlify/` | `NETLIFY_TOKEN`, `NETLIFY_SITE_ID` |
| OpenRouter | `openrouter/` | `OPENROUTER_API_KEY` |
| Vercel | `vercel/` | `AI_GATEWAY_API_KEY` |

Azure OpenAI is configured with `new AzureOpenAIGateway({...})` from `@mastra/core/llm` in `new Mastra({ gateways })`. The management variables (`AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_SUBSCRIPTION_ID`) are only needed for dynamic deployment discovery. See `api.md` (Gateways).

---

## Major providers

| Provider | Prefix | Environment variables |
|---|---|---|
| Anthropic | `anthropic/` | `ANTHROPIC_API_KEY` |
| DeepSeek | `deepseek/` | `DEEPSEEK_API_KEY` |
| Google | `google/` | `GOOGLE_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY` |
| Groq | `groq/` | `GROQ_API_KEY` |
| Mistral | `mistral/` | `MISTRAL_API_KEY` |
| OpenAI | `openai/` | `OPENAI_API_KEY` |
| xAI | `xai/` | `XAI_API_KEY` |

---

## All providers (A to Z)

| Provider | Prefix | Environment variables |
|---|---|---|
| 302.AI | `302ai/` | `302AI_API_KEY` |
| Abacus | `abacus/` | `ABACUS_API_KEY` |
| abliteration.ai | `abliteration-ai/` | `ABLIT_KEY` |
| above.dev | `above/` | `ABOVE_API_KEY` |
| AgentRouter | `agentrouter/` | `AGENTROUTER_API_KEY` |
| Agnes AI | `agnes/` | `AGNES_API_KEY` |
| AI-ROUTER | `ai-router/` | `AI_ROUTER_API_KEY` |
| AI/ML API | `aimlapi/` | `AIMLAPI_API_KEY` |
| ai& | `aiand/` | `AIAND_API_KEY` |
| AI21 Labs | `ai21/` | `AI21_API_KEY` |
| ainetcafe | `ainetcafe/` | `AINETCAFE_API_KEY` |
| Aixy | `aixy/` | `AIXY_API_KEY` |
| AKI.IO | `aki-io/` | `AKI_IO_API_KEY` |
| Alibaba | `alibaba/` | `DASHSCOPE_API_KEY` |
| Alibaba (China) | `alibaba-cn/` | `DASHSCOPE_API_KEY` |
| Alibaba Coding Plan | `alibaba-coding-plan/` | `ALIBABA_CODING_PLAN_API_KEY` |
| Alibaba Coding Plan (China) | `alibaba-coding-plan-cn/` | `ALIBABA_CODING_PLAN_API_KEY` |
| Alibaba Token Plan | `alibaba-token-plan/` | `ALIBABA_TOKEN_PLAN_API_KEY` |
| Alibaba Token Plan (China) | `alibaba-token-plan-cn/` | `ALIBABA_TOKEN_PLAN_API_KEY` |
| Ambient | `ambient/` | `AMBIENT_API_KEY` |
| AMD | `amd/` | `AMD_API_KEY` |
| Anthropic | `anthropic/` | `ANTHROPIC_API_KEY` |
| AnyAPI | `anyapi/` | `ANYAPI_API_KEY` |
| Arcee | `arcee/` | `ARCEE_API_KEY` |
| Atomic Chat | `atomic-chat/` | `ATOMIC_CHAT_API_KEY` |
| Auriko | `auriko/` | `AURIKO_API_KEY` |
| Bailing | `bailing/` | `BAILING_API_TOKEN` |
| Baseten | `baseten/` | `BASETEN_API_KEY` |
| Bee by HEOSSI | `bee/` | `BEE_API_KEY` |
| Berget.AI | `berget/` | `BERGET_API_KEY` |
| Blue Claw | `blueclaw/` | `BLUECLAW_API_KEY` |
| Bothub | `bothub/` | `BOTHUB_API_KEY` |
| Boundless | `boundless/` | `BOUNDLESS_API_KEY` |
| Cerebras | `cerebras/` | `CEREBRAS_API_KEY` |
| Charm Hyper | `hyper/` | `HYPER_API_KEY` |
| Chutes | `chutes/` | `CHUTES_API_KEY` |
| Clarifai | `clarifai/` | `CLARIFAI_PAT` |
| Claudinio | `claudinio/` | `CLAUDINIO_API_KEY` |
| ClinePass | `cline-pass/` | `CLINE_API_KEY` |
| CloudFerro Sherlock | `cloudferro-sherlock/` | `CLOUDFERRO_SHERLOCK_API_KEY` |
| Cloudflare Workers AI | `cloudflare-workers-ai/` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_KEY` |
| CommandCode | `commandcode/` | `CMD_API_KEY` |
| CoralBricks | `coralbricks/` | `CORAL_API_KEY` |
| CoreWeave | `wandb/` | `WANDB_API_KEY` |
| Cortecs | `cortecs/` | `CORTECS_API_KEY` |
| CrossModel | `crossmodel/` | `CROSSMODEL_API_KEY` |
| Crusoe | `crusoe/` | `CRUSOE_API_KEY` |
| D.Run (China) | `drun/` | `DRUN_API_KEY` |
| DaoXE | `daoxe/` | `DAOXE_API_KEY` |
| Databricks | `databricks/` | `DATABRICKS_HOST`, `DATABRICKS_TOKEN` |
| Deep Infra | `deepinfra/` | `DEEPINFRA_API_KEY` |
| DeepSeek | `deepseek/` | `DEEPSEEK_API_KEY` |
| DevPass (LLM Gateway) | `llmgateway/` | `LLMGATEWAY_API_KEY` |
| DigitalOcean | `digitalocean/` | `DIGITALOCEAN_ACCESS_TOKEN` |
| DInference | `dinference/` | `DINFERENCE_API_KEY` |
| EBCloud | `ebcloud/` | `EBCLOUD_API_KEY` |
| Echo | `echo/` | `ECHO_API_KEY` |
| Eden AI | `edenai/` | `EDENAI_API_KEY` |
| EmpirioLabs AI | `empiriolabs/` | `EMPIRIOLABS_API_KEY` |
| engy | `engy/` | `ENGY_API_KEY` |
| evroc | `evroc/` | `EVROC_API_KEY` |
| FastRouter | `fastrouter/` | `FASTROUTER_API_KEY` |
| Fireworks AI | `fireworks-ai/` | `FIREWORKS_API_KEY` |
| FreeModel | `freemodel/` | `FREEMODEL_API_KEY` |
| Friendli | `friendli/` | `FRIENDLI_TOKEN` |
| FrogBot | `frogbot/` | `FROGBOT_API_KEY` |
| GMI Cloud | `gmicloud/` | `GMICLOUD_API_KEY` |
| Google | `google/` | `GOOGLE_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY` |
| GreenPT | `greenpt/` | `GREENPT_API_KEY` |
| Groq | `groq/` | `GROQ_API_KEY` |
| Helicone | `helicone/` | `HELICONE_API_KEY` |
| Hetzner | `hetzner/` | `HETZNER_API_KEY` |
| Hopper | `hopper/` | `HOPPER_API_KEY` |
| HPC-AI | `hpc-ai/` | `HPC_AI_API_KEY` |
| Hugging Face | `huggingface/` | `HF_TOKEN` |
| Impossibl | `impossibl/` | `IMPOSSIBL_API_KEY` |
| Inception | `inception/` | `INCEPTION_API_KEY` |
| Inceptron | `inceptron/` | `INCEPTRON_API_KEY` |
| Inco | `inco/` | `INCO_API_KEY` |
| Infer by Flow7 | `infer/` | `INFER_API_KEY` |
| Inference | `inference/` | `INFERENCE_API_KEY` |
| InferX | `inferx/` | `INFERX_API_KEY` |
| Infomaniak | `infomaniak/` | `INFOMANIAK_PRODUCT_ID`, `INFOMANIAK_API_KEY` |
| IO.NET | `io-net/` | `IOINTELLIGENCE_API_KEY` |
| IteraCompute | `iteracompute/` | `ITERACOMPUTE_API_KEY` |
| Jalapeno Cloud | `jalapeno/` | `JALAPENO_API_KEY` |
| Jiekou.AI | `jiekou/` | `JIEKOU_API_KEY` |
| Kenari | `kenari/` | `KENARI_API_KEY` |
| Kilo Gateway | `kilo/` | `KILO_API_KEY` |
| Kimi For Coding (kimi.ai) | `kimi-code-plan-global/` | `KIMI_API_KEY` |
| Kimi For Coding (kimi.com) | `kimi-code-plan-cn/` | `KIMI_API_KEY` |
| klokintegration.se | `klokintegration/` | `KLOKINTEGRATION_API_KEY` |
| Kosmik Compute | `kosmik/` | `KOSMIK_API_KEY` |
| KUAE Cloud Coding Plan | `kuae-cloud-coding-plan/` | `KUAE_API_KEY` |
| Lilac | `lilac/` | `LILAC_API_KEY` |
| Liquid Inference | `liquid/` | `LIQUID_API_KEY` |
| LLM Gateway | `llmgateway-providers/` | `LLMGATEWAY_API_KEY` |
| LLM Tech | `llmtech/` | `LLMTECH_API_KEY` |
| LLMTR | `llmtr/` | `LLMTR_API_KEY` |
| LMStudio | `lmstudio/` | `LMSTUDIO_API_KEY` |
| LongCat | `longcat/` | `LONGCAT_API_KEY` |
| LowRouter | `lowrouter/` | `LOWROUTER_API_KEY` |
| LucidQuery | `lucidquery/` | `LUCIDQUERY_API_KEY` |
| Lynkr | `lynkr/` | `LYNKR_API_KEY` |
| Meganova | `meganova/` | `MEGANOVA_API_KEY` |
| Melious | `melious/` | `MELIOUS_API_KEY` |
| Meta | `meta/` | `META_MODEL_API_KEY` |
| MiniMax (minimax.cn) | `minimax-cn/` | `MINIMAX_API_KEY` |
| MiniMax (minimax.io) | `minimax/` | `MINIMAX_API_KEY` |
| MiniMax Token Plan (minimax.cn) | `minimax-cn-coding-plan/` | `MINIMAX_API_KEY` |
| MiniMax Token Plan (minimax.io) | `minimax-coding-plan/` | `MINIMAX_API_KEY` |
| Mistral | `mistral/` | `MISTRAL_API_KEY` |
| Mixlayer | `mixlayer/` | `MIXLAYER_API_KEY` |
| Moark | `moark/` | `MOARK_API_KEY` |
| Modal | `modal/` | `MODAL_PROXY_TOKEN` |
| Model Oracle AI | `model-oracle-ai/` | `MODEL_ORACLE_API_KEY` |
| Modelis | `modelis/` | `MODELIS_API_KEY` |
| ModelScope | `modelscope/` | `MODELSCOPE_API_KEY` |
| Modular | `modular/` | `MODULAR_API_KEY` |
| Moonshot AI | `moonshotai/` | `MOONSHOT_API_KEY` |
| Moonshot AI (China) | `moonshotai-cn/` | `MOONSHOT_API_KEY` |
| Morph | `morph/` | `MORPH_API_KEY` |
| Munito AI | `munito/` | `MUNITO_API_KEY` |
| Munito AI (EU) | `munito-eu/` | `MUNITO_API_KEY` |
| NaN | `nan/` | `NAN_API_KEY` |
| NanoGPT | `nano-gpt/` | `NANO_GPT_API_KEY` |
| NEAR AI Cloud | `nearai/` | `NEARAI_API_KEY` |
| Nebius Token Factory | `nebius/` | `NEBIUS_API_KEY` |
| NeoSmith | `neosmith/` | `NEOSMITH_API_KEY` |
| Neuralwatt | `neuralwatt/` | `NEURALWATT_API_KEY` |
| Nova | `nova/` | `NOVA_API_KEY` |
| Novita AI | `novita-ai/` | `NOVITA_API_KEY` |
| Nvidia | `nvidia/` | `NVIDIA_API_KEY` |
| OCI Generative AI | `oci/` | `OCI_GENAI_API_KEY` |
| Ofox | `ofox/` | `OFOX_API_KEY` |
| Ollama Cloud | `ollama-cloud/` | `OLLAMA_API_KEY` |
| OpenAI | `openai/` | `OPENAI_API_KEY` |
| OpenCode | `opencode/` | `OPENCODE_API_KEY` |
| OpenCode Go | `opencode-go/` | `OPENCODE_API_KEY` |
| OpenReason | `openreason/` | `OPENREASON_API_KEY` |
| Opper | `opper/` | `OPPER_API_KEY` |
| OrcaRouter | `orcarouter/` | `ORCAROUTER_API_KEY` |
| OVHcloud AI Endpoints | `ovhcloud/` | `OVHCLOUD_API_KEY` |
| Pareto Inference | `pareto/` | `PARETO_API_KEY` |
| Pendra | `pendra/` | `PENDRA_API_KEY` |
| Perplexity | `perplexity/` | `PERPLEXITY_API_KEY` |
| Perplexity Agent | `perplexity-agent/` | `PERPLEXITY_API_KEY` |
| Pioneer | `pioneer/` | `PIONEER_API_KEY` |
| Poe | `poe/` | `POE_API_KEY` |
| Poolside | `poolside/` | `POOLSIDE_API_KEY` |
| Prime Inference | `prime/` | `PRIME_API_KEY` |
| Privatemode AI | `privatemode-ai/` | `PRIVATEMODE_API_KEY` |
| QiHang | `qihang-ai/` | `QIHANG_API_KEY` |
| Qiniu | `qiniu-ai/` | `QINIU_API_KEY` |
| Reflection | `reflection/` | `REFLECTION_API_KEY` |
| Regolo AI | `regolo-ai/` | `REGOLO_API_KEY` |
| Requesty | `requesty/` | `REQUESTY_API_KEY` |
| routing.run | `routing-run/` | `ROUTING_RUN_API_KEY` |
| RunInfra | `runinfra/` | `RUNINFRA_GATEWAY_KEY` |
| Sakana AI | `sakana/` | `SAKANA_API_KEY` |
| SambaNova | `sambanova/` | `SAMBANOVA_API_KEY` |
| Sarvam AI | `sarvam/` | `SARVAM_API_KEY` |
| Scaleway | `scaleway/` | `SCALEWAY_API_KEY` |
| SCNet Token Plan | `scnet-token-plan/` | `SCNET_API_KEY` |
| SCX.ai | `scx-ai/` | `SCX_API_KEY` |
| SenseNova (China) | `sensenova/` | `SENSENOVA_API_KEY` |
| SiliconFlow | `siliconflow/` | `SILICONFLOW_API_KEY` |
| SiliconFlow (China) | `siliconflow-cn/` | `SILICONFLOW_CN_API_KEY` |
| Snowflake Cortex | `snowflake-cortex/` | `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_CORTEX_PAT` |
| STACKIT | `stackit/` | `STACKIT_API_KEY` |
| Standard Compute | `standardcompute/` | `STANDARDCOMPUTE_API_KEY` |
| StepFun (China) | `stepfun/` | `STEPFUN_API_KEY` |
| StepFun (Global) | `stepfun-ai/` | `STEPFUN_API_KEY` |
| StepFun Step Plan (China) | `stepfun-step-plan/` | `STEPFUN_API_KEY` |
| StepFun Step Plan (Global) | `stepfun-ai-step-plan/` | `STEPFUN_API_KEY` |
| Subconscious | `subconscious/` | `SUBCONSCIOUS_API_KEY` |
| submodel | `submodel/` | `SUBMODEL_INSTAGEN_ACCESS_KEY` |
| Synthetic | `synthetic/` | `SYNTHETIC_API_KEY` |
| Tempr Gateway | `tempr/` | `TEMPR_API_KEY` |
| Tencent Coding Plan (China) | `tencent-coding-plan/` | `TENCENT_CODING_PLAN_API_KEY` |
| Tencent Token Plan | `tencent-token-plan/` | `TENCENT_TOKEN_PLAN_API_KEY` |
| Tencent TokenHub | `tencent-tokenhub/` | `TENCENT_TOKENHUB_API_KEY` |
| TensorX | `tensorx/` | `TENSORX_API_KEY` |
| The Grid AI | `the-grid-ai/` | `THEGRID_API_KEY` |
| Thinking Machines | `thinkingmachines/` | `TINKER_API_KEY` |
| Tinfoil | `tinfoil/` | `TINFOIL_API_KEY` |
| Together AI | `togetherai/` | `TOGETHER_API_KEY` |
| TokenGo | `tokengo/` | `TOKENGO_API_KEY` |
| TokenRouter | `tokenrouter/` | `TOKENROUTER_API_KEY` |
| TrustedRouter | `trustedrouter/` | `TRUSTEDROUTER_API_KEY` |
| Umans AI | `umans-ai/` | `UMANS_AI_API_KEY` |
| Umans AI Coding Plan | `umans-ai-coding-plan/` | `UMANS_AI_CODING_PLAN_API_KEY` |
| UnoRouter | `unorouter/` | `UNOROUTER_API_KEY` |
| Upstage | `upstage/` | `UPSTAGE_API_KEY` |
| Vancine | `vancine/` | `VANCINE_API_KEY` |
| Vispark | `vispark/` | `VISPARK_LAB_API_KEY` |
| Vivgrid | `vivgrid/` | `VIVGRID_API_KEY` |
| Volcengine Ark | `volcengine/` | `ARK_API_KEY` |
| Volcengine Ark Coding Plan | `volcengine-coding-plan/` | `ARK_CODING_PLAN_API_KEY` |
| Vultr | `vultr/` | `VULTR_API_KEY` |
| Wafer | `wafer.ai/` | `WAFER_API_KEY` |
| Wallaby | `wallaby/` | `WALLABY_API_KEY` |
| Wally | `wally/` | `WALLY_API_KEY` |
| xAI | `xai/` | `XAI_API_KEY` |
| Xiaomi | `xiaomi/` | `XIAOMI_API_KEY` |
| Xiaomi Token Plan (China) | `xiaomi-token-plan-cn/` | `XIAOMI_API_KEY` |
| Xiaomi Token Plan (Europe) | `xiaomi-token-plan-ams/` | `XIAOMI_API_KEY` |
| Xiaomi Token Plan (Singapore) | `xiaomi-token-plan-sgp/` | `XIAOMI_API_KEY` |
| Xpersona | `xpersona/` | `XPERSONA_API_KEY` |
| Z.AI | `zai/` | `ZHIPU_API_KEY` |
| Z.AI Coding Plan | `zai-coding-plan/` | `ZHIPU_API_KEY` |
| Zeldoc | `zeldoc/` | `ZELDOC_API_KEY` |
| Zenifra | `zenifra/` | `ZENIFRA_AI_KEY` |
| ZenMux | `zenmux/` | `ZENMUX_API_KEY` |
| Zhipu AI | `zhipuai/` | `ZHIPU_API_KEY` |
| Zhipu AI Coding Plan | `zhipuai-coding-plan/` | `ZHIPU_API_KEY` |
